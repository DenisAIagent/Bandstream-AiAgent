from quart import Quart, jsonify
import os
from dotenv import load_dotenv
import logging
from api.routes import register_routes
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

# Initialisation de l'application
app = Quart(__name__)

# Ajout de la configuration manquante pour éviter l'erreur KeyError
app.config['PROVIDE_AUTOMATIC_OPTIONS'] = True

# Initialisation des gestionnaires
cache_manager = CacheManager(default_ttl=3600)  # 1 heure par défaut
auth_manager = ChartmetricAuth(chartmetric_refresh_token)
chartmetric_client = ChartmetricClient(auth_manager, cache_manager)

# Enregistrement des routes
register_routes(app, chartmetric_client)

# Route de santé
@app.route('/health', methods=['GET'])
async def health_check():
    return jsonify({
        "status": "healthy",
        "service": "Chartmetric Service",
        "version": "1.0.0"
    })

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=8080)
