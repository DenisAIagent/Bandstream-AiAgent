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

# Fonction pour nettoyer et valider les données
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
        language = request.form.get('language', 'fr')
        tone = request.form.get('tone', 'engageant')
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
        style_display = ', '.join(styles)

        # Étape 1 : Appeler campaign_optimizer pour obtenir les termes de recherche et artistes similaires
        logger.info(f"Sending request to campaign_optimizer at {CAMPAIGN_OPTIMIZER_URL}/optimize with data: {{'artist': {artist}, 'styles': {styles}, 'language': {language}, 'tone': {tone}, 'lyrics': {lyrics}, 'bio': {bio}}}")
        response = requests.post(f"{CAMPAIGN_OPTIMIZER_URL}/optimize", json={"artist": artist, "styles": styles, "language": language, "tone": tone, "lyrics": lyrics, "bio": bio})
        response.raise_for_status()
        optimizer_data = response.json()
        logger.info(f"Received response from campaign_optimizer: {optimizer_data}")
        
        if not isinstance(optimizer_data, dict) or "youtube_description" not in optimizer_data:
            logger.error(f"campaign_optimizer response is invalid: {optimizer_data}")
            youtube_description = {
                "description": f"{artist.upper()}\n'Default Song' (clip officiel)\nExtrait de l’album : Default Album\n\n▶ Commander / Écouter : XXXX\n\nCRÉDITS:\nRéalisation: Instagram: XXXX\n\n➡️ Suivre {artist.upper()}:\nFacebook: XXXX\nInstagram: XXXX\nYoutube: XXXX\nTikTok: (rajoutez votre lien)\nSpotify: XXXX\nSite: XXXX\n\nLYRICS:\nLyrics not available",
                "search_terms": ["best metal song", "top metal bands"],
                "similar_artists": ["Slipknot", "Korn"]
            }
        else:
            youtube_description = optimizer_data.get("youtube_description", {
                "description": f"{artist.upper()}\n'Default Song' (clip officiel)\nExtrait de l’album : Default Album\n\n▶ Commander / Écouter : XXXX\n\nCRÉDITS:\nRéalisation: Instagram: XXXX\n\n➡️ Suivre {artist.upper()}:\nFacebook: XXXX\nInstagram: XXXX\nYoutube: XXXX\nTikTok: (rajoutez votre lien)\nSpotify: XXXX\nSite: XXXX\n\nLYRICS:\nLyrics not available",
                "search_terms": ["best metal song", "top metal bands"],
                "similar_artists": ["Slipknot", "Korn"]
            })
        youtube_description = sanitize_data(youtube_description)
        optimizer_similar_artists = youtube_description.get("similar_artists", ["Slipknot", "Korn"])

        # Étape 2 : Appeler campaign_analyst avec les artistes similaires de campaign_optimizer
        logger.info(f"Sending request to campaign_analyst at {CAMPAIGN_ANALYST_URL}/analyze with data: {{'artist': {artist}, 'styles': {styles}, 'optimizer_similar_artists': {optimizer_similar_artists}}}")
        response = requests.post(f"{CAMPAIGN_ANALYST_URL}/analyze", json={"artist": artist, "styles": styles, "optimizer_similar_artists": optimizer_similar_artists})
        response.raise_for_status()
        analysis_data = response.json()
        logger.info(f"Received response from campaign_analyst: {analysis_data}")
        
        if not isinstance(analysis_data, dict):
            logger.error(f"campaign_analyst response is not a dictionary: {analysis_data}")
            analysis_data = {"trends": ["Trend 1", "Trend 2"], "lookalike_artists": ["Artist 1", "Artist 2"], "style": style_display, "artist_image_url": "https://via.placeholder.com/120?text=Artist"}
        analysis_data = sanitize_data(analysis_data)
        
        # Étape 3 : Appeler marketing_agents
        logger.info(f"Sending request to marketing_agents at {MARKETING_AGENTS_URL}/generate_ads with data: {{'artist': {artist}, 'genres': {styles}, 'language': {language}, 'tone': {tone}, 'lyrics': {lyrics}, 'bio': {bio}}}")
        response = requests.post(f"{MARKETING_AGENTS_URL}/generate_ads", json={"artist": artist, "genres": styles, "language": language, "tone": tone, "lyrics": lyrics, "bio": bio})
        response.raise_for_status()
        ad_data = response.json()
        logger.info(f"Received response from marketing_agents: {ad_data}")

        short_titles = ad_data.get("short_titles", [{"title": "Short Title 1", "character_count": 13}] * 5)
        long_titles = ad_data.get("long_titles", [{"title": "Long Title 1", "character_count": 12}] * 5)
        long_descriptions = ad_data.get("long_descriptions", [{"description": "Description 1", "character_count": 13}] * 5)
        
        short_titles = sanitize_data(short_titles)
        long_titles = sanitize_data(long_titles)
        long_descriptions = sanitize_data(long_descriptions)
        
        # Étape 4 : Rendre les résultats
        logger.info(f"Rendering results.html with artist={artist}, style={style_display}, analysis_data={analysis_data}, short_titles={short_titles}, long_titles={long_titles}, long_descriptions={long_descriptions}, youtube_description={youtube_description}")
        try:
            return render_template('results.html', 
                                  artist=artist, 
                                  style=style_display,  
                                  analysis=analysis_data,
                                  short_titles=short_titles, 
                                  long_titles=long_titles, 
                                  long_descriptions=long_descriptions, 
                                  youtube_description=youtube_description)
        except Exception as e:
            logger.error(f"Error rendering template: {str(e)}")
            return render_template('error.html', 
                                  error=str(e), 
                                  artist=artist, 
                                  style=style_display), 500
    except Exception as e:
        logger.error(f"Error in generate_campaign: {str(e)}")
        return jsonify({"error": "Failed to generate campaign", "details": str(e)}), 500

@app.errorhandler(500)
def handle_500(error):
    logger.error(f"Template error: {str(error)}")
    return jsonify({"error": "Template rendering failed", "details": str(error)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
