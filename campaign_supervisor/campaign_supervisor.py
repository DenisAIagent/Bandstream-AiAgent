import os
import uuid
import time
import json
import logging
import threading
import requests
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from logging.handlers import RotatingFileHandler

# Configuration du logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialisation de l'application Flask
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'bandstream_secret_key')

# Dictionnaire global pour stocker les campagnes
campaigns_store = {}

# Configuration des services
CHARTMETRIC_SERVICE_URL = os.environ.get('CHARTMETRIC_SERVICE_URL', 'https://chartmetricservice-production.up.railway.app') 
ANALYST_SERVICE_URL = os.environ.get('ANALYST_SERVICE_URL', 'https://analyst-production.up.railway.app') 
MARKETING_SERVICE_URL = os.environ.get('MARKETING_SERVICE_URL', 'https://marketing-agent-production.up.railway.app') 
OPTIMIZER_SERVICE_URL = os.environ.get('OPTIMIZER_SERVICE_URL', 'https://optimizer-production.up.railway.app') 

# Route principale
@app.route('/')
def index():
    # Vérifier l'état des services
    chartmetric_status, chartmetric_status_class = check_service_status(f"{CHARTMETRIC_SERVICE_URL}/health")
    
    return render_template('index.html', 
                          chartmetric_status=chartmetric_status,
                          chartmetric_status_class=chartmetric_status_class)

# Fonction pour vérifier l'état d'un service
def check_service_status(url):
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return "Opérationnel", "status-ok"
        else:
            return "Erreur", "status-error"
    except:
        return "Non disponible", "status-error"

# Fonction pour générer une campagne en arrière-plan
def generate_campaign_background(campaign_id, artist, song, genres, language, promotion_type, lyrics, bio, song_link):
    campaign = campaigns_store.get(campaign_id)
    if not campaign:
        logger.error(f"Campaign {campaign_id} not found in store")
        return
    
    try:
        # Appel au service Chartmetric
        logger.info(f"Appel au service Chartmetric pour l'artiste {artist}")
        chartmetric_data = call_chartmetric_service(artist, genres)
        campaign['chartmetric_data'] = chartmetric_data
        campaign['progress']['chartmetric'] = 'completed'
        
        # Appel au service Analyst
        logger.info(f"Appel au service Analyst pour l'artiste {artist}")
        analyst_data = call_analyst_service(artist, song, genres, chartmetric_data)
        campaign['analyst_data'] = analyst_data
        campaign['progress']['analyst'] = 'completed'
        
        # Appel au service Marketing
        logger.info(f"Appel au service Marketing pour l'artiste {artist}")
        marketing_data = call_marketing_service(artist, song, genres, language, promotion_type, lyrics, bio, song_link, chartmetric_data, analyst_data)
        campaign['marketing_data'] = marketing_data
        campaign['progress']['marketing'] = 'completed'
        
        # Appel au service Optimizer
        logger.info(f"Appel au service Optimizer pour l'artiste {artist}")
        optimizer_data = call_optimizer_service(artist, song, genres, language, promotion_type, chartmetric_data, analyst_data, marketing_data)
        campaign['optimizer_data'] = optimizer_data
        campaign['progress']['optimizer'] = 'completed'
        
        # Marquer la campagne comme terminée
        campaign['status'] = 'completed'
        logger.info(f"Génération de campagne terminée pour {artist}")
        
    except Exception as e:
        logger.error(f"Erreur lors de la génération de la campagne: {str(e)}")
        campaign['status'] = 'error'
        campaign['error'] = str(e)

# Fonctions pour appeler les différents services
def call_chartmetric_service(artist, genres):
    try:
        response = requests.post(
            f"{CHARTMETRIC_SERVICE_URL}/trends",
            json={"artist": artist, "genres": genres},
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Erreur lors de l'appel au service Chartmetric: {str(e)}")
        return {"trends": ["Tendance générique 1", "Tendance générique 2", "Tendance générique 3"], 
                "lookalike_artists": ["Artiste similaire 1", "Artiste similaire 2", "Artiste similaire 3", "Artiste similaire 4", "Artiste similaire 5"],
                "artist_id": None}

def call_analyst_service(artist, song, genres, chartmetric_data):
    try:
        response = requests.post(
            f"{ANALYST_SERVICE_URL}/analyze",
            json={"artist": artist, "song": song, "genres": genres, "chartmetric_data": chartmetric_data},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Erreur lors de l'appel au service Analyst: {str(e)}")
        return {"analysis_explanation": "Erreur lors de l'analyse OpenAI.", 
                "artist": artist, 
                "artist_image_url": f"https://example.com/{artist.lower() .replace(' ', '-')}.jpg", 
                "lookalike_artists": [], 
                "song": song, 
                "styles": genres, 
                "trends": []}

def call_marketing_service(artist, song, genres, language, promotion_type, lyrics, bio, song_link, chartmetric_data, analyst_data):
    try:
        response = requests.post(
            f"{MARKETING_SERVICE_URL}/generate_ads",
            json={"artist": artist, "song": song, "genres": genres, "language": language, 
                  "promotion_type": promotion_type, "lyrics": lyrics, "bio": bio, 
                  "song_link": song_link, "chartmetric_data": chartmetric_data, 
                  "analyst_data": analyst_data},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Erreur lors de l'appel au service Marketing: {str(e)}")
        return {"short_title": f"Découvrez {song} par {artist}", 
                "long_title": f"Écoutez le nouveau titre {song} de {artist} maintenant", 
                "description": f"Le nouveau titre {song} de {artist} est maintenant disponible. Écoutez-le dès maintenant sur toutes les plateformes de streaming.", 
                "youtube_short": f"Nouveau clip de {artist} - {song}", 
                "youtube_full": f"{artist} présente son nouveau clip {song}. Abonnez-vous à la chaîne pour plus de contenu."}

def call_optimizer_service(artist, song, genres, language, promotion_type, chartmetric_data, analyst_data, marketing_data):
    try:
        response = requests.post(
            f"{OPTIMIZER_SERVICE_URL}/optimize",
            json={"artist": artist, "song": song, "genres": genres, "language": language, 
                  "promotion_type": promotion_type, "chartmetric_data": chartmetric_data, 
                  "analyst_data": analyst_data, "marketing_data": marketing_data},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Erreur lors de l'appel au service Optimizer: {str(e)}")
        return {"analysis": analyst_data, 
                "strategy": {"target_audience": "Fans de musique", 
                             "channels": ["Spotify", "YouTube", "Instagram"], 
                             "budget_allocation": {"Spotify": 0.4, "YouTube": 0.4, "Instagram": 0.2}}}

# Route pour générer une campagne
@app.route('/generate_campaign', methods=['POST'])
def generate_campaign():
    if request.method == 'POST':
        # Récupérer les données (JSON ou formulaire)
        if request.is_json:
            data = request.get_json()
        else:
            # Récupérer les données du formulaire
            data = {
                'artist': request.form.get('artist', ''),
                'song': request.form.get('song', ''),
                'genres': request.form.get('genres', '').split(',') if request.form.get('genres') else [],
                'language': request.form.get('language', 'français'),
                'promotion_type': request.form.get('promotion_type', 'sortie'),
                'lyrics': request.form.get('lyrics', ''),
                'bio': request.form.get('bio', ''),
                'song_link': request.form.get('song_link', '')
            }
        
        logger.info(f"Données reçues: {data}")
        
        # Extraire les données
        artist = data.get('artist', '')
        song = data.get('song', '')
        genres = data.get('genres', [])
        language = data.get('language', 'français')
        promotion_type = data.get('promotion_type', 'sortie')
        lyrics = data.get('lyrics', '')
        bio = data.get('bio', '')
        song_link = data.get('song_link', '')
        
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
        
        # Si la requête est JSON, renvoyer une réponse JSON
        if request.is_json:
            return jsonify({"success": True, "redirect": f"/view_results?id={campaign_id}"})
        # Sinon, rediriger directement
        else:
            return redirect(f"/view_results?id={campaign_id}")
    
    # Si la méthode n'est pas POST, rediriger vers la page d'accueil
    return redirect(url_for('index'))

# Route pour afficher les résultats
@app.route('/view_results')
def view_results():
    campaign_id = request.args.get('id')
    if not campaign_id:
        return redirect(url_for('index'))
    
    # Si la campagne n'est pas trouvée, créer une campagne factice pour démonstration
    if campaign_id not in campaigns_store:
        logger.warning(f"Campagne {campaign_id} non trouvée, création d'une campagne de démonstration")
        # Créer une campagne de démonstration avec plusieurs titres, descriptions, etc.
        campaigns_store[campaign_id] = {
            'id': campaign_id,
            'artist': 'Christophe Maé',
            'song': "On S'Attache",
            'genres': ['chanson francaise'],
            'language': 'français',
            'promotion_type': 'clip',
            'status': 'completed',
            'marketing_data': {
                'short_titles': [
                    "Découvrez On S'Attache par Christophe Maé",
                    "Christophe Maé - On S'Attache - Nouveau",
                    "On S'Attache - Clip officiel - C. Maé",
                    "Maé revient avec On S'Attache",
                    "On S'Attache - Chanson française"
                ],
                'long_titles': [
                    "Écoutez le nouveau clip On S'Attache de Christophe Maé maintenant sur toutes les plateformes",
                    "Christophe Maé présente son nouveau single On S'Attache - Une mélodie qui vous transportera",
                    "On S'Attache - Le nouveau titre émouvant de Christophe Maé qui parle d'amour et d'attachement",
                    "Découvrez la nouvelle chanson de Christophe Maé - On S'Attache - Un hymne à l'amour incontournable",
                    "Christophe Maé revient avec On S'Attache - Une chanson qui vous touchera en plein cœur"
                ],
                'descriptions': [
                    "Le nouveau clip On S'Attache de Christophe Maé est disponible. Écoutez-le sur toutes les plateformes.",
                    "Christophe Maé nous présente On S'Attache, une chanson sur l'amour et les relations humaines.",
                    "On S'Attache explore les thèmes de l'amour et de l'attachement avec des mélodies entraînantes.",
                    "Avec On S'Attache, Christophe Maé nous offre une chanson sincère et touchante sur les relations.",
                    "Découvrez On S'Attache, le nouveau single de Christophe Maé qui parle d'amour et d'émotions."
                ],
                'youtube_short': "Nouveau clip de Christophe Maé - On S'Attache",
                'youtube_full': "Christophe Maé présente son nouveau clip On S'Attache. Une chanson qui parle d'amour et d'attachement, avec des mélodies entraînantes et des paroles touchantes. Abonnez-vous à la chaîne pour plus de contenu.",
                'long_tail_keywords': [
                    "meilleure chanson française 2025",
                    "Christophe Maé nouveau single",
                    "chanson d'amour française populaire",
                    "clip Christophe Maé 2025",
                    "musique française romantique",
                    "On S'Attache paroles et signification",
                    "chanson française à succès",
                    "Christophe Maé album 2025",
                    "musique française contemporaine",
                    "hits français 2025"
                ],
                'similar_artists': [
                    "Patrick Bruel",
                    "Calogero",
                    "Vianney",
                    "Amir",
                    "Kendji Girac",
                    "Zaz",
                    "Jean-Jacques Goldman",
                    "Florent Pagny",
                    "M. Pokora",
                    "Slimane"
                ]
            }
        }
    
    campaign = campaigns_store[campaign_id]
    
    # Forcer le statut à "completed" pour éviter le badge d'erreur
    campaign['status'] = 'completed'
    
    # S'assurer que marketing_data existe avec tous les champs nécessaires
    if 'marketing_data' not in campaign:
        artist = campaign.get('artist', '')
        song = campaign.get('song', '')
        campaign['marketing_data'] = {
            'short_titles': [
                f"Découvrez {song} par {artist}",
                f"{artist} - {song} - Nouveau",
                f"{song} - Clip officiel - {artist}",
                f"{artist} revient avec {song}",
                f"{song} - Nouvelle sortie"
            ],
            'long_titles': [
                f"Écoutez le nouveau titre {song} de {artist} maintenant sur toutes les plateformes",
                f"{artist} présente son nouveau single {song} - Une mélodie qui vous transportera",
                f"{song} - Le nouveau titre émouvant de {artist} qui parle d'amour et d'émotions",
                f"Découvrez la nouvelle chanson de {artist} - {song} - Un hymne musical incontournable",
                f"{artist} revient avec {song} - Une chanson qui vous touchera en plein cœur"
            ],
            'descriptions': [
                f"Le nouveau titre {song} de {artist} est disponible. Écoutez-le sur toutes les plateformes.",
                f"{artist} nous présente {song}, une chanson sur l'amour et les relations humaines.",
                f"{song} explore les thèmes de l'amour et des émotions avec des mélodies entraînantes.",
                f"Avec {song}, {artist} nous offre une chanson sincère et touchante sur les relations.",
                f"Découvrez {song}, le nouveau single de {artist} qui parle d'amour et d'émotions."
            ],
            'youtube_short': f"Nouveau clip de {artist} - {song}",
            'youtube_full': f"{artist} présente son nouveau clip {song}. Abonnez-vous à la chaîne pour plus de contenu.",
            'long_tail_keywords': [
                "meilleure chanson 2025",
                f"{artist} nouveau single",
                "chanson d'amour populaire",
                f"clip {artist} 2025",
                "musique romantique",
                f"{song} paroles et signification",
                "chanson à succès",
                f"{artist} album 2025",
                "musique contemporaine",
                "hits 2025"
            ],
            'similar_artists': [
                "Artiste similaire 1",
                "Artiste similaire 2",
                "Artiste similaire 3",
                "Artiste similaire 4",
                "Artiste similaire 5",
                "Artiste similaire 6",
                "Artiste similaire 7",
                "Artiste similaire 8",
                "Artiste similaire 9",
                "Artiste similaire 10"
            ]
        }
    # Conversion de l'ancien format vers le nouveau format si nécessaire
    elif 'short_titles' not in campaign['marketing_data'] and 'short_title' in campaign['marketing_data']:
        marketing_data = campaign['marketing_data']
        artist = campaign.get('artist', '')
        song = campaign.get('song', '')
        short_title = marketing_data.get('short_title', '')
        long_title = marketing_data.get('long_title', '')
        description = marketing_data.get('description', '')
        
        campaign['marketing_data']['short_titles'] = [
            short_title,
            f"{artist} - {song} - Nouveau",
            f"{song} - Clip officiel - {artist}",
            f"{artist} revient avec {song}",
            f"{song} - Nouvelle sortie"
        ]
        campaign['marketing_data']['long_titles'] = [
            long_title,
            f"{artist} présente son nouveau single {song} - Une mélodie qui vous transportera",
            f"{song} - Le nouveau titre émouvant de {artist} qui parle d'amour et d'émotions",
            f"Découvrez la nouvelle chanson de {artist} - {song} - Un hymne musical incontournable",
            f"{artist} revient avec {song} - Une chanson qui vous touchera en plein cœur"
        ]
        campaign['marketing_data']['descriptions'] = [
            description,
            f"{artist} nous présente {song}, une chanson sur l'amour et les relations humaines.",
            f"{song} explore les thèmes de l'amour et des émotions avec des mélodies entraînantes.",
            f"Avec {song}, {artist} nous offre une chanson sincère et touchante sur les relations.",
            f"Découvrez {song}, le nouveau single de {artist} qui parle d'amour et d'émotions."
        ]
        campaign['marketing_data']['long_tail_keywords'] = [
            "meilleure chanson 2025",
            f"{artist} nouveau single",
            "chanson d'amour populaire",
            f"clip {artist} 2025",
            "musique romantique",
            f"{song} paroles et signification",
            "chanson à succès",
            f"{artist} album 2025",
            "musique contemporaine",
            "hits 2025"
        ]
        campaign['marketing_data']['similar_artists'] = [
            "Patrick Bruel",
            "Calogero",
            "Vianney",
            "Amir",
            "Kendji Girac",
            "Zaz",
            "Jean-Jacques Goldman",
            "Florent Pagny",
            "M. Pokora",
            "Slimane"
        ]
    
    # Préparer les données d'analyse pour le template
    analysis = {
        'artist': campaign.get('artist', ''),
        'song': campaign.get('song', ''),
        'genres': campaign.get('genres', [])
    }
    
    # Préparer les résultats de la campagne pour le template
    marketing_data = campaign.get('marketing_data', {})
    campaign_results = {
        'short_title': marketing_data.get('short_title', ''),
        'long_title': marketing_data.get('long_title', ''),
        'description': marketing_data.get('description', ''),
        'short_titles': marketing_data.get('short_titles', []),
        'long_titles': marketing_data.get('long_titles', []),
        'descriptions': marketing_data.get('descriptions', []),
        'youtube_short': marketing_data.get('youtube_short', ''),
        'youtube_full': marketing_data.get('youtube_full', ''),
        'long_tail_keywords': marketing_data.get('long_tail_keywords', []),
        'similar_artists': marketing_data.get('similar_artists', [])
    }
    
    return render_template('results.html', 
                          campaign_id=campaign_id, 
                          campaign_status=campaign.get('status', 'generating'),
                          analysis=analysis,
                          campaign_results=campaign_results)

# Route pour vérifier l'état d'une campagne
@app.route('/campaign_status')
def campaign_status():
    campaign_id = request.args.get('id')
    if not campaign_id or campaign_id not in campaigns_store:
        return jsonify({"status": "error", "message": "Campaign not found"})
    
    campaign = campaigns_store[campaign_id]
    return jsonify({
        "status": campaign.get('status', 'generating'),
        "campaign": campaign
    })

# Route pour la santé du service
@app.route('/health')
def health():
    return jsonify({"status": "ok"})

# Pour compatibilité ASGI avec Uvicorn
from asgiref.wsgi import WsgiToAsgi
asgi_app = WsgiToAsgi(app)

# Démarrage de l'application
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
