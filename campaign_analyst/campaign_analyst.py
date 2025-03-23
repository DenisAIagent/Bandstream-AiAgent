import os
import logging
from quart import Quart, request, jsonify
import aiohttp
import asyncio
from cachetools import TTLCache
import musicbrainzngs
import openai
from serpapi import GoogleSearch

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialisation de Quart
app = Quart(__name__)

# Cache (24h)
musicbrainz_cache = TTLCache(maxsize=100, ttl=24*60*60)
serpapi_cache = TTLCache(maxsize=100, ttl=24*60*60)

# Clés API
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Configuration de MusicBrainz
musicbrainzngs.set_useragent("Bandstream-AiAgent", "1.0", "your-email@example.com")

# Fonctions asynchrones pour les appels aux services externes
async def fetch_youtube_data(session, artist, styles):
    """Récupère des données YouTube pour l’artiste et les styles."""
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "q": f"{artist} {' '.join(styles)}",
        "key": YOUTUBE_API_KEY,
        "maxResults": 5,
        "type": "video"
    }
    try:
        async with session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return {
                    "trends": [item["snippet"]["title"] for item in data.get("items", [])],
                    "success": True
                }
            logger.error(f"YouTube API error: {response.status}")
            return {"error": f"YouTube API error: {response.status}", "success": False}
    except Exception as e:
        logger.error(f"Exception in fetch_youtube_data: {str(e)}")
        return {"error": str(e), "success": False}

async def fetch_serpapi_data(session, artist, styles):
    """Récupère des données via SerpAPI pour des tendances liées à l’artiste."""
    try:
        if f"{artist}_{'_'.join(styles)}" in serpapi_cache:
            return serpapi_cache[f"{artist}_{'_'.join(styles)}"]
        
        search = GoogleSearch({
            "q": f"{artist} {' '.join(styles)} music trends 2025",
            "api_key": SERPAPI_KEY,
            "num": 5
        })
        results = search.get_dict()
        trends = [result.get("title", "") for result in results.get("organic_results", [])]
        serpapi_cache[f"{artist}_{'_'.join(styles)}"] = {"trends": trends, "success": True}
        return serpapi_cache[f"{artist}_{'_'.join(styles)}"]
    except Exception as e:
        logger.error(f"Exception in fetch_serpapi_data: {str(e)}")
        return {"error": str(e), "success": False}

async def fetch_openai_data(session, artist, styles):
    """Génère des données d’analyse via OpenAI."""
    try:
        openai.api_key = OPENAI_API_KEY
        prompt = f"Analyze current music trends for {artist} in the styles {', '.join(styles)}. Provide 2 short trends (max 50 characters each) relevant to 2025."
        response = await asyncio.to_thread(
            openai.Completion.create,
            model="text-davinci-003",
            prompt=prompt,
            max_tokens=60,
            temperature=0.7
        )
        trends = response.choices[0].text.strip().split("\n")[:2]
        return {"trends": trends, "success": True}
    except Exception as e:
        logger.error(f"Exception in fetch_openai_data: {str(e)}")
        return {"error": str(e), "success": False}

async def fetch_musicbrainz_data(session, artist, styles):
    """Récupère des artistes similaires via MusicBrainz."""
    try:
        if artist in musicbrainz_cache:
            return musicbrainz_cache[artist]
        
        result = await asyncio.to_thread(
            musicbrainzngs.search_artists,
            query=artist,
            limit=1
        )
        if result["artist-list"]:
            artist_id = result["artist-list"][0]["id"]
            relations = await asyncio.to_thread(
                musicbrainzngs.get_artist_by_id,
                artist_id,
                includes=["artist-rels"]
            )
            similar_artists = [
                rel["artist"]["name"]
                for rel in relations["artist"].get("artist-relation-list", [])
                if rel["type"] == "similar"
            ][:3]
            musicbrainz_cache[artist] = {"lookalike_artists": similar_artists, "success": True}
            return musicbrainz_cache[artist]
        return {"lookalike_artists": [], "success": True}
    except Exception as e:
        logger.error(f"Exception in fetch_musicbrainz_data: {str(e)}")
        return {"error": str(e), "success": False}

def process_data(youtube_data, serpapi_data, openai_data, musicbrainz_data):
    """Traite les données récupérées pour générer le résultat final."""
    trends = []
    lookalike_artists = []

    if youtube_data.get("success"):
        trends.extend(youtube_data.get("trends", []))
    if serpapi_data.get("success"):
        trends.extend(serpapi_data.get("trends", []))
    if openai_data.get("success"):
        trends.extend(openai_data.get("trends", []))
    if musicbrainz_data.get("success"):
        lookalike_artists.extend(musicbrainz_data.get("lookalike_artists", []))

    # Limiter les tendances à 5 et les artistes similaires à 3
    trends = list(set(trends))[:5]
    lookalike_artists = list(set(lookalike_artists))[:3]

    return {
        "trends": trends,
        "lookalike_artists": lookalike_artists,
        "style": " ".join(request.json.get("styles", [])) if request.json else "unknown"
    }

@app.route("/analyze", methods=["POST"])
async def analyze():
    """Endpoint pour analyser un artiste et ses styles."""
    logger.info("Received analyze request")
    try:
        data = await request.get_json()
        if not data or "artist" not in data or "styles" not in data:
            return jsonify({"error": "Missing artist or styles in request"}), 400
        
        artist = data["artist"]
        styles = data["styles"]
        logger.info(f"Analyzing artist: {artist}, styles: {styles}")

        async with aiohttp.ClientSession() as session:
            youtube_task = fetch_youtube_data(session, artist, styles)
            serpapi_task = fetch_serpapi_data(session, artist, styles)
            openai_task = fetch_openai_data(session, artist, styles)
            musicbrainz_task = fetch_musicbrainz_data(session, artist, styles)
            youtube_data, serpapi_data, openai_data, musicbrainz_data = await asyncio.gather(
                youtube_task, serpapi_task, openai_task, musicbrainz_task
            )

        result = process_data(youtube_data, serpapi_data, openai_data, musicbrainz_data)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in analyze: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route("/health")
async def health_check():
    """Endpoint de vérification de santé."""
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    port
