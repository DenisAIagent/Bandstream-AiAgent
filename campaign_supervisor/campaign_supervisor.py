import os
import requests
from flask import Flask, request, jsonify, render_template, redirect, url_for
from urllib.parse import quote as url_quote
from dotenv import load_dotenv
import logging

# Configurer les logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Charger les variables d'environnement
load_dotenv()

app = Flask(__name__)

# URLs des APIs (utiliser les URLs publiques de Railway)
API_SERVER_URL = os.getenv('API_SERVER_URL', 'https://api-server-production-e858.up.railway.app')
ANALYST_URL = os.getenv('ANALYST_URL', 'https://analyst-production.up.railway.app')
OPTIMIZER_URL = os.getenv('OPTIMIZER_URL', 'https://optimizer-production.up.railway.app')
MARKETING_URL = os.getenv('MARKETING_URL', 'https://marketing-agent-production.up.railway.app')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint de vérification de santé pour Railway"""
    return jsonify({"status": "ok", "message": "Campaign Supervisor is running"}), 200

@app.route('/generate_campaign', methods=['POST'])
def generate_campaign():
    artist = request.form.get('artist')
    style = request.form.get('style')
    song = request.form.get('song', '')
    lyrics = request.form.get('lyrics', '')
    bio = request.form.get('bio', '')

    if not artist or not style:
        logger.error("Artist or style missing in form data")
        return jsonify({"error": "Artist and style are required"}), 400

    # Étape 1 : Envoyer les données à campaign_analyst
    try:
        logger.info(f"Sending request to campaign_analyst at {ANALYST_URL}/analyze with data: {{'artist': {artist}, 'style': {style}}}")
        analyst_response = requests.post(f"{ANALYST_URL}/analyze", json={
            "artist": artist,
            "style": style
        })
        analyst_response.raise_for_status()
        analysis_data = analyst_response.json()
        logger.info(f"Received response from campaign_analyst: {analysis_data}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error communicating with campaign_analyst: {str(e)}")
        return jsonify({"error": "Failed to communicate with campaign_analyst", "details": str(e)}), 500

    # Étape 2 : Envoyer les données à marketing_agents
    try:
        logger.info(f"Sending request to marketing_agents at {MARKETING_URL}/generate_ads with data: {{'artist': {artist}, 'lyrics': {lyrics}, 'bio': {bio}}}")
        marketing_response = requests.post(f"{MARKETING_URL}/generate_ads", json={
            "artist": artist,
            "lyrics": lyrics,
            "bio": bio
        })
        marketing_response.raise_for_status()
        ad_drafts = marketing_response.json().get('drafts', [])
        logger.info(f"Received response from marketing_agents: {ad_drafts}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error communicating with marketing_agents: {str(e)}")
        return jsonify({"error": "Failed to communicate with marketing_agents", "details": str(e)}), 500

    # Étape 3 : Envoyer les données à campaign_optimizer
    try:
        logger.info(f"Sending request to campaign_optimizer at {OPTIMIZER_URL}/optimize with data: {{'artist': {artist}}}")
        optimizer_response = requests.post(f"{OPTIMIZER_URL}/optimize", json={
            "artist": artist
        })
        optimizer_response.raise_for_status()
        strategy = optimizer_response.json().get('strategy', {})
        logger.info(f"Received response from campaign_optimizer: {strategy}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error communicating with campaign_optimizer: {str(e)}")
        return jsonify({"error": "Failed to communicate with campaign_optimizer", "details": str(e)}), 500

    # Rendre les résultats
    try:
        logger.info(f"Rendering results.html with artist={artist}, style={style}, analysis_data={analysis_data}, ad_drafts={ad_drafts}, strategy={strategy}")
        return render_template('results.html', artist=artist, style=style, analysis=analysis_data, ad_drafts=ad_drafts, strategy=strategy)
    except Exception as e:
        logger.error(f"Error rendering results.html: {str(e)}")
        return jsonify({"error": "Failed to render results page", "details": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5004))
    app.run(host='0.0.0.0', port=port, debug=True)
