import aiohttp
import logging
import urllib.parse

logger = logging.getLogger(__name__) 

class ChartmetricClient:
    def __init__(self, auth_manager, cache_manager):
        self.auth_manager = auth_manager
        self.cache_manager = cache_manager
    
    async def search_artist(self, artist_name):
        """Recherche un artiste par son nom"""
        cache_key = f"search_artist_{artist_name}"
        cached_result = self.cache_manager.get(cache_key)
        if cached_result:
            return cached_result
            
        token = await self.auth_manager.get_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        # Encoder le nom de l'artiste pour l'URL
        encoded_artist_name = urllib.parse.quote(artist_name)
        
        url = f"https://api.chartmetric.com/api/artist/search?name={encoded_artist_name}"
        
        async with aiohttp.ClientSession()  as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    result = data.get('obj', {}).get('artists', [])
                    self.cache_manager.set(cache_key, result)
                    return result
                else:
                    return []
    
    async def get_similar_artists(self, artist_id):
        """Obtient des artistes similaires à partir d'un ID d'artiste"""
        cache_key = f"similar_artists_{artist_id}"
        cached_result = self.cache_manager.get(cache_key)
        if cached_result:
            return cached_result
            
        token = await self.auth_manager.get_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        url = f"https://api.chartmetric.com/api/artist/{artist_id}/similar"
        
        async with aiohttp.ClientSession()  as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    result = data.get('obj', [])
                    self.cache_manager.set(cache_key, result)
                    return result
                else:
                    return []
    
    async def get_genre_trends(self, genre):
        """Obtient des tendances basées sur un genre musical"""
        cache_key = f"genre_trends_{genre}"
        cached_result = self.cache_manager.get(cache_key)
        if cached_result:
            return cached_result
            
        # Liste de tendances par genre (fictives pour l'instant)
        genre_trends = {
            "metal": ["Collaborations avec des orchestres symphoniques", "Retour aux racines thrash", "Thèmes environnementaux"],
            "metal indus": ["Fusion avec l'électronique", "Visuels cyberpunk", "Sonorités lo-fi industrielles"],
            "rock": ["Influences post-punk", "Collaborations cross-genre", "Thèmes sociaux engagés"],
            "pop": ["Sonorités rétro des années 80", "Collaborations avec des artistes urbains", "Clips TikTok-friendly"]
        }
        
        result = genre_trends.get(genre.lower(), ["Tendance générique 1", "Tendance générique 2", "Tendance générique 3"])
        self.cache_manager.set(cache_key, result)
        return result
