import os
import requests
import json
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import logging
import openai
from datetime import datetime, timedelta

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

# Configurer RapidAPI (Billboard-API)
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
if not RAPIDAPI_KEY:
    logger.error("RAPIDAPI_KEY is not set in environment variables")
    raise ValueError("RAPIDAPI_KEY is required")

# Configurer Last.fm
LASTFM_API_KEY = os.getenv("LASTFM_API_KEY")
if not LASTFM_API_KEY:
    logger.error("LASTFM_API_KEY is not set in environment variables")
    raise ValueError("LASTFM_API_KEY is required")

# Cache pour les données de Billboard-API (valide pendant 24 heures)
billboard_cache = {}
cache_duration = timedelta(hours=24)

# Fonction pour obtenir les artistes tendance et l’image via Billboard-API
def get_trending_artists_billboard(artist, style):
    # Vérifier si les données sont dans le cache
    cache_key = f"billboard_{style}"
    if cache_key in billboard_cache:
        cache_entry = billboard_cache[cache_key]
        if datetime.now() - cache_entry["timestamp"] < cache_duration:
            logger.info(f"Using cached Billboard data for style: {style}")
            return cache_entry["trending_artists"], cache_entry["artist_image_url"]
    
    try:
        # Mapper les styles musicaux aux endpoints Billboard-API
        style_to_endpoint = {
            "chanson française": "france-songs",
            "metal": "hot-100",  # Exemple, à ajuster selon les styles
            "pop": "hot-100",
            "rock": "hot-100",
            # Ajouter d'autres styles selon les besoins
        }
        endpoint = style_to_endpoint.get(style.lower(), "hot-100")  # Par défaut, utiliser Hot 100
        
        url = f"https://billboard-api2.p.rapidapi.com/{endpoint}"
        headers = {
            "X-RapidAPI-Key": RAPIDAPI_KEY,
            "X-RapidAPI-Host": "billboard-api2.p.rapidapi.com"
        }
        params = {
            "date": "2025-03-20"  # Date actuelle ou récente
        }
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        # Extraire les artistes tendance et l’image
        trending_artists = []
        artist_image_url = "https://via.placeholder.com/120?text=Artist"
        if "content" in data:
            for entry in data["content"][:10]:  # Limiter à 10 artistes
                artist_name = entry.get("artist", "Unknown Artist")
                trending_artists.append(artist_name)
                # Récupérer l’image de l’artiste recherché (si disponible)
                if artist_name.lower() == artist.lower() and "image" in entry:
                    artist_image_url = entry["image"]
                # Si l’artiste n’est pas trouvé, utiliser l’image du premier artiste comme fallback
                elif artist_image_url == "https://via.placeholder.com/120?text=Artist" and "image" in entry:
                    artist_image_url = entry["image"]
        
        # Mettre en cache les données
        billboard_cache[cache_key] = {
            "trending_artists": trending_artists,
            "artist_image_url": artist_image_url,
            "timestamp": datetime.now()
        }
        return trending_artists, artist_image_url
    except Exception as e:
        logger.error(f"Error fetching trending artists from Billboard-API: {str(e)}")
        return [], "https://via.placeholder.com/120?text=Artist"

# Fonction pour obtenir les artistes tendance et similaires via Last.fm
def get_artists_lastfm(artist, style):
    trending_artists = []
    lookalike_artists = []
    
    try:
        # Récupérer les artistes tendance dans le style via Last.fm
        lastfm_trending_url = f"http://ws.audioscrobbler.com/2.0/?method=tag.gettopartists&tag={style}&api_key={LASTFM_API_KEY}&format=json"
        response = requests.get(lastfm_trending_url)
        response.raise_for_status()
        data = response.json()
        
        if "topartists" in data and "artist" in data["topartists"]:
            trending_artists = [trending_artist["name"] for trending_artist in data["topartists"]["artist"][:10]]
        
        # Récupérer les artistes similaires via Last.fm
        lastfm_similar_url = f"http://ws.audioscrobbler.com/2.0/?method=artist.getsimilar&artist={artist}&api_key={LASTFM_API_KEY}&format=json"
        response = requests.get(lastfm_similar_url)
        response.raise_for_status()
        data = response.json()
        
        if "similarartists" in data and "artist" in data["similarartists"]:
            lookalike_artists = [similar_artist["name"] for similar_artist in data["similarartists"]["artist"][:10]]
        
        return trending_artists, lookalike_artists
    except Exception as e:
        logger.error(f"Error fetching artists from Last.fm: {str(e)}")
        return [], []

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
    
    # Obtenir les artistes tendance et l’image via Billboard-API
    billboard_artists, artist_image_url = get_trending_artists_billboard(artist, style)
    
    # Obtenir les artistes tendance et similaires via Last.fm
    lastfm_trending, lastfm_similar = get_artists_lastfm(artist, style)
    
    # Obtenir les tendances et artistes similaires via OpenAI
    openai_trends, openai_similar = get_trends_and_artists_openai(artist, style)
    
    # Croiser les tendances
    trends = []
    # Prioriser les tendances basées sur les artistes tendance (Billboard et Last.fm)
    if billboard_artists:
        trends.append(f"Rise of {style} artists like {billboard_artists[0]}"[:50])
    if lastfm_trending and len(trends) < 2:
        trends.append(f"Popularity of {style} with {lastfm_trending[0]}"[:50])
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
    for artist_name in billboard_artists:
        if artist_name in lastfm_similar or artist_name in openai_similar:
            combined_artists.append(artist_name)
    for artist_name in lastfm_similar:
        if artist_name in openai_similar and artist_name not in combined_artists:
            combined_artists.append(artist_name)
    # Ajouter les artistes restants
    for artist_name in billboard_artists + lastfm_trending + lastfm_similar + openai_similar:
        if artist_name not in combined_artists and len(combined_artists) < 15:
            combined_artists.append(artist_name)
    combined_artists = combined_artists[:15]  # Limiter à 15 artistes
    
    # Stocker les données dans api_server
    try:
        requests.post(f"{os.getenv('API_SERVER_URL', 'https://api-server-production-e858.up.railway.app')}/store/trending_artists", json={"trends": trends})
        requests.post(f"{os.getenv('API_SERVER_URL', 'https://api-server-production-e858.up.railway.app')}/store/lookalike_artists", json={"lookalike_artists": combined_artists})
    except Exception as e:
        logger.error(f"Error storing data in api_server: {str(e)}")
        # Ne pas renvoyer une erreur 500, continuer avec la réponse
    
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
