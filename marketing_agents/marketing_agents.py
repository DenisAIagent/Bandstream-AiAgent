import os
import json
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import logging
import openai

# Configurer les logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Charger les variables d'environnement
load_dotenv()

# Initialiser Flask
app = Flask(__name__)

# Configurer OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    logger.error("OPENAI_API_KEY is not set in environment variables")
    raise ValueError("OPENAI_API_KEY is required")

# Liste des appels à l’action valides (en minuscules pour la comparaison)
VALID_CALLS_TO_ACTION = [
    "écoutez maintenant",
    "abonnez-vous maintenant",
    "regardez maintenant",
    "like et abonnez-vous"
]

# Fonction pour valider les descriptions longues
def validate_long_descriptions(descriptions):
    errors = []
    for i, desc in enumerate(descriptions, 1):
        desc_text = desc.get("description", "").lower().strip()
        # Vérifier si la description se termine par un appel à l’action valide
        if not any(desc_text.endswith(cta) for cta in VALID_CALLS_TO_ACTION):
            errors.append(f"Long description {i} does not end with a valid call to action")
    return errors

# Endpoint pour générer des annonces
@app.route('/generate_ads', methods=['POST'])
def generate_ads():
    data = request.get_json()
    if not data or "artist" not in data or "genres" not in data or "language" not in data or "tone" not in data:
        logger.error("Missing required fields in request")
        return jsonify({"error": "Missing required fields: artist, genres, language, tone"}), 400

    artist = data.get("artist")
    genres = data.get("genres", [])
    language = data.get("language")
    tone = data.get("tone")

    logger.info(f"Generating ad content for artist: {artist}, genres: {genres}, language: {language}, tone: {tone}")

    try:
        genres_str = ", ".join(genres)
        prompt = f"""
        You are a marketing expert specializing in music promotion. Generate ad content for the following artist and genres:
        - Artist: {artist}
        - Genres: {genres_str}
        - Language: {language}
        - Tone: {tone}

        Generate the following:
        - A list of 5 short titles (max 30 characters each).
        - A list of 5 long titles (max 60 characters each).
        - A list of 5 long descriptions (max 80 characters each). Ensure that each long description ends with one of the following calls to action: "Écoutez maintenant", "Abonnez-vous maintenant", "Regardez maintenant", "Like et abonnez-vous".
        - A short YouTube description (max 120 characters).
        - A full YouTube description (max 1000 characters).

        Return the response in the following JSON format:
        {{
            "short_titles": ["<title1>", "<title2>", ..., "<title5>"],
            "long_titles": ["<title1>", "<title2>", ..., "<title5>"],
            "long_descriptions": [
                {{"description": "<desc1>", "character_count": <count1>}},
                {{"description": "<desc2>", "character_count": <count2>}},
                ...
            ],
            "youtube_description_short": {{"description": "<desc>", "character_count": <count>}},
            "youtube_description_full": {{"description": "<desc>", "character_count": <count>}}
        }}
        """

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.7
        )

        raw_text = response.choices[0].message.content.strip()
        logger.info(f"Raw response from OpenAI: {raw_text}")

        data = json.loads(raw_text)

        # Ajouter le nombre de caractères pour chaque description
        for desc in data["long_descriptions"]:
            desc["character_count"] = len(desc["description"])
        data["youtube_description_short"]["character_count"] = len(data["youtube_description_short"]["description"])
        data["youtube_description_full"]["character_count"] = len(data["youtube_description_full"]["description"])

        # Valider les descriptions longues
        validation_errors = validate_long_descriptions(data["long_descriptions"])
        if validation_errors:
            logger.warning(f"Validation failed: {validation_errors}")
            # On continue malgré l'avertissement, mais cela pourrait être une erreur fatale selon les besoins

        return jsonify(data), 200

    except Exception as e:
        logger.error(f"Error generating ad content: {str(e)}")
        return jsonify({"error": "Failed to generate ad content"}), 500

# Endpoint de santé
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "message": "Marketing Agent is running"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
