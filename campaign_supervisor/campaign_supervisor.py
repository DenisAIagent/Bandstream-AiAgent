import logging
import os
import uuid
import threading
import time
import requests
import json
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from jinja2 import Environment, FileSystemLoader
from asgiref.wsgi import WsgiToAsgi

# Créer l'application Flask avec le chemin correct vers les templates
app = Flask(__name__, 
           template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__) ), 'templates'))
app.secret_key = os.environ.get('SECRET_KEY', 'bandstream_secret_key')

# Configuration des logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration de Jinja2 avec un chemin absolu
current_dir = os.path.dirname(os.path.abspath(__file__))
templates_dir = os.path.join(current_dir, 'templates')
env = Environment(loader=FileSystemLoader(templates_dir))

# URLs des services
CHARTMETRIC_SERVICE_URL = "https://chartmetricservice-production.up.railway.app"
ANALYST_SERVICE_URL = "https://analyst-production.up.railway.app"
MARKETING_AGENT_URL = "https://marketing-agent-production.up.railway.app"
OPTIMIZER_SERVICE_URL = "https://optimizer-production.up.railway.app"
API_SERVER_URL = "https://api-server-production-e858.up.railway.app"

# Endpoints API - MODIFIÉS POUR CORRIGER LES ERREURS 404
CHARTMETRIC_TRENDS_ENDPOINT = f"{CHARTMETRIC_SERVICE_URL}/trends"
ANALYST_ANALYZE_ENDPOINT = f"{ANALYST_SERVICE_URL}/analyze"
MARKETING_GENERATE_ENDPOINT = f"{MARKETING_AGENT_URL}/generate_ads"
OPTIMIZER_OPTIMIZE_ENDPOINT = f"{OPTIMIZER_SERVICE_URL}/optimize"

# Dictionnaire global pour stocker les campagnes (au lieu d'utiliser session) 
campaigns_store = {}

@app.route('/')
def index():
    # Vérifier si une analyse existe déjà dans la session
    analysis = session.get('analysis', {})
    
    # Si aucune analyse n'existe, créer une analyse vide avec des valeurs par défaut
    if not analysis:
        analysis = {
            'artist': '',
            'song': '',
            'genres': []
        }
        session['analysis'] = analysis
    
    # Vérifier le statut des services
    chartmetric_status, chartmetric_class = check_service_status(CHARTMETRIC_SERVICE_URL)
    analyst_status, analyst_class = check_service_status(ANALYST_SERVICE_URL)
    marketing_status, marketing_class = check_service_status(MARKETING_AGENT_URL)
    optimizer_status, optimizer_class = check_service_status(OPTIMIZER_SERVICE_URL)
    
    return render_template('index.html', 
                          analysis=analysis,
                          chartmetric_status=chartmetric_status,
                          chartmetric_class=chartmetric_class,
                          analyst_status=analyst_status,
                          analyst_class=analyst_class,
                          marketing_status=marketing_status,
                          marketing_class=marketing_class,
                          optimizer_status=optimizer_status,
                          optimizer_class=optimizer_class)

@app.route('/generate_campaign', methods=['POST'])
def generate_campaign():
    if request.method == 'POST':
        # Récupérer les données JSON au lieu des données de formulaire
        data = request.get_json()
        if not data:
            logger.info("Aucune donnée JSON reçue")
            return redirect(url_for('index'))
        
        # Extraire les données du JSON
        artist = data.get('artist', '')
        song = data.get('song', '')
        genres = data.get('genres', [])
        language = data.get('language', 'français')
        promotion_type = data.get('promotion_type', 'sortie')
        lyrics = data.get('lyrics', '')
        bio = data.get('bio', '')
        song_link = data.get('song_link', '')
        
        logger.info(f"Données JSON reçues: {data}")

        # Générer un ID unique pour la campagne
        campaign_id = str(uuid.uuid4())
        
        # Créer un dictionnaire pour stocker les données de la campagne
        campaign = {
            'id': campaign_id,
            'artist': artist,
            'song': song,
            'genres': genres,
            'language': language,
            'promotion_type': promotion_type,
            'lyrics': lyrics,
            'bio': bio,
            'song_link': song_link,
            'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'pending',
            'progress': {
                'chartmetric': 'pending',
                'analyst': 'pending',
                'marketing': 'pending',
                'optimizer': 'pending'
            }
        }
        
        # Stocker la campagne dans le dictionnaire global
        campaigns_store[campaign_id] = campaign
        
        # Lancer la génération de la campagne en arrière-plan
        threading.Thread(target=generate_campaign_background, args=(campaign_id, artist, song, genres, language, promotion_type, lyrics, bio, song_link)).start()
        
        # Rediriger vers la page de résultats avec le statut "generating"
        return render_template('results.html', 
                              campaign_id=campaign_id, 
                              campaign_status="generating",
                              analysis={
                                  'artist': artist,
                                  'song': song,
                                  'genres': genres
                              })
    
    # Si la méthode n'est pas POST, rediriger vers la page d'accueil
    return redirect(url_for('index'))

@app.route('/campaign_status')
def campaign_status():
    campaign_id = request.args.get('id')
    
    # Si un ID spécifique est fourni, renvoyer uniquement cette campagne
    if campaign_id:
        campaign = campaigns_store.get(campaign_id)
        if campaign:
            return jsonify(campaign)
        else:
            return jsonify({"error": "Campagne non trouvée"}), 404
    
    # Sinon, renvoyer toutes les campagnes
    return jsonify(campaigns_store)

@app.route('/campaign_results/<id>')
def view_campaign_results(id):
    # Récupérer les données de la campagne depuis le dictionnaire global
    campaign = campaigns_store.get(id)
    
    if not campaign:
        flash("Campagne non trouvée.")
        return redirect(url_for('index'))
    
    # Préparer les données pour le template
    campaign_results = {}
    
    if 'marketing_data' in campaign:
        marketing_data = campaign['marketing_data']
        campaign_results = {
            'short_title': marketing_data.get('short_titles', [''])[0] if marketing_data.get('short_titles') else '',
            'long_title': marketing_data.get('long_titles', [''])[0] if marketing_data.get('long_titles') else '',
            'description': marketing_data.get('long_descriptions', [{'description': ''}])[0].get('description', '') if marketing_data.get('long_descriptions') else '',
            'youtube_short': marketing_data.get('youtube_description_short', {}).get('description', '') if marketing_data.get('youtube_description_short') else '',
            'youtube_full': marketing_data.get('youtube_description_full', {}).get('description', '') if marketing_data.get('youtube_description_full') else ''
        }
    
    # Rendre le template avec les données de la campagne
    return render_template('results.html', 
                          campaign_id=id, 
                          campaign_status="completed",
                          campaign_results=campaign_results,
                          analysis={
                              'artist': campaign.get('artist', ''),
                              'song': campaign.get('song', ''),
                              'genres': campaign.get('genres', [])
                          })

def generate_campaign_background(campaign_id, artist_name, song_name, genres, language, promotion_type, lyrics, bio, song_link):
    # Récupérer la campagne depuis le dictionnaire global au lieu de la session
    campaign = campaigns_store.get(campaign_id, {})
    
    # Appel au service Chartmetric pour obtenir des tendances et des artistes similaires
    chartmetric_data = {}
    logger.info(f"Appel au service Chartmetric pour l'artiste {artist_name}")
    try:
        response = requests.post(
            CHARTMETRIC_TRENDS_ENDPOINT,
            json={
                "artist": artist_name,
                "genres": genres
            },
            timeout=30
        )
        if response.status_code == 200:
            chartmetric_data = response.json()
            campaign["progress"]["chartmetric"] = "completed"
        else:
            logger.warning(f"Erreur lors de l'appel à Chartmetric: {response.status_code}")
            campaign["progress"]["chartmetric"] = "error"
    except Exception as e:
        logger.error(f"Exception lors de l'appel à Chartmetric: {str(e)}")
        campaign["progress"]["chartmetric"] = "error"
    
    # Appel au service Analyst pour analyser l'artiste et la chanson
    analyst_data = {}
    logger.info(f"Appel au service Analyst pour l'artiste {artist_name}")
    try:
        response = requests.post(
            ANALYST_ANALYZE_ENDPOINT,
            json={
                "artist": artist_name,
                "song": song_name,
                "genres": genres,
                "lyrics": lyrics,
                "bio": bio
            },
            timeout=30
        )
        if response.status_code == 200:
            analyst_data = response.json()
            campaign["progress"]["analyst"] = "completed"
        else:
            logger.warning(f"Erreur lors de l'appel à Analyst: {response.status_code}")
            campaign["progress"]["analyst"] = "error"
    except Exception as e:
        logger.error(f"Exception lors de l'appel à Analyst: {str(e)}")
        campaign["progress"]["analyst"] = "error"
    
    # Appel au service Marketing pour générer des annonces
    marketing_data = {}
    logger.info(f"Appel au service Marketing pour l'artiste {artist_name}")
    try:
        response = requests.post(
            MARKETING_GENERATE_ENDPOINT,
            json={
                "artist": artist_name,
                "song": song_name,
                "genres": genres,
                "language": language,
                "promotion_type": promotion_type,
                "lyrics": lyrics,
                "bio": bio,
                "song_link": song_link,
                "chartmetric_data": chartmetric_data,
                "analyst_data": analyst_data
            },
            timeout=60
        )
        if response.status_code == 200:
            marketing_data = response.json()
            campaign["progress"]["marketing"] = "completed"
        else:
            logger.warning(f"Erreur lors de l'appel à Marketing: {response.status_code}")
            campaign["progress"]["marketing"] = "error"
    except Exception as e:
        logger.error(f"Exception lors de l'appel à Marketing: {str(e)}")
        campaign["progress"]["marketing"] = "error"
    
    # Appel au service Optimizer pour optimiser les annonces
    optimizer_data = {}
    logger.info(f"Appel au service Optimizer pour l'artiste {artist_name}")
    try:
        response = requests.post(
            OPTIMIZER_OPTIMIZE_ENDPOINT,
            json={
                "artist": artist_name,
                "song": song_name,
                "genres": genres,
                "language": language,
                "promotion_type": promotion_type,
                "marketing_data": marketing_data
            },
            timeout=30
        )
        if response.status_code == 200:
            optimizer_data = response.json()
            campaign["progress"]["optimizer"] = "completed"
        else:
            logger.warning(f"Erreur lors de l'appel à Optimizer: {response.status_code}")
            campaign["progress"]["optimizer"] = "error"
    except Exception as e:
        logger.error(f"Exception lors de l'appel à Optimizer: {str(e)}")
        campaign["progress"]["optimizer"] = "error"
    
    # Mettre à jour les données de la campagne
    campaign["chartmetric_data"] = chartmetric_data
    campaign["analyst_data"] = analyst_data
    campaign["marketing_data"] = marketing_data
    campaign["optimizer_data"] = optimizer_data
    campaign["status"] = "completed"
    
    # Mettre à jour le dictionnaire global
    campaigns_store[campaign_id] = campaign
    
    logger.info(f"Génération de campagne terminée pour {artist_name}")

def check_service_status(service_url):
    """
    Vérifie si un service est disponible
    """
    try:
        response = requests.get(f"{service_url}/health", timeout=5)
        if response.status_code == 200:
            return "Opérationnel", "status-operational"
        else:
            return "Dégradé", "status-degraded"
    except:
        return "Indisponible", "status-unavailable"

# Point d'entrée ASGI pour uvicorn
asgi_app = WsgiToAsgi(app)

if __name__ == "__main__":
    # Démarrer l'application Flask en mode développement
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
