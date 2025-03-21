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

@app.route('/optimize', methods=['POST'])
def optimize():
    try:
        data = request.get_json()
        if not data or "artist" not in data or "styles" not in data:
            logger.error("Missing required fields 'artist' or 'styles' in request")
            return jsonify({"error": "Missing required fields 'artist' or 'styles'"}), 400

        artist = data.get("artist")
        styles = data.get("styles", [])
        language = data.get("language", "fr")
        tone = data.get("tone", "engageant")
        lyrics = data.get("lyrics", "")
        bio = data.get("bio", "")
        
        if not styles:
            logger.error("Styles list is empty")
            return jsonify({"error": "At least one style is required"}), 400
        
        styles_str = ", ".join(styles)
        logger.info(f"Generating YouTube description for artist: {artist}, styles: {styles}, language: {language}, tone: {tone}")

        # Définir le nom de la langue pour le prompt
        language_names = {
            "fr": "French",
            "en": "English",
            "de": "German",
            "es": "Spanish",
            "pt": "Portuguese"
        }
        language_name = language_names.get(language, "French")

        # Prompt pour générer la description YouTube et les termes de recherche
        prompt = f"""
You are a YouTube marketing expert specializing in music promotion. Your task is to create an optimized YouTube description and long-tail search terms for the artist and genres below:
- Artist: {artist}
- Genres: {styles_str}
- Bio: {bio if bio else "Not provided"}
- Lyrics sample: {lyrics if lyrics else "Not provided"}

Generate the following in {language_name} with a {tone} tone:
1. A perfect YouTube description (max 2000 characters) structured like this:
   - Line 1: "{artist.upper()} - 'Adelphité' (clip officiel)" (use 'Adelphité' as the default song title unless bio/lyrics suggest another).
   - Line 2: "Extrait de l’album : Que La Lumière Soit" (use 'Que La Lumière Soit' as default album unless bio suggests another).
   - Line 3: "▶ Commander / Écouter : XXXX".
   - Section "CRÉDITS" : List fictional credits (e.g., Réalisation, Chorégraphe) with Instagram placeholders (e.g., "Instagram: XXXX").
   - Section "➡️ Suivre {artist.upper()}" : List social media placeholders (e.g., "Facebook: XXXX", "Instagram: XXXX", "Youtube: XXXX", etc.).
   - Section "LYRICS" : Include the full lyrics sample if provided, otherwise a short placeholder.
   - Use bio/lyrics to personalize where relevant (e.g., album title, song title).
2. A list of 3 long-tail YouTube search terms (each max 60 characters) related to {styles_str}, realistic for 2025 (e.g., "best metal song 2025", "top metal industriel français").

Return the response in the following JSON format:
{{
    "youtube_description": {{
        "description": "<description_text>",
        "search_terms": ["<term1>", "<term2>", ..., "<term10>"]
    }}
}}
"""

        # Appel à OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,  # Augmenté pour inclure les paroles
            temperature=0.7
        )

        raw_text = response.choices[0].message.content.strip()
        logger.info(f"Raw response from OpenAI: {raw_text}")

        # Parsing sécurisé de la réponse JSON
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI response as JSON: {str(e)}")
            return jsonify({"error": "Invalid response format from OpenAI", "details": str(e)}), 500

        # Validation et formatage
        youtube_description = data.get("youtube_description", {
            "description": f"{artist.upper()}\n'Default Song' (clip officiel)\nExtrait de l’album : Default Album\n\n▶ Commander / Écouter : XXXX\n\nCRÉDITS:\nRéalisation: Instagram: XXXX\n\n➡️ Suivre {artist.upper()}:\nFacebook: XXXX\nInstagram: XXXX\nYoutube: XXXX",
            "search_terms": ["best metal song", "top metal bands"]
        })

        # Vérifier la longueur de la description
        if len(youtube_description["description"]) > 2000:
            youtube_description["description"] = youtube_description["description"][:1997] + "..."

        return jsonify({"youtube_description": youtube_description}), 200

    except Exception as e:
        logger.error(f"Error generating YouTube description: {str(e)}")
        return jsonify({"error": "Failed to generate YouTube description", "details": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
