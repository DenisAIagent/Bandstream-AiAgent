from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
import logging
import aiohttp
import asyncio
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

app = Flask(__name__)

# Configuration des logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Chargement des variables d'environnement
load_dotenv()
youtube_api_key = os.getenv("YOUTUBE_API_KEY")

if not youtube_api_key:
    logger.critical("YOUTUBE_API_KEY manquant")
    raise ValueError("YOUTUBE_API_KEY manquant")

# Initialisation de l'API YouTube
youtube = build('youtube', 'v3', developerKey=youtube_api_key)

async def fetch_data(session, url, data, retries=5):
    for attempt in range(retries):
        try:
            async with session.post(url, json=data) as response:
                response.raise_for_status()
                return await response.json()
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1}/{retries} failed for {url}: {str(e)}")
            if attempt + 1 == retries:
                raise Exception(f"Failed to call {url} after {retries} attempts: {str(e)}")
            await asyncio.sleep(2 ** attempt)

async def fetch_analysis_data(session, artist, song):
    try:
        data = {'artist': artist, 'song': song}
        return await fetch_data(session, "https://analyst-production.up.railway.app/analyze", data)
    except Exception as e:
        logger.error(f"Error fetching analysis data: {str(e)}")
        # Fallback en cas d'erreur
        return {
            'artist': artist,
            'song': song,
            'styles': ['rock'],  # Valeur par défaut
            'artist_image_url': None,
            'lookalike_artists': [],
            'trends': []
        }

def fetch_youtube_data(genre):
    try:
        # Générer des mots-clés "long tail" basés sur le genre
        long_tail_keywords = [
            f"best {genre} song 2025",
            f"best playlist {genre} 2025",
            f"top {genre} bands 2025"
        ]

        # Recherche YouTube pour identifier les artistes similaires
        search_query = f"{long_tail_keywords[0]}"
        request = youtube.search().list(
            part="snippet",
            q=search_query,
            type="video",
            maxResults=5,
            order="relevance"
        )
        response = request.execute()

        # Extraire les artistes similaires à partir des résultats
        lookalike_artists = set()
        for item in response.get('items', []):
            title = item['snippet']['title']
            description = item['snippet']['description']
            # Recherche simple d'artistes dans le titre ou la description
            for artist in ["Nirvana", "Pearl Jam", "Soundgarden", "Green Day", "The Offspring", "Blink-182", "Coldplay", "Imagine Dragons", "Maroon 5", "Metallica", "Rammstein", "Nightwish"]:
                if artist.lower() in title.lower() or artist.lower() in description.lower():
                    lookalike_artists.add(artist)
                    if len(lookalike_artists) >= 3:
                        break

        # Si moins de 3 artistes trouvés, utiliser une liste par défaut
        if len(lookalike_artists) < 3:
            lookalike_artists = ["Nirvana", "Pearl Jam", "Soundgarden"]

        return list(lookalike_artists)[:3], long_tail_keywords

    except HttpError as e:
        logger.error(f"Erreur lors de la recherche YouTube : {str(e)}")
        # Fallback en cas d'erreur (ex. quota dépassé)
        return ["Nirvana", "Pearl Jam", "Soundgarden"], [f"best {genre} song 2025", f"best playlist {genre} 2025", f"top {genre} bands 2025"]

@app.route('/optimize', methods=['POST'])
async def optimize_campaign():
    try:
        data = request.get_json()
        if not data:
            logger.error("Aucune donnée JSON fournie")
            return jsonify({"error": "Aucune donnée fournie"}), 400

        artist = data.get('artist', 'Artiste Inconnu')
        song = data.get('song', '')
        genres = data.get('genres', ['rock']) if isinstance(data.get('genres'), list) else [data.get('genres', 'rock')]

        logger.info(f"Optimizing campaign for artist: {artist}, song: {song}")

        # Récupérer les données d'analyse
        async with aiohttp.ClientSession() as session:
            analysis_data = await fetch_analysis_data(session, artist, song)

        logger.info(f"Successfully fetched data from https://analyst-production.up.railway.app/analyze: {analysis_data}")

        # Vérifier et corriger les styles si incorrects
        analysis_styles = analysis_data.get('styles', genres)
        if set(analysis_styles).isdisjoint(set(genres)):
            logger.warning(f"Styles incorrects dans analysis_data ({analysis_styles}), utilisation des genres fournis ({genres})")
            analysis_styles = genres

        # Récupérer les tendances et artistes similaires via YouTube
        lookalike_artists, trends = fetch_youtube_data(genres[0])

        # Mettre à jour les données d'analyse avec les informations correctes
        analysis_data['styles'] = genres
        analysis_data['trends'] = trends
        analysis_data['lookalike_artists'] = lookalike_artists

        # Définir la stratégie d'optimisation
        strategy = {
            "target_audience": f"Fans of {', '.join(lookalike_artists)}",
            "channels": ["Spotify", "YouTube", "Instagram"],
            "budget_allocation": {
                "Spotify": 0.4,
                "YouTube": 0.4,
                "Instagram": 0.2
            }
        }

        # Réponse finale
        response = {
            "analysis": analysis_data,
            "strategy": strategy
        }

        logger.info(f"Returning optimized campaign: {response}")
        return jsonify(response)

    except Exception as e:
        logger.error(f"Error in optimize_campaign: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
