import os
import requests
import json
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import logging
import openai
from datetime import datetime, timedelta
import time
import musicbrainzngs  # Ajout pour MusicBrainz

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

# Configurer MusicBrainz
musicbrainzngs.set_useragent("BandStreamIAgent", "1.0", "https://github.com/DenisAIagent/Bandstream-AiAgent")
musicbrainzngs.set_rate_limit(limit_or_interval=1.0)  # Limite de 1 requête par seconde

# Cache pour les données de MusicBrainz (valide pendant 24 heures)
musicbrainz_cache = {}
cache_duration = timedelta(hours=24)

# Fonction pour obtenir les artistes tendance via MusicBrainz
def get_trending_artists_musicbrainz(style):
    # Vérifier si les données sont dans le cache
    cache_key = f"musicbrainz_trending_{style}"
    if cache_key in musicbrainz_cache:
        cache_entry = musicbrainz_cache[cache_key]
        if datetime.now() - cache_entry["timestamp"] < cache_duration:
            logger.info(f"Using cached MusicBrainz trending data for style: {style}")
            return cache_entry["trending_artists"]
    
    try:
        # Normaliser le style en minuscules
        normalized_style = style.lower()
        # Rechercher des artistes par tag (genre)
        result = musicbrainzngs.search_artists(query=f'tag:"{normalized_style}"', limit=10)
        trending_artists = []
        if "artist-list" in result:
            for artist in result["artist-list"]:
                if "name" in artist:
                    trending_artists.append(artist["name"])
        # Mettre en cache les données
        musicbrainz_cache[cache_key] = {
            "trending_artists": trending_artists,
            "timestamp": datetime.now()
        }
        return trending_artists
    except Exception as e:
        logger.error(f"Error fetching trending artists from MusicBrainz: {str(e)}")
        return []

# Fonction pour obtenir les artistes similaires et l’image via MusicBrainz
def get_similar_artists_musicbrainz(artist):
    lookalike_artists = []
    artist_image_url = "https://via.placeholder.com/120?text=Artist"
    
    try:
        # Rechercher l’artiste
        result = musicbrainzngs.search_artists(artist=artist, limit=1)
        if "artist-list" not in result or not result["artist-list"]:
            return lookalike_artists, artist_image_url
        
        artist_data = result["artist-list"][0]
        artist_id = artist_data["id"]
        
        # Ajouter un délai pour respecter la limite de taux (1 req/s)
        time.sleep(1.0)
        
        # Récupérer les relations de l’artiste
        relations = musicbrainzngs.get_artist_by_id(artist_id, includes=["artist-rels"])
        if "artist" in relations and "artist-relation-list" in relations["artist"]:
            for relation in relations["artist"]["artist-relation-list"]:
                if relation["type"] in ["associated with", "influenced by", "collaborates with"]:
                    if "artist" in relation and "name" in relation["artist"]:
                        lookalike_artists.append(relation["artist"]["name"])
        lookalike_artists = lookalike_artists[:10]  # Limiter à 10 artistes
        
        # Ajouter un délai pour respecter la limite de taux (1 req/s)
        time.sleep(1.0)
        
        # Récupérer une image via Cover Art Archive
        releases = musicbrainzngs.get_artist_by_id(artist_id, includes=["release-groups"])
        if "artist" in releases and "release-group-list" in releases["artist"]:
            for release_group in releases["artist"]["release-group-list"]:
                release_group_id = release_group["id"]
                try:
                    # Ajouter un délai pour respecter la limite de taux (1 req/s)
                    time.sleep(1.0)
                    cover_art = musicbrainzngs.get_release_group_image_list(release_group_id)
                    if "images" in cover_art and cover_art["images"]:
                        artist_image_url = cover_art["images"][0]["image"]
                        break
                except musicbrainzngs.ResponseError:
                    continue
        
        return lookalike_artists, artist_image_url
    except Exception as e:
        logger.error(f"Error fetching similar artists or image from MusicBrainz: {str(e)}")
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
    
    # Obtenir les artistes tendance via MusicBrainz
    musicbrainz_trending = get_trending_artists_musicbrainz(style)
    
    # Obtenir les artistes similaires et l’image via MusicBrainz
    musicbrainz_similar, artist_image_url = get_similar_artists_musicbrainz(artist)
    
    # Obtenir les tendances et artistes similaires via OpenAI
    openai_trends, openai_similar = get_trends_and_artists_openai(artist, style)
    
    # Croiser les tendances
    trends = []
    # Prioriser les tendances basées sur les artistes tendance (MusicBrainz)
    if musicbrainz_trending:
        trends.append(f"Rise of {style} artists like {musicbrainz_trending[0]}"[:50])
    if musicbrainz_trending and len(trends) < 2 and len(musicbrainz_trending) > 1:
        trends.append(f"Popularity of {style} with {musicbrainz_trending[1]}"[:50])
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
    for artist_name in musicbrainz_trending:
        if artist_name in musicbrainz_similar or artist_name in openai_similar:
            combined_artists.append(artist_name)
    for artist_name in musicbrainz_similar:
        if artist_name in openai_similar and artist_name not in combined_artists:
            combined_artists.append(artist_name)
    # Ajouter les artistes restants
    for artist_name in musicbrainz_trending + musicbrainz_similar + openai_similar:
        if artist_name not in combined_artists and len(combined_artists) < 15:
            combined_artists.append(artist_name)
    combined_artists = combined_artists[:15]  # Limiter à 15 artistes
    
    # Retourner la réponse
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
