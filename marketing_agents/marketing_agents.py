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

@app.route('/generate_ads', methods=['POST'])
def generate_ads():
    data = request.json
    artist = data.get('artist')
    lyrics = data.get('lyrics', '')
    bio = data.get('bio', '')

    if not artist:
        return jsonify({"error": "Artist is required"}), 400

    # Récupérer les lookalikes depuis api_server
    lookalikes_response = requests.get(f"{API_SERVER_URL}/retrieve/lookalike_artists?artist={artist}")
    lookalikes_response.raise_for_status()
    lookalikes = lookalikes_response.json().get('data', [])

    # Générer des drafts d'annonces
    drafts = [
        {
            "title": f"Ne manquez pas {artist}",
            "title_long": f"Fans de {lookalikes[0] if lookalikes else 'Chanson française'} Ne manquez pas {artist}",
            "description": "Evenement unique Decouvrez {artist} en concert 2025"
        },
        {
            "title": "Chanson française Dernière chance",
            "title_long": f"{artist} Chanson française Dernière chance",
            "description": f"Rejoignez les fans de {lookalikes[1] if len(lookalikes) > 1 else 'Chanson française'} et découvrez {artist}"
        },
        {
            "title": f"Fans de {lookalikes[0] if lookalikes else 'Chanson française'}",
            "title_long": f"Vous aimez {lookalikes[0] if lookalikes else 'Chanson française'} Découvrez {artist}",
            "description": f"Evenement unique {artist} le nouveau phénomène Chanson française"
        },
        {
            "title": f"Places limitées {artist}",
            "title_long": f"Jean j en ai {artist} Réservez maintenant",
            "description": f"Comme {artist} va vous surprendre"
        }
    ]

    # Stocker les drafts dans api_server
    response = requests.post(f"{API_SERVER_URL}/store/ad_drafts", json={
        "artist": artist,
        "drafts": drafts
    })
    response.raise_for_status()

    return jsonify({"status": "success", "drafts": drafts}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5003))
    app.run(host='0.0.0.0', port=port, debug=True)
