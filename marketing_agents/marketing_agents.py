from flask import Flask, request, jsonify
import openai
import os
from dotenv import load_dotenv
from cachetools import TTLCache
import logging
import json

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
    bio_summary = data.get('bio_summary', f"Artiste passionné par {genres[0]} avec une approche unique.")
    bio_tone = data.get('bio_tone', 'authentique')
    bio_themes = data.get('bio_themes', 'émotion, créativité')
    target_audience = data.get('target_audience', 'tous publics')

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
        "rock": ["Rock Revival", "Live Energy", "Guitar Riffs"],
        "punk": ["Punk Energy", "Rebellion Vibes", "Fast Beats"],
        "grunge": ["Grunge Nostalgia", "Raw Emotion", "90s Revival"],
        "pop": ["Pop Hits", "Melodic Vibes", "Chart Toppers"],
        "metal": ["Metal Symphonique", "Dark Vibes", "Heavy Riffs"],
        "default": ["Trend 1", "Trend 2", "Trend 3"]
    }
    primary_genre = genres[0].lower()
    selected_lookalikes = lookalike_artists.get(primary_genre, lookalike_artists["default"])
    selected_trends = trends.get(primary_genre, trends["default"])

    # Prompt structuré
    prompt = f"""
    📋 OBJECTIF
    Générer un ensemble de contenus marketing pour promouvoir la {promotion_type} de l’artiste {artist}, avec un focus sur la chanson "{song}". Le contenu doit s’adapter au style musical ({', '.join(genres)}), au ton et aux thèmes de la biographie ({bio_summary}), et refléter les attentes du public cible ({target_audience}), en {language}. La réponse doit être un objet JSON structuré pour une intégration directe dans une page web, avec un respect strict des limites de caractères.

    🔄 VARIABLES PRINCIPALES
    - {{promotion_type}} : "{promotion_type}"
    - {{artist}} : "{artist}"
    - {{song}} : "{song}"
    - {{genres}} : "{', '.join(genres)}"
    - {{language}} : "{language}"
    - {{tone}} : "{tone}"
    - {{song_link}} : "{song_link}"
    - {{bio_summary}} : "{bio_summary}"
    - {{bio_tone}} : "{bio_tone}"
    - {{bio_themes}} : "{bio_themes}"
    - {{target_audience}} : "{target_audience}"

    🎸 ANALYSE CONTEXTUELLE
    1️⃣ Analyse des Genres Musicaux ({{genres}})
    - Identifier les caractéristiques et le vocabulaire spécifique :
      - Rock : énergie, riffs, puissance, authenticité
      - Punk : rébellion, énergie brute, urgence, attitude
      - Grunge : émotion brute, nostalgie, intensité, authenticité
      - Metal : intensité, riffs lourds, dramaturgie, puissance
      - Pop : mélodie, accessibilité, accrocheur, universalité, émotion
      - Électro/Dance : rythme, beats, immersion, modernité, euphorie
      - Rap/Hip-Hop : flow, authenticité, lyrics, urbanité, engagement
      - Jazz/Blues : sophistication, improvisation, émotion, profondeur, soul
      - Folk/Acoustique : simplicité, authenticité, narration, chaleur
      - Classique : élégance, virtuosité, grandeur, intemporalité
      - R&B/Soul : sensualité, groove, émotion, chaleur
      - Reggae : détente, positivisme, spiritualité, vibration
    - Si plusieurs genres, prioriser le premier comme dominant.
    - Adapter le ton recommandé par genre si {{tone}} n’est pas spécifié (ex. énergique pour rock/punk).

    2️⃣ Analyse de la Biographie ({{bio_summary}})
    - Extraire les éléments clés :
      - **Faits marquants** : Date/lieu de formation, accomplissements, collaborations.
      - **Style musical** : Influences, description du style, particularités sonores.
      - **Thèmes narratifs** : Histoires personnelles, valeurs, messages récurrents.
    - Déterminer le ton dominant ({{bio_tone}}) : Formel, Décontracté, Poétique, Engagé, Humoristique.
    - Identifier 2-3 thèmes principaux ({{bio_themes}}) : ex. rébellion, authenticité, nostalgie.

    3️⃣ Fusion Genre-Biographie
    - Combiner les caractéristiques du genre avec les éléments biographiques :
      - Prioriser {{genres}} pour le cadre général (vocabulaire, intensité).
      - Ajuster avec {{bio_tone}} pour le style d’écriture.
      - Intégrer {{bio_themes}} pour la cohérence thématique.
      - Si conflit entre {{tone}} et {{bio_tone}}, privilégier {{bio_tone}}.

    📱 CONTENU À GÉNÉRER
    Retourner un objet JSON avec les clés suivantes :

    1️⃣ "short_titles" : Liste de 5 titres courts (max 30 caractères)
    - Utiliser le vocabulaire spécifique à {{genres}} (ex. "riffs", "énergie brute" pour rock/punk/grunge).
    - Intégrer 1 élément thématique ({{bio_themes}}) dans au moins 2 titres.
    - Inclure {{song}} dans au moins 2 titres.
    - 2-3 appels à l’action variés adaptés au genre (ex. "Rockez", "Plongez", "Vibrez").
    - Ton aligné sur {{bio_tone}} et intensité du genre.
    - Contenu en {{language}}.
    - **Respect strict** : Aucun titre ne doit dépasser 30 caractères.

    2️⃣ "long_titles" : Liste de 5 titres longs (max 55 caractères)
    - Combiner élément accrocheur (genre), descriptif (bio), et appel à l’action.
    - Mentionner {{song}} dans 2 titres, {{artist}} dans 1-2 titres.
    - Référencer {{genres}} via vocabulaire ou ambiance (ex. "riffs percutants").
    - Intégrer un thème de {{bio_themes}} dans au moins 2 titres.
    - Adapter le ton à {{bio_tone}} avec nuances du genre.
    - Contenu en {{language}}.
    - **Respect strict** : Aucun titre ne doit dépasser 55 caractères.

    3️⃣ "long_descriptions" : Liste de 5 objets avec "description" (max 80 caractères) et "character_count"
    - Structurer : accroche (genre) + contexte (bio) + appel à l’action.
    - Mentionner {{song}} in 2 descriptions, {{artist}} in 2 max.
    - Intégrer {{bio_themes}} et vocabulaire de {{genres}}.
    - Inclure 3 appels à l’action variés (ex. "Plongez", "Vibrez", "Découvrez").
    - Aligner le style sur {{bio_tone}} et l’intensité du genre.
    - Contenu en {{language}}.
    - **Respect strict** : Aucune description ne doit dépasser 80 caractères.

    4️⃣ "youtube_description_short" : Objet avec "description" (max 120 caractères) et "character_count"
    - Créer une description concise pour YouTube, adaptée à {{genres}} et {{bio_tone}}.
    - Mentionner {{song}} et inclure un appel à l’action.
    - **Respect strict** : Ne pas dépasser 120 caractères.

    5️⃣ "youtube_description_full" : Objet avec "description" (max 5000 caractères) et "character_count"
    - Structurer :
      - Introduction : Contexte biographique ({{bio_summary}}). Il faut un texte mélant biographie et promotion du single.
      - Corps : Description de la sortie ({{song}}, {{promotion_type}}, lien avec {{genres}} et {{bio_themes}}).
      - Conclusion : Invitation à écouter (inclure {{song_link}}) et hashtags adaptés à {{genres}}.
    - Intégrer {{bio_themes}}, {{genres}}, et un ton aligné sur {{bio_tone}}.
    - Ne pas inclure les paroles de la chanson.
    - Inclure des placeholders pour les liens et crédits (ex. "collez votre smartlink").
    - **Respect strict** : Ne pas dépasser 5000 caractères.

    6️⃣ "analysis" : Objet avec :
      - "trends" : Liste de 3 tendances liées à {{genres}}.
      - "lookalike_artists" : Liste de 3 artistes similaires mais distincts.
      - "artist_image_url" : URL fictive (ex. "https://example.com/{artist.lower().replace(' ', '-')}.jpg").

    **Format de sortie** :
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

        # Appel à l'API OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.7
        )
        result = response.choices[0].message['content']
        logger.info("Réponse OpenAI reçue")

        # Vérification que la réponse est un JSON valide
        try:
            result_json = json.loads(result)
        except json.JSONDecodeError as e:
            logger.error(f"Réponse OpenAI non-JSON : {result}")
            return jsonify({"error": "La génération a échoué : réponse non-JSON"}), 500

        # Vérification des clés attendues
        required_keys = ["short_titles", "long_titles", "long_descriptions", "youtube_description_short", "youtube_description_full", "analysis"]
        missing_keys = [key for key in required_keys if key not in result_json]
        if missing_keys:
            logger.error(f"Clés manquantes dans la réponse JSON : {missing_keys}")
            return jsonify({"error": f"Clés manquantes dans la réponse : {missing_keys}"}), 500

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
    app.run(debug=True, host='0.0.0.0', port=5000)
