import os
import logging
from quart import Quart, request, jsonify
import aiohttp
import asyncio
from cachetools import TTLCache
import musicbrainzngs
from openai import AsyncOpenAI
from serpapi import GoogleSearch
from tenacity import retry, stop_after_attempt, wait_exponential

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialisation de Quart et OpenAI
app = Quart(__name__)
openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Cache global (24h)
cache = TTLCache(maxsize=200, ttl=24*60*60)

# Clés API
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

# Configuration MusicBrainz
musicbrainzngs.set_useragent("Bandstream-AiAgent", "1.0", "your-email@example.com")

# Fonction générique pour appels API avec retry
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def fetch_api_data(session, url, params=None, cache_key=None):
    """Fonction générique pour récupérer des données avec mise en cache et retry."""
    if cache_key and cache_key in cache:
        return cache[cache_key]
    async with session.get(url, params=params) as response:
        if response.status == 200:
            data = await response.json()
            if cache_key:
                cache[cache_key] = data
            return data
        raise Exception(f"API error: {response.status}")

# Sources de données spécifiques
async def fetch_youtube_data(session, artist, styles):
    """Récupère des tendances YouTube."""
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "q": f"{artist} {' '.join(styles)}",
        "key": YOUTUBE_API_KEY,
        "maxResults": 5,
        "type": "video"
    }
    try:
        data = await fetch_api_data(session, url, params, f"yt_{artist}_{'_'.join(styles)}")
        return {"trends": [item["snippet"]["title"] for item in data.get("items", [])], "success": True}
    except Exception as e:
        logger.error(f"YouTube fetch failed: {str(e)}")
        return {"error": str(e), "success": False}

async def fetch_serpapi_data(artist, styles):
    """Récupère des tendances SerpAPI."""
    cache_key = f"serp_{artist}_{'_'.join(styles)}"
    try:
        if cache_key in cache:
            return cache[cache_key]
        search = GoogleSearch({"q": f"{artist} {' '.join(styles)} music trends 2025", "api_key": SERPAPI_KEY, "num": 5})
        results = search.get_dict()
        trends = [result.get("title", "") for result in results.get("organic_results", [])]
        cache[cache_key] = {"trends": trends, "success": True}
        return cache[cache_key]
    except Exception as e:
        logger.error(f"SerpAPI fetch failed: {str(e)}")
        return {"error": str(e), "success": False}

async def fetch_openai_data(artist, styles):
    """Génère des tendances avec OpenAI Chat API."""
    cache_key = f"oai_{artist}_{'_'.join(styles)}"
    try:
        if cache_key in cache:
            return cache[cache_key]
        prompt = f"Provide 2 short music trends (max 50 chars each) for {artist} in styles {', '.join(styles)} for 2025."
        response = await openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=60,
            temperature=0.7
        )
        trends = response.choices[0].message.content.strip().split("\n")[:2]
        cache[cache_key] = {"trends": trends, "success": True}
        return cache[cache_key]
    except Exception as e:
        logger.error(f"OpenAI fetch failed: {str(e)}")
        return {"error": str(e), "success": False}

async def fetch_musicbrainz_data(artist):
    """Récupère des artistes similaires via MusicBrainz."""
    cache_key = f"mb_{artist}"
    try:
        if cache_key in cache:
            return cache[cache_key]
        result = await asyncio.to_thread(musicbrainzngs.search_artists, query=artist, limit=1)
        if not result["artist-list"]:
            return {"lookalike_artists": [], "success": True}
        artist_id = result["artist-list"][0]["id"]
        relations = await asyncio.to_thread(musicbrainzngs.get_artist_by_id, artist_id, includes=["artist-rels"])
        similar_artists = [
            rel["artist"]["name"] for rel in relations["artist"].get("artist-relation-list", [])
            if rel["type"] == "similar"
        ][:3]
        cache[cache_key] = {"lookalike_artists": similar_artists, "success": True}
        return cache[cache_key]
    except Exception as e:
        logger.error(f"MusicBrainz fetch failed: {str(e)}")
        return {"error": str(e), "success": False}

def process_results(results):
    """Agrège les résultats des différentes sources."""
    trends = []
    lookalike_artists = []
    for result in results:
        if result.get("success"):
            trends.extend(result.get("trends", []))
            lookalike_artists.extend(result.get("lookalike_artists", []))
    return {
        "trends": list(dict.fromkeys(trends))[:5],  # Élimine les doublons et limite à 5
        "lookalike_artists": list(dict.fromkeys(lookalike_artists))[:3],  # Limite à 3
        "style": " ".join(request.json.get("styles", [])) if request.json else "unknown"
    }

@app.route("/analyze", methods=["POST"])
async def analyze():
    """Endpoint pour analyser un artiste et ses styles."""
    logger.info("Received analyze request")
    try:
        data = await request.get_json()
        if not isinstance(data, dict) or "artist" not in data or "styles" not in data or not isinstance(data["styles"], list):
            return jsonify({"error": "Invalid request: 'artist' (str) and 'styles' (list) are required"}), 400
        
        artist = data["artist"]
        styles = data["styles"]
        logger.info(f"Analyzing artist: {artist}, styles: {styles}")

        async with aiohttp.ClientSession() as session:
            tasks = [
                fetch_youtube_data(session, artist, styles),
                fetch_serpapi_data(artist, styles),
                fetch_openai_data(artist, styles),
                fetch_musicbrainz_data(artist)
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            processed_result = process_results(results)
            return jsonify(processed_result)
    except Exception as e:
        logger.error(f"Analyze endpoint failed: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@app.route("/health")
async def health_check():
    """Endpoint de vérification de santé."""
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
