from quart import Quart, request
import aiohttp
import musicbrainzngs
import openai
from cachetools import TTLCache
import os
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from googleapiclient.discovery import build

# Initialisation de l'application Quart
app = Quart(__name__)

# Configuration des clés API (via variables d'environnement)
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

# Configuration de Spotipy
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=os.getenv("SPOTIFY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIFY_CLIENT_SECRET")
))

# Configuration de YouTube Data API
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

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
        search_result = musicbrainzngs.search_artists(query=artist_name, limit=1)
        if not search_result['artist-list']:
            return None
        artist = search_result['artist-list'][0]
        artist_id = artist['id']
        artist_data = musicbrainzngs.get_artist_by_id(artist_id, includes=['url-rels'])
        relations = artist_data['artist'].get('relation-list', [])
        wikidata_url = None
        for relation in relations:
            if relation['type'] == 'wikidata':
                wikidata_url = relation['target']
                break
        if not wikidata_url:
            return None
        wikidata_id = wikidata_url.split('/')[-1]
        wikidata_api_url = f"https://www.wikidata.org/w/api.php?action=wbgetentities&ids={wikidata_id}&props=claims&format=json"
        async with aiohttp.ClientSession() as session:
            async with session.get(wikidata_api_url) as response:
                wikidata_data = await response.json()
        entity = wikidata_data['entities'][wikidata_id]
        claims = entity.get('claims', {})
        image_claim = claims.get('P18', [])
        if not image_claim:
            return None
        image_file = image_claim[0]['mainsnak']['datavalue']['value']
        image_file = image_file.replace(" ", "_")
        image_url = f"https://commons.wikimedia.org/wiki/Special:FilePath/{image_file}"
        return image_url
    except Exception as e:
        print(f"Erreur lors de la récupération de l'image de l'artiste {artist_name}: {e}")
        return None

async def get_song_link(artist, song):
    """Récupère le lien de streaming de la chanson via Spotipy."""
    try:
        query = f"track:{song} artist:{artist}"
        results = sp.search(q=query, type='track', limit=1)
        if results['tracks']['items']:
            track = results['tracks']['items'][0]
            return track['external_urls']['spotify']
        return "[insert link]"
    except Exception as e:
        print(f"Erreur lors de la récupération du lien de la chanson {song} de {artist}: {e}")
        return "[insert link]"

async def get_youtube_trends_and_similar_artists(artist, styles):
    """Récupère les tendances et artistes similaires via l'API YouTube Data V3, MusicBrainz, et OpenAI."""
    try:
        # Générer des requêtes "long tail" basées sur le style musical
        style = styles[0] if styles else "music"
        search_queries = [
            f"best {style} song 2025",
            f"best {style} release 2025",
            f"top {style} artists 2025",
            f"new {style} music 2025",
            f"{style} events and concerts 2025"
        ]

        trends_summary = []
        youtube_similar_artists = []

        # Étape 1 : Rechercher via YouTube Data API
        for query in search_queries:
            try:
                response = youtube.search().list(
                    q=query,
                    part="snippet",
                    maxResults=5
                ).execute()
                for item in response.get("items", []):
                    title = item["snippet"]["title"]
                    description = item["snippet"]["description"]
                    # Ajouter le titre à la liste des tendances
                    if title and title not in trends_summary:
                        trends_summary.append(title)
                    # Extraire les noms d'artistes similaires depuis le titre et la description
                    for word in (title + " " + description).split():
                        if word in artist:
                            continue
                        if word in ["best", "song", "release", "top", "artists", "new", "music", "events", "concerts", "2025"]:
                            continue
                        if len(word) > 2 and word not in youtube_similar_artists:
                            youtube_similar_artists.append(word)
            except Exception as e:
                print(f"YouTube API error for query {query}: {e}")

        # Étape 2 : Compléter avec MusicBrainz pour les artistes similaires
        musicbrainz_similar_artists = []
        try:
            cache_key = f"musicbrainz_{artist}"
            if cache_key in cache:
                musicbrainz_similar_artists = cache[cache_key]
            else:
                similar_artists = musicbrainzngs.search_artists(query=artist, limit=3)['artist-list']
                musicbrainz_similar_artists = [a['name'] for a in similar_artists if a['name'] != artist]
                cache[cache_key] = musicbrainz_similar_artists
        except Exception as e:
            print(f"MusicBrainz error: {e}")

        # Étape 3 : Enrichir avec OpenAI pour les tendances et artistes similaires
        openai_trends = []
        openai_similar_artists = []
        try:
            cache_key = f"openai_{artist}_{style}"
            if cache_key in cache:
                openai_data = cache[cache_key]
                openai_trends = openai_data.get("trends", [])
                openai_similar_artists = openai_data.get("similar_artists", [])
            else:
                prompt = f"Generate music trends and similar artists for {artist} with style {style}. Provide up to 5 trends and 5 similar artists."
                response = openai.ChatCompletion.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=150
                )
                openai_response = response.choices[0].message.content
                # Simuler le parsing (à adapter selon le format réel)
                lines = openai_response.split("\n")
                for line in lines:
                    if "Trends" in line:
                        continue
                    if "Similar Artists" in line:
                        continue
                    if line.startswith("- "):
                        item = line[2:].strip()
                        if "Trends" in lines[lines.index(line) - 1]:
                            openai_trends.append(item)
                        elif "Similar Artists" in lines[lines.index(line) - 1]:
                            if item != artist and item not in openai_similar_artists:
                                openai_similar_artists.append(item)
                cache[cache_key] = {"trends": openai_trends, "similar_artists": openai_similar_artists}
        except Exception as e:
            print(f"OpenAI error: {e}")

        # Fusionner les tendances (YouTube + OpenAI)
        all_trends = trends_summary + openai_trends
        # Supprimer les doublons et limiter à 5 tendances
        trends_summary = list(dict.fromkeys(all_trends))[:5]

        # Fusionner les artistes similaires (YouTube prioritaire, puis MusicBrainz, puis OpenAI)
        all_similar_artists = youtube_similar_artists + musicbrainz_similar_artists + openai_similar_artists
        # Supprimer les doublons et limiter à 5 artistes
        similar_artists = list(dict.fromkeys(all_similar_artists))[:5]

        return trends_summary, similar_artists

    except Exception as e:
        print(f"Erreur lors de la récupération des tendances et artistes similaires: {e}")
        return [], []

@app.route('/analyze', methods=['POST'])
async def analyze():
    # Récupérer les données du formulaire
    data = await request.get_json()
    artist = data.get('artist')
    styles = data.get('styles')
    song = data.get('song', '')  # Ajout du champ song

    if not artist or not styles:
        return {"error": "Artist and styles are required"}, 400

    # Récupérer l’image de l’artiste
    artist_image_url = await get_artist_image(artist)

    # Récupérer le lien de la chanson
    song_link = await get_song_link(artist, song) if song else "[insert link]"

    # Récupérer les tendances et artistes similaires via YouTube, MusicBrainz, et OpenAI
    trends_summary, similar_artists = await get_youtube_trends_and_similar_artists(artist, styles)

    # Retourner les résultats
    return {
        "artist": artist,
        "styles": styles,
        "song": song,
        "lookalike_artists": similar_artists,
        "trends": trends_summary,
        "artist_image_url": artist_image_url,
        "song_link": song_link
    }

# Point d'entrée pour le serveur intégré de Quart
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
