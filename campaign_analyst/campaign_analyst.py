from flask import Flask, jsonify, request
import os
import requests
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

app = Flask(__name__)

# URL de l'API Server (utiliser l'URL publique de Railway)
API_SERVER_URL = os.getenv('API_SERVER_URL', 'https://api-server-production-e858.up.railway.app')

# Clés API (à remplir avec tes clés réelles)
SERPAPI_KEY = os.getenv('SERPAPI_KEY')
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
DEEZER_ACCESS_TOKEN = os.getenv('DEEZER_ACCESS_TOKEN')

# Route pour analyser les données
@app.route('/analyze', methods=['POST'])
def analyze():
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    artist = data.get('artist')
    style = data.get('style')

    if not artist or not style:
        return jsonify({"error": "Artist and style are required"}), 400

    # Simuler une analyse (remplace ceci par une vraie logique d'analyse)
    trends = get_trends_serpapi(artist)
    lookalike_artists = get_lookalike_artists(artist)

    # Stocker les données dans api_server
    requests.post(f"{API_SERVER_URL}/store/trending_artists", json={"artists": trends})
    requests.post(f"{API_SERVER_URL}/store/lookalike_artists", json={"artists": lookalike_artists})

    return jsonify({
        "trends": trends,
        "lookalike_artists": lookalike_artists,
        "style": style
    }), 200

# Fonction pour obtenir les tendances via SerpApi (simulée)
def get_trends_serpapi(artist):
    if not SERPAPI_KEY:
        return ["Trend 1", "Trend 2"]  # Simulé
    # Logique réelle avec SerpApi ici
    return ["Trend 1", "Trend 2"]

# Fonction pour obtenir des artistes similaires (simulée)
def get_lookalike_artists(artist):
    if not (SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET and DEEZER_ACCESS_TOKEN):
        return ["Artist 1", "Artist 2"]  # Simulé
    # Logique réelle avec Spotify et Deezer ici
    return ["Artist 1", "Artist 2"]

# Route pour vérifier la santé du serveur
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "success", "message": "Campaign Analyst is running"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=True)
