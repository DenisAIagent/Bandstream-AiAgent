from fastapi import FastAPI, Response
import os
from dotenv import load_dotenv
import logging
from api.routes import register_routes  # Fonction adaptée pour FastAPI
from auth.chartmetric_auth import ChartmetricAuth
from cache.cache_manager import CacheManager
from client.chartmetric_client import ChartmetricClient

# Configuration des logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Chargement des variables d'environnement
load_dotenv()
chartmetric_refresh_token = os.getenv("CHARTMETRIC_REFRESH_TOKEN")

if not chartmetric_refresh_token:
    logger.critical("CHARTMETRIC_REFRESH_TOKEN manquant")
    raise ValueError("CHARTMETRIC_REFRESH_TOKEN manquant")

# Initialisation de l'application FastAPI
app = FastAPI(title="Chartmetric Service", version="1.0.0")

# Initialisation des gestionnaires
cache_manager = CacheManager(default_ttl=3600)
auth_manager = ChartmetricAuth(chartmetric_refresh_token)
chartmetric_client = ChartmetricClient(auth_manager, cache_manager)

# Enregistrement des routes
register_routes(app, chartmetric_client)

# Route de santé
@app.get('/health')
async def health_check():
    return {
        "status": "healthy",
        "service": "Chartmetric Service",
        "version": "1.0.0"
    }
