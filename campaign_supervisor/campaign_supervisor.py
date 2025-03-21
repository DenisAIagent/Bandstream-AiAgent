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

# Activer le mode de débogage pour les templates
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['EXPLAIN_TEMPLATE_LOADING'] = True

# URLs des services
CAMPAIGN_ANALYST_URL = os.getenv("CAMPAIGN_ANALYST_URL", "https://analyst-production.up.railway.app")
MARKETING_AGENTS_URL = os.getenv("MARKETING_AGENTS_URL", "https://marketing-agent-production.up.railway.app")
CAMPAIGN_OPTIMIZER_URL = os.getenv("CAMPAIGN_OPTIMIZER_URL", "https://optimizer-production.up.railway.app")

# Fonction pour nettoyer et valider les données avant de les passer au template
def sanitize_data(data):
    """Nettoie et valide les données avant de les passer au template."""
    if isinstance(data, dict):
        return {k: sanitize_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_data(item) for item in data]
    elif isinstance(data, str):
        return data.strip().rstrip(';')
    else:
        return data

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
        style_input = request.form.get('style')
        song = request.form.get('song')
        lyrics = request.form.get('lyrics')
        bio = request.form.get('bio')
        
        if not artist:
            logger.error("Missing required field 'artist' in form data")
            return render_template('index.html', error="Le nom de l'artiste est requis."), 400
        
        if not style_input:
            logger.error("Missing required field 'style' in form data")
            return render_template('index.html', error="Le style musical est requis."), 400

        # Splitter les styles musicaux en une liste
        styles = [style.strip() for style in style_input.split(',')]
        # Joindre les styles pour l'affichage dans results.html
        style_display = ', '.join(styles)

        # Étape 1 : Appeler campaign_analyst pour obtenir les tendances et artistes similaires
        logger.info(f"Sending request to campaign_analyst at {CAMPAIGN_ANALYST_URL}/analyze with data: {{'artist': {artist}, 'styles': {styles}}}")
        response = requests.post(f"{CAMPAIGN_ANALYST_URL}/analyze", json={"artist": artist, "styles": styles})
        response.raise_for_status()
        analysis_data = response.json()
        logger.info(f"Received response from campaign_analyst: {analysis_data}")
        
        # Vérifier les données de campaign_analyst
        if not isinstance(analysis_data, dict):
            logger.error(f"campaign_analyst response is not a dictionary: {analysis_data}")
            analysis_data = {"trends": ["Trend 1", "Trend 2"], "lookalike_artists": ["Artist 1", "Artist 2"], "style": style_display, "artist_image_url": "https://via.placeholder.com/120?text=Artist"}
        
        # Nettoyer les données de campaign_analyst
        analysis_data = sanitize_data(analysis_data)
        
        # Étape 2 : Appeler marketing_agents pour générer les annonces
        logger.info(f"Sending request to marketing_agents at {MARKETING_AGENTS_URL}/generate_ads with data: {{'artist': {artist}, 'genres': {styles}, 'lyrics': {lyrics}, 'bio': {bio}}}")
        response = requests.post(f"{MARKETING_AGENTS_URL}/generate_ads", json={"artist": artist, "genres": styles, "lyrics": lyrics, "bio": bio})
        response.raise_for_status()
        ad_data = response.json()
        logger.info(f"Received response from marketing_agents: {ad_data}")

        # Adaptation du format de données
        short_titles = []
        long_titles = []
        long_descriptions = []

        if "drafts" in ad_data:
            drafts = ad_data.get("drafts", [])
            short_titles = drafts[:5] if len(drafts) >= 5 else drafts
            long_titles = drafts[5:10] if len(drafts) >= 10 else drafts[5:] if len(drafts) >= 5 else []
            long_descriptions = ["Description par défaut" for _ in range(5)]
        else:
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
        
        # Nettoyer les données de marketing_agents
        short_titles = sanitize_data(short_titles)
        long_titles = sanitize_data(long_titles)
        long_descriptions = sanitize_data(long_descriptions)
        
        # Étape 3 : Appeler campaign_optimizer pour optimiser la stratégie
        logger.info(f"Sending request to campaign_optimizer at {CAMPAIGN_OPTIMIZER_URL}/optimize with data: {{'artist': {artist}}}")
        response = requests.post(f"{CAMPAIGN_OPTIMIZER_URL}/optimize", json={"artist": artist})
        response.raise_for_status()
        strategy_data = response.json()
        logger.info(f"Received response from campaign_optimizer: {strategy_data}")
        
        # Vérifier les données de campaign_optimizer et extraire la sous-clé "strategy"
        if not isinstance(strategy_data, dict):
            logger.error(f"campaign_optimizer response is not a dictionary: {strategy_data}")
            strategy = {"target_audience": "Fans of similar artists", "channels": ["Spotify", "YouTube"], "budget_allocation": {"Spotify": 0.5, "YouTube": 0.5}}
        else:
            strategy = strategy_data.get("strategy", {"target_audience": "Fans of similar artists", "channels": ["Spotify", "YouTube"], "budget_allocation": {"Spotify": 0.5, "YouTube": 0.5}})
            if not isinstance(strategy, dict):
                logger.error(f"strategy is not a dictionary: {strategy}")
                strategy = {"target_audience": "Fans of similar artists", "channels": ["Spotify", "YouTube"], "budget_allocation": {"Spotify": 0.5, "YouTube": 0.5}}
        
        # Nettoyer les données de campaign_optimizer
        strategy = sanitize_data(strategy)
        
        # Étape 4 : Rendre les résultats
        logger.info(f"Rendering results.html with artist={artist}, style={style_display}, analysis_data={analysis_data}, short_titles={short_titles}, long_titles={long_titles}, long_descriptions={long_descriptions}, strategy={strategy}")
        try:
            return render_template('results.html', 
                                  artist=artist, 
                                  style=style_display,  # Utiliser la version affichable des styles
                                  analysis=analysis_data,
                                  short_titles=short_titles, 
                                  long_titles=long_titles, 
                                  long_descriptions=long_descriptions, 
                                  strategy=strategy)
        except Exception as e:
            logger.error(f"Error rendering template: {str(e)}")
            return render_template('error.html', 
                                  error=str(e), 
                                  artist=artist, 
                                  style=style_display), 500
    except Exception as e:
        logger.error(f"Error in generate_campaign: {str(e)}")
        return jsonify({"error": "Failed to generate campaign", "details": str(e)}), 500

# Gestion des erreurs 500
@app.errorhandler(500)
def handle_500(error):
    logger.error(f"Template error: {str(error)}")
    return jsonify({"error": "Template rendering failed", "details": str(error)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
