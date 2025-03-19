import os
import requests
from flask import Flask, request, jsonify, render_template, redirect, url_for
from urllib.parse import quote as url_quote  # Import corrigé pour url_quote
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

app = Flask(__name__)

# URLs des APIs
API_SERVER_URL = os.getenv('API_SERVER_URL', 'http://api_server:5005')
ANALYST_URL = os.getenv('ANALYST_URL', 'http://campaign_analyst:5001')
OPTIMIZER_URL = os.getenv('OPTIMIZER_URL', 'http://campaign_optimizer:5002')
MARKETING_URL = os.getenv('MARKETING_URL', 'http://marketing_agents:5003')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/generate_campaign', methods=['POST'])
def generate_campaign():
    artist = request.form.get('artist')
    style = request.form.get('style')
    song = request.form.get('song', '')
    lyrics = request.form.get('lyrics', '')
    bio = request.form.get('bio', '')

    if not artist or not style:
        return jsonify({"error": "Artist and style are required"}), 400

    # Étape 1 : Envoyer les données à campaign_analyst
    analyst_response = requests.post(f"{ANALYST_URL}/analyze", json={
        "artist": artist,
        "style": style
    })
    analyst_response.raise_for_status()
    analysis_data = analyst_response.json()

    # Étape 2 : Envoyer les données à marketing_agents
    marketing_response = requests.post(f"{MARKETING_URL}/generate_ads", json={
        "artist": artist,
        "lyrics": lyrics,
        "bio": bio
    })
    marketing_response.raise_for_status()
    ad_drafts = marketing_response.json().get('drafts', [])

    # Étape 3 : Envoyer les données à campaign_optimizer
    optimizer_response = requests.post(f"{OPTIMIZER_URL}/optimize", json={
        "artist": artist
    })
    optimizer_response.raise_for_status()
    strategy = optimizer_response.json().get('strategy', {})

    # Rendre les résultats
    return render_template('results.html', artist=artist, style=style, analysis=analysis_data, ad_drafts=ad_drafts, strategy=strategy)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5004))
    app.run(host='0.0.0.0', port=port, debug=True)
