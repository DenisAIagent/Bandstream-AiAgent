import os
import requests
import json
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import logging
import openai
from datetime import datetime, timedelta
import time
import hashlib

# Configurer les logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Charger les variables d'environnement
load_dotenv()

app = Flask(__name__)

# Configurer OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    logger.error("OPENAI_API_KEY is not set in environment variables")
    raise ValueError("OPENAI_API_KEY is required")

# Configurer Last.fm
LASTFM_API_KEY = os.getenv("LASTFM_API_KEY")
if not LASTFM_API_KEY:
    logger.error("LASTFM_API_KEY is not set in environment variables")
    raise ValueError("LASTFM_API_KEY is required")

LASTFM_SHARED_SECRET = os.getenv("LASTFM_SHARED_SECRET")
if not LASTFM_SHARED_SECRET:
    logger.error("LASTFM_SHARED_SECRET is not set in environment variables")
    raise ValueError("LASTFM_SHARED_SECRET is required")

# Cache pour les données de Last.fm (valide pendant 24 heures)
lastfm_cache = {}
cache_duration = timedelta(hours=24)

# Fonction pour générer une signature OAuth pour Last.fm
def generate_lastfm_signature(params):
    # Supprimer api_sig si présent pour éviter de l'inclure dans la signature
    params_copy = params.copy()
    if 'api_sig' in params_copy:
        del params_copy['api_sig']
    
    # Trier les paramètres par nom
    sorted_params = sorted(params_copy.items())
    
    # Construire la chaîne de signature
    signature_string = ""
    for key, value in sorted_params:
        signature_string += key + str(value)
    
    # Ajouter la clé secrète
    signature_string += LASTFM_SHARED_SECRET
    
    # Calculer le hash MD5
    return hashlib.md5(signature_string.encode('utf-8')).hexdigest()

# Fonction pour effectuer des appels à l'API Last.fm avec retry
def call_lastfm_api(method, params):
    base_url = "http://ws.audioscrobbler.com/2.0/"
    headers = {"User-Agent": "BandStreamIAgent/1.0"}
    
    # Ajouter les paramètres de base
    api_params = {
        "method": method,
        "api_key": LASTFM_API_KEY,
        "format": "json"
    }
    api_params.update(params) 
    
    # Générer la signature
    api_params["api_sig"] = generate_lastfm_signature(api_params)
    
    # Effectuer la requête avec retry
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            response = requests.get(base_url, params=api_params, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if response.status_code == 403:
                logger.error(f"Last.fm API returned 403 Forbidden: {str(e)}")
                logger.info(f"Request parameters: {api_params}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds... (Attempt {attempt+1}/{max_retries})")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Augmenter le délai exponentiellement
                else:
                    logger.error("Max retries reached, giving up.")
                    raise
            else:
                raise

# Fonction pour obtenir les artistes tendance via Last.fm
def get_trending_artists_lastfm(style):
    # Vérifier si les données sont dans le cache
    cache_key = f"lastfm_trending_{style}"
    if cache_key in lastfm_cache:
        cache_entry = lastfm_cache[cache_key]
        if datetime.now() - cache_entry["timestamp"] < cache_duration:
            logger.info(f"Using cached Last.fm trending data for style: {style}")
            return cache_entry["trending_artists"]
    
    try:
        # Récupérer les artistes tendance dans le style via Last.fm
        params = {"tag": style}
        data = call_lastfm_api("tag.getTopArtists", params)
        
        trending_artists = []
        if "topartists" in data and "artist" in data["topartists"]:
            trending_artists = [trending_artist["name"] for trending_artist in data["topartists"]["artist"][:10]]
        
        # Mettre en cache les données
        lastfm_cache[cache_key] = {
            "trending_artists": trending_artists,
            "timestamp": datetime.now()
        }
        return trending_artists
    except Exception as e:
        logger.error(f"Error fetching trending artists from Last.fm: {str(e)}")
        return []

# Fonction pour obtenir les artistes similaires et l’image via Last.fm
def get_similar_artists_lastfm(artist):
    lookalike_artists = []
    artist_image_url = "https://via.placeholder.com/120?text=Artist"
    
    try:
        # Récupérer les artistes similaires via Last.fm
        params = {"artist": artist}
        data = call_lastfm_api("artist.getSimilar", params)
        
        if "similarartists" in data and "artist" in data["similarartists"]:
            lookalike_artists = [similar_artist["name"] for similar_artist in data["similarartists"]["artist"][:10]]
        
        # Ajouter un délai pour respecter la limite de requêtes (5 req/s)
        time.sleep(5.0)  # 5 secondes de délai
        
        # Récupérer l’image de l’artiste via Last.fm
        params = {"artist": artist}
        data = call_lastfm_api("artist.getInfo", params)
        if "artist" in data and "image" in data["artist"]:
            for image in data["artist"]["image"]:
                if image["size"] == "large":
                    artist_image_url = image["#text"]
                    break
        
        return lookalike_artists, artist_image_url
    except Exception as e:
        logger.error(f"Error fetching similar artists or image from Last.fm: {str(e)}")
        return [], "https://via.placeholder.com/120?text=Artist"

# Fonction pour obtenir les tendances et artistes similaires via OpenAI
def get_trends_and_artists_openai(artist, style):
    try:
        prompt = f"""
        You are a music industry expert. Provide information for the following artist and genre:
        - Artist: {artist}
        - Genre: {style}

        Generate the following:
        - A list of 2 current trends in the {style} genre (short phrases, max 50 characters each).
        - A list of 15 trending artists in the {style} genre (just the artist names, no additional text).

        Return the response in the following JSON format:
        {{
            "trends": ["<trend1>", "<trend2>"],
            "lookalike_artists": ["<artist1>", "<artist2>", ..., "<artist15>"]
        }}
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.7
        )
        
        raw_text = response.choices[0].message.content.strip()
        logger.info(f"Raw response from OpenAI: {raw_text}")
        
        # Parser la réponse JSON
        data = json.loads(raw_text)
        
        return data.get("trends", ["No trends found"]), data.get("lookalike_artists", ["No similar artists found"])
    except Exception as e:
        logger.error(f"Error fetching trends and artists with OpenAI: {str(e)}")
        return ["Trend 1", "Trend 2"], ["Artist 1", "Artist 2"]

# Endpoint principal
@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.get_json()
    if not data or "artist" not in data or "style" not in data:
        logger.error("Missing required fields 'artist' or 'style' in request")
        return jsonify({"error": "Missing required fields 'artist' or 'style'"}), 400
    
    artist = data.get("artist")
    style = data.get("style")
    
    logger.info(f"Analyzing trends and lookalike artists for artist: {artist}, style: {style}")
    
    # Obtenir les artistes tendance via Last.fm
    lastfm_trending = get_trending_artists_lastfm(style)
    
    # Obtenir les artistes similaires et l’image via Last.fm
    lastfm_similar, artist_image_url = get_similar_artists_lastfm(artist)
    
    # Obtenir les tendances et artistes similaires via OpenAI
    openai_trends, openai_similar = get_trends_and_artists_openai(artist, style)
    
    # Croiser les tendances
    trends = []
    # Prioriser les tendances basées sur les artistes tendance (Last.fm)
    if lastfm_trending:
        trends.append(f"Rise of {style} artists like {lastfm_trending[0]}"[:50])
    if lastfm_trending and len(trends) < 2 and len(lastfm_trending) > 1:
        trends.append(f"Popularity of {style} with {lastfm_trending[1]}"[:50])
    # Compléter avec les tendances d’OpenAI si nécessaire
    for trend in openai_trends:
        if len(trends) < 2 and trend not in trends:
            trends.append(trend)
    # Fallback si aucune tendance n’est trouvée
    if not trends:
        trends = ["Trend 1", "Trend 2"]
    trends = trends[:2]  # Limiter à 2 tendances
    
    # Croiser les artistes similaires
    combined_artists = []
    # Prioriser les artistes qui apparaissent dans plusieurs sources
    for artist_name in lastfm_trending:
        if artist_name in lastfm_similar or artist_name in openai_similar:
            combined_artists.append(artist_name)
    for artist_name in lastfm_similar:
        if artist_name in openai_similar and artist_name not in combined_artists:
            combined_artists.append(artist_name)
    # Ajouter les artistes restants
    for artist_name in lastfm_trending + lastfm_similar + openai_similar:
        if artist_name not in combined_artists and len(combined_artists) < 15:
            combined_artists.append(artist_name)
    combined_artists = combined_artists[:15]  # Limiter à 15 artistes
    
    # Retourner la réponse même si certaines API échouent
    return jsonify({
        "trends": trends,
        "lookalike_artists": combined_artists,
        "style": style,
        "artist_image_url": artist_image_url
    }), 200

# Endpoint de santé
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "message": "Campaign Analyst is running"}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
