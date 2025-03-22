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
from cachetools import TTLCache
from asgiref.wsgi import WsgiToAsgi  # Ajout de l’importation pour WsgiToAsgi

# Configurer les logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Log au démarrage de l'application
logger.info("Starting campaign_analyst application...")

# Charger les variables d'environnement
load_dotenv()

# Initialiser Flask
app = Flask(__name__)
logger.info("Flask application initialized.")

# Configurer OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    logger.error("OPENAI_API_KEY is not set in environment variables")
    raise ValueError("OPENAI_API_KEY is required")
logger.info("OpenAI API key loaded successfully.")

# Configurer SerpAPI
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
if not SERPAPI_KEY:
    logger.error("SERPAPI_KEY is not set in environment variables")
    raise ValueError("SERPAPI_KEY is required for search functionality")
logger.info("SerpAPI key loaded successfully.")

# Configurer MusicBrainz
musicbrainzngs.set_useragent("BandStreamIAgent", "1.0", "https://github.com/DenisAIagent/Bandstream-AiAgent")
musicbrainzngs.set_rate_limit(limit_or_interval=1.0)  # Limite de 1 requête par seconde
logger.info("MusicBrainz configured successfully.")

# Définir un timeout pour les appels à MusicBrainz (en secondes)
MUSICBRAINZ_TIMEOUT = 5

# Cache pour les données de MusicBrainz et SerpAPI (valide pendant 24 heures)
musicbrainz_cache = TTLCache(maxsize=100, ttl=24*60*60)  # Cache pour 24 heures
serpapi_cache = TTLCache(maxsize=100, ttl=24*60*60)  # Cache pour 24 heures

# Gestionnaire de timeout avec signal
def timeout_handler(signum, frame):
    logger.error("Timeout occurred in MusicBrainz API call")
    raise TimeoutError("MusicBrainz API call timed out")

# Fonction pour effectuer une recherche via SerpAPI
async def search_with_serpapi(query):
    logger.info(f"Searching SerpAPI with query: {query}")
    # Vérifier si le résultat est déjà en cache
    if query in serpapi_cache:
        logger.info(f"Using cached SerpAPI data for query: {query}")
        return serpapi_cache[query]

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
                            "ozuna", "nicky jam", "farruko", "daddy yankee", "anuel aa", "arcángel", "sech",
                            "christophe maé", "vianney", "louane", "m pokora", "patrick bruel"
                        ]
                        for artist in known_artists:
                            if artist.lower() in title or artist.lower() in snippet:
                                artists.append(artist)
                
                # Mettre en cache le résultat
                serpapi_cache[query] = list(set(artists))
                logger.info(f"Found artists from SerpAPI: {artists}")
                return list(set(artists))  # Éliminer les doublons
        except Exception as e:
            logger.error(f"Error during SerpAPI search for query '{query}': {str(e)}")
            return []

# Fonction pour rechercher les mots-clés long tail et extraire les artistes et tendances
async def search_long_tail_keywords(style):
    logger.info(f"Searching long tail keywords for style: {style}")
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

    logger.info(f"Long tail search results - Artists: {relevant_artists}, Keywords: {relevant_keywords}")
    return list(relevant_artists), relevant_keywords

# Fonction pour obtenir les artistes tendance via MusicBrainz
def get_trending_artists_musicbrainz(styles):
    logger.info(f"Fetching trending artists from MusicBrainz for styles: {styles}")
    cache_key = f"musicbrainz_trending_{'_'.join(sorted(styles))}"
    if cache_key in musicbrainz_cache:
        logger.info(f"Using cached MusicBrainz trending data for styles: {styles}")
        return musicbrainz_cache[cache_key]
    
    try:
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(MUSICBRAINZ_TIMEOUT)
        
        trending_artists = set()
        for style in styles:
            normalized_style = style.lower()
            result = musicbrainzngs.search_artists(query=f'tag:"{normalized_style}"', limit=3)  # Réduire à 3 pour limiter les appels
            if "artist-list" in result:
                for artist in result["artist-list"]:
                    if "name" in artist:
                        trending_artists.add(artist["name"])
        
        signal.alarm(0)
        
        trending_artists = list(trending_artists)[:10]  # Limiter à 10 artistes uniques
        musicbrainz_cache[cache_key] = trending_artists
        logger.info(f"Trending artists from MusicBrainz: {trending_artists}")
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
    logger.info(f"Fetching similar artists from MusicBrainz for artist: {artist}")
    cache_key = f"musicbrainz_similar_{artist}"
    if cache_key in musicbrainz_cache:
        logger.info(f"Using cached MusicBrainz similar artists and image for artist: {artist}")
        return musicbrainz_cache[cache_key]["lookalike_artists"], musicbrainz_cache[cache_key]["artist_image_url"]
    
    lookalike_artists = []
    artist_image_url = "https://via.placeholder.com/120?text=Artist"
    
    try:
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(MUSICBRAINZ_TIMEOUT)
        
        result = musicbrainzngs.search_artists(artist=artist, limit=1)
        if "artist-list" not in result or not result["artist-list"]:
            signal.alarm(0)
            logger.warning(f"No artist found in MusicBrainz for: {artist}")
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
            "artist_image_url": artist_image_url
        }
        logger.info(f"Similar artists from MusicBrainz: {lookalike_artists}, Image URL: {artist_image_url}")
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
    logger.info(f"Fetching trends and artists from OpenAI for artist: {artist}, styles: {styles}")
    try:
        styles_str = ", ".join(styles)
        prompt = f"""
        You are a music industry expert. Provide information for the following artist and genres:
        - Artist: {artist}
        - Genres: {styles_str}

        Generate the following:
        - A list of 2 current trends across the genres {styles_str} (short phrases, max 50 characters each). Focus on modern trends relevant to 2025, such as chart performance, streaming popularity, or emerging styles.
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
        
        trends = data.get("trends", ["No trends found"])
        lookalike_artists = data.get("lookalike_artists", ["No similar artists found"])
        logger.info(f"OpenAI trends: {trends}, Lookalike artists: {lookalike_artists}")
        return trends, lookalike_artists
    except Exception as e:
        logger.error(f"Error fetching trends and artists with OpenAI: {str(e)}")
        return ["Trend 1", "Trend 2"], ["Artist 1", "Artist 2"]

# Endpoint principal
@app.route('/analyze', methods=['POST'])
async def analyze():
    logger.info("Received request for /analyze endpoint")
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
    # Prioriser les tendances d'OpenAI (plus pertinentes)
    for trend in openai_trends:
        if len(trends) < 2 and trend not in trends:
            trends.append(trend)
    
    # Si OpenAI n'a pas fourni assez de tendances, utiliser MusicBrainz comme fallback
    if len(trends) < 2 and musicbrainz_trending:
        trends.append(f"Retour de {styles[0]} dans les charts"[:50])
    if len(trends) < 2 and musicbrainz_trending and len(musicbrainz_trending) > 1:
        trends.append(f"Popularité croissante de {styles[0]}"[:50])
    
    # Si aucune tendance n'est disponible, utiliser des valeurs par défaut
    if not trends:
        trends = ["Trend 1", "Trend 2"]
    trends = trends[:2]
    
    # Ajouter les mots-clés long tail aux tendances
    trends.extend(serpapi_keywords)
    logger.info(f"Combined trends: {trends}")
    
    # Étape 5 : Fusionner les artistes similaires
    combined_artists = []
    seen_artists = set()  # Pour suivre les artistes déjà ajoutés (en ignorant la casse)

    # Priorité aux artistes de campaign_optimizer
    for artist_name in optimizer_similar_artists:
        artist_lower = artist_name.lower()
        if artist_lower not in seen_artists and artist_name != artist:
            combined_artists.append(artist_name)
            seen_artists.add(artist_lower)

    # Ajouter les artistes de MusicBrainz et OpenAI
    for artist_name in musicbrainz_trending:
        artist_lower = artist_name.lower()
        if (artist_name in musicbrainz_similar or artist_name in openai_similar) and artist_lower not in seen_artists and artist_name != artist:
            combined_artists.append(artist_name)
            seen_artists.add(artist_lower)

    for artist_name in musicbrainz_similar:
        artist_lower = artist_name.lower()
        if artist_name in openai_similar and artist_lower not in seen_artists and artist_name != artist:
            combined_artists.append(artist_name)
            seen_artists.add(artist_lower)

    # Ajouter les artistes de SerpAPI
    for artist_name in serpapi_artists:
        artist_lower = artist_name.lower()
        if artist_lower not in seen_artists and artist_name != artist:
            combined_artists.append(artist_name)
            seen_artists.add(artist_lower)

    # Ajouter les autres artistes de MusicBrainz et OpenAI
    for artist_name in musicbrainz_trending + musicbrainz_similar + openai_similar:
        artist_lower = artist_name.lower()
        if artist_lower not in seen_artists and len(combined_artists) < 15 and artist_name != artist:
            combined_artists.append(artist_name)
            seen_artists.add(artist_lower)

    combined_artists = combined_artists[:15]
    logger.info(f"Combined artists: {combined_artists}")
    
    response = {
        "trends": trends,
        "lookalike_artists": combined_artists,
        "style": ", ".join(styles),
        "artist_image_url": artist_image_url
    }
    logger.info(f"Returning response: {response}")
    return jsonify(response), 200

# Endpoint de santé
@app.route('/health', methods=['GET'])
def health_check():
    logger.info("Received request for /health endpoint")
    response = {"status": "ok", "message": "Campaign Analyst is running"}
    logger.info(f"Returning health check response: {response}")
    return jsonify(response), 200

# Convertir l’application Flask (WSGI) en ASGI
asgi_app = WsgiToAsgi(app)

if __name__ == '__main__':
    import uvicorn
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Starting uvicorn on port {port}")
    # Utiliser asgi_app au lieu de app
    uvicorn.run(asgi_app, host='0.0.0.0', port=port)
