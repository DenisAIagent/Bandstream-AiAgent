import logging
import os
import uuid
import threading
import time
import requests
import json
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
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
# Suppression du préfixe "/api" pour correspondre aux routes réelles
CHARTMETRIC_TRENDS_ENDPOINT = f"{CHARTMETRIC_SERVICE_URL}/trends"
ANALYST_ANALYZE_ENDPOINT = f"{ANALYST_SERVICE_URL}/analyze"
MARKETING_GENERATE_ENDPOINT = f"{MARKETING_AGENT_URL}/generate"
OPTIMIZER_OPTIMIZE_ENDPOINT = f"{OPTIMIZER_SERVICE_URL}/optimize"

# Stockage temporaire des campagnes en cours de génération
# Dans une application de production, utilisez une base de données
campaigns = {}

@app.route('/') 
def index():
    template = env.get_template('index.html')
    
    # Vérifier l'état des services
    chartmetric_status, chartmetric_status_class = check_service_status(CHARTMETRIC_SERVICE_URL)
    
    # Fournir des valeurs par défaut pour toutes les variables utilisées dans le template
    return template.render(
        analysis={
            "artist": "Aucun artiste sélectionné",
            "song": "Aucune chanson sélectionnée",
            "genres": [],
            "trends": [],
            "lookalike_artists": [],
            "metrics": {
                "spotify": {"followers": 0, "monthly_listeners": 0, "popularity": 0},
                "youtube": {"subscribers": 0, "views": 0},
                "social_media": {"instagram": 0, "tiktok": 0, "twitter": 0}
            }
        },
        # Ajouter les variables manquantes utilisées dans le template
        chartmetric_status=chartmetric_status,
        chartmetric_status_class=chartmetric_status_class
    )

@app.route('/generate_campaign', methods=['POST'])
def generate_campaign():
    # Récupérer les données du formulaire
    data = request.get_json() if request.is_json else request.form.to_dict()
    
    # Log des données reçues pour le débogage
    logger.info(f"Données de formulaire reçues: {data}")
    
    # Correction du traitement des genres
    # Vérifier si genres est déjà une liste ou une chaîne de caractères
    genres = data.get('genres', [])
    if isinstance(genres, str):
        genres = genres.split(',') if genres else []
    
    # Créer un identifiant unique pour cette campagne
    campaign_id = str(uuid.uuid4())
    
    # Stocker les données de la campagne
    campaigns[campaign_id] = {
        "status": "generating",
        "data": {
            "artist": data.get('artist', "Aucun artiste sélectionné"),
            "song": data.get('song', "Aucune chanson sélectionnée"),
            "genres": genres,
            "lyrics": data.get('lyrics', ""),
            "language": data.get('language', "français"),
            "promotion_type": data.get('promotion_type', "single"),
            "bio": data.get('bio', ""),
            "song_link": data.get('song_link', "")
        },
        "results": None,
        "progress": {
            "chartmetric": "pending",
            "analyst": "pending",
            "marketing": "pending",
            "optimizer": "pending"
        }
    }
    
    # Lancer la génération de la campagne en arrière-plan avec un thread
    thread = threading.Thread(target=orchestrate_campaign_generation, args=(campaign_id,))
    thread.daemon = True  # Le thread s'arrêtera quand le programme principal s'arrête
    thread.start()
    
    # Rediriger vers la page de résultats
    return render_template('results.html', 
                          campaign_id=campaign_id,
                          campaign_status="generating",
                          analysis={
                              "artist": data.get('artist', "Aucun artiste sélectionné"),
                              "song": data.get('song', "Aucune chanson sélectionnée"),
                              "genres": genres,
                              "lyrics": data.get('lyrics', "")
                          })

@app.route('/campaign_status')
def campaign_status():
    campaign_id = request.args.get('id')
    if campaign_id in campaigns:
        return jsonify({
            "status": campaigns[campaign_id]["status"],
            "progress": campaigns[campaign_id]["progress"]
        })
    return jsonify({"status": "not_found"})

@app.route('/campaign_results/<campaign_id>')
def campaign_results(campaign_id):
    if campaign_id in campaigns:
        campaign = campaigns[campaign_id]
        return render_template('results.html', 
                              campaign_id=campaign_id,
                              campaign_status=campaign["status"],
                              campaign_data=campaign["data"],
                              campaign_results=campaign["results"],
                              analysis=campaign["data"])  # Utiliser les données de la campagne comme analyse
    return render_template('error.html', message="Campagne non trouvée")

def orchestrate_campaign_generation(campaign_id):
    """
    Fonction qui orchestre la génération de la campagne en appelant les différents services
    """
    if campaign_id not in campaigns:
        logger.error(f"Campaign ID {campaign_id} not found")
        return
    
    campaign = campaigns[campaign_id]
    artist_name = campaign["data"]["artist"]
    song_name = campaign["data"]["song"]
    genres = campaign["data"]["genres"]
    lyrics = campaign["data"]["lyrics"]
    language = campaign["data"]["language"]
    promotion_type = campaign["data"]["promotion_type"]
    bio = campaign["data"]["bio"]
    song_link = campaign["data"]["song_link"]
    
    # Appel au service Chartmetric pour obtenir des tendances et des artistes similaires
    logger.info(f"Appel au service Chartmetric pour l'artiste {artist_name}")
    chartmetric_data = None
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
    logger.info(f"Appel au service Analyst pour l'artiste {artist_name}")
    analyst_data = None
    try:
        response = requests.post(
            ANALYST_ANALYZE_ENDPOINT,
            json={
                "artist": artist_name,
                "song": song_name,
                "genres": genres,
                "lyrics": lyrics,
                "chartmetric_data": chartmetric_data
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
    logger.info(f"Appel au service Marketing pour l'artiste {artist_name}")
    marketing_data = None
    try:
        response = requests.post(
            MARKETING_GENERATE_ENDPOINT,
            json={
                "artist": artist_name,
                "song": song_name,
                "genres": genres,
                "lyrics": lyrics,
                "language": language,
                "promotion_type": promotion_type,
                "bio": bio,
                "song_link": song_link,
                "analyst_data": analyst_data,
                "chartmetric_data": chartmetric_data
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
    logger.info(f"Appel au service Optimizer pour l'artiste {artist_name}")
    optimizer_data = None
    try:
        response = requests.post(
            OPTIMIZER_OPTIMIZE_ENDPOINT,
            json={
                "artist": artist_name,
                "song": song_name,
                "genres": genres,
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
    
    # Mise à jour des résultats de la campagne
    campaign["results"] = {
        "chartmetric": chartmetric_data,
        "analyst": analyst_data,
        "marketing": marketing_data,
        "optimizer": optimizer_data
    }
    
    # Mise à jour du statut de la campagne
    if all(status == "completed" for status in campaign["progress"].values()):
        campaign["status"] = "completed"
    elif any(status == "error" for status in campaign["progress"].values()):
        campaign["status"] = "error"
    else:
        campaign["status"] = "partial"
    
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
