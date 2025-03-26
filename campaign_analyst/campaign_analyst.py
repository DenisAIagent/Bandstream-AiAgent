from quart import Quart, request, jsonify
import openai
import os
from dotenv import load_dotenv
import logging
import musicbrainzngs
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import aiohttp
import asyncio
from cachetools import TTLCache

app = Quart(__name__)

# Configuration des logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Chargement des variables d'environnement
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
youtube_api_key = os.getenv("YOUTUBE_API_KEY")

# Validation des variables d'environnement
if not openai_api_key:
    logger.critical("OPENAI_API_KEY manquant")
    raise ValueError("OPENAI_API_KEY manquant")
if not youtube_api_key:
    logger.critical("YOUTUBE_API_KEY manquant")
    raise ValueError("YOUTUBE_API_KEY manquant")

# Initialisation des clients
# MusicBrainz
musicbrainzngs.set_useragent("music-analyzer", "1.0", "your-email@example.com")

# YouTube
youtube = build('youtube', 'v3', developerKey=youtube_api_key)

# Cache avec TTL de 24h
cache = TTLCache(maxsize=100, ttl=86400)

async def fetch_musicbrainz_data(artist):
    """Récupère des données sur l'artiste via MusicBrainz."""
    try:
        result = musicbrainzngs.search_artists(artist=artist, limit=1)
        artists = result.get("artist-list", [])
        if not artists:
            logger.warning(f"Aucune donnée MusicBrainz trouvée pour {artist}")
            return []

        artist_data = artists[0]
        tags = [tag["name"] for tag in artist_data.get("tag-list", []) if tag.get("name")]
        return tags

    except Exception as e:
        logger.error(f"Erreur lors de la récupération des données MusicBrainz : {str(e)}")
        return []

async def fetch_youtube_data(artist, song):
    """Récupère des données via YouTube (par exemple, popularité ou tendances)."""
    try:
        search_query = f"{artist} {song} official"
        request = youtube.search().list(
            part="snippet",
            q=search_query,
            type="video",
            maxResults=1,
            order="relevance"
        )
        response = request.execute()
        items = response.get("items", [])
        if not items:
            logger.warning(f"Aucune vidéo YouTube trouvée pour {artist} - {song}")
            return None

        video = items[0]
        video_id = video["id"]["videoId"]
        video_request = youtube.videos().list(
            part="statistics",
            id=video_id
        )
        video_response = video_request.execute()
        stats = video_response.get("items", [{}])[0].get("statistics", {})
        view_count = int(stats.get("viewCount", 0))
        return view_count

    except HttpError as e:
        logger.error(f"Erreur lors de la recherche YouTube : {str(e)}")
        return None

async def analyze_with_openai(artist, song, genres, additional_data):
    """Analyse les données avec OpenAI pour affiner les styles."""
    try:
        client = openai.OpenAI(api_key=openai_api_key)  # Initialisation sans proxies
        prompt = f"""
        Tu es un analyste musical expert. Analyse les données suivantes pour affiner les styles musicaux de l'artiste et fournir une analyse concise.

        Artiste : {artist}
        Chanson : {song}
        Genres initiaux : {', '.join(genres)}
        Données supplémentaires : {additional_data}

        Instructions :
        - Affine les genres initiaux en te basant sur les données supplémentaires (par exemple, tags MusicBrainz).
        - Si les genres initiaux sont incorrects ou trop génériques (ex. "rock" pour un artiste de metal symphonique), corrige-les.
        - Renvoie une liste de styles précis et pertinents (max 3 styles).
        - Fournis une courte explication (1-2 phrases) sur pourquoi ces styles ont été choisis.

        Format de sortie (JSON) :
        {{
          "styles": ["style1", "style2", "style3"],
          "explanation": "Explication concise."
        }}
        """
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Tu es un analyste musical."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.7
        )
        result = response.choices[0].message.content

        result_cleaned = result.strip().replace("```json\n", "").replace("\n```", "")
        try:
            result_json = eval(result_cleaned)
            return result_json.get("styles", genres), result_json.get("explanation", "Analyse basée sur les données fournies.")
        except Exception as e:
            logger.error(f"Erreur lors du parsing de la réponse OpenAI : {str(e)}")
            return genres, "Erreur lors de l'analyse OpenAI."

    except openai.APIError as e:
        logger.error(f"Erreur OpenAI : {str(e)}")
        return genres, "Erreur lors de l'analyse OpenAI."
    except Exception as e:
        logger.error(f"Erreur inattendue lors de l'analyse OpenAI : {str(e)}")
        return genres, "Erreur lors de l'analyse OpenAI."

@app.route('/analyze', methods=['POST'])
async def analyze():
    try:
        data = await request.get_json()
        if not data:
            logger.error("Aucune donnée JSON fournie")
            return jsonify({"error": "Aucune donnée fournie"}), 400

        # Validation des champs obligatoires
        required_fields = ['artist', 'song', 'genres']
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            logger.error(f"Champs manquants : {missing_fields}")
            return jsonify({"error": f"Champs manquants : {missing_fields}"}), 400

        artist = data.get('artist')
        song = data.get('song')
        genres = data.get('genres') if isinstance(data.get('genres'), list) else [data.get('genres')]

        # Clé de cache
        cache_key = f"{artist}_{song}_{'_'.join(genres)}"
        if cache_key in cache:
            logger.info(f"Réponse trouvée dans le cache pour : {cache_key}")
            return jsonify(cache[cache_key])

        # Récupérer des données supplémentaires
        tasks = [
            fetch_musicbrainz_data(artist),
            fetch_youtube_data(artist, song)
        ]
        musicbrainz_tags, youtube_views = await asyncio.gather(*tasks)

        # Combiner les données pour l'analyse
        additional_data = {
            "musicbrainz_tags": musicbrainz_tags,
            "youtube_views": youtube_views
        }

        # Analyser avec OpenAI pour affiner les styles
        refined_styles, explanation = await analyze_with_openai(artist, song, genres, additional_data)

        # Construire la réponse
        analysis_data = {
            "artist": artist,
            "song": song,
            "styles": refined_styles,
            "artist_image_url": f"https://example.com/{artist.lower().replace(' ', '-')}.jpg",
            "lookalike_artists": [],
            "trends": [],
            "analysis_explanation": explanation
        }

        # Mettre en cache
        cache[cache_key] = analysis_data
        logger.info(f"Analyse générée et mise en cache pour : {cache_key}")

        return jsonify(analysis_data), 200

    except Exception as e:
        logger.error(f"Erreur inattendue : {str(e)}")
        return jsonify({"error": f"Erreur interne : {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=8080)
