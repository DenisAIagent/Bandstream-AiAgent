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
    announcement_style = data.get('announcement_style', 'Sérieux')  # Style des annonces

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

    # Nouveau prompt amélioré avec exemples inspirés de vos annonces
    prompt = f"""
OBJECTIF :
Générer du contenu marketing pour promouvoir la {promotion_type} de l'artiste {artist} autour de la chanson "{song}". Le contenu doit être rédigé en {language} et refléter l'ambiance et le style de {genres[0]} avec un ton {bio_tone}. La réponse devra être un objet JSON structuré, prêt à intégrer dans une page web, en respectant strictement les limites de caractères indiquées. Utilisez toute la puissance de GPT-4o et, si nécessaire, effectuez des recherches sur internet pour enrichir les données.

VARIABLES :
- promotion_type : "{promotion_type}"
- artiste : "{artist}"
- chanson : "{song}"
- genres : "{', '.join(genres)}"
- langue : "{language}"
- ton général : "{tone}"
- style des annonces : "{announcement_style}" (Engageant = Fomo et descriptif, Poétique = envolée lyrique et honirique, Humoristique = humour et sarcasme, Sérieux = purement descriptif)
- lien chanson : "{song_link}"
- biographie : "{bio_summary}" (thèmes : {bio_themes})
- public cible : "{target_audience}"

INSTRUCTIONS :

1. Adaptez l'ensemble des contenus (titres, descriptions, etc.) au style des annonces spécifié.

2. TITRES COURTS (max 30 caractères)  
   Exemples à suivre :  
   - "Nouveau Clip Jeanne Cherhal"  
   - "Jeanne Cherhal avec Dedienne"  
   - "Jeanne Cherhal présente Jean"  
   - "Jeanne Cherhal duo complice"  
   - "Jeanne Cherhal et Jean"

3. TITRES LONGS (max 90 caractères)  
   Exemples à suivre :  
   - "Nouveau Clip Jeanne Cherhal avec l’irrésistible Vincent Dedienne à ses côtés dans Jean"  
   - "Jeanne Cherhal dévoile Jean accompagnée par Vincent Dedienne un clip drôle et charmant"  
   - "Jeanne Cherhal et Vincent Dedienne ensemble dans Jean un moment pétillant à découvrir"  
   - "Jean par Jeanne Cherhal avec Vincent Dedienne une complicité qui fait plaisir à voir"  
   - "Découvrez Jean, le nouveau clip joyeux de Jeanne Cherhal avec le brillant Vincent Dedienne"

4. DESCRIPTIONS AVEC CALL TO ACTION  
   Exemples à suivre :  
   - "Qui est Jean Jeanne Cherhal répond avec humour aux côtés du talentueux Vincent Dedienne"  
   - "Jeanne Cherhal réalise son rêve avec Vincent Dedienne dans son nouveau clip Jean"  
   - "Le nouveau clip Jean de Jeanne Cherhal, complice et drôle avec Vincent Dedienne"  
   - "Découvrez la belle complicité entre Jeanne Cherhal et Vincent Dedienne dans le clip Jean"  
   - "À découvrir dès maintenant, le clip de Jean par Jeanne Cherhal et Vincent Dedienne"

5. DESCRIPTION YOUTUBE  
   La description YouTube doit être structurée en deux parties :  
   - **Courte** (max 120 caractères) : Exemple, "Plongez dans le chaos musical avec Silver Dust !"  
   - **Complète** (max 5000 caractères) : Inclure une introduction (biographie), le corps (détails sur la sortie, lien avec le style et les thèmes, éventuellement les paroles si c'est souhaité), et une conclusion avec appel à l'action, crédits et informations complémentaires.

6. ANALYSE  
   - "trends" : Fournir une liste de 3 mots-clés long tail pour {genres[0]} en 2025, par exemple ["best {genres[0]} song 2025", "top {genres[0]} hits 2025", "influence {genres[0]} 2025"].
   - "lookalike_artists" : Fournir une liste de 3 artistes similaires (exemple pour metal : ["Metallica", "Rammstein", "Nightwish"]).
   - "artist_image_url" : Générer une URL fictive au format "https://example.com/{artist.lower().replace(' ', '-')}.jpg".

FORMAT DE SORTIE ATTENDU (objet JSON) :
{{
  "short_titles": ["titre1", "titre2", "titre3", "titre4", "titre5"],
  "long_titles": ["titre1", "titre2", "titre3", "titre4", "titre5"],
  "long_descriptions": [
    {{"description": "desc1", "character_count": 37}},
    {{"description": "desc2", "character_count": 41}},
    {{"description": "desc3", "character_count": 38}},
    {{"description": "desc4", "character_count": 34}},
    {{"description": "desc5", "character_count": 41}}
  ],
  "youtube_description_short": {{"description": "desc", "character_count": 41}},
  "youtube_description_full": {{"description": "desc", "character_count": 200}},
  "analysis": {{
    "trends": {json.dumps(selected_trends)},
    "lookalike_artists": {json.dumps(selected_lookalikes)},
    "artist_image_url": "https://example.com/{artist.lower().replace(' ', '-')}.jpg"
  }}
}}
"""
    return prompt

@app.route('/generate_ads', methods=['POST'])
def generate_ads():
    try:
        data = request.get_json()
        if not data:
            logger.error("Aucune donnée JSON fournie")
            return jsonify({"error": "Aucune donnée fournie"}), 400

        # Vérification des champs obligatoires
        required_fields = ['artist', 'genres', 'language', 'promotion_type']
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            logger.error(f"Champs manquants : {missing_fields}")
            return jsonify({"error": f"Champs manquants : {missing_fields}"}), 400

        # Clé de cache
        cache_key = "_".join([str(data.get(field, '')) for field in required_fields + ['song', 'tone']])
        logger.info(f"Clé de cache : {cache_key}")

        # Vérification du cache
        if cache_key in cache:
            logger.info(f"Réponse trouvée dans le cache pour : {cache_key}")
            cached_result = cache[cache_key]
            if not cached_result or "short_titles" not in cached_result:
                logger.warning(f"Données en cache vides ou corrompues pour : {cache_key}")
                cache.pop(cache_key)
            else:
                return jsonify(cached_result)

        # Génération du prompt
        prompt = generate_prompt(data)
        logger.info("Prompt généré avec succès")

        # Appel à l'API OpenAI avec GPT-4o
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.7
        )
        result = response.choices[0].message['content']
        logger.info("Réponse OpenAI reçue")

        # Nettoyer la réponse pour enlever les balises ```json ... ```
        result_cleaned = re.sub(r'^```json\n|\n```$', '', result).strip()

        # Vérification que la réponse est un JSON valide
        try:
            result_json = json.loads(result_cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"Réponse OpenAI non-JSON après nettoyage : {result_cleaned}")
            return jsonify({"error": "La génération a échoué : réponse non-JSON"}), 500

        # Vérification des clés attendues
        required_keys = ["short_titles", "long_titles", "long_descriptions", "youtube_description_short", "youtube_description_full", "analysis"]
        missing_keys = [key for key in required_keys if key not in result_json]
        if missing_keys:
            logger.error(f"Clés manquantes dans la réponse JSON : {missing_keys}")
            return jsonify({"error": f"Clés manquantes dans la réponse : {missing_keys}"}), 500

        # Vérification du nombre d'éléments
        if len(result_json["short_titles"]) != 5:
            logger.error(f"Nombre incorrect de short_titles : {len(result_json['short_titles'])}")
            return jsonify({"error": "Nombre incorrect de short_titles"}), 500
        if len(result_json["long_titles"]) != 5:
            logger.error(f"Nombre incorrect de long_titles : {len(result_json['long_titles'])}")
            return jsonify({"error": "Nombre incorrect de long_titles"}), 500
        if len(result_json["long_descriptions"]) != 5:
            logger.error(f"Nombre incorrect de long_descriptions : {len(result_json['long_descriptions'])}")
            return jsonify({"error": "Nombre incorrect de long_descriptions"}), 500

        # Mise en cache et réponse
        cache[cache_key] = result_json
        logger.info(f"Contenu généré et mis en cache pour : {cache_key}")
        return jsonify(result_json)

    except openai.error.OpenAIError as e:
        logger.error(f"Erreur OpenAI : {str(e)}")
        return jsonify({"error": f"Erreur OpenAI : {str(e)}"}), 500
    except Exception as e:
        logger.error(f"Erreur inattendue : {str(e)}")
        return jsonify({"error": f"Erreur interne : {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
