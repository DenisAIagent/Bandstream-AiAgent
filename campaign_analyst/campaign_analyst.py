from quart import Quart, request
import aiohttp
import musicbrainzngs
import serpapi
import openai
from cachetools import TTLCache

# Initialisation de l'application Quart
app = Quart(__name__)

# Configuration des clés API (via variables d'environnement)
import os
from dotenv import load_dotenv
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
SERPAPI_KEY = os.getenv("SERPAPI_KEY")

# Configuration de MusicBrainz
musicbrainzngs.set_useragent("bandstream-ai-agent", "0.1", "your-email@example.com")

# Cache pour les résultats (24h)
cache = TTLCache(maxsize=100, ttl=86400)

@app.route('/analyze', methods=['POST'])
async def analyze():
    # Récupérer les données du formulaire
    data = await request.get_json()
    artist = data.get('artist')
    styles = data.get('styles')

    if not artist or not styles:
        return {"error": "Artist and styles are required"}, 400

    # 1. Recherche d'artistes similaires via MusicBrainz
    try:
        cache_key = f"musicbrainz_{artist}"
        if cache_key in cache:
            similar_artist_names = cache[cache_key]
        else:
            similar_artists = musicbrainzngs.search_artists(query=artist, limit=3)['artist-list']
            similar_artist_names = [a['name'] for a in similar_artists]
            cache[cache_key] = similar_artist_names
    except Exception as e:
        similar_artist_names = []
        print(f"MusicBrainz error: {e}")

    # 2. Extraction de tendances via SerpAPI
    try:
        cache_key = f"serpapi_{artist}"
        if cache_key in cache:
            trends_summary = cache[cache_key]
        else:
            params = {"q": f"{artist} music trends", "api_key": SERPAPI_KEY}
            async with aiohttp.ClientSession() as session:
                async with session.get("https://serpapi.com/search", params=params) as response:
                    serp_data = await response.json()
                    trends = serp_data.get("organic_results", [])[:3]
                    trends_summary = [result.get("title") for result in trends]
                    cache[cache_key] = trends_summary
    except Exception as e:
        trends_summary = []
        print(f"SerpAPI error: {e}")

    # 3. Génération de tendances via OpenAI
    try:
        cache_key = f"openai_{artist}_{styles}"
        if cache_key in cache:
            openai_trends = cache[cache_key]
        else:
            prompt = f"Generate music trends and similar artists for {artist} with styles {styles}."
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150
            )
            openai_trends = response.choices[0].message.content
            cache[cache_key] = openai_trends
    except Exception as e:
        openai_trends = ""
        print(f"OpenAI error: {e}")

    # Retourner les résultats
    return {
        "artist": artist,
        "styles": styles,
        "similar_artists": similar_artist_names,
        "trends": trends_summary,
        "openai_trends": openai_trends
    }

# Point d'entrée pour Hypercorn
if __name__ == "__main__":
    app.run()
