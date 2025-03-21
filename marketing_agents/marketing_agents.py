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

def smart_truncate(text, max_length, preserve_words=True, preserve_cta=True):
    """Tronque intelligemment un texte en préservant les mots complets et les calls to action."""
    if len(text) <= max_length:
        return text
        
    ctas = ["abonnez-vous maintenant", "écoutez maintenant", "like et abonnez-vous", "regardez maintenant"]
    for cta in ctas:
        if preserve_cta and text.endswith(cta):
            available_space = max_length - len(cta) - 1  # -1 pour l'espace
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
    """Valide que le contenu publicitaire respecte les contraintes."""
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
    
    if "youtube_description_short" in content and len(content["youtube_description_short"]) > 120:
        valid = False
        errors.append(f"YouTube short description exceeds 120 characters: {len(content['youtube_description_short'])}")
    
    return valid, errors

@app.route('/generate_ads', methods=['POST'])
def generate_ads():
    try:
        data = request.get_json()
        if not data or "artist" not in data or "genres" not in data:
            logger.error("Missing required fields 'artist' or 'genres' in request")
            return jsonify({"error": "Missing required fields 'artist' or 'genres'"}), 400

        artist = data.get("artist")
        genres = data.get("genres", [])
        language = data.get("language", "fr")
        tone = data.get("tone", "engageant")
        if not genres:
            logger.error("Genres list is empty")
            return jsonify({"error": "At least one genre is required"}), 400
        genres_str = ", ".join(genres)
        lyrics = data.get("lyrics", "")
        bio = data.get("bio", "")

        logger.info(f"Generating ad content for artist: {artist}, genres: {genres}, language: {language}, tone: {tone}")

        # Définir le nom de la langue pour le prompt
        language_names = {
            "fr": "French",
            "en": "English",
            "de": "German",
            "es": "Spanish",
            "pt": "Portuguese"
        }
        language_name = language_names.get(language, "French")

        # Prompt mis à jour avec description YouTube complète
        prompt = f"""
You are a creative marketing expert specializing in music promotion. Your task is to generate compelling ad content for the following artist and genres:
- Artist: {artist}
- Genres: {genres_str}
- Bio: {bio if bio else "Not provided"}
- Lyrics sample: {lyrics if lyrics else "Not provided"}

CRITICAL REQUIREMENTS:
1. Generate EXACTLY 5 short titles, 5 long titles, 5 long descriptions, 1 short YouTube description, and 1 full YouTube description in {language_name}.
2. STRICT CHARACTER LIMITS:
   - Short titles: MAXIMUM 30 characters (MUST be complete phrases)
   - Long titles: MAXIMUM 55 characters (MUST be complete phrases)
   - Long descriptions: MAXIMUM 80 characters (MUST be complete sentences)
   - Short YouTube description: MAXIMUM 120 characters (MUST be a complete sentence)
   - Full YouTube description: No strict limit, but keep it concise and professional (around 500-1000 characters)
3. DO NOT exceed the character limits for short titles, long titles, long descriptions, or short YouTube description.
4. NEVER truncate words or phrases abruptly - all content must be meaningful and complete.
5. Each long description and the short YouTube description MUST end with one of these calls to action (included in their respective limits):
   - "abonnez-vous maintenant"
   - "écoutez maintenant"
   - "like et abonnez-vous"
   - "regardez maintenant"
6. The full YouTube description should follow this template:
   - Intro: "<Artist> '<Song>' from '<Album>', lien: <placeholder URL>"
   - Subscription: "🔔 Abonnez-vous à ma chaîne 👉 <placeholder URL>"
   - Crédits: "Montage: <placeholder>, Vidéos: <placeholder>"
   - Lyrics: Short excerpt from the lyrics provided
   - Bio: Brief bio in {language_name} and English with stats
   - Contact: "Label: <placeholder email>, Booking: <placeholder email>"
   - Social: "Suivez <Artist> sur Instagram, TikTok, etc."
   - Hashtags: "#<Artist> #<Song> #<Genre>"

Style guidelines:
- Tone: {tone} (be creative, evocative, and tailored to {genres_str})
- Capitalization: Use lowercase except for proper nouns (e.g., "{artist}", song titles)
- Punctuation: Only use commas and periods (no !, ?, ;, /, or ...)
- Short titles: Include a call to action (e.g., "découvrez", "écoutez")
- Long titles: Highlight the artist's unique qualities
- Long descriptions: Evoke emotion and end with a call to action
- YouTube descriptions: Craft compelling summaries, with the full version styled like a professional YouTube post

Return ONLY the following JSON format:
{{
    "short_titles": ["<title1>", "<title2>", "<title3>", "<title4>", "<title5>"],
    "long_titles": ["<title1>", "<title2>", "<title3>", "<title4>", "<title5>"],
    "long_descriptions": ["<desc1>", "<desc2>", "<desc3>", "<desc4>", "<desc5>"],
    "youtube_description_short": "<youtube_short_desc>",
    "youtube_description_full": "<youtube_full_desc>"
}}
"""

        # Appel à OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,  # Augmenté pour inclure la description complète
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

        # Vérification et formatage des données
        short_titles = data.get("short_titles", ["no short title"] * 5)
        long_titles = data.get("long_titles", ["no long title"] * 5)
        long_descriptions = data.get("long_descriptions", ["no description"] * 5)
        youtube_description_short = data.get("youtube_description_short", "No short YouTube description provided")
        youtube_description_full = data.get("youtube_description_full", "No full YouTube description provided")

        # Assurer que chaque liste a exactement 5 éléments
        short_titles = (short_titles + ["no short title"] * 5)[:5]
        long_titles = (long_titles + ["no long title"] * 5)[:5]
        long_descriptions = (long_descriptions + ["no description"] * 5)[:5]

        # Tronquer intelligemment
        formatted_short_titles = [{"title": smart_truncate(title, 30), "character_count": len(smart_truncate(title, 30))} for title in short_titles]
        formatted_long_titles = [{"title": smart_truncate(title, 55), "character_count": len(smart_truncate(title, 55))} for title in long_titles]
        formatted_long_descriptions = [{"description": smart_truncate(desc, 80, preserve_cta=True), "character_count": len(smart_truncate(desc, 80, preserve_cta=True))} for desc in long_descriptions]
        formatted_youtube_short = {"description": smart_truncate(youtube_description_short, 120, preserve_cta=True), "character_count": len(smart_truncate(youtube_description_short, 120, preserve_cta=True))}
        formatted_youtube_full = {"description": youtube_description_full, "character_count": len(youtube_description_full)}  # Pas de troncature stricte pour la version complète

        # Valider le contenu
        content = {
            "short_titles": [item["title"] for item in formatted_short_titles],
            "long_titles": [item["title"] for item in formatted_long_titles],
            "long_descriptions": [item["description"] for item in formatted_long_descriptions],
            "youtube_description_short": formatted_youtube_short["description"]
        }
        valid, validation_errors = validate_ad_content(content)
        if not valid:
            logger.warning(f"Validation failed: {validation_errors}")

        return jsonify({
            "short_titles": formatted_short_titles,
            "long_titles": formatted_long_titles,
            "long_descriptions": formatted_long_descriptions,
            "youtube_description_short": formatted_youtube_short,
            "youtube_description_full": formatted_youtube_full
        }), 200

    except Exception as e:
        logger.error(f"Error generating ads: {str(e)}")
        return jsonify({"error": "Failed to generate ads", "details": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
