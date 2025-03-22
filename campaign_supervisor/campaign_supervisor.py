import os
import requests
import json
import asyncio
import aiohttp
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
import logging
import time
from requests.exceptions import RequestException
from asgiref.wsgi import WsgiToAsgi

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

# Fonction asynchrone pour effectuer des appels HTTP
async def fetch_data(session, url, data, retries=3, timeout=15):
    for attempt in range(retries):
        try:
            async with session.post(url, json=data, timeout=timeout) as response:
                response.raise_for_status()
                return await response.json()
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.warning(f"Attempt {attempt + 1}/{retries} failed for {url}: {str(e)}")
            if attempt == retries - 1:
                raise Exception(f"Failed to call {url} after {retries} attempts: {str(e)}. Please try again later.")
            await asyncio.sleep(2)  # Attendre 2 secondes avant de réessayer

@app.route('/')
async def index():
    try:
        logger.info("Rendering index.html")
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error rendering index.html: {str(e)}")
        return jsonify({"error": "Failed to render index page", "details": str(e)}), 500

@app.route('/generate_campaign', methods=['POST'])
async def generate_campaign():
    try:
        # Récupérer les données du formulaire
        artist = request.form.get('artist')
        song = request.form.get('song')
        style_input = request.form.get('style')
        language = request.form.get('language', 'fr')
        tone = request.form.get('tone', 'engageant')
        lyrics = request.form.get('lyrics')
        bio = request.form.get('bio')
        
        logger.info(f"Received form data: artist={artist}, song={song}, style={style_input}, language={language}, tone={tone}")

        if not artist:
            logger.error("Missing required field 'artist' in form data")
            return render_template('index.html', error="Le nom de l'artiste est requis."), 400
        
        if not song:
            logger.error("Missing required field 'song' in form data")
            return render_template('index.html', error="Le nom de la chanson est requis."), 400
        
        if not style_input:
            logger.error("Missing required field 'style' in form data")
            return render_template('index.html', error="Le style musical est requis."), 400

        # Splitter les styles musicaux en une liste
        styles = [style.strip() for style in style_input.split(',')]
        style_display = ', '.join(styles)

        # Extraire l'artiste principal et le collaborateur
        if " X " in artist:
            artist_name, collaborator = artist.split(" X ", 1)
        else:
            artist_name = artist
            collaborator = ""

        # Créer une session asynchrone pour les appels HTTP
        async with aiohttp.ClientSession() as session:
            # Étape 1 : Appeler campaign_analyst
            logger.info(f"Sending request to campaign_analyst at {CAMPAIGN_ANALYST_URL}/analyze with data: {{'artist': {artist}, 'styles': {styles}}}")
            analysis_task = asyncio.create_task(fetch_data(session, f"{CAMPAIGN_ANALYST_URL}/analyze", {"artist": artist, "styles": styles}))

            # Étape 2 : Appeler marketing_agents
            logger.info(f"Sending request to marketing_agents at {MARKETING_AGENTS_URL}/generate_ads with data: {{'artist': {artist}, 'genres': {styles}, 'language': {language}, 'tone': {tone}, 'lyrics': {lyrics}, 'bio': {bio}}}")
            marketing_task = asyncio.create_task(fetch_data(session, f"{MARKETING_AGENTS_URL}/generate_ads", {"artist": artist, "genres": styles, "language": language, "tone": tone, "lyrics": lyrics, "bio": bio}))

            # Étape 3 : Appeler campaign_optimizer
            logger.info(f"Sending request to campaign_optimizer at {CAMPAIGN_OPTIMIZER_URL}/optimize with data: {{'artist': {artist}, 'song': {song}}}")
            optimizer_task = asyncio.create_task(fetch_data(session, f"{CAMPAIGN_OPTIMIZER_URL}/optimize", {"artist": artist, "song": song}))

            # Attendre que tous les appels soient terminés
            analysis_data, ad_data, strategy_data = await asyncio.gather(analysis_task, marketing_task, optimizer_task)

        # Traiter les réponses
        logger.info(f"Processing responses: analysis_data={analysis_data}, ad_data={ad_data}, strategy_data={strategy_data}")

        # Analyse
        logger.info("Processing analysis_data")
        if not isinstance(analysis_data, dict):
            logger.error(f"campaign_analyst response is not a dictionary: {analysis_data}")
            analysis_data = {"trends": ["Trend 1", "Trend 2"], "lookalike_artists": ["Artist 1", "Artist 2"], "style": style_display, "artist_image_url": "https://via.placeholder.com/120?text=Artist"}
        analysis_data = sanitize_data(analysis_data)
        logger.info(f"Sanitized analysis_data: {analysis_data}")

        # Annonces
        logger.info("Processing ad_data")
        short_titles = ad_data.get("short_titles", [{"title": "Short Title 1", "character_count": 13}] * 5)
        long_titles = ad_data.get("long_titles", [{"title": "Long Title 1", "character_count": 12}] * 5)
        long_descriptions = ad_data.get("long_descriptions", [{"description": "Description 1", "character_count": 13}] * 5)
        youtube_description_short = ad_data.get("youtube_description_short", {"description": "No short YouTube description", "character_count": 28})
        youtube_description_full_raw = ad_data.get("youtube_description_full", {"description": "No full YouTube description provided", "character_count": 36})

        # Reformater la description YouTube complète selon le template demandé
        youtube_description_full = {
            "description": (
                f'{artist_name} X {collaborator} "{song}"\n'
                f'Taken from "collez le nom de l\'album" album: collez votre smartlink\n\n'
                f'🔔 Subscribe to my channel 👉 collez le lien de votre chaîne YouTube\n\n'
                f'Crédits :\n'
                f'Montage : collez le nom du monteur\n'
                f'Vidéos : collez le nom du vidéaste\n\n'
                f'LYRICS :\n'
                f'{lyrics}\n\n'
                f'🇬🇧 With his unique style, {artist_name} is experiencing growing success across the globe. With each release, {artist_name} continues to surprise his audience and build excitement, cementing his place as a key figure in the {style_display} scene.\n\n'
                f'🇫🇷 Avec son style unique, {artist_name} rencontre un succès grandissant aux quatre coins du globe. À chacune de ses sorties, il continue de surprendre et de créer l’engouement, s’imposant comme une figure essentielle de la scène {style_display}.\n\n'
                f'Label: collez l\'email du label\n'
                f'Booking Europe, Africa & North America: collez l\'email de booking (Europe, Afrique, Amérique du Nord)\n'
                f'Booking Latin America: collez l\'email de booking (Amérique Latine)\n\n'
                f'Follow {artist_name} on :\n'
                f'Instagram : collez votre handle Instagram\n'
                f'TikTok : collez votre handle TikTok\n'
                f'Website : collez l\'URL de votre site web\n\n'
                f'#{artist_name.replace(" ", "")} #{style_display.replace(" ", "")} #collez le tag de l\'album'
            ),
            "character_count": len(
                f'{artist_name} X {collaborator} "{song}"\n'
                f'Taken from "collez le nom de l\'album" album: collez votre smartlink\n\n'
                f'🔔 Subscribe to my channel 👉 collez le lien de votre chaîne YouTube\n\n'
                f'Crédits :\n'
                f'Montage : collez le nom du monteur\n'
                f'Vidéos : collez le nom du vidéaste\n\n'
                f'LYRICS :\n'
                f'{lyrics}\n\n'
                f'🇬🇧 With his unique style, {artist_name} is experiencing growing success across the globe. With each release, {artist_name} continues to surprise his audience and build excitement, cementing his place as a key figure in the {style_display} scene.\n\n'
                f'🇫🇷 Avec son style unique, {artist_name} rencontre un succès grandissant aux quatre coins du globe. À chacune de ses sorties, il continue de surprendre et de créer l’engouement, s’imposant comme une figure essentielle de la scène {style_display}.\n\n'
                f'Label: collez l\'email du label\n'
                f'Booking Europe, Africa & North America: collez l\'email de booking (Europe, Afrique, Amérique du Nord)\n'
                f'Booking Latin America: collez l\'email de booking (Amérique Latine)\n\n'
                f'Follow {artist_name} on :\n'
                f'Instagram : collez votre handle Instagram\n'
                f'TikTok : collez votre handle TikTok\n'
                f'Website : collez l\'URL de votre site web\n\n'
                f'#{artist_name.replace(" ", "")} #{style_display.replace(" ", "")} #collez le tag de l\'album'
            )
        }
        
        short_titles = sanitize_data(short_titles)
        long_titles = sanitize_data(long_titles)
        long_descriptions = sanitize_data(long_descriptions)
        youtube_description_short = sanitize_data(youtube_description_short)
        youtube_description_full = sanitize_data(youtube_description_full)
        logger.info(f"Sanitized ad_data: short_titles={short_titles}, long_titles={long_titles}, long_descriptions={long_descriptions}, youtube_short={youtube_description_short}, youtube_full={youtube_description_full}")

        # Stratégie
        logger.info("Processing strategy_data")
        if not isinstance(strategy_data, dict):
            logger.error(f"campaign_optimizer response is not a dictionary: {strategy_data}")
            strategy = {"target_audience": "Fans of similar artists", "channels": ["Spotify", "YouTube"], "budget_allocation": {"Spotify": 0.5, "YouTube": 0.5}}
        else:
            strategy = strategy_data.get("strategy", {"target_audience": "Fans of similar artists", "channels": ["Spotify", "YouTube"], "budget_allocation": {"Spotify": 0.5, "YouTube": 0.5}})
            if not isinstance(strategy, dict):
                logger.error(f"strategy is not a dictionary: {strategy}")
                strategy = {"target_audience": "Fans of similar artists", "channels": ["Spotify", "YouTube"], "budget_allocation": {"Spotify": 0.5, "YouTube": 0.5}}
        strategy = sanitize_data(strategy)
        logger.info(f"Sanitized strategy: {strategy}")
        
        # Étape 4 : Rendre les résultats
        logger.info(f"Rendering results.html with artist={artist}, song={song}, style={style_display}, analysis_data={analysis_data}, short_titles={short_titles}, long_titles={long_titles}, long_descriptions={long_descriptions}, youtube_short={youtube_description_short}, youtube_full={youtube_description_full}, strategy={strategy}")
        return render_template('results.html', 
                              artist=artist,
                              song=song,
                              style=style_display,  
                              analysis=analysis_data,
                              short_titles=short_titles, 
                              long_titles=long_titles, 
                              long_descriptions=long_descriptions,
                              youtube_description_short=youtube_description_short,
                              youtube_description_full=youtube_description_full,
                              strategy=strategy)

    except Exception as e:
        logger.error(f"Error in generate_campaign: {str(e)}", exc_info=True)
        return render_template('error.html', error=str(e), artist=artist, style=style_input), 500

@app.errorhandler(500)
async def handle_500(error):
    logger.error(f"Template error: {str(error)}", exc_info=True)
    return render_template('error.html', error=str(error), artist="Unknown Artist", style="Unknown Style"), 500

# Convertir l'application Flask (WSGI) en ASGI pour uvicorn
app = WsgiToAsgi(app)

if __name__ == '__main__':
    import uvicorn
    port = int(os.environ.get('PORT', 5000))
    uvicorn.run(app, host='0.0.0.0', port=port)
