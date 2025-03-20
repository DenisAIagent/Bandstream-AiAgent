from flask import Flask, jsonify, request
import os
import requests
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

app = Flask(__name__)

# URL de l'API Server (utiliser l'URL publique de Railway)
API_SERVER_URL = os.getenv('API_SERVER_URL', 'https://api-server-production-e858.up.railway.app')

# Route pour générer des annonces
@app.route('/generate_ads', methods=['POST'])
def generate_ads():
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    artist = data.get('artist')
    lyrics = data.get('lyrics', '')
    bio = data.get('bio', '')

    if not artist:
        return jsonify({"error": "Artist is required"}), 400

    # Simuler la génération d'annonces (remplace ceci par une vraie logique de génération)
    drafts = [
        {
            "title": f"Discover {artist} - New Single Out Now!",
            "content": f"Check out the latest single from {artist}. {bio}",
            "platform": "Instagram"
        },
        {
            "title": f"{artist} - Feel the Beat!",
            "content": f"Listen to {artist}'s new track with these amazing lyrics: {lyrics[:50]}...",
            "platform": "YouTube"
        }
    ]

    # Stocker les données dans api_server
    requests.post(f"{API_SERVER_URL}/store/ad_draft", json={"drafts": drafts})

    return jsonify({"drafts": drafts}), 200

# Route pour vérifier la santé du serveur
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "success", "message": "Marketing Agents is running"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5003))
    app.run(host="0.0.0.0", port=port, debug=True)
