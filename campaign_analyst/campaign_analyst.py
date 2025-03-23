from quart import Quart, request
import aiohttp
import musicbrainzngs
import serpapi
import openai
from cachetools import TTLCache
import os
from dotenv import load_dotenv
import requests  # Ajout pour les appels à Wikidata

# Initialisation de l'application Quart
app = Quart(__name__)

# Configuration des clés API (via variables d'environnement)
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
SERPAPI_KEY = os.getenv("SERPAPI_KEY")

# Configuration de MusicBrainz
musicbrainzngs.set_useragent(
    os.getenv("MUSICBRAINZ_APP_NAME", "bandstream-ai-agent"),
    os.getenv("MUSICBRAINZ_APP_VERSION", "0.1"),
    os.getenv("MUSICBRAINZ_CONTACT_EMAIL", "your-email@example.com")
)

# Cache pour les résultats (24h)
cache = TTLCache(maxsize=100, ttl=86400)

async def get_artist_image(artist_name):
    """Récupère une image de l'artiste via MusicBrainz et Wikidata."""
    try:
        # Étape 1 : Rechercher l’artiste principal pour obtenir son MBID
        search_result = musicbrainzngs.search_artists(query=artist_name, limit=1)
        if not search_result['artist-list']:
            return None
        artist = search_result['artist-list'][0]
        artist_id = artist['id']

        # Étape 2 : Obtenir les relations de l’artiste (notamment Wikidata)
        artist_data = musicbrainzngs.get_artist_by_id(artist_id, includes=['url-rels'])
        relations = artist_data['artist'].get('relation-list', [])

        # Étape 3 : Chercher un lien Wikidata
        wikidata_url = None
        for relation in relations:
            if relation['type'] == 'wikidata':
                wikidata_url = relation['target']
                break

        if not wikidata_url:
            return None

        # Étape 4 : Extraire l’ID Wikidata (ex. https://www.wikidata.org/wiki/Q123 -> Q123)
        wikidata_id = wikidata_url.split('/')[-1]

        # Étape 5 : Appeler l’API Wikidata pour obtenir l’image
        wikidata_api_url = f"https://www.wikidata.org/w/api.php?action=wbgetentities&ids={wikidata_id}&props=claims&format=json"
        async with aiohttp.ClientSession() as session:
            async with session.get(wikidata_api_url) as response:
                wikidata_data = await response.json()

        # Étape 6 : Chercher la propriété P18 (image)
        entity = wikidata_data['entities'][wikidata_id]
        claims = entity.get('claims', {})
        image_claim = claims.get('P18', [])
        if not image_claim:
            return None

        # Étape 7 : Extraire le nom du fichier image (ex. "File:Artist.jpg")
        image_file = image_claim[0]['mainsnak']['datavalue']['value']
        # Convertir le nom du fichier en URL d’image via Wikimedia Commons
        image_file = image_file.replace(" ", "_")
        image_url = f"https://commons.wikimedia.org/wiki/Special:FilePath/{image_file}"

        return image_url

    except Exception as e:
        print(f"Erreur lors de la récupération de l'image de l'artiste {artist_name}: {e}")
        return None

@app.route('/analyze', methods=['POST'])
async def analyze():
    # Récupérer les données du formulaire
    data = await request.get_json()
    artist = data.get('artist')
    styles = data.get('styles')

    if not artist or not styles:
        return {"error": "Artist and styles are required"}, 400

    # Récupérer l’image de l’artiste
    artist_image = await get_artist_image(artist)

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

    # Retourner les résultats, incluant l’URL de l’image
    return {
        "artist": artist,
        "styles": styles,
        "similar_artists": similar_artist_names,
        "trends": trends_summary,
        "openai_trends": openai_trends,
        "artist_image": artist_image  # Ajout de l’URL de l’image
    }

# Point d'entrée pour Hypercorn
if __name__ == "__main__":
    app.run()
