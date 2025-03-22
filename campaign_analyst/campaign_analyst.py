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
        - A list of 2 current trends across the genres {styles_str} (short phrases, max 50 characters each). Focus on modern trends relevant to 2025, such as chart performanc
