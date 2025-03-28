from fastapi import FastAPI
import os
from dotenv import load_dotenv
import logging
from api.routes import register_routes  # Vous devrez adapter cette fonction pour FastAPI
from auth.chartmetric_auth import ChartmetricAuth
from cache.cache_manager import CacheManager
from client.chartmetric_client import ChartmetricClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()
chartmetric_refresh_token = os.getenv("CHARTMETRIC_REFRESH_TOKEN")

if not chartmetric_refresh_token:
    logger.critical("CHARTMETRIC_REFRESH_TOKEN manquant")
    raise ValueError("CHARTMETRIC_REFRESH_TOKEN manquant")

app = FastAPI(title="Chartmetric Service", version="1.0.0")

# Initialisation avec le TTL par défaut de 3600 secondes (1 heure)
cache_manager = CacheManager(default_ttl=3600)
auth_manager = ChartmetricAuth(chartmetric_refresh_token)
chartmetric_client = ChartmetricClient(auth_manager, cache_manager)

# Vous devrez adapter cette fonction pour FastAPI
# register_routes(app, chartmetric_client)

@app.get('/health')
async def health_check():
    return {
        "status": "healthy",
        "service": "Chartmetric Service",
        "version": "1.0.0"
    }

# Exemple de route adaptée pour FastAPI
# @app.get('/api/artist/{artist_id}')
# async def get_artist(artist_id: int):
#     return await chartmetric_client.get_artist(artist_id)
