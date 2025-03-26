import logging
import asyncio
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class ChartmetricClient:
    def __init__(self, auth_manager, cache_manager):
        self.auth_manager = auth_manager
        self.cache_manager = cache_manager
        self.base_url = os.getenv("CHARTMETRIC_API_BASE_URL", "https://api.chartmetric.com/api")
        self.max_retries = 5
        self.retry_delay = 1
        
    async def request(self, session, endpoint, method="GET", params=None, data=None, cache_key=None, cache_ttl=None):
        if cache_key and self.cache_manager:
            cached_data = self.cache_manager.get(cache_key)
            if cached_data:
                logger.debug(f"Données récupérées depuis le cache pour la clé: {cache_key}")
                return cached_data
                
        url = f"{self.base_url}{endpoint}"
        headers = {"Content-Type": "application/json"}
        
        for attempt in range(self.max_retries):
            try:
                access_token = await self.auth_manager.get_access_token(session)
                headers["Authorization"] = f"Bearer {access_token}"
                logger.debug(f"Tentative {attempt + 1}/{self.max_retries} pour {method} {url}")
                if method.upper() == "GET":
                    async with session.get(url, params=params, headers=headers) as response:
                        response.raise_for_status()
                        result = await response.json()
                elif method.upper() == "POST":
                    async with session.post(url, json=data, headers=headers) as response:
                        response.raise_for_status()
                        result = await response.json()
                else:
                    raise ValueError(f"Méthode HTTP non supportée: {method}")
                if cache_key and self.cache_manager:
                    self.cache_manager.set(cache_key, result, cache_ttl)
                    logger.debug(f"Données mises en cache pour la clé: {cache_key}")
                return result
            except aiohttp.ClientResponseError as e:
                if e.status == 401 and attempt < self.max_retries - 1:
                    logger.warning(f"Token expiré, renouvellement forcé (tentative {attempt + 1})")
                    await self.auth_manager.refresh_access_token(session)
                    continue
                if e.status == 429 and attempt < self.max_retries - 1:
                    retry_after = int(e.headers.get("Retry-After", self.retry_delay * (2 ** attempt)))
                    logger.warning(f"Rate limit atteint, attente de {retry_after}s avant retry (tentative {attempt + 1})")
                    await asyncio.sleep(retry_after)
                    continue
                logger.error(f"Erreur API Chartmetric ({e.status}): {str(e)}")
                raise
            except Exception as e:
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.warning(f"Erreur lors de la requête, attente de {wait_time}s avant retry (tentative {attempt + 1}): {str(e)}")
                    await asyncio.sleep(wait_time)
                    continue
                logger.error(f"Erreur lors de la requête Chartmetric après {self.max_retries} tentatives: {str(e)}")
                raise
        
    async def search_artist(self, session, name, limit=5):
        endpoint = "/artist"
        params = {"name": name, "limit": limit}
        cache_key = f"search_artist_{name}_{limit}"
        return await self.request(session, endpoint, params=params, cache_key=cache_key, cache_ttl=86400)
        
    async def get_artist(self, session, artist_id):
        endpoint = f"/artist/{artist_id}"
        cache_key = f"artist_{artist_id}"
        return await self.request(session, endpoint, cache_key=cache_key, cache_ttl=86400)
        
    async def get_similar_artists(self, session, artist_id, limit=5):
        endpoint = f"/artist/{artist_id}/neighboring"
        params = {"limit": limit}
        cache_key = f"similar_artists_{artist_id}_{limit}"
        return await self.request(session, endpoint, params=params, cache_key=cache_key, cache_ttl=86400)
        
    async def get_trends_by_genre(self, session, genre):
        endpoint = "/artist"
        params = {"genre": genre, "limit": 10, "sort": "popularity"}
        cache_key = f"trends_genre_{genre}"
        return await self.request(session, endpoint, params=params, cache_key=cache_key, cache_ttl=86400)
