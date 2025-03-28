import asyncio
import logging
import os
from flask import Flask, render_template, request, jsonify
import aiohttp
from jinja2 import Environment, FileSystemLoader
from asgiref.wsgi import WsgiToAsgi

# Créer l'application Flask avec le chemin correct vers les templates
app = Flask(__name__, 
           template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__) ), 'templates'))

# Configuration des logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration de Jinja2 avec un chemin absolu
current_dir = os.path.dirname(os.path.abspath(__file__))
templates_dir = os.path.join(current_dir, 'templates')
env = Environment(loader=FileSystemLoader(templates_dir))

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

# Créer l'application ASGI à partir de l'application WSGI
asgi_app = WsgiToAsgi(app)
