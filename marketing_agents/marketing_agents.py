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

# Fonction pour générer une description par défaut si nécessaire
def generate_default_description(artist, index):
    default_ctas = ["Écoutez maintenant", "Abonnez-vous maintenant", "Regardez maintenant", "Like et abonnez-vous"]
    cta = default_ctas[index % len(default_ctas)]
    desc = f"Découvrez {artist} et son univers musical unique. {cta}"
    return {
        "description": desc,
        "character_count": len(desc)
    }

# Fonction pour tronquer une description longue tout en préservant l’appel à l’action
def truncate_description(description, max_length=80):
    if len(description) <= max_length:
        return description

    # Trouver l’appel à l’action à la fin
    desc_lower = description.lower()
    cta = None
    for valid_cta in VALID_CALLS_TO_ACTION:
        if desc_lower.endswith(valid_cta):
            cta = description[-len(valid_cta):]
            break
    
    if not cta:
        return description[:max_length]  # Si aucun appel à l’action, tronquer simplement

    # Tronquer le texte avant l’appel à l’action
    text_before_cta = description[:-len(cta)]
    max_text_length = max_length - len(cta) - 1  # -1 pour l’espace
    if max_text_length <= 0:
        return description[:max_length]  # Si l’appel à l’action est trop long, tronquer simplement
    
    truncated_text = text_before_cta[:max_text_length].rstrip() + " " + cta
    return truncated_text

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
    lyrics = data.get("lyrics", "")
    bio = data.get("bio", "")
    promotion_type = data.get("promotion_type", "single")

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
        - A list of exactly 5 short titles (max 30 characters each).
        - A list of exactly 5 long titles (max 60 characters each).
        - A list of exactly 5 long descriptions (max 80 characters each, including the call to action). Each long description must end with one of the following calls to action: "Écoutez maintenant", "Abonnez-vous maintenant", "Regardez maintenant", "Like et abonnez-vous". Ensure all 5 descriptions are provided.
        - A short YouTube description (max 120 characters).
        - A full YouTube description (max 1000 characters).

        Return the response in the following JSON format:
        {{
            "short_titles": ["<title1>", "<title2>", "<title3>", "<title4>", "<title5>"],
            "long_titles": ["<title1>", "<title2>", "<title3>", "<title4>", "<title5>"],
            "long_descriptions": [
                {{"description": "<desc1>", "character_count": <count1>}},
                {{"description": "<desc2>", "character_count": <count2>}},
                {{"description": "<desc3>", "character_count": <count3>}},
                {{"description": "<desc4>", "character_count": <count4>}},
                {{"description": "<desc5>", "character_count": <count5>}}
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

        # Vérifier que 5 descriptions longues sont bien présentes
        long_descriptions = data.get("long_descriptions", [])
        if len(long_descriptions) < 5:
            logger.warning(f"OpenAI returned only {len(long_descriptions)} long descriptions, expected 5. Adding default descriptions.")
            while len(long_descriptions) < 5:
                long_descriptions.append(generate_default_description(artist, len(long_descriptions)))

        # Tronquer les descriptions longues si nécessaire
        for desc in long_descriptions:
            desc["description"] = truncate_description(desc["description"], max_length=80)
            desc["character_count"] = len(desc["description"])

        # Ajouter le nombre de caractères pour les autres champs
        for desc in long_descriptions:
            desc["character_count"] = len(desc["description"])
        data["youtube_description_short"]["character_count"] = len(data["youtube_description_short"]["description"])
        data["youtube_description_full"]["character_count"] = len(data["youtube_description_full"]["description"])

        # Valider les descriptions longues
        validation_errors = validate_long_descriptions(long_descriptions)
        if validation_errors:
            logger.warning(f"Validation failed: {validation_errors}")
            # On continue malgré l'avertissement, mais cela pourrait être une erreur fatale selon les besoins

        data["long_descriptions"] = long_descriptions
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
