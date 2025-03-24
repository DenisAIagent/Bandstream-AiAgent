from flask import Flask, request, jsonify
import openai
import os
from dotenv import load_dotenv
from cachetools import TTLCache
import logging

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
    artist = data.get('artist', '')
    song = data.get('song', '')
    genres = data.get('genres', ['unknown']) if isinstance(data.get('genres'), list) else [data.get('genres', 'unknown')]
    language = data.get('language', 'français')
    tone = data.get('tone', '')
    promotion_type = data.get('promotion_type', 'sortie')
    song_link = data.get('song_link', '[insert link]')
    bio_summary = data.get('bio_summary', f"Artiste passionné par {genres[0]} avec une approche unique.")
    bio_tone = data.get('bio_tone', 'authentique')  # Détection manuelle ou par défaut
    bio_themes = data.get('bio_themes', 'émotion, créativité')  # Détection manuelle ou par défaut
    target_audience = data.get('target_audience', 'tous publics')

    # Prompt dynamique
    prompt = f"""
    📋 OBJECTIF
    Générer un ensemble de contenus marketing percutants pour promouvoir la {promotion_type} de l’artiste {artist}, avec un focus sur la chanson "{song}". Le contenu doit s’adapter dynamiquement au style musical ({', '.join(genres)}), au ton et aux thèmes extraits de la biographie ({bio_summary}), et refléter les attentes du public cible ({target_audience}), tout en respectant la langue demandée ({language}).

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
    - Identifier les caractéristiques principales et le vocabulaire spécifique pour chaque genre listé :
      - Rock/Metal : énergie, intensité, riffs, puissance, rébellion
      - Pop : mélodie, accessibilité, accrocheur, universalité, émotion
      - Électro/Dance : rythme, beats, immersion, modernité, euphorie
      - Rap/Hip-Hop : flow, authenticité, lyrics, urbanité, engagement
      - Jazz/Blues : sophistication, improvisation, émotion, profondeur, soul
      - Folk/Acoustique : simplicité, authenticité, narration, chaleur
      - Classique : élégance, virtuosité, grandeur, intemporalité
      - R&B/Soul : sensualité, groove, émotion, chaleur
      - Reggae : détente, positivisme, spiritualité, vibration
    - Si plusieurs genres, prioriser le premier comme dominant et intégrer les autres comme nuances.
    - Adapter le ton recommandé par genre si {{tone}} n’est pas spécifié (ex. énergique pour rock, sophistiqué pour jazz).

    2️⃣ Analyse de la Biographie ({{bio_summary}})
    - Extraire les éléments clés selon les directives :
      - **Faits marquants** : Date/lieu de formation, accomplissements (albums, tournées), collaborations.
      - **Style musical** : Influences, description du style, particularités sonores.
      - **Thèmes narratifs** : Histoires personnelles, valeurs, messages récurrents.
    - Déterminer le ton dominant ({{bio_tone}}) :
      - Formel : langage soutenu, structure claire.
      - Décontracté : style direct, expressions familières.
      - Poétique : images fortes, métaphores.
      - Engagé : convictions, messages forts.
      - Humoristique : légèreté, autodérision.
    - Identifier 2-3 thèmes principaux ({{bio_themes}}) : ex. liberté, innovation, tradition.

    3️⃣ Fusion Genre-Biographie
    - Combiner les caractéristiques du genre avec les éléments biographiques :
      - Prioriser {{genres}} pour le cadre général (vocabulaire, intensité).
      - Ajuster avec {{bio_tone}} pour le style d’écriture.
      - Intégrer {{bio_themes}} pour la cohérence thématique.
      - Si conflit entre {{tone}} et {{bio_tone}}, privilégier {{bio_tone}} pour l’authenticité.

    📱 CONTENU À GÉNÉRER
    1️⃣ TITRES COURTS (5 titres, max 30 caractères)
    - Utiliser le vocabulaire spécifique à {{genres}}.
    - Intégrer 1 élément biographique distinctif ou thématique ({{bio_themes}}).
    - Inclure {{song}} dans au moins 2 titres.
    - 2-3 appels à l’action adaptés au genre.
    - Ton aligné sur {{bio_tone}} et intensité du genre.
    - Contenu en {{language}}.

    2️⃣ TITRES LONGS (5 titres, max 55 caractères)
    - Combiner élément accrocheur (genre), descriptif (bio), et appel à l’action.
    - Mentionner {{song}} dans 2 titres, {{artist}} dans 1-2 titres.
    - Référencer {{genres}} via vocabulaire ou ambiance.
    - Intégrer un thème de {{bio_themes}} dans au moins 2 titres.
    - Adapter le ton à {{bio_tone}} avec nuances du genre.
    - Contenu en {{language}}.

    3️⃣ DESCRIPTIONS LONGUES (5 descriptions, max 80 caractères)
    - Structurer : accroche (genre) + contexte (bio) + appel à l’action.
    - Mentionner {{song}} dans 2 descriptions, {{artist}} dans 2 max.
    - Intégrer {{bio_themes}} et vocabulaire de {{genres}}.
    - Inclure 3 appels à l’action variés.
    - Aligner le style sur {{bio_tone}} et l’intensité du genre.
    - Contenu en {{language}}.

    🌐 ADAPTATION MULTIPLATEFORME
    - Instagram/TikTok : Ton court, percutant, émojis adaptés à {{genres}}.
    - YouTube : Ton narratif, référence au parcours ({{bio_summary}}), invitation détaillée.
    - Spotify : Ton immersif, focus sur l’expérience d’écoute liée à {{genres}}.
    - Hashtags : Générer 3-5 hashtags pertinents selon {{genres}}.
    """
    return prompt

@app.route('/generate_ads', methods=['POST'])
def generate_ads():
    try:
        data = request.get_json()
        if not data:
            logger.error("Aucune donnée JSON fournie")
            return jsonify({"error": "Aucune donnée fournie"}), 400

        required_fields = ['artist', 'genres', 'language', 'promotion_type']
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            logger.error(f"Champs manquants : {missing_fields}")
            return jsonify({"error": f"Champs manquants : {missing_fields}"}), 400

        cache_key = "_".join([str(data.get(field, '')) for field in required_fields + ['song', 'tone']])
        logger.info(f"Clé de cache : {cache_key}")

        if cache_key in cache:
            logger.info(f"Réponse trouvée dans le cache pour : {cache_key}")
            return jsonify(cache[cache_key])

        prompt = generate_prompt(data)
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,
            temperature=0.7
        )
        result = response.choices[0].message['content']

        cache[cache_key] = {"content": result}
        logger.info(f"Contenu généré et mis en cache pour : {cache_key}")
        return jsonify({"content": result})

    except openai.error.OpenAIError as e:
        logger.error(f"Erreur OpenAI : {str(e)}")
        return jsonify({"error": "Erreur lors de la génération"}), 500
    except Exception as e:
        logger.error(f"Erreur inattendue : {str(e)}")
        return jsonify({"error": "Erreur interne"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
