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
chartmetric_refresh_token = os.getenv("CHARTMETRIC_REFRESH_TOKEN")

if not youtube_api_key:
    logger.critical("YOUTUBE_API_KEY manquant")
    raise ValueError("YOUTUBE_API_KEY manquant")

if not chartmetric_refresh_token:
    logger.critical("CHARTMETRIC_REFRESH_TOKEN manquant")
    raise ValueError("CHARTMETRIC_REFRESH_TOKEN manquant")

# Initialisation de l'API YouTube
youtube = build('youtube', 'v3', developerKey=youtube_api_key)

async def fetch_data(session, url, data, retries=5):
    for attempt in range(retries):
        try:
            async with session.post(url, json=data, timeout=10) as response:
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
            'lookalike_artists': [],  # Ne pas inclure ici, car cela doit venir de l'Optimizer
            'trends': []
        }

# Fonction pour obtenir un access token Chartmetric
async def get_chartmetric_access_token(session):
    url = "https://api.chartmetric.com/api/token"
    data = {"refreshtoken": chartmetric_refresh_token}
    headers = {"Content-Type": "application/json"}

    try:
        async with session.post(url, json=data, headers=headers) as response:
            response.raise_for_status()
            result = await response.json()
            access_token = result.get("token")
            if not access_token:
                raise ValueError("Access token non trouvé dans la réponse Chartmetric")
            return access_token
    except Exception as e:
        logger.error(f"Erreur lors de l'obtention de l'access token Chartmetric : {str(e)}")
        raise

# Fonction pour récupérer des artistes similaires via Chartmetric
async def fetch_chartmetric_similar_artists(session, access_token, artist_name, genre):
    # Liste d'artistes par défaut par genre (en cas d'échec de l'API)
    genre_to_artists = {
        "rock": ["Nirvana", "Pearl Jam", "Soundgarden", "Red Hot Chili Peppers", "The Smashing Pumpkins", "Radiohead", "The White Stripes", "Arctic Monkeys", "Queens of the Stone Age", "Linkin Park"],
        "punk": ["Green Day", "The Offspring", "Blink-182", "Ramones", "Sex Pistols", "The Clash", "NOFX", "Bad Religion", "Rancid", "Sum 41"],
        "grunge": ["Nirvana", "Alice in Chains", "Soundgarden", "Pearl Jam", "Mudhoney", "Stone Temple Pilots", "Screaming Trees", "Melvins", "Tad", "L7"],
        "pop": ["Coldplay", "Imagine Dragons", "Maroon 5", "Ed Sheeran", "Taylor Swift", "Billie Eilish", "Dua Lipa", "The Weeknd", "Ariana Grande", "Shawn Mendes"],
        "metal": ["Metallica", "Rammstein", "Nightwish", "Iron Maiden", "Slayer", "Pantera", "Megadeth", "Judas Priest", "Black Sabbath", "Slipknot"],
        "metal symphonique": ["Nightwish", "Epica", "Within Temptation", "Evanescence", "Lacuna Coil", "Delain", "Amaranthe", "Tarja", "Symphony X", "Kamelot"],
        "metal indus": ["Rammstein", "Marilyn Manson", "Nine Inch Nails", "Ministry", "KMFDM", "Rob Zombie", "Static-X", "Fear Factory", "Godflesh", "White Zombie"],
        "default": ["Nirvana", "Pearl Jam", "Soundgarden"]
    }

    try:
        # Étape 1 : Rechercher l'artiste pour obtenir son ID Chartmetric
        search_url = f"https://api.chartmetric.com/api/artist/search?query={artist_name}"
        headers = {"Authorization": f"Bearer {access_token}"}
        async with session.get(search_url, headers=headers) as response:
            response.raise_for_status()
            result = await response.json()
            artists = result.get("artists", [])
            if not artists:
                logger.warning(f"Artiste {artist_name} non trouvé sur Chartmetric")
                return genre_to_artists.get(genre.lower(), genre_to_artists["default"])[:3]

            # Prendre le premier artiste correspondant
            artist_id = artists[0].get("id")
            if not artist_id:
                logger.warning(f"ID de l'artiste {artist_name} non trouvé")
                return genre_to_artists.get(genre.lower(), genre_to_artists["default"])[:3]

        # Étape 2 : Récupérer les artistes similaires
        similar_url = f"https://api.chartmetric.com/api/artist/{artist_id}/similar"
        async with session.get(similar_url, headers=headers) as response:
            response.raise_for_status()
            result = await response.json()
            similar_artists = result.get("similar_artists", [])
            if not similar_artists:
                logger.warning(f"Aucun artiste similaire trouvé pour {artist_name} sur Chartmetric")
                return genre_to_artists.get(genre.lower(), genre_to_artists["default"])[:3]

            # Extraire les noms des artistes similaires
            lookalike_artists = [artist.get("name") for artist in similar_artists if artist.get("name")]
            return lookalike_artists[:3]

    except Exception as e:
        logger.error(f"Erreur lors de la récupération des artistes similaires via Chartmetric : {str(e)}")
        return genre_to_artists.get(genre.lower(), genre_to_artists["default"])[:3]

# Fonction pour récupérer des tendances via Chartmetric
async def fetch_chartmetric_trends(session, access_token, genre):
    try:
        # Récupérer les artistes populaires dans le genre
        charts_url = f"https://api.chartmetric.com/api/charts/artists?genre={genre}&limit=5"
        headers = {"Authorization": f"Bearer {access_token}"}
        async with session.get(charts_url, headers=headers) as response:
            response.raise_for_status()
            result = await response.json()
            artists = result.get("artists", [])
            if not artists:
                logger.warning(f"Aucune tendance trouvée pour le genre {genre} sur Chartmetric")
                return [f"best {genre} song 2025", f"best playlist {genre} 2025", f"top {genre} bands 2025", f"new {genre} releases 2025", f"{genre} anthems 2025"]

            # Générer des tendances basées sur les artistes populaires
            trends = []
            for artist in artists:
                artist_name = artist.get("name")
                if artist_name:
                    trends.append(f"best {artist_name} songs 2025")
            return trends[:5]

    except Exception as e:
        logger.error(f"Erreur lors de la récupération des tendances via Chartmetric : {str(e)}")
        return [f"best {genre} song 2025", f"best playlist {genre} 2025", f"top {genre} bands 2025", f"new {genre} releases 2025", f"{genre} anthems 2025"]

# Fonction pour récupérer des artistes similaires via YouTube
def fetch_youtube_data(genre):
    try:
        # Définir des artistes similaires par genre
        genre_to_artists = {
            "rock": ["Nirvana", "Pearl Jam", "Soundgarden", "Red Hot Chili Peppers", "The Smashing Pumpkins", "Radiohead", "The White Stripes", "Arctic Monkeys", "Queens of the Stone Age", "Linkin Park"],
            "punk": ["Green Day", "The Offspring", "Blink-182", "Ramones", "Sex Pistols", "The Clash", "NOFX", "Bad Religion", "Rancid", "Sum 41"],
            "grunge": ["Nirvana", "Alice in Chains", "Soundgarden", "Pearl Jam", "Mudhoney", "Stone Temple Pilots", "Screaming Trees", "Melvins", "Tad", "L7"],
            "pop": ["Coldplay", "Imagine Dragons", "Maroon 5", "Ed Sheeran", "Taylor Swift", "Billie Eilish", "Dua Lipa", "The Weeknd", "Ariana Grande", "Shawn Mendes"],
            "metal": ["Metallica", "Rammstein", "Nightwish", "Iron Maiden", "Slayer", "Pantera", "Megadeth", "Judas Priest", "Black Sabbath", "Slipknot"],
            "metal symphonique": ["Nightwish", "Epica", "Within Temptation", "Evanescence", "Lacuna Coil", "Delain", "Amaranthe", "Tarja", "Symphony X", "Kamelot"],
            "metal indus": ["Rammstein", "Marilyn Manson", "Nine Inch Nails", "Ministry", "KMFDM", "Rob Zombie", "Static-X", "Fear Factory", "Godflesh", "White Zombie"],
            "default": ["Nirvana", "Pearl Jam", "Soundgarden"]
        }

        # Générer des mots-clés "long tail" basés sur le genre
        long_tail_keywords = [
            f"best {genre} song 2025",
            f"best playlist {genre} 2025",
            f"top {genre} bands 2025",
            f"new {genre} releases 2025",
            f"{genre} anthems 2025"
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
        genre_artists = genre_to_artists.get(genre.lower(), genre_to_artists["default"])
        for item in response.get('items', []):
            title = item['snippet']['title']
            description = item['snippet']['description']
            # Recherche d'artistes dans le titre ou la description
            for artist in genre_artists:
                if artist.lower() in title.lower() or artist.lower() in description.lower():
                    lookalike_artists.add(artist)
                    if len(lookalike_artists) >= 3:
                        break

        # Si moins de 3 artistes trouvés, utiliser la liste par défaut pour ce genre
        if len(lookalike_artists) < 3:
            lookalike_artists = genre_artists[:3]

        return list(lookalike_artists)[:3], long_tail_keywords

    except HttpError as e:
        logger.error(f"Erreur lors de la recherche YouTube : {str(e)}")
        # Fallback en cas d'erreur (ex. quota dépassé)
        genre_artists = genre_to_artists.get(genre.lower(), genre_to_artists["default"])
        return genre_artists[:3], [f"best {genre} song 2025", f"best playlist {genre} 2025", f"top {genre} bands 2025", f"new {genre} releases 2025", f"{genre} anthems 2025"]

# Fonction pour combiner les données de YouTube et Chartmetric
def combine_data(youtube_data, chartmetric_data):
    # Combiner les lookalike_artists
    youtube_artists, youtube_trends = youtube_data
    chartmetric_artists, chartmetric_trends = chartmetric_data

    # Fusionner les artistes similaires (en évitant les doublons)
    combined_artists = list(set(youtube_artists + chartmetric_artists))
    # Limiter à 3 artistes pour éviter une liste trop longue
    combined_artists = combined_artists[:3]

    # Fusionner les tendances (en évitant les doublons)
    combined_trends = list(set(youtube_trends + chartmetric_trends))
    # Limiter à 5 tendances pour éviter une liste trop longue
    combined_trends = combined_trends[:5]

    return combined_artists, combined_trends

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
            # Récupérer les données de l'Analyst
            analysis_data = await fetch_analysis_data(session, artist, song)

            # Obtenir l'access token Chartmetric
            access_token = await get_chartmetric_access_token(session)

            # Récupérer les données de YouTube
            youtube_lookalikes, youtube_trends = fetch_youtube_data(genres[0])

            # Récupérer les données de Chartmetric
            chartmetric_lookalikes = await fetch_chartmetric_similar_artists(session, access_token, artist, genres[0])
            chartmetric_trends = await fetch_chartmetric_trends(session, access_token, genres[0])

        # Combiner les données de YouTube et Chartmetric
        combined_lookalikes, combined_trends = combine_data(
            (youtube_lookalikes, youtube_trends),
            (chartmetric_lookalikes, chartmetric_trends)
        )

        logger.info(f"Successfully fetched data from https://analyst-production.up.railway.app/analyze: {analysis_data}")

        # Vérifier et corriger les styles si incorrects
        analysis_styles = analysis_data.get('styles', genres)
        if set(analysis_styles).isdisjoint(set(genres)):
            logger.warning(f"Styles incorrects dans analysis_data ({analysis_styles}), utilisation des genres fournis ({genres})")
            analysis_styles = genres

        # Mettre à jour les données d'analyse avec les informations correctes
        analysis_data['styles'] = genres
        analysis_data['trends'] = combined_trends
        analysis_data['lookalike_artists'] = combined_lookalikes

        # Définir la stratégie d'optimisation
        strategy = {
            "target_audience": f"Fans of {', '.join(combined_lookalikes)}",
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
