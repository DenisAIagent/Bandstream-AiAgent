import os
import requests
import json
import asyncio
import aiohttp
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import logging
import openai
from datetime import datetime, timedelta
import time
import musicbrainzngs
import signal
from asgiref.wsgi import WsgiToAsgi

# Configurer les logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Charger les variables d'environnement
load_dotenv()

# Initialiser Flask
app = Flask(__name__)

# Configurer OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    logger.error("OPENAI_API_KEY is not set in environment variables")
    raise ValueError("OPENAI_API_KEY is required")

# Configurer SerpAPI
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
if not SERPAPI_KEY:
    logger.error("SERPAPI_KEY is not set in environment variables")
    raise ValueError("SERPAPI_KEY is required for search functionality")

# Configurer MusicBrainz
musicbrainzngs.set_useragent("BandStreamIAgent", "1.0", "https://github.com/DenisAIagent/Bandstream-AiAgent")
musicbrainzngs.set_rate_limit(limit_or_interval=1.0)  # Limite de 1 requête par seconde

# Définir un timeout pour les appels à MusicBrainz (en secondes)
MUSICBRAINZ_TIMEOUT = 5

# Cache pour les données de MusicBrainz (valide pendant 24 heures)
musicbrainz_cache = {}
cache_duration = timedelta(hours=24)

# Gestionnaire de timeout avec signal
def timeout_handler(signum, frame):
    raise TimeoutError("MusicBrainz API call timed out")

# Fonction pour effectuer une recherche via SerpAPI
async def search_with_serpapi(query):
    url = "https://serpapi.com/search"
    params = {
        "q": query,
        "api_key": SERPAPI_KEY,
        "num": 10  # Limiter à 10 résultats
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params) as response:
                response.raise_for_status()
                data = await response.json()
                logger.info(f"SerpAPI response for query '{query}': {data}")
                
                # Extraire les artistes des résultats organiques
                artists = []
                if "organic_results" in data:
                    for result in data.get("organic_results", []):
                        title = result.get("title", "").lower()
                        snippet = result.get("snippet", "").lower()
                        # Rechercher des noms d'artistes connus ou des mots-clés liés à des artistes
                        known_artists = [
                            "korn", "slipknot", "octavion", "various artists", "kiss", "grabbitz", "the beatles",
                            "machine head", "riot", "rammstein", "linkin park", "marilyn manson", "disturbed",
                            "nine inch nails", "hatebreed", "converge", "terror", "knocked loose", "turnstile",
                            "code orange", "every time i die", "the ghost inside", "don omar", "wisin & yandel",
                            "sean paul", "enrique iglesias", "jennifer lopez", "j balvin", "bad bunny", "maluma",
                            "ozuna", "nicky jam", "farruko", "daddy yankee", "anuel aa", "arcángel", "sech"
                        ]
                        for artist in known_artists:
                            if artist.lower() in title or artist.lower() in snippet:
                                artists.append(artist)
                
                # Si aucun artiste n'est trouvé, retourner une liste vide
                return list(set(artists))  # Éliminer les doublons
        except Exception as e:
            logger.error(f"Error during SerpAPI search for query '{query}': {str(e)}")
            return []

# Fonction pour rechercher les mots-clés long tail et extraire les artistes et tendances
async def search_long_tail_keywords(style):
    # Exemple de mots-clés long tail basés sur le style musical
    keywords = [
        f"best {style} song 2025",
        f"top {style} artists 2025",
        f"new {style} releases 2025",
        f"best {style} bands 2025"
    ]

    relevant_artists = set()
    relevant_keywords = []

    for keyword in keywords:
        artists = await search_with_serpapi(keyword)
        if artists:  # Si des artistes sont trouvés, ajouter le mot-clé aux tendances
            relevant_artists.update(artists)
            relevant_keywords.append(keyword)

    return list(relevant_artists), relevant_keywords

# Fonction pour obtenir les artistes tendance via MusicBrainz
def get_trending_artists_musicbrainz(styles):
    cache_key = f"musicbrainz_trending_{'_'.join(sorted(styles))}"
    if cache_key in musicbrainz_cache:
        cache_entry = musicbrainz_cache[cache_key]
        if datetime.now() - cache_entry["timestamp"] < cache_duration:
            logger.info(f"Using cached MusicBrainz trending data for styles: {styles}")
            return cache_entry["trending_artists"]
    
    try:
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(MUSICBRAINZ_TIMEOUT)
        
        trending_artists = set()
        for style in styles:
            normalized_style = style.lower()
            result = musicbrainzngs.search_artists(query=f'tag:"{normalized_style}"', limit=5)
            if "artist-list" in result:
                for artist in result["artist-list"]:
                    if "name" in artist:
                        trending_artists.add(artist["name"])
        
        signal.alarm(0)
        
        trending_artists = list(trending_artists)[:10]  # Limiter à 10 artistes uniques
        musicbrainz_cache[cache_key] = {
            "trending_artists": trending_artists,
            "timestamp": datetime.now()
        }
        return trending_artists
    except TimeoutError:
        logger.error(f"Timeout fetching trending artists from MusicBrainz: {styles}")
        return []
    except (musicbrainzngs.WebServiceError, Exception) as e:
        logger.error(f"Error fetching trending artists from MusicBrainz: {str(e)}")
        return []
    finally:
        signal.alarm(0)

# Fonction pour obtenir les artistes similaires et l’image via MusicBrainz
def get_similar_artists_musicbrainz(artist):
    cache_key = f"musicbrainz_similar_{artist}"
    if cache_key in musicbrainz_cache:
        cache_entry = musicbrainz_cache[cache_key]
        if datetime.now() - cache_entry["timestamp"] < cache_duration:
            logger.info(f"Using cached MusicBrainz similar artists and image for artist: {artist}")
            return cache_entry["lookalike_artists"], cache_entry["artist_image_url"]
    
    lookalike_artists = []
    artist_image_url = "https://via.placeholder.com/120?text=Artist"
    
    try:
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(MUSICBRAINZ_TIMEOUT)
        
        result = musicbrainzngs.search_artists(artist=artist, limit=1)
        if "artist-list" not in result or not result["artist-list"]:
            signal.alarm(0)
            return lookalike_artists, artist_image_url
        
        artist_data = result["artist-list"][0]
        artist_id = artist_data["id"]
        
        signal.alarm(0)
        
        time.sleep(1.0)
        
        signal.alarm(MUSICBRAINZ_TIMEOUT)
        relations = musicbrainzngs.get_artist_by_id(artist_id, includes=["artist-rels"])
        if "artist" in relations and "artist-relation-list" in relations["artist"]:
            for relation in relations["artist"]["artist-relation-list"]:
                if relation["type"] in ["associated with", "influenced by", "collaborates with"]:
                    if "artist" in relation and "name" in relation["artist"]:
                        lookalike_artists.append(relation["artist"]["name"])
        lookalike_artists = lookalike_artists[:10]
        
        signal.alarm(0)
        
        time.sleep(1.0)
        
        signal.alarm(MUSICBRAINZ_TIMEOUT)
        releases = musicbrainzngs.get_artist_by_id(artist_id, includes=["release-groups"])
        if "artist" in releases and "release-group-list" in releases["artist"]:
            for release_group in releases["artist"]["release-group-list"]:
                release_group_id = release_group["id"]
                try:
                    time.sleep(1.0)
                    signal.alarm(MUSICBRAINZ_TIMEOUT)
                    cover_art = musicbrainzngs.get_release_group_image_list(release_group_id)
                    if "images" in cover_art and cover_art["images"]:
                        artist_image_url = cover_art["images"][0]["image"].rstrip(';').strip()
                        signal.alarm(0)
                        break
                    signal.alarm(0)
                except musicbrainzngs.ResponseError:
                    continue
        
        signal.alarm(0)
        
        musicbrainz_cache[cache_key] = {
            "lookalike_artists": lookalike_artists,
            "artist_image_url": artist_image_url,
            "timestamp": datetime.now()
        }
        
        return lookalike_artists, artist_image_url
    except TimeoutError:
        logger.error(f"Timeout fetching similar artists or image from MusicBrainz for artist: {artist}")
        return [], "https://via.placeholder.com/120?text=Artist"
    except (musicbrainzngs.WebServiceError, Exception) as e:
        logger.error(f"Error fetching similar artists or image from MusicBrainz: {str(e)}")
        return [], "https://via.placeholder.com/120?text=Artist"
    finally:
        signal.alarm(0)

# Fonction pour obtenir les tendances et artistes similaires via OpenAI
def get_trends_and_artists_openai(artist, styles):
    try:
        styles_str = ", ".join(styles)
        prompt = f"""
        You are a music industry expert. Provide information for the following artist and genres:
        - Artist: {artist}
        - Genres: {styles_str}

        Generate the following:
        - A list of 2 current trends across the genres {styles_str} (short phrases, max 50 characters each).
        - A list of 15 trending artists across the genres {styles_str} (just the artist names, no additional text).

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
        
        data = json.loads(raw_text)
        
        return data.get("trends", ["No trends found"]), data.get("lookalike_artists", ["No similar artists found"])
    except Exception as e:
        logger.error(f"Error fetching trends and artists with OpenAI: {str(e)}")
        return ["Trend 1", "Trend 2"], ["Artist 1", "Artist 2"]

# Endpoint principal
@app.route('/analyze', methods=['POST'])
async def analyze():
    data = request.get_json()
    if not data or "artist" not in data or "styles" not in data:
        logger.error("Missing required fields 'artist' or 'styles' in request")
        return jsonify({"error": "Missing required fields 'artist' or 'styles'"}), 400
    
    artist = data.get("artist")
    styles = data.get("styles", [])
    optimizer_similar_artists = data.get("optimizer_similar_artists", [])
    if not styles:
        logger.error("Styles list is empty")
        return jsonify({"error": "At least one style is required"}), 400
    
    logger.info(f"Analyzing trends and lookalike artists for artist: {artist}, styles: {styles}, optimizer_similar_artists: {optimizer_similar_artists}")
    
    # Étape 1 : Récupérer les données de MusicBrainz
    musicbrainz_trending = get_trending_artists_musicbrainz(styles)
    musicbrainz_similar, artist_image_url = get_similar_artists_musicbrainz(artist)
    
    # Étape 2 : Récupérer les données d'OpenAI
    openai_trends, openai_similar = get_trends_and_artists_openai(artist, styles)
    
    # Étape 3 : Récupérer les données via SerpAPI (mots-clés long tail)
    primary_style = styles[0].lower()
    serpapi_artists, serpapi_keywords = await search_long_tail_keywords(primary_style)
    
    # Étape 4 : Fusionner les tendances
    trends = []
    if musicbrainz_trending:
        trends.append(f"Rise of {styles[0]} artists like {musicbrainz_trending[0]}"[:50])
    if musicbrainz_trending and len(trends) < 2 and len(musicbrainz_trending) > 1:
        trends.append(f"Popularity of {styles[0]} with {musicbrainz_trending[1]}"[:50])
    for trend in openai_trends:
        if len(trends) < 2 and trend not in trends:
            trends.append(trend)
    if not trends:
        trends = ["Trend 1", "Trend 2"]
    trends = trends[:2]
    # Ajouter les mots-clés long tail aux tendances
    trends.extend(serpapi_keywords)
    
    # Étape 5 : Fusionner les artistes similaires
    combined_artists = []
    # Priorité aux artistes de campaign_optimizer
    for artist_name in optimizer_similar_artists:
        if artist_name not in combined_artists and artist_name != artist:
            combined_artists.append(artist_name)
    
    # Ajouter les artistes de MusicBrainz et OpenAI
    for artist_name in musicbrainz_trending:
        if artist_name in musicbrainz_similar or artist_name in openai_similar:
            if artist_name not in combined_artists and artist_name != artist:
                combined_artists.append(artist_name)
    for artist_name in musicbrainz_similar:
        if artist_name in openai_similar and artist_name not in combined_artists and artist_name != artist:
            combined_artists.append(artist_name)
    # Ajouter les artistes de SerpAPI
    for artist_name in serpapi_artists:
        if artist_name not in combined_artists and artist_name != artist:
            combined_artists.append(artist_name)
    # Ajouter les autres artistes de MusicBrainz et OpenAI
    for artist_name in musicbrainz_trending + musicbrainz_similar + openai_similar:
        if artist_name not in combined_artists and len(combined_artists) < 15 and artist_name != artist:
            combined_artists.append(artist_name)
    combined_artists = combined_artists[:15]
    
    return jsonify({
        "trends": trends,
        "lookalike_artists": combined_artists,
        "style": ", ".join(styles),
        "artist_image_url": artist_image_url
    }), 200

# Endpoint de santé
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "message": "Campaign Analyst is running"}), 200

# Convertir l'application Flask (WSGI) en ASGI pour uvicorn
app = WsgiToAsgi(app)

if __name__ == '__main__':
    import uvicorn
    # Récupérer le port dynamiquement via os.environ
    port = int(os.environ.get('PORT', 5000))  # Utilise 5000 comme valeur par défaut si PORT n'est pas défini
    uvicorn.run(app, host='0.0.0.0', port=port)
