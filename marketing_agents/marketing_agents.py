import os
import json
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import logging
import openai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = Flask(__name__)

openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    logger.error("OPENAI_API_KEY is not set in environment variables")
    raise ValueError("OPENAI_API_KEY is required")

def smart_truncate(text, max_length, preserve_words=True, preserve_cta=True):
    if len(text) <= max_length:
        return text
    ctas = ["abonnez-vous maintenant", "écoutez maintenant", "like et abonnez-vous", "regardez maintenant"]
    for cta in ctas:
        if preserve_cta and text.endswith(cta):
            available_space = max_length - len(cta) - 1
            if available_space <= 0:
                return cta
            prefix = text[:-len(cta)].strip()
            if preserve_words and len(prefix) > available_space:
                prefix = prefix[:available_space].rsplit(' ', 1)[0]
            else:
                prefix = prefix[:available_space]
            return f"{prefix} {cta}"
    if preserve_words:
        truncated = text[:max_length].rsplit(' ', 1)[0]
        if len(truncated) > max_length:
            return truncated[:max_length]
        return truncated
    return text[:max_length]

def validate_ad_content(content):
    valid = True
    errors = []
    for i, title in enumerate(content.get("short_titles", [])):
        if len(title) > 30:
            valid = False
            errors.append(f"Short title {i+1} exceeds 30 characters: {len(title)}")
    for i, title in enumerate(content.get("long_titles", [])):
        if len(title) > 55:
            valid = False
            errors.append(f"Long title {i+1} exceeds 55 characters: {len(title)}")
    ctas = ["abonnez-vous maintenant", "écoutez maintenant", "like et abonnez-vous", "regardez maintenant"]
    for i, desc in enumerate(content.get("long_descriptions", [])):
        if len(desc) > 80:
            valid = False
            errors.append(f"Long description {i+1} exceeds 80 characters: {len(desc)}")
        if not any(desc.endswith(cta) for cta in ctas):
            valid = False
            errors.append(f"Long description {i+1} does not end with a valid call to action")
    return valid, errors

@app.route('/generate_ads', methods=['POST'])
def generate_ads():
    try:
        data = request.get_json()
        if not data or "artist" not in data or "genres" not in data or "song" not in data:
            logger.error("Missing required fields 'artist', 'genres', or 'song' in request")
            return jsonify({"error": "Missing required fields 'artist', 'genres', or 'song'"}), 400

        artist = data.get("artist")
        song = data.get("song")  # Nouveau champ
        genres = data.get("genres", [])
        language = data.get("language", "fr")
        tone = data.get("tone", "engageant")
        if not genres:
            logger.error("Genres list is empty")
            return jsonify({"error": "At least one genre is required"}), 400
        genres_str = ", ".join(genres)
        lyrics = data.get("lyrics", "")
        bio = data.get("bio", "")

        logger.info(f"Generating ad content for artist: {artist}, song: {song}, genres: {genres}, language: {language}, tone: {tone}")

        language_names = {
            "fr": "French",
            "en": "English",
            "de": "German",
            "es": "Spanish",
            "pt": "Portuguese"
        }
        language_name = language_names.get(language, "French")

        prompt = f"""
You are a creative marketing expert specializing in music promotion. Your task is to generate compelling ad content for the artist '{artist}' and their song '{song}' in the genres '{genres_str}'.

CRITICAL REQUIREMENTS:
1. Generate EXACTLY 5 short titles, 5 long titles, and 5 long descriptions in {language_name}.
2. STRICT CHARACTER LIMITS:
   - Short titles: MAXIMUM 30 characters (MUST be complete phrases, include '{song}' where relevant)
   - Long titles: MAXIMUM 55 characters (MUST be complete phrases, include '{song}' where relevant)
   - Long descriptions: MAXIMUM 80 characters (MUST be complete sentences, include '{song}' where relevant)
3. DO NOT exceed these limits under any circumstances.
4. NEVER truncate words or phrases abruptly - all content must be meaningful and complete.
5. Each long description MUST end with one of these calls to action (included in the 80-character limit):
   - "abonnez-vous maintenant"
   - "écoutez maintenant"
   - "like et abonnez-vous"
   - "regardez maintenant"

Style guidelines:
- Tone: {tone} (be creative, evocative, and tailored to '{genres_str}')
- Capitalization: Use lowercase except for proper nouns (e.g., "{artist}", "{song}")
- Punctuation: Only use commas and periods (no !, ?, ;, /, or ...)
- Short titles: Include a call to action (e.g., "découvrez", "écoutez")
- Long titles: Highlight the artist's and song's unique qualities
- Long descriptions: Evoke emotion, reference '{song}', and end with a call to action
- Use the bio and lyrics if provided: {bio if bio else "Not provided"}, {lyrics if lyrics else "Not provided"}

Return ONLY the following JSON format:
{{
    "short_titles": ["<title1>", "<title2>", "<title3>", "<title4>", "<title5>"],
    "long_titles": ["<title1>", "<title2>", "<title3>", "<title4>", "<title5>"],
    "long_descriptions": ["<desc1>", "<desc2>", "<desc3>", "<desc4>", "<desc5>"]
}}
"""

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600,
            temperature=0.7
        )

        raw_text = response.choices[0].message.content.strip()
        logger.info(f"Raw response from OpenAI: {raw_text}")

        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI response as JSON: {str(e)}")
            return jsonify({"error": "Invalid response format from OpenAI", "details": str(e)}), 500

        short_titles = data.get("short_titles", ["no short title"] * 5)
        long_titles = data.get("long_titles", ["no long title"] * 5)
        long_descriptions = data.get("long_descriptions", ["no description"] * 5)

        short_titles = (short_titles + ["no short title"] * 5)[:5]
        long_titles = (long_titles + ["no long title"] * 5)[:5]
        long_descriptions = (long_descriptions + ["no description"] * 5)[:5]

        formatted_short_titles = []
        for title in short_titles:
            truncated = smart_truncate(title, 30)
            formatted_short_titles.append({
                "title": truncated,
                "character_count": len(truncated)
            })

        formatted_long_titles = []
        for title in long_titles:
            truncated = smart_truncate(title, 55)
            formatted_long_titles.append({
                "title": truncated,
                "character_count": len(truncated)
            })

        formatted_long_descriptions = []
        for desc in long_descriptions:
            truncated = smart_truncate(desc, 80, preserve_cta=True)
            formatted_long_descriptions.append({
                "description": truncated,
                "character_count": len(truncated)
            })

        content = {
            "short_titles": [item["title"] for item in formatted_short_titles],
            "long_titles": [item["title"] for item in formatted_long_titles],
            "long_descriptions": [item["description"] for item in formatted_long_descriptions]
        }
        valid, validation_errors = validate_ad_content(content)
        if not valid:
            logger.warning(f"Validation failed: {validation_errors}")

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
