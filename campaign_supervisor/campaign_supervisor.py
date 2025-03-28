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

# Endpoints API
CHARTMETRIC_TRENDS_ENDPOINT = f"{CHARTMETRIC_SERVICE_URL}/api/trends"
ANALYST_ANALYZE_ENDPOINT = f"{ANALYST_SERVICE_URL}/api/analyze"
MARKETING_GENERATE_ENDPOINT = f"{MARKETING_AGENT_URL}/api/generate"
OPTIMIZER_OPTIMIZE_ENDPOINT = f"{OPTIMIZER_SERVICE_URL}/api/optimize"

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
    if not campaign_id or campaign_id not in campaigns:
        return jsonify({"status": "error", "message": "Campagne non trouvée"}), 404
    
    return jsonify({
        "status": campaigns[campaign_id]["status"],
        "campaign_id": campaign_id,
        "progress": campaigns[campaign_id]["progress"]
    })

@app.route('/campaign_results/<campaign_id>')
def campaign_results(campaign_id):
    if not campaign_id or campaign_id not in campaigns:
        return redirect('/')
    
    campaign = campaigns[campaign_id]
    
    return render_template('results.html',
                          campaign_id=campaign_id,
                          campaign_status=campaign["status"],
                          analysis=campaign["data"],
                          campaign_results=campaign["results"] if campaign["results"] else {},
                          progress=campaign["progress"])

def check_service_status(service_url):
    """Vérifie si un service est opérationnel"""
    try:
        response = requests.get(f"{service_url}/health", timeout=5)
        if response.status_code == 200:
            return "Opérationnel", "status-ok"
        else:
            return "Dégradé", "status-pending"
    except:
        try:
            # Essayer simplement de se connecter au service
            response = requests.get(service_url, timeout=5)
            if response.status_code < 500:
                return "Opérationnel", "status-ok"
            else:
                return "Dégradé", "status-pending"
        except:
            return "Indisponible", "status-error"

def orchestrate_campaign_generation(campaign_id):
    """Fonction qui orchestre la génération de campagne en appelant les différents services"""
    if campaign_id not in campaigns:
        return
    
    campaign_data = campaigns[campaign_id]["data"]
    artist = campaign_data["artist"]
    song = campaign_data["song"]
    genres = campaign_data["genres"]
    lyrics = campaign_data["lyrics"]
    
    try:
        # 1. Appeler Chartmetric Service pour obtenir les tendances et données d'artistes
        logger.info(f"Appel au service Chartmetric pour l'artiste {artist}")
        campaigns[campaign_id]["progress"]["chartmetric"] = "in_progress"
        
        try:
            chartmetric_response = requests.post(
                CHARTMETRIC_TRENDS_ENDPOINT,
                json={
                    "artist": artist,
                    "song": song,
                    "genres": genres
                },
                timeout=30
            )
            
            if chartmetric_response.status_code == 200:
                chartmetric_data = chartmetric_response.json()
                campaigns[campaign_id]["progress"]["chartmetric"] = "completed"
                logger.info(f"Données Chartmetric reçues pour {artist}")
            else:
                # En cas d'erreur, utiliser des données fictives pour continuer le flux
                logger.warning(f"Erreur lors de l'appel à Chartmetric: {chartmetric_response.status_code}")
                chartmetric_data = {
                    "trends": ["metal", "rock alternatif", "électro"],
                    "lookalike_artists": ["Nine Inch Nails", "Mass Hysteria", "Celldweller"],
                    "metrics": {
                        "spotify": {"followers": 15000, "monthly_listeners": 8000, "popularity": 45},
                        "youtube": {"subscribers": 5000, "views": 120000},
                        "social_media": {"instagram": 3000, "tiktok": 1500, "twitter": 2000}
                    }
                }
                campaigns[campaign_id]["progress"]["chartmetric"] = "completed_with_fallback"
        except Exception as e:
            logger.error(f"Exception lors de l'appel à Chartmetric: {str(e)}")
            # En cas d'exception, utiliser des données fictives pour continuer le flux
            chartmetric_data = {
                "trends": ["metal", "rock alternatif", "électro"],
                "lookalike_artists": ["Nine Inch Nails", "Mass Hysteria", "Celldweller"],
                "metrics": {
                    "spotify": {"followers": 15000, "monthly_listeners": 8000, "popularity": 45},
                    "youtube": {"subscribers": 5000, "views": 120000},
                    "social_media": {"instagram": 3000, "tiktok": 1500, "twitter": 2000}
                }
            }
            campaigns[campaign_id]["progress"]["chartmetric"] = "completed_with_fallback"
        
        # 2. Appeler Analyst pour l'analyse
        logger.info(f"Appel au service Analyst pour l'artiste {artist}")
        campaigns[campaign_id]["progress"]["analyst"] = "in_progress"
        
        try:
            analyst_response = requests.post(
                ANALYST_ANALYZE_ENDPOINT,
                json={
                    "artist": artist,
                    "song": song,
                    "genres": genres,
                    "lyrics": lyrics,
                    "chartmetric_data": chartmetric_data
                },
                timeout=30
            )
            
            if analyst_response.status_code == 200:
                analyst_data = analyst_response.json()
                campaigns[campaign_id]["progress"]["analyst"] = "completed"
                logger.info(f"Analyse reçue pour {artist}")
            else:
                # En cas d'erreur, utiliser des données fictives pour continuer le flux
                logger.warning(f"Erreur lors de l'appel à Analyst: {analyst_response.status_code}")
                analyst_data = {
                    "insights": {
                        "audience": "Fans de metal et d'électro, 25-40 ans",
                        "key_themes": ["intensité", "dualité", "engagement social"],
                        "unique_selling_points": ["fusion de styles", "paroles engagées", "énergie live"]
                    }
                }
                campaigns[campaign_id]["progress"]["analyst"] = "completed_with_fallback"
        except Exception as e:
            logger.error(f"Exception lors de l'appel à Analyst: {str(e)}")
            # En cas d'exception, utiliser des données fictives pour continuer le flux
            analyst_data = {
                "insights": {
                    "audience": "Fans de metal et d'électro, 25-40 ans",
                    "key_themes": ["intensité", "dualité", "engagement social"],
                    "unique_selling_points": ["fusion de styles", "paroles engagées", "énergie live"]
                }
            }
            campaigns[campaign_id]["progress"]["analyst"] = "completed_with_fallback"
        
        # 3. Appeler Marketing Agent pour générer les annonces
        logger.info(f"Appel au service Marketing pour l'artiste {artist}")
        campaigns[campaign_id]["progress"]["marketing"] = "in_progress"
        
        try:
            marketing_response = requests.post(
                MARKETING_GENERATE_ENDPOINT,
                json={
                    "artist": artist,
                    "song": song,
                    "genres": genres,
                    "lyrics": lyrics,
                    "chartmetric_data": chartmetric_data,
                    "analyst_data": analyst_data,
                    "language": campaign_data["language"]
                },
                timeout=30
            )
            
            if marketing_response.status_code == 200:
                marketing_data = marketing_response.json()
                campaigns[campaign_id]["progress"]["marketing"] = "completed"
                logger.info(f"Annonces générées pour {artist}")
            else:
                # En cas d'erreur, utiliser des données fictives pour continuer le flux
                logger.warning(f"Erreur lors de l'appel à Marketing: {marketing_response.status_code}")
                marketing_data = {
                    "ads": {
                        "short_title": f"Découvrez {song} par {artist}",
                        "long_title": f"{artist} - {song} | Nouvelle sortie à ne pas manquer",
                        "description": f"Écoutez le nouveau titre de {artist}, {song}. Une expérience musicale unique qui vous transportera.",
                        "youtube_short": f"{artist} présente {song}. Écoutez maintenant sur toutes les plateformes de streaming.",
                        "youtube_full": f"Découvrez {song}, le nouveau titre de {artist}.\n\nParoles:\n{lyrics[:500]}...\n\nSuivez {artist} sur les réseaux sociaux pour ne rien manquer des prochaines sorties."
                    }
                }
                campaigns[campaign_id]["progress"]["marketing"] = "completed_with_fallback"
        except Exception as e:
            logger.error(f"Exception lors de l'appel à Marketing: {str(e)}")
            # En cas d'exception, utiliser des données fictives pour continuer le flux
            marketing_data = {
                "ads": {
                    "short_title": f"Découvrez {song} par {artist}",
                    "long_title": f"{artist} - {song} | Nouvelle sortie à ne pas manquer",
                    "description": f"Écoutez le nouveau titre de {artist}, {song}. Une expérience musicale unique qui vous transportera.",
                    "youtube_short": f"{artist} présente {song}. Écoutez maintenant sur toutes les plateformes de streaming.",
                    "youtube_full": f"Découvrez {song}, le nouveau titre de {artist}.\n\nParoles:\n{lyrics[:500]}...\n\nSuivez {artist} sur les réseaux sociaux pour ne rien manquer des prochaines sorties."
                }
            }
            campaigns[campaign_id]["progress"]["marketing"] = "completed_with_fallback"
        
        # 4. Appeler Optimizer pour optimiser les annonces
        logger.info(f"Appel au service Optimizer pour l'artiste {artist}")
        campaigns[campaign_id]["progress"]["optimizer"] = "in_progress"
        
        try:
            optimizer_response = requests.post(
                OPTIMIZER_OPTIMIZE_ENDPOINT,
                json={
                    "artist": artist,
                    "song": song,
                    "genres": genres,
                    "chartmetric_data": chartmetric_data,
                    "analyst_data": analyst_data,
                    "marketing_data": marketing_data
                },
                timeout=30
            )
            
            if optimizer_response.status_code == 200:
                optimizer_data = optimizer_response.json()
                campaigns[campaign_id]["progress"]["optimizer"] = "completed"
                logger.info(f"Annonces optimisées pour {artist}")
            else:
                # En cas d'erreur, utiliser les données du Marketing Agent
                logger.warning(f"Erreur lors de l'appel à Optimizer: {optimizer_response.status_code}")
                optimizer_data = {
                    "optimized_ads": marketing_data["ads"]
                }
                campaigns[campaign_id]["progress"]["optimizer"] = "completed_with_fallback"
        except Exception as e:
            logger.error(f"Exception lors de l'appel à Optimizer: {str(e)}")
            # En cas d'exception, utiliser les données du Marketing Agent
            optimizer_data = {
                "optimized_ads": marketing_data["ads"]
            }
            campaigns[campaign_id]["progress"]["optimizer"] = "completed_with_fallback"
        
        # 5. Stocker les résultats finaux
        campaigns[campaign_id]["results"] = {
            "short_title": optimizer_data["optimized_ads"]["short_title"],
            "long_title": optimizer_data["optimized_ads"]["long_title"],
            "description": optimizer_data["optimized_ads"]["description"],
            "youtube_short": optimizer_data["optimized_ads"]["youtube_short"],
            "youtube_full": optimizer_data["optimized_ads"]["youtube_full"]
        }
        
        # Mettre à jour les données de l'artiste avec les informations de Chartmetric
        campaigns[campaign_id]["data"]["trends"] = chartmetric_data["trends"]
        campaigns[campaign_id]["data"]["lookalike_artists"] = chartmetric_data["lookalike_artists"]
        campaigns[campaign_id]["data"]["metrics"] = chartmetric_data["metrics"]
        
        # Mettre à jour le statut
        campaigns[campaign_id]["status"] = "completed"
        logger.info(f"Génération de campagne terminée pour {artist}")
        
    except Exception as e:
        logger.error(f"Erreur lors de l'orchestration de la campagne: {str(e)}")
        # En cas d'erreur globale, générer des résultats fictifs
        campaigns[campaign_id]["results"] = {
            "short_title": f"Découvrez {song} par {artist}",
            "long_title": f"{artist} - {song} | Nouvelle sortie à ne pas manquer",
            "description": f"Écoutez le nouveau titre de {artist}, {song}. Une expérience musicale unique qui vous transportera.",
            "youtube_short": f"{artist} présente {song}. Écoutez maintenant sur toutes les plateformes de streaming.",
            "youtube_full": f"Découvrez {song}, le nouveau titre de {artist}.\n\nParoles:\n{lyrics[:500]}...\n\nSuivez {artist} sur les réseaux sociaux pour ne rien manquer des prochaines sorties."
        }
        campaigns[campaign_id]["status"] = "completed_with_errors"

# Créer l'application ASGI à partir de l'application WSGI
asgi_app = WsgiToAsgi(app)
