import os
import json
import asyncio
import aiohttp
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import logging
import googleapiclient.discovery
import googleapiclient.errors
import serpapi

# Configurer les logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Charger les variables d'environnement
load_dotenv()

# Initialiser Flask
app = Flask(__name__)
logger.info("Flask application initialized.")

# URLs des services
CAMPAIGN_ANALYST_URL = os.getenv("CAMPAIGN_ANALYST_URL", "https://analyst-production.up.railway.app")

# Configurer la clé API YouTube Data v3
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
if not YOUTUBE_API_KEY:
    logger.error("YOUTUBE_API_KEY is not set in environment variables")
    raise ValueError("YOUTUBE_API_KEY is required for YouTube Data API")

# Configurer la clé API SerpAPI
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
if not SERPAPI_KEY:
    logger.error("SERPAPI_KEY is not set in environment variables")
    raise ValueError("SERPAPI_KEY is required for SerpAPI")

# Initialiser le client YouTube Data API
youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

# Fonction pour nettoyer et valider les données
def sanitize_data(data):
    """Nettoie et valide les données avant de les passer au template."""
    if isinstance(data, dict):
        return {k: sanitize_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_data(item) for item in data]
    elif isinstance(data, str):
        return data.strip().rstrip(';')
    else:
        return data

# Fonction pour effectuer une recherche sur YouTube et extraire les mots-clés long tail et les artistes
def search_youtube_for_trends_and_artists(styles):
    logger.info(f"Searching YouTube for trends and artists with styles: {styles}")
    try:
        # Créer une requête de recherche basée sur les styles
        query = f"{' '.join(styles)} 2025"
        request = youtube.search().list(
            part="snippet",
            q=query,
            type="video",
            maxResults=3,  # Limiter aux 3 premiers résultats
            order="relevance"
        )
        response = request.execute()

        # Extraire les mots-clés long tail et les artistes
        long_tail_keywords = []
        artists = []

        for item in response.get("items", []):
            title = item["snippet"]["title"]
            description = item["snippet"]["description"]
            channel_title = item["snippet"]["channelTitle"]

            # Extraire les mots-clés long tail à partir du titre
            title_lower = title.lower()
            for style in styles:
                style_lower = style.lower()
                if style_lower in title_lower:
                    # Supprimer le nom de l'artiste et le style pour isoler les mots-clés long tail
                    keyword = title_lower.replace(style_lower, "").strip()
                    # Supprimer les noms d'artistes connus pour ne garder que les mots-clés
                    known_artists = [
                        "foo fighters", "christophe maé", "various artists", "line renaud",
                        "serge lama", "michel tor", "edith piaf", "les compagnons de la chanson",
                        "bruce springsteen", "the beatles", "amir", "vianney", "louane",
                        "m pokora", "patrick bruel"
                    ]
                    for artist_name in known_artists:
                        keyword = keyword.replace(artist_name.lower(), "").strip()
                    # Nettoyer les mots-clés (supprimer les caractères spéciaux, etc.)
                    keyword = ' '.join(keyword.split()).replace('-', '').replace('  ', ' ')
                    if keyword and len(keyword) > 5 and keyword not in long_tail_keywords:  # Éviter les mots-clés trop courts ou vides
                        long_tail_keywords.append(keyword[:50])  # Limiter à 50 caractères

            # Extraire les artistes à partir du titre et du nom de la chaîne
            for artist_name in known_artists:
                if artist_name.lower() in title_lower or artist_name.lower() in channel_title.lower():
                    if artist_name not in artists:
                        artists.append(artist_name)

        logger.info(f"YouTube trends: {long_tail_keywords}, Artists: {artists}")
        return long_tail_keywords, artists

    except googleapiclient.errors.HttpError as e:
        logger.error(f"Error searching YouTube: {str(e)}")
        return [], []
    except Exception as e:
        logger.error(f"Unexpected error during YouTube search: {str(e)}")
        return [], []

# Fonction pour effectuer une recherche via SerpAPI et extraire les mots-clés long tail et les artistes
def search_serpapi_for_trends_and_artists(styles):
    logger.info(f"Searching SerpAPI for trends and artists with styles: {styles}")
    try:
        # Créer une requête de recherche basée sur les styles
        query = f"{' '.join(styles)} 2025"
        params = {
            "q": query,
            "api_key": SERPAPI_KEY,
            "num": 3  # Limiter aux 3 premiers résultats
        }
        search = serpapi.GoogleSearch(params)
        results = search.get_dict()

        # Extraire les mots-clés long tail et les artistes
        long_tail_keywords = []
        artists = []

        for result in results.get("organic_results", [])[:3]:
            title = result.get("title", "").lower()
            snippet = result.get("snippet", "").lower()

            # Extraire les mots-clés long tail à partir du titre
            for style in styles:
                style_lower = style.lower()
                if style_lower in title:
                    # Supprimer le nom de l'artiste et le style pour isoler les mots-clés long tail
                    keyword = title.replace(style_lower, "").strip()
                    # Supprimer les noms d'artistes connus pour ne garder que les mots-clés
                    known_artists = [
                        "foo fighters", "christophe maé", "various artists", "line renaud",
                        "serge lama", "michel tor", "edith piaf", "les compagnons de la chanson",
                        "bruce springsteen", "the beatles", "amir", "vianney", "louane",
                        "m pokora", "patrick bruel"
                    ]
                    for artist_name in known_artists:
                        keyword = keyword.replace(artist_name.lower(), "").strip()
                    # Nettoyer les mots-clés
                    keyword = ' '.join(keyword.split()).replace('-', '').replace('  ', ' ')
                    if keyword and len(keyword) > 5 and keyword not in long_tail_keywords:
                        long_tail_keywords.append(keyword[:50])

            # Extraire les artistes à partir du titre et du snippet
            for artist_name in known_artists:
                if artist_name.lower() in title or artist_name.lower() in snippet:
                    if artist_name not in artists:
                        artists.append(artist_name)

        logger.info(f"SerpAPI trends: {long_tail_keywords}, Artists: {artists}")
        return long_tail_keywords, artists

    except Exception as e:
        logger.error(f"Error searching SerpAPI: {str(e)}")
        return [], []

# Fonction asynchrone pour effectuer des appels HTTP
async def fetch_data(session, url, data, retries=5, delay=1):
    for attempt in range(retries):
        try:
            async with session.post(url, json=data, timeout=30) as response:
                response.raise_for_status()
                result = await response.json()
                logger.info(f"Successfully fetched data from {url}: {result}")
                return result
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.warning(f"Attempt {attempt + 1}/{retries} failed for {url}: {str(e)}")
            if attempt == retries - 1:
                logger.error(f"Failed to call {url} after {retries} attempts: {str(e)}")
                raise Exception(f"Failed to call {url} after {retries} attempts: {str(e)}. Please try again later.")
            await asyncio.sleep(delay)

@app.route('/optimize', methods=['POST'])
async def optimize():
    try:
        data = request.get_json()
        if not data or "artist" not in data or "song" not in data:
            logger.error("Missing required fields 'artist' or 'song' in request")
            return jsonify({"error": "Missing required fields 'artist' or 'song'"}), 400

        artist = data.get("artist")
        song = data.get("song")
        logger.info(f"Optimizing campaign for artist: {artist}, song: {song}")

        # Appeler campaign_analyst pour obtenir les données d'analyse
        async with aiohttp.ClientSession() as session:
            analysis_data = await fetch_data(session, f"{CAMPAIGN_ANALYST_URL}/analyze", {"artist": artist, "styles": ["chanson française", "pop"]})

        # Traiter les données d'analyse
        logger.info("Processing analysis_data")
        if not isinstance(analysis_data, dict):
            logger.error(f"campaign_analyst response is not a dictionary: {analysis_data}")
            analysis_data = {
                "trends": ["Trend 1", "Trend 2"],
                "lookalike_artists": ["Artist 1", "Artist 2"],
                "style": "chanson française, pop",
                "artist_image_url": "https://via.placeholder.com/120?text=Artist"
            }
        analysis_data = sanitize_data(analysis_data)

        # Effectuer une recherche YouTube pour obtenir des tendances et artistes similaires
        youtube_trends, youtube_artists = search_youtube_for_trends_and_artists(["chanson française", "pop"])

        # Effectuer une recherche SerpAPI pour croiser les sources
        serpapi_trends, serpapi_artists = search_serpapi_for_trends_and_artists(["chanson française", "pop"])

        # Fusionner les tendances
        trends = []
        # Prioriser les tendances YouTube
        for trend in youtube_trends:
            if len(trends) < 2 and trend not in trends:
                trends.append(trend)
        
        # Ajouter les tendances SerpAPI si nécessaire
        for trend in serpapi_trends:
            if len(trends) < 2 and trend not in trends:
                trends.append(trend)
        
        # Si YouTube et SerpAPI n'ont pas fourni assez de tendances, utiliser celles d'OpenAI (via campaign_analyst)
        for trend in analysis_data.get("trends", []):
            if len(trends) < 2 and trend not in trends:
                trends.append(trend)
        
        # Si aucune tendance n'est disponible, utiliser des valeurs par défaut
        if not trends:
            trends = ["Trend 1", "Trend 2"]
        trends = trends[:2]

        # Fusionner les artistes similaires
        lookalike_artists = []
        seen_artists = set()

        # Prioriser les artistes YouTube
        for artist_name in youtube_artists:
            artist_lower = artist_name.lower()
            if artist_lower not in seen_artists and artist_name != artist:
                lookalike_artists.append(artist_name)
                seen_artists.add(artist_lower)

        # Ajouter les artistes SerpAPI
        for artist_name in serpapi_artists:
            artist_lower = artist_name.lower()
            if artist_lower not in seen_artists and artist_name != artist:
                lookalike_artists.append(artist_name)
                seen_artists.add(artist_lower)

        # Ajouter les artistes de campaign_analyst
        for artist_name in analysis_data.get("lookalike_artists", []):
            artist_lower = artist_name.lower()
            if artist_lower not in seen_artists and artist_name != artist:
                lookalike_artists.append(artist_name)
                seen_artists.add(artist_lower)

        lookalike_artists = lookalike_artists[:15]

        # Mettre à jour les données d'analyse
        analysis_data["trends"] = trends
        analysis_data["lookalike_artists"] = lookalike_artists

        # Générer une stratégie d'optimisation (simulée pour l'instant)
        strategy = {
            "target_audience": f"Fans of {', '.join(lookalike_artists[:3])}",
            "channels": ["Spotify", "YouTube", "Instagram"],
            "budget_allocation": {"Spotify": 0.4, "YouTube": 0.4, "Instagram": 0.2}
        }

        response = {
            "strategy": strategy,
            "analysis": analysis_data
        }
        logger.info(f"Returning optimized campaign: {response}")
        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Error in optimize: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

# Endpoint de santé
@app.route('/health', methods=['GET'])
def health_check():
    logger.info("Received request for /health endpoint")
    response = {"status": "ok", "message": "Campaign Optimizer is running"}
    logger.info(f"Returning health check response: {response}")
    return jsonify(response), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
