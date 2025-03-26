from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
import logging
import aiohttp
import asyncio
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import urllib.parse

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

async def fetch_analysis_data(session, artist, song, genres):
    try:
        data = {'artist': artist, 'song': song, 'genres': genres}
        return await fetch_data(session, "https://analyst-production.up.railway.app/analyze", data)
    except Exception as e:
        logger.error(f"Error fetching analysis data: {str(e)}")
        return {
            'artist': artist,
            'song': song,
            'styles': genres,
            'artist_image_url': None,
            'lookalike_artists': [],
            'trends': []
        }

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

async def fetch_chartmetric_similar_artists(session, access_token, artist_name, genre):
    genre_to_artists = {
        "rock": ["Nirvana", "Pearl Jam", "Soundgarden"],
        "punk": ["Green Day", "The Offspring", "Blink-182"],
        "grunge": ["Nirvana", "Alice in Chains", "Soundgarden"],
        "pop": ["Coldplay", "Imagine Dragons", "Maroon 5"],
        "metal": ["Metallica", "Rammstein", "Nightwish"],
        "symphonic metal": ["Nightwish", "Epica", "Within Temptation"],
        "industrial metal": ["Rammstein", "Marilyn Manson", "Nine Inch Nails"],
        "default": ["Nirvana", "Pearl Jam", "Soundgarden"]
    }

    try:
        encoded_artist_name = urllib.parse.quote(artist_name)
        search_url = f"https://api.chartmetric.com/api/artist/search?name={encoded_artist_name}"
        headers = {"Authorization": f"Bearer {access_token}"}
        async with session.get(search_url, headers=headers) as response:
            response.raise_for_status()
            result = await response.json()
            artists = result.get("obj", {}).get("artists", [])
            if not artists:
                logger.warning(f"Artiste {artist_name} non trouvé sur Chartmetric")
                return genre_to_artists.get(genre.lower(), genre_to_artists["default"])[:3]

            artist_id = artists[0].get("id")
            if not artist_id:
                logger.warning(f"ID de l'artiste {artist_name} non trouvé")
                return genre_to_artists.get(genre.lower(), genre_to_artists["default"])[:3]

        similar_url = f"https://api.chartmetric.com/api/artist/{artist_id}/similar"
        async with session.get(similar_url, headers=headers) as response:
            response.raise_for_status()
            result = await response.json()
            similar_artists = result.get("obj", [])
            if not similar_artists:
                logger.warning(f"Aucun artiste similaire trouvé pour {artist_name} sur Chartmetric")
                return genre_to_artists.get(genre.lower(), genre_to_artists["default"])[:3]

            lookalike_artists = [artist.get("name") for artist in similar_artists if artist.get("name")]
            return lookalike_artists[:3]

    except Exception as e:
        logger.error(f"Erreur lors de la récupération des artistes similaires via Chartmetric : {str(e)}")
        return genre_to_artists.get(genre.lower(), genre_to_artists["default"])[:3]

async def fetch_chartmetric_trends(session, access_token, genre):
    genre_mapping = {
        "metal symphonique": "symphonic metal",
        "metal indus": "industrial metal",
        "symphonic metal": "symphonic metal",
        "industrial metal": "industrial metal",
        "gothic metal": "gothic metal",
        "rock": "rock",
        "punk": "punk",
        "grunge": "grunge",
        "pop": "pop",
        "metal": "metal"
    }
    chartmetric_genre = genre_mapping.get(genre.lower(), "rock")
    encoded_genre = urllib.parse.quote(chartmetric_genre)

    try:
        charts_url = f"https://api.chartmetric.com/api/artist/genre/{encoded_genre}/top?limit=5"
        headers = {"Authorization": f"Bearer {access_token}"}
        async with session.get(charts_url, headers=headers) as response:
            response.raise_for_status()
            result = await response.json()
            artists = result.get("obj", [])
            if not artists:
                logger.warning(f"Aucune tendance trouvée pour le genre {genre} sur Chartmetric")
                return [f"best {genre} song 2025", f"best playlist {genre} 2025", f"top {genre} bands 2025", f"new {genre} releases 2025", f"{genre} anthems 2025"]

            trends = []
            for artist in artists:
                artist_name = artist.get("name")
                if artist_name:
                    trends.append(f"best {artist_name} songs 2025")
            return trends[:5]

    except Exception as e:
        logger.error(f"Erreur lors de la récupération des tendances via Chartmetric : {str(e)}")
        return [f"best {genre} song 2025", f"best playlist {genre} 2025", f"top {genre} bands 2025", f"new {genre} releases 2025", f"{genre} anthems 2025"]

def fetch_youtube_data(genre):
    genre_to_artists = {
        "rock": ["Nirvana", "Pearl Jam", "Soundgarden"],
        "punk": ["Green Day", "The Offspring", "Blink-182"],
        "grunge": ["Nirvana", "Alice in Chains", "Soundgarden"],
        "pop": ["Coldplay", "Imagine Dragons", "Maroon 5"],
        "metal": ["Metallica", "Rammstein", "Nightwish"],
        "symphonic metal": ["Nightwish", "Epica", "Within Temptation"],
        "industrial metal": ["Rammstein", "Marilyn Manson", "Nine Inch Nails"],
        "default": ["Nirvana", "Pearl Jam", "Soundgarden"]
    }

    long_tail_keywords = [
        f"best {genre} song 2025",
        f"best playlist {genre} 2025",
        f"top {genre} bands 2025",
        f"new {genre} releases 2025",
        f"{genre} anthems 2025"
    ]

    try:
        search_query = f"{long_tail_keywords[0]}"
        request = youtube.search().list(
            part="snippet",
            q=search_query,
            type="video",
            maxResults=5,
            order="relevance"
        )
        response = request.execute()

        lookalike_artists = set()
        genre_artists = genre_to_artists.get(genre.lower(), genre_to_artists["default"])
        for item in response.get('items', []):
            title = item['snippet']['title']
            description = item['snippet']['description']
            for artist in genre_artists:
                if artist.lower() in title.lower() or artist.lower() in description.lower():
                    lookalike_artists.add(artist)
                    if len(lookalike_artists) >= 3:
                        break

        if len(lookalike_artists) < 3:
            lookalike_artists = genre_artists[:3]

        return list(lookalike_artists)[:3], long_tail_keywords

    except HttpError as e:
        logger.error(f"Erreur lors de la recherche YouTube : {str(e)}")
        genre_artists = genre_to_artists.get(genre.lower(), genre_to_artists["default"])
        return genre_artists[:3], [f"best {genre} song 2025", f"best playlist {genre} 2025", f"top {genre} bands 2025", f"new {genre} releases 2025", f"{genre} anthems 2025"]

def combine_data(youtube_data, chartmetric_data):
    youtube_artists, youtube_trends = youtube_data
    chartmetric_artists, chartmetric_trends = chartmetric_data

    combined_artists = list(set(youtube_artists + chartmetric_artists))[:3]
    combined_trends = list(set(youtube_trends + chartmetric_trends))[:5]

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

        async with aiohttp.ClientSession() as session:
            analysis_data = await fetch_analysis_data(session, artist, song, genres)

            access_token = await get_chartmetric_access_token(session)

            refined_styles = analysis_data.get('styles', genres)
            primary_style = refined_styles[0] if refined_styles else genres[0]

            youtube_lookalikes, youtube_trends = fetch_youtube_data(primary_style)
            chartmetric_lookalikes = await fetch_chartmetric_similar_artists(session, access_token, artist, primary_style)
            chartmetric_trends = await fetch_chartmetric_trends(session, access_token, primary_style)

        combined_lookalikes, combined_trends = combine_data(
            (youtube_lookalikes, youtube_trends),
            (chartmetric_lookalikes, chartmetric_trends)
        )

        logger.info(f"Successfully fetched data from https://analyst-production.up.railway.app/analyze: {analysis_data}")

        analysis_data['trends'] = combined_trends
        analysis_data['lookalike_artists'] = combined_lookalikes

        strategy = {
            "target_audience": f"Fans of {', '.join(combined_lookalikes)}",
            "channels": ["Spotify", "YouTube", "Instagram"],
            "budget_allocation": {
                "Spotify": 0.4,
                "YouTube": 0.4,
                "Instagram": 0.2
            }
        }

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
