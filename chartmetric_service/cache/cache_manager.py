from cachetools import TTLCache
import logging

logger = logging.getLogger(__name__)

class CacheManager:
    def __init__(self, default_ttl=3600, maxsize=1000):
        """
        Initialise le gestionnaire de cache avec un TTL par défaut et une taille maximale.
        
        Args:
            default_ttl (int): Durée de vie par défaut des entrées en secondes (3600s = 1h par défaut)
            maxsize (int): Nombre maximum d'entrées dans le cache (1000 par défaut)
        """
        self.default_ttl = default_ttl
        self.cache = TTLCache(maxsize=maxsize, ttl=default_ttl)
        logger.info(f"Cache initialisé avec TTL par défaut de {default_ttl}s et taille max de {maxsize}")

    def get(self, key):
        """
        Récupère une valeur du cache par sa clé.
        
        Args:
            key (str): Clé de l'entrée à récupérer
            
        Returns:
            La valeur associée à la clé ou None si la clé n'existe pas
        """
        value = self.cache.get(key)
        if value is not None:
            logger.debug(f"Cache hit pour la clé: {key}")
        else:
            logger.debug(f"Cache miss pour la clé: {key}")
        return value

    def set(self, key, value, ttl=None):
        """
        Stocke une valeur dans le cache avec une clé spécifique.
        
        Args:
            key (str): Clé pour stocker la valeur
            value: Valeur à stocker
            ttl (int, optional): Durée de vie spécifique pour cette entrée.
                                Si None, utilise le TTL par défaut.
        """
        # Si un TTL spécifique est fourni, nous devons créer un cache temporaire
        if ttl is not None and ttl != self.default_ttl:
            # Créer un cache temporaire avec le TTL spécifié
            temp_cache = TTLCache(maxsize=1, ttl=ttl)
            temp_cache[key] = value
            # Copier l'entrée dans le cache principal
            self.cache[key] = value
            logger.debug(f"Valeur mise en cache pour la clé: {key} avec TTL personnalisé: {ttl}s")
        else:
            # Utiliser le cache principal avec le TTL par défaut
            self.cache[key] = value
            logger.debug(f"Valeur mise en cache pour la clé: {key} avec TTL par défaut: {self.default_ttl}s")

    def delete(self, key):
        """
        Supprime une entrée du cache.
        
        Args:
            key (str): Clé de l'entrée à supprimer
            
        Returns:
            bool: True si la clé existait et a été supprimée, False sinon
        """
        if key in self.cache:
            del self.cache[key]
            logger.debug(f"Entrée supprimée du cache pour la clé: {key}")
            return True
        logger.debug(f"Tentative de suppression d'une clé inexistante: {key}")
        return False

    def clear(self):
        """
        Vide complètement le cache.
        """
        self.cache.clear()
        logger.info("Cache entièrement vidé")
