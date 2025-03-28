import asyncio
import logging
import os
import uuid
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import aiohttp
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

# Stockage temporaire des campagnes en cours de génération
# Dans une application de production, utilisez une base de données
campaigns = {}

async def fetch_data(session, url, data, retries=5):
    for attempt in range(retries):
        try:
            async with session.post(url, json=data, timeout=10) as response:
                response.raise_for_status()
                return await response.json()
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1}/{retries} failed for {url}: {str(e)}")
            if attempt + 1 == retries:
                raise Exception(f"Failed to call {url} after {retries} attempts: {str(e)}. Please try again later.")
            await asyncio.sleep(2 ** attempt)

@app.route('/')
def index():
    template = env.get_template('index.html')
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
        chartmetric_status="Opérationnel",
        chartmetric_status_class="status-ok"
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
        "results": None
    }
    
    # Lancer la génération de la campagne en arrière-plan (simulation)
    # Dans une application réelle, vous utiliseriez Celery ou un autre système de tâches asynchrones
    asyncio.create_task(generate_campaign_async(campaign_id))
    
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
        "campaign_id": campaign_id
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
                          campaign_results=campaign["results"] if campaign["results"] else {})

async def generate_campaign_async(campaign_id):
    """Fonction asynchrone pour générer la campagne marketing"""
    if campaign_id not in campaigns:
        return
    
    # Simuler un délai de traitement
    await asyncio.sleep(10)
    
    # Générer des résultats fictifs pour la démonstration
    # Dans une application réelle, vous appelleriez ici vos services d'IA
    campaign_data = campaigns[campaign_id]["data"]
    artist = campaign_data["artist"]
    song = campaign_data["song"]
    
    campaigns[campaign_id]["results"] = {
        "short_title": f"Découvrez {song} par {artist}",
        "long_title": f"{artist} - {song} | Nouvelle sortie à ne pas manquer",
        "description": f"Écoutez le nouveau titre de {artist}, {song}. Une expérience musicale unique qui vous transportera.",
        "youtube_short": f"{artist} présente {song}. Écoutez maintenant sur toutes les plateformes de streaming.",
        "youtube_full": f"Découvrez {song}, le nouveau titre de {artist}.\n\nParoles:\n{campaign_data['lyrics']}\n\nSuivez {artist} sur les réseaux sociaux pour ne rien manquer des prochaines sorties."
    }
    
    # Mettre à jour le statut
    campaigns[campaign_id]["status"] = "completed"

# Créer l'application ASGI à partir de l'application WSGI
asgi_app = WsgiToAsgi(app)
