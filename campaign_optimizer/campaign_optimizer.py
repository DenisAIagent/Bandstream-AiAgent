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

@app.route('/optimize', methods=['POST'])
def optimize():
    data = request.json
    artist = data.get('artist')

    if not artist:
        return jsonify({"error": "Artist is required"}), 400

    # Récupérer les tendances et lookalikes depuis api_server
    trends_response = requests.get(f"{API_SERVER_URL}/retrieve/trending_artists?artist={artist}")
    trends_response.raise_for_status()
    trends = trends_response.json().get('data', [])

    lookalikes_response = requests.get(f"{API_SERVER_URL}/retrieve/lookalike_artists?artist={artist}")
    lookalikes_response.raise_for_status()
    lookalikes = lookalikes_response.json().get('data', [])

    # Générer une stratégie optimisée
    strategy = {
        "artist": artist,
        "promote_videos": [trend['title'] for trend in trends[:2] if 'title' in trend],
        "target_lookalikes": lookalikes
    }

    # Stocker la stratégie dans api_server
    response = requests.post(f"{API_SERVER_URL}/store/optimized_campaign", json=strategy)
    response.raise_for_status()

    return jsonify({"status": "success", "strategy": strategy}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5002))
    app.run(host='0.0.0.0', port=port, debug=True)
