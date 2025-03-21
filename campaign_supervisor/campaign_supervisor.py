import os
import requests
import json
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = Flask(__name__, template_folder='templates')
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['EXPLAIN_TEMPLATE_LOADING'] = True

CAMPAIGN_ANALYST_URL = os.getenv("CAMPAIGN_ANALYST_URL", "https://analyst-production.up.railway.app")
MARKETING_AGENTS_URL = os.getenv("MARKETING_AGENTS_URL", "https://marketing-agent-production.up.railway.app")
CAMPAIGN_OPTIMIZER_URL = os.getenv("CAMPAIGN_OPTIMIZER_URL", "https://optimizer-production.up.railway.app")

def sanitize_data(data):
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
        artist = request.form.get('artist')
        song = request.form.get('song')  # Nouveau champ
        style_input = request.form.get('style')
        language = request.form.get('language', 'fr')
        tone = request.form.get('tone', 'engageant')
        lyrics = request.form.get('lyrics')
        bio = request.form.get('bio')
        
        if not artist:
            logger.error("Missing required field 'artist' in form data")
            return render_template('index.html', error="Le nom de l'artiste est requis."), 400
        
        if not song:
            logger.error("Missing required field 'song' in form data")
            return render_template('index.html', error="Le nom de la chanson est requis."), 400
        
        if not style_input:
            logger.error("Missing required field 'style' in form data")
            return render_template('index.html', error="Le style musical est requis."), 400

        styles = [style.strip() for style in style_input.split(',')]
        style_display = ', '.join(styles)

        # Étape 1 : Appeler campaign_analyst
        logger.info(f"Sending request to campaign_analyst at {CAMPAIGN_ANALYST_URL}/analyze with data: {{'artist': {artist}, 'styles': {styles}}}")
        response = requests.post(f"{CAMPAIGN_ANALYST_URL}/analyze", json={"artist": artist, "styles": styles})
        response.raise_for_status()
        analysis_data = response.json()
        logger.info(f"Received response from campaign_analyst: {analysis_data}")
        
        if not isinstance(analysis_data, dict):
            logger.error(f"campaign_analyst response is not a dictionary: {analysis_data}")
            analysis_data = {"trends": ["Trend 1", "Trend 2"], "lookalike_artists": ["Artist 1", "Artist 2"], "style": style_display, "artist_image_url": "https://via.placeholder.com/120?text=Artist"}
        analysis_data = sanitize_data(analysis_data)
        
        # Étape 2 : Appeler marketing_agents avec le nom de la chanson
        logger.info(f"Sending request to marketing_agents at {MARKETING_AGENTS_URL}/generate_ads with data: {{'artist': {artist}, 'song': {song}, 'genres': {styles}, 'language': {language}, 'tone': {tone}, 'lyrics': {lyrics}, 'bio': {bio}}}")
        response = requests.post(f"{MARKETING_AGENTS_URL}/generate_ads", json={"artist": artist, "song": song, "genres": styles, "language": language, "tone": tone, "lyrics": lyrics, "bio": bio})
        response.raise_for_status()
        ad_data = response.json()
        logger.info(f"Received response from marketing_agents: {ad_data}")

        short_titles = ad_data.get("short_titles", [{"title": "Short Title 1", "character_count": 13}] * 5)
        long_titles = ad_data.get("long_titles", [{"title": "Long Title 1", "character_count": 12}] * 5)
        long_descriptions = ad_data.get("long_descriptions", [{"description": "Description 1", "character_count": 13}] * 5)
        
        short_titles = sanitize_data(short_titles)
        long_titles = sanitize_data(long_titles)
        long_descriptions = sanitize_data(long_descriptions)
        
        # Étape 3 : Appeler campaign_optimizer avec le nom de la chanson
        logger.info(f"Sending request to campaign_optimizer at {CAMPAIGN_OPTIMIZER_URL}/optimize with data: {{'artist': {artist}, 'song': {song}}}")
        response = requests.post(f"{CAMPAIGN_OPTIMIZER_URL}/optimize", json={"artist": artist, "song": song})
        response.raise_for_status()
        strategy_data = response.json()
        logger.info(f"Received response from campaign_optimizer: {strategy_data}")
        
        if not isinstance(strategy_data, dict) or "strategy" not in strategy_data:
            logger.error(f"campaign_optimizer response is invalid: {strategy_data}")
            strategy = {"target_audience": "Fans of similar artists", "channels": ["Spotify", "YouTube"], "budget_allocation": {"Spotify": 0.6, "YouTube": 0.4}}
        else:
            strategy = strategy_data["strategy"]
            # Vérification simple pour éviter l'erreur "invalid"
            required_keys = {"target_audience", "channels", "budget_allocation"}
            if not all(key in strategy for key in required_keys):
                logger.error(f"campaign_optimizer strategy missing required keys: {strategy}")
                strategy = {"target_audience": "Fans of similar artists", "channels": ["Spotify", "YouTube"], "budget_allocation": {"Spotify": 0.6, "YouTube": 0.4}}
        strategy = sanitize_data(strategy)
        
        # Étape 4 : Rendre les résultats avec le nom de la chanson
        logger.info(f"Rendering results.html with artist={artist}, song={song}, style={style_display}, analysis_data={analysis_data}, short_titles={short_titles}, long_titles={long_titles}, long_descriptions={long_descriptions}, strategy={strategy}")
        try:
            return render_template('results.html', 
                                  artist=artist, 
                                  song=song,  # Ajouté ici
                                  style=style_display,  
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

@app.errorhandler(500)
def handle_500(error):
    logger.error(f"Template error: {str(error)}")
    return jsonify({"error": "Template rendering failed", "details": str(error)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
