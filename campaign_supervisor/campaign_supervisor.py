import os
import requests
import json
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
import logging

# Configurer les logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Charger les variables d'environnement
load_dotenv()

# Initialiser Flask avec un dossier de templates explicite
app = Flask(__name__, template_folder='templates')

# URLs des services
CAMPAIGN_ANALYST_URL = os.getenv("CAMPAIGN_ANALYST_URL", "https://analyst-production.up.railway.app")
MARKETING_AGENTS_URL = os.getenv("MARKETING_AGENTS_URL", "https://marketing-agent-production.up.railway.app")
CAMPAIGN_OPTIMIZER_URL = os.getenv("CAMPAIGN_OPTIMIZER_URL", "https://optimizer-production.up.railway.app")

@app.route('/')
def index():
    try:
        logger.info("Rendering index.html")
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error rendering index.html: {str(e)}")
        return jsonify({"error": "Failed to render index page", "details": str(e)}), 500

@app.route('/generate_campaign', methods=['POST'])
def generate_campaign():
    try:
        # Récupérer les données du formulaire
        artist = request.form.get('artist')
        style = request.form.get('style')
        song = request.form.get('song')
        lyrics = request.form.get('lyrics')
        bio = request.form.get('bio')
        
        if not artist:
            logger.error("Missing required field 'artist' in form data")
            return render_template('index.html', error="Le nom de l'artiste est requis."), 400
        
        # Étape 1 : Appeler campaign_analyst pour obtenir les tendances et artistes similaires
        logger.info(f"Sending request to campaign_analyst at {CAMPAIGN_ANALYST_URL}/analyze with data: {{'artist': {artist}, 'style': {style}}}")
        response = requests.post(f"{CAMPAIGN_ANALYST_URL}/analyze", json={"artist": artist, "style": style})
        response.raise_for_status()
        analysis_data = response.json()
        logger.info(f"Received response from campaign_analyst: {analysis_data}")
        
        # Vérifier les données de campaign_analyst
        if not isinstance(analysis_data, dict):
            logger.error(f"campaign_analyst response is not a dictionary: {analysis_data}")
            analysis_data = {"trends": ["Trend 1", "Trend 2"], "lookalike_artists": ["Artist 1", "Artist 2"], "style": style, "artist_image_url": "https://via.placeholder.com/120?text=Artist"}
        
        # Étape 2 : Appeler marketing_agents pour générer les annonces
        logger.info(f"Sending request to marketing_agents at {MARKETING_AGENTS_URL}/generate_ads with data: {{'artist': {artist}, 'genre': {style}, 'lyrics': {lyrics}, 'bio': {bio}}}")
        response = requests.post(f"{MARKETING_AGENTS_URL}/generate_ads", json={"artist": artist, "genre": style, "lyrics": lyrics, "bio": bio})
        response.raise_for_status()
        ad_data = response.json()
        logger.info(f"Received response from marketing_agents: {ad_data}")
        short_titles = ad_data.get("short_titles", [])
        long_titles = ad_data.get("long_titles", [])
        long_descriptions = ad_data.get("long_descriptions", [])
        
        # Vérifier les données de marketing_agents
        if not isinstance(short_titles, list):
            logger.error(f"short_titles is not a list: {short_titles}")
            short_titles = [{"title": "Short Title 1", "character_count": 0}]
        if not isinstance(long_titles, list):
            logger.error(f"long_titles is not a list: {long_titles}")
            long_titles = [{"title": "Long Title 1", "character_count": 0}]
        if not isinstance(long_descriptions, list):
            logger.error(f"long_descriptions is not a list: {long_descriptions}")
            long_descriptions = [{"description": "Description 1", "character_count": 0}]
        
        # Étape 3 : Appeler campaign_optimizer pour optimiser la stratégie
        logger.info(f"Sending request to campaign_optimizer at {CAMPAIGN_OPTIMIZER_URL}/optimize with data: {{'artist': {artist}}}")
        response = requests.post(f"{CAMPAIGN_OPTIMIZER_URL}/optimize", json={"artist": artist})
        response.raise_for_status()
        strategy = response.json()
        logger.info(f"Received response from campaign_optimizer: {strategy}")
        
        # Vérifier les données de campaign_optimizer
        if not isinstance(strategy, dict):
            logger.error(f"campaign_optimizer response is not a dictionary: {strategy}")
            strategy = {"target_audience": "Fans of similar artists", "channels": ["Spotify", "YouTube"], "budget_allocation": {"Spotify": 0.5, "YouTube": 0.5}}
        
        # Étape 4 : Rendre les résultats
        logger.info(f"Rendering results.html with artist={artist}, style={style}, analysis_data={analysis_data}, short_titles={short_titles}, long_titles={long_titles}, long_descriptions={long_descriptions}, strategy={strategy}")
        return render_template('results.html', artist=artist, style=style, analysis=analysis_data, short_titles=short_titles, long_titles=long_titles, long_descriptions=long_descriptions, strategy=strategy)
    except Exception as e:
        logger.error(f"Error in generate_campaign: {str(e)}")
        return jsonify({"error": "Failed to generate campaign", "details": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
