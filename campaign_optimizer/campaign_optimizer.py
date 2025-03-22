import os
import json
import asyncio
import aiohttp
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import logging
import googleapiclient.discovery
import googleapiclient.errors
import serpapi

# Configurer les logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Charger les variables d'environnement
load_dotenv()

# Initialiser Flask
app = Flask(__name__)
logger.info("Flask application initialized.")

# URLs des services
CAMPAIGN_ANALYST_URL = os.getenv("CAMPAIGN_ANALYST_URL", "https://analyst-production.up.railway.app")

# Configurer la clé API YouTube Data v3
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
if not YOUTUBE_API_KEY:
    logger.error("YOUTUBE_API_KEY is not set in environment variables")
    raise ValueError("YOUTUBE_API_KEY is required for YouTube Data API")

# Configurer la clé API SerpAPI
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
if not SERPAPI_KEY:
    logger.error("SERPAPI_KEY is not set in environment variables")
    raise ValueError("SERPAPI_KEY is required for SerpAPI")

# Initialiser le client YouTube Data API
youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

# Fonction pour nettoyer et valider les données
def sanitize_data(data):
    """Nettoie et valide les données avant de les passer au template."""
    if isinstance(data, dict):
        return {k: sanitize_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_data(item) for item in data]
    elif isinstance(data, str):
        return data.strip().rstrip(';')
    else:
        return data

# Fonction pour effectuer une recherche sur YouTube et extraire les mots-clés long tail et les artistes
def search_youtube_for_trends_and_artists(styles):
    logger.info(f"Searching YouTube for trends and artists with styles: {styles}")
    try:
        # Créer une requête de recherche basée sur les styles
        query = f"{' '.join(styles)} 2025"
        request = youtube.search().list(
            part="snippet",
            q=query,
            type="video",
            maxResults=3,  # Limiter aux 3 premiers résultats
            order="relevance"
        )
        response = request.execute()

        # Extraire les mots-clés long tail et les artistes
        long_tail_keywords = []
        artists = []

        for item in response.get("items", []):
            title = item["snippet"]["title"]
            description = item["snippet"]["description"]
            channel_title = item["snippet"]["channelTitle"]

            # Extraire les mots-clés long tail à partir du titre
            title_lower = title.lower()
            for style in styles:
                style_lower = style.lower()
                if style_lower in title_lower:
                    # Supprimer le nom de l'artiste et le style pour isoler les mots-clés long tail
                    keyword = title_lower.replace(style_lower, "").strip()
                    # Supprimer les noms d'artistes connus pour ne garder que les mots-clés
                    known_artists = [
                        "foo fighters", "christophe maé", "various artists", "line renaud",
                        "serge lama", "michel tor", "edith piaf", "les compagnons de la chanson",
                        "bruce springsteen", "the beatles", "amir", "vianney", "louane",
                        "m pokora", "patrick bruel"
                    ]
                    for artist_name in known_artists:
                        keyword = keyword.replace(artist_name.lower(), "").strip()
                    # Nettoyer les mots-clés (supprimer les caractères spéciaux, etc.)
                    keyword = ' '.join(keyword.split()).replace('-', '').replace('  ', ' ')
                    if keyword and len(keyword) > 5 and keyword not in long_tail_keywords:  # Éviter les mots-clés trop courts ou vides
                        long_tail_keywords.append(keyword[:50])  # Limiter à 50 caractères

            # Extraire les artistes à partir du titre et du nom de la chaîne
            for artist_name in known_artists:
                if artist_name.lower() in title_lower or artist_name.lower() in channel_title.lower():
                    if artist_name not in artists:
                        artists.append(artist_name)

        logger.info(f"YouTube trends: {long_tail_keywords}, Artists: {artists}")
        return long_tail_keywords, artists

    except googleapiclient.errors.HttpError as e:
        logger.error(f"Error searching YouTube: {str(e)}")
        return [], []
    except Exception as e:
        logger.error(f"Unexpected error during YouTube search: {str(e)}")
        return [], []

# Fonction pour effectuer une recherche via SerpAPI et extraire les mots-clés long tail et les artistes
def search_serpapi_for_trends_and_artists(styles):
    logger.info(f"Searching SerpAPI for trends and artists with styles: {styles}")
    try:
        # Créer une requête de recherche basée sur les styles
        query = f"{' '.join(styles)} 2025"
        params = {
            "q": query,
            "api_key": SERPAPI_KEY,
            "num": 3  # Limiter aux 3 premiers résultats
        }
        search = serpapi.GoogleSearch(params)
        results = search.get_dict()

        # Extraire les mots-clés long tail et les artistes
        long_tail_keywords = []
        artists = []

        for result in results.get("organic_results", [])[:3]:
            title = result.get("title", "").lower()
            snippet = result.get("snippet", "").lower()

            # Extraire les mots-clés long tail à partir du titre
            for style in styles:
                style_lower = style.lower()
                if style_lower in title:
                    # Supprimer le nom de l'artiste et le style pour isoler les mots-clés long tail
                    keyword = title.replace(style_lower, "").strip()
                    # Supprimer les noms d'artistes connus pour ne garder que les mots-clés
                    known_artists = [
                        "foo fighters", "christophe maé", "various artists", "line renaud",
                        "serge lama", "michel tor", "edith pia
