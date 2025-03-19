import os
import requests
from flask import Flask, request, jsonify
from urllib.parse import quote as url_quote  # Import corrigé pour url_quote
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

app = Flask(__name__)

# URLs des APIs
API_SERVER_URL = os.getenv('API_SERVER_URL', 'http://api_server:5005')
SERPAPI_KEY = os.getenv('SERPAPI_KEY')
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
DEEZER_ACCESS_TOKEN = os.getenv('DEEZER_ACCESS_TOKEN')

# Fonction pour rechercher des artistes similaires (lookalikes) via Deezer
def get_lookalike_artists_deezer(artist_name):
    try:
        url = f"https://api.deezer.com/search/artist?q={artist_name}"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if 'data' in data and len(data['data']) > 0:
            artist_id = data['data'][0]['id']
            related_url = f"https://api.deezer.com/artist/{artist_id}/related"
            related_response = requests.get(related_url)
            related_response.raise_for_status()
            related_data = related_response.json()
            return [artist['name'] for artist in related_data['data'][:3]]
        return []
    except requests.RequestException as e:
        print(f"Erreur Deezer: {e}")
        return []

# Fonction pour rechercher des tendances via SerpApi (Google Trends)
def get_trends_serpapi(artist_name):
    try:
        url = "https://serpapi.com/search"
        params = {
            "engine": "google_trends",
            "q": artist_name,
            "api_key": SERPAPI_KEY
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get('interest_over_time', {}).get('timeline_data', [])
    except requests.RequestException as e:
        print(f"Erreur SerpApi: {e}")
        return []

# Fonction pour rechercher des artistes similaires via Spotify
def get_lookalike_artists_spotify(artist_name):
    try:
        # Obtenir un token d'accès Spotify
        token_url = "https://accounts.spotify.com/api/token"
        response = requests.post(token_url, data={
            "grant_type": "client_credentials",
            "client_id": SPOTIFY_CLIENT_ID,
            "client_secret": SPOTIFY_CLIENT_SECRET
        })
        response.raise_for_status()
        token = response.json()['access_token']

        # Rechercher l'artiste
        search_url = "https://api.spotify.com/v1/search"
        headers = {"Authorization": f"Bearer {token}"}
        params = {"q": artist_name, "type": "artist", "limit": 1}
        search_response = requests.get(search_url, headers=headers, params=params)
        search_response.raise_for_status()
        artist_id = search_response.json()['artists']['items'][0]['id']

        # Obtenir des artistes similaires
        related_url = f"https://api.spotify.com/v1/artists/{artist_id}/related-artists"
        related_response = requests.get(related_url, headers=headers)
        related_response.raise_for_status()
        return [artist['name'] for artist in related_response.json()['artists'][:3]]
    except requests.RequestException as e:
        print(f"Erreur Spotify: {e}")
        return []

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.json
    artist = data.get('artist')
    style = data.get('style')

    if not artist or not style:
        return jsonify({"error": "Artist and style are required"}), 400

    # Rechercher des artistes similaires
    lookalikes_deezer = get_lookalike_artists_deezer(artist)
    lookalikes_spotify = get_lookalike_artists_spotify(artist)
    trends = get_trends_serpapi(artist)

    # Combiner les lookalikes
    lookalikes = list(set(lookalikes_deezer + lookalikes_spotify))

    # Stocker les données dans api_server
    response = requests.post(f"{API_SERVER_URL}/store/trending_artists", json={
        "artist": artist,
        "trending_artists": trends
    })
    response.raise_for_status()

    response = requests.post(f"{API_SERVER_URL}/store/lookalike_artists", json={
        "artist": artist,
        "lookalike_artists": lookalikes
    })
    response.raise_for_status()

    return jsonify({
        "artist": artist,
        "style": style,
        "lookalikes": lookalikes,
        "trends": trends
    }), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)
