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

def clean_description(description):
    generic_phrases = [
        r"Avec son style unique, .* rencontre un succès grandissant aux quatre coins du globe",
        r"With his unique style, .* is experiencing growing success across the globe",
        r"À chacune de ses sorties, il continue de surprendre et de créer l’engouement",
        r"With each release, .* continues to surprise his audience and build excitement",
        r"s’imposant comme une figure essentielle de la scène",
        r"cementing his place as a key figure in the .* scene"
    ]
    for phrase in generic_phrases:
        if re.search(phrase, description, re.IGNORECASE):
            description = re.sub(phrase, "", description, flags=re.IGNORECASE)
            description += "\nDécouvrez une expérience musicale authentique et vibrante !"
    return description.strip()

def generate_prompt(data):
    prompt = """
    Tu es un agent IA expert en marketing musical, spécialisé dans la génération automatique de campagnes publicitaires optimisées pour YouTube Ads. Ta mission est de créer des annonces (titres courts, titres longs et descriptions avec call-to-action) et des descriptions YouTube respectant scrupuleusement les meilleures pratiques SEO afin de maximiser la visibilité, le taux de clics et l'engagement des vidéos musicales.

    Chaque réponse doit impérativement être fournie sous forme d'un objet JSON strict pour une intégration directe et fonctionnelle.

    ⚠️ Consignes strictes :
    - Évite absolument les formulations génériques telles que :
      - « Avec son style unique, [artiste] rencontre un succès grandissant… »
      - « À chacune de ses sorties, il continue de surprendre… »
    - Inclue impérativement un fait concret, unique et précis (collaboration, anecdote, événement spécifique à l'artiste) pour personnaliser chaque description.

    Structure à respecter :

    1. Titres courts (5 propositions)
    - Maximum 30 caractères chacun.

    2. Titres longs (5 propositions)
    - Maximum 90 caractères chacun.

    3. Descriptions (5 propositions)
    - Maximum entre 80 et 90 caractères, incluant un call-to-action.

    4. Description YouTube courte optimisée SEO
    - Maximum 120 caractères, mention de l'artiste, chanson, et appel à l'action.

    5. Description YouTube complète optimisée SEO
    - Mentionner titre vidéo avec "(Official Video)", brève présentation, date sortie, liens, crédits visuels, hashtags pertinents.

    6. Analyse contextuelle
    - Genres musicaux, tendances actuelles, artistes similaires.

    Assure-toi que chaque contenu produit maximise l'impact promotionnel, l'attractivité, et les performances SEO sur YouTube.
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

        if 'song_lyrics' not in data:
            data['song_lyrics'] = ""

        cache_key = "_".join([str(data.get(field, '')) for field in required_fields + ['song', 'tone']])
        if cache_key in cache:
            cached_result = cache[cache_key]
            if cached_result and "short_titles" in cached_result:
                return jsonify(cached_result)

        prompt = generate_prompt(data)

        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.7
        )
        result = response.choices[0].message['content']
        result_cleaned = re.sub(r'^```json\n|\n```$', '', result).strip()
        result_json = json.loads(result_cleaned)

        result_json["youtube_description_full"]["description"] = clean_description(result_json["youtube_description_full"]["description"])
        result_json["youtube_description_full"]["character_count"] = len(result_json["youtube_description_full"]["description"])

        cache[cache_key] = result_json
        return jsonify(result_json)

    except openai.error.OpenAIError as e:
        return jsonify({"error": f"Erreur OpenAI : {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Erreur interne : {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
