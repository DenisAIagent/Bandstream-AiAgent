from flask import Flask, request, jsonify
import openai
import os
from dotenv import load_dotenv
from cachetools import TTLCache
import logging
import json
import re

app = Flask(__name__)

# Configuration des logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Chargement des variables d'environnement
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    logger.critical("OPENAI_API_KEY manquant")
    raise ValueError("OPENAI_API_KEY manquant")

# Cache avec TTL de 24h
cache = TTLCache(maxsize=100, ttl=86400)

def generate_prompt(data):
    # Extraction et validation des données
    artist = data.get('artist', 'Artiste Inconnu')
    song = data.get('song', '')
    genres = data.get('genres', ['rock']) if isinstance(data.get('genres'), list) else [data.get('genres', 'rock')]
    language = data.get('language', 'français')
    tone = data.get('tone', 'authentique')
    promotion_type = data.get('promotion_type', 'sortie')
    song_link = data.get('song_link', '[insert link]')
    bio_summary = data.get('bio', f"Artiste passionné par {genres[0]} avec une approche unique.")
    bio_tone = data.get('bio_tone', 'authentique')
    bio_themes = data.get('bio_themes', 'émotion, créativité')
    target_audience = data.get('target_audience', 'tous publics')
    announcement_style = data.get('announcement_style', 'Sérieux')  # Nouvel élément pour le style des annonces

    # Déterminer les artistes similaires et tendances en fonction des genres
    lookalike_artists = {
        "rock": ["Nirvana", "Pearl Jam", "Soundgarden"],
        "punk": ["Green Day", "The Offspring", "Blink-182"],
        "grunge": ["Nirvana", "Alice in Chains", "Soundgarden"],
        "pop": ["Coldplay", "Imagine Dragons", "Maroon 5"],
        "metal": ["Metallica", "Rammstein", "Nightwish"],
        "default": ["Artiste 1", "Artiste 2", "Artiste 3"]
    }
    trends = {
        "rock": ["best rock song 2025", "best playlist rock 2025", "top grunge bands 2025"],
        "punk": ["best punk song 2025", "top punk bands 2025", "punk revival 2025"],
        "grunge": ["best grunge song 2025", "grunge revival 2025", "top grunge bands 2025"],
        "pop": ["best pop song 2025", "top pop hits 2025", "pop chart toppers 2025"],
        "metal": ["best metal song 2025", "top metal bands 2025", "metal symphonique 2025"],
        "default": ["Trend 1", "Trend 2", "Trend 3"]
    }
    primary_genre = genres[0].lower()
    selected_lookalikes = lookalike_artists.get(primary_genre, lookalike_artists["default"])
    selected_trends = trends.get(primary_genre, trends["default"])

    # Nouveau prompt amélioré incluant la recherche internet et le style des annonces
    prompt = f"""
OBJECTIF :
Générer du contenu marketing pour promouvoir la {promotion_type} de l'artiste {artist} autour de la chanson "{song}". Le contenu doit être rédigé en {language} et refléter l'ambiance et le style de {genres[0]} avec un ton {bio_tone}. La réponse devra être un objet JSON structuré, prêt à intégrer dans une page web, en respectant strictement les limites de caractères indiquées. Utilisez toute la puissance de GPT-4o pour la rédaction et, si nécessaire, effectuez des recherches sur internet afin d'enrichir les données et compléter les éléments manquants ou obsolètes.

VARIABLES :
- promotion_type : "{promotion_type}"
- artiste : "{artist}"
- chanson : "{song}"
- genres : "{', '.join(genres)}"
- langue : "{language}"
- ton général : "{tone}"
- style des annonces : "{announcement_style}" (Engageant = Fomo et descriptif, Poétique = envolée lyrique et honirique, Humoristique = avec une tendance à l'humour et sarcasme, Sérieux = purement descriptif)
- lien chanson : "{song_link}"
- biographie : "{bio_summary}" (thèmes : {bio_themes})
- public cible : "{target_audience}"

INSTRUCTIONS :

1. Adaptez l'ensemble des contenus (titres, descriptions, etc.) au style des annonces spécifié. Veuillez vous assurer que le ton global reflète ce style :
   - Engageant : induire un sentiment d'urgence (FOMO) et être descriptif.
   - Poétique : adopter une envolée lyrique et honirique.
   - Humoristique : intégrer de l'humour et du sarcasme.
   - Sérieux : rester purement descriptif.

2. TITRES COURTS
   - Générer 5 titres courts, chacun ne dépassant pas 30 caractères.
   - Exemple : "Riffs & Révolte", "Énergie {song}", "Vibrez Ensemble".
   - Au moins 2 titres doivent mentionner la chanson "{song}".
   - Utiliser le vocabulaire spécifique à {genres[0]} et intégrer un élément thématique issu de {bio_themes}.

3. TITRES LONGS
   - Générer 5 titres longs, chacun ne dépassant pas 55 caractères.
   - Exemple : "Découvrez {song} par {artist}", "Plongez dans l'univers {genres[0]}".
   - Au moins 2 titres doivent mentionner la chanson "{song}" et 1 titre doit mentionner l'artiste "{artist}".
   - Incorporer des éléments descriptifs en lien avec la biographie.

4. DESCRIPTIONS LONGUES
   - Créer 5 descriptions, chacune ne dépassant pas 80 caractères.
   - Exemple : "Vibrez avec {song} – énergie et passion en live !".
   - Au moins 2 descriptions doivent mentionner la chanson "{song}" et 2 l'artiste "{artist}".
   - Varier les formulations et éviter les phrases génériques.

5. DESCRIPTION YOUTUBE COURTE
   - Générer une description concise (max 120 caractères).
   - Exemple : "Découvrez {song} – un mix explosif, à écouter sans modération !"
   - Inclure un appel à
