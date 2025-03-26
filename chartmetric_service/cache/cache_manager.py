import time
import logging
import os
from cachetools import TTLCache
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class CacheManager:
    def __init__(self):
        self.default_ttl = int(os.getenv("CACHE_DEFAULT_TTL", 3600))
        self.max_size = int(os.getenv("CACHE_MAX_SIZE", 1000))
        self.cache = TTLCache(maxsize=self.max_size, ttl=self.default_ttl)
        self.expiry_times = {}
        logger.info(f"Cache initialisé avec TTL par défaut de {self.default_ttl}s et taille max de {self.max_size}")
        
    def get(self, key):
        try:
            value = self.cache.get(key)
            if value is not None:
                logger.debug(f"Cache hit pour la clé: {key}")
                return value
            logger.debug(f"Cache miss pour la clé: {key}")
            return None
        except Exception as e:
            logger.error(f"Erreur lors de la récupération depuis le cache: {str(e)}")
            return None
        
    def set(self, key, value, ttl=None):
        try:
            self.cache[key] = value
            if ttl is not None:
                expiry = time.time() + ttl
                self.expiry_times[key] = expiry
                logger.debug(f"Valeur mise en cache pour la clé: {key} avec TTL personnalisé de {ttl}s")
            else:
                logger.debug(f"Valeur mise en cache pour la clé: {key} avec TTL par défaut")
        except Exception as e:
            logger.error(f"Erreur lors de la mise en cache: {str(e)}")
            
    def invalidate(self, key):
        try:
            if key in self.cache:
                del self.cache[key]
                if key in self.expiry_times:
                    del self.expiry_times[key]
                logger.debug(f"Entrée de cache invalidée pour la clé: {key}")
        except Exception as e:
            logger.error(f"Erreur lors de l'invalidation du cache: {str(e)}")
            
    def invalidate_pattern(self, pattern):
        try:
            keys_to_delete = [k for k in self.cache.keys() if pattern in k]
            for key in keys_to_delete:
                self.invalidate(key)
            logger.debug(f"{len(keys_to_delete)} entrées de cache invalidées pour le motif: {pattern}")
        except Exception as e:
            logger.error(f"Erreur lors de l'invalidation du cache par motif: {str(e)}")
            
    def clear(self):
        try:
            self.cache.clear()
            self.expiry_times.clear()
            logger.info("Cache entièrement vidé")
        except Exception as e:
            logger.error(f"Erreur lors du vidage du cache: {str(e)}")
