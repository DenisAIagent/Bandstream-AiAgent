import time
import logging
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class ChartmetricAuth:
    def __init__(self, refresh_token=None):
        self.refresh_token = refresh_token or os.getenv("CHARTMETRIC_REFRESH_TOKEN")
        if not self.refresh_token:
            raise ValueError("Refresh token Chartmetric non fourni")
        self.base_url = os.getenv("CHARTMETRIC_API_BASE_URL", "https://api.chartmetric.com/api")
        self.access_token = None
        self.expires_at = 0
        
    async def get_access_token(self, session):
        current_time = int(time.time())
        if not self.access_token or current_time >= self.expires_at - 300:
            logger.info("Access token expiré ou non existant, renouvellement...")
            await self.refresh_access_token(session)
        return self.access_token
        
    async def refresh_access_token(self, session):
        url = f"{self.base_url}/token"
        data = {"refreshtoken": self.refresh_token}
        headers = {"Content-Type": "application/json"}
        try:
            logger.debug(f"Demande d'un nouveau access token à {url}")
            async with session.post(url, json=data, headers=headers) as response:
                response.raise_for_status()
                result = await response.json()
                self.access_token = result.get("token")
                expires_in = result.get("expires_in", 3600)
                self.expires_at = int(time.time()) + expires_in
                if not self.access_token:
                    raise ValueError("Access token non trouvé dans la réponse Chartmetric")
                logger.info(f"Nouveau access token obtenu, valide jusqu'à {time.ctime(self.expires_at)}")
                return self.access_token
        except aiohttp.ClientResponseError as e:
            logger.error(f"Erreur HTTP lors de l'obtention de l'access token: {e.status} - {e.message}")
            raise
        except Exception as e:
            logger.error(f"Erreur lors de l'obtention de l'access token: {str(e)}")
            raise
