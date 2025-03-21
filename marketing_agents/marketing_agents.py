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

app = Flask(__name__)

# Configurer OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    logger.error("OPENAI_API_KEY is not set in environment variables")
    raise ValueError("OPENAI_API_KEY is required")

@app.route('/generate_ads', methods=['POST'])
def generate_ads():
    try:
        data = request.get_json()
        if not data or "artist" not in data or "genres" not in data:
            logger.error("Missing required fields 'artist' or 'genres' in request")
            return jsonify({"error": "Missing required fields 'artist' or 'genres'"}), 400

        artist = data.get("artist")
        genres = data.get("genres", [])
        language = data.get("language", "fr")  # Français par défaut si non spécifié
        if not genres:
            logger.error("Genres list is empty")
            return jsonify({"error": "At least one genre is required"}), 400
        genres_str = ", ".join(genres)  # Joindre les genres pour le prompt
        lyrics = data.get("lyrics", "")
        bio = data.get("bio", "")

        logger.info(f"Generating ad content for artist: {artist}, genres: {genres}, language: {language}")

        # Définir le nom de la langue pour le prompt
        language_names = {
            "fr": "French",
            "en": "English",
            "de": "German",
            "es": "Spanish",
            "pt": "Portuguese"
        }
        language_name = language_names.get(language, "French")  # Par défaut en français

        # Prompt mis à jour avec minuscules et limites strictes
        prompt = f"""
You are a creative marketing expert specializing in music promotion. Your task is to generate compelling ad content for the following artist and genres:
- Artist: {artist}
- Genres: {genres_str}
- Bio: {bio if bio else "Not provided"}
- Lyrics sample: {lyrics if lyrics else "Not provided"}

Generate the following in {language_name}:
- A list of 5 short ad titles (max 30 characters each, strictly enforced) that are catchy, energetic, and include a call to action (e.g., "discover", "experience", "unleash").
- A list of 5 long ad titles (max 60 characters each, strictly enforced) that are bold, descriptive, and highlight the artist's unique qualities across the genres {genres_str}.
- A list of 5 long ad descriptions (max 90 characters each, strictly enforced) that are engaging, evoke emotion, and include a call to action (e.g., "feel the power", "join the journey").

Ensure the tone is exciting, professional, and tailored to the {genres_str} genres. Use the bio and lyrics (if provided) to add specific details about the artist. Do not exceed the character limits under any circumstances. Use lowercase for all words except proper nouns (e.g., the artist’s name like "{artist}" or specific titles from the bio/lyrics); do not use full uppercase words like "METAL" or "DISCOVER".

Return the response in the following JSON format:
{{
    "short_titles": ["<title1>", "<title2>", "<title3>", "<title4>", "<title5>"],
    "long_titles": ["<title1>", "<title2>", "<title3>", "<title4>", "<title5>"],
    "long_descriptions": ["<desc1>", "<desc2>", "<desc3>", "<desc4>", "<desc5>"]
}}
"""

        # Appel à OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600,
            temperature=0.8
        )

        raw_text = response.choices[0].message.content.strip()
        logger.info(f"Raw response from OpenAI: {raw_text}")

        # Parsing sécurisé de la réponse JSON
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI response as JSON: {str(e)}")
            return jsonify({"error": "Invalid response format from OpenAI", "details": str(e)}), 500

        # Vérification et formatage des données
        short_titles = data.get("short_titles", ["no short title"] * 5)
        long_titles = data.get("long_titles", ["no long title"] * 5)
        long_descriptions = data.get("long_descriptions", ["no description"] * 5)

        # Assurer que chaque liste a exactement 5 éléments
        short_titles = (short_titles + ["no short title"] * 5)[:5]
        long_titles = (long_titles + ["no long title"] * 5)[:5]
        long_descriptions = (long_descriptions + ["no description"] * 5)[:5]

        # Formater les résultats avec character_count
        formatted_short_titles = [{"title": title, "character_count": len(title)} for title in short_titles]
        formatted_long_titles = [{"title": title, "character_count": len(title)} for title in long_titles]
        formatted_long_descriptions = [{"description": desc, "character_count": len(desc)} for desc in long_descriptions]

        return jsonify({
            "short_titles": formatted_short_titles,
            "long_titles": formatted_long_titles,
            "long_descriptions": formatted_long_descriptions
        }), 200

    except Exception as e:
        logger.error(f"Error generating ads: {str(e)}")
        return jsonify({"error": "Failed to generate ads", "details": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
