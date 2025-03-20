from flask import Flask, jsonify, request
import os
import requests
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

app = Flask(__name__)

# URL de l'API Server (utiliser l'URL publique de Railway)
API_SERVER_URL = os.getenv('API_SERVER_URL', 'https://api-server-production-e858.up.railway.app')

# Route pour optimiser une campagne
@app.route('/optimize', methods=['POST'])
def optimize():
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    artist = data.get('artist')

    if not artist:
        return jsonify({"error": "Artist is required"}), 400

    # Simuler une optimisation (remplace ceci par une vraie logique d'optimisation)
    strategy = {
        "artist": artist,
        "target_audience": "Fans of similar artists",
        "channels": ["Spotify", "YouTube"],
        "budget_allocation": {"Spotify": 0.6, "YouTube": 0.4}
    }

    # Stocker les données dans api_server
    requests.post(f"{API_SERVER_URL}/store/optimized_campaign", json={"campaign": strategy})

    return jsonify({"strategy": strategy}), 200

# Route pour vérifier la santé du serveur
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "success", "message": "Campaign Optimizer is running"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5002))
    app.run(host="0.0.0.0", port=port, debug=True)
