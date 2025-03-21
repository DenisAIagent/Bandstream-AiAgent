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
    """
    Tronque intelligemment un texte en préservant les mots complets et les calls to action.
    
    Args:
        text (str): Texte à tronquer
        max_length (int): Longueur maximale
        preserve_words (bool): Préserver les mots complets
        preserve_cta (bool): Préserver les calls to action
        
    Returns:
        str: Texte tronqué
    """
    if len(text) <= max_length:
        return text
        
    # Liste des calls to action à préserver
    ctas = ["abonnez-vous maintenant", "écoutez maintenant", 
            "like et abonnez-vous", "regardez maintenant"]
    
    # Vérifier si le texte se termine par un call to action
    for cta in ctas:
        if preserve_cta and text.endswith(cta):
            # Calculer l'espace disponible pour le reste du texte
            available_space = max_length - len(cta) - 1  # -1 pour l'espace
            if available_space <= 0:
                return cta  # Si pas assez d'espace, retourner juste le CTA
                
            # Tronquer le reste du texte
            prefix = text[:-len(cta)].strip()
            if preserve_words:
                # Tronquer au dernier espace avant la limite
                if len(prefix) > available_space:
                    prefix = prefix[:available_space].rsplit(' ', 1)[0]
            else:
                prefix = prefix[:available_space]
                
            return f"{prefix} {cta}"
    
    # Si pas de CTA, tronquer normalement
    if preserve_words:
        truncated = text[:max_length].rsplit(' ', 1)[0]
        if len(truncated) > max_length:
            return truncated[:max_length]
        return truncated
    return text[:max_length]

def validate_ad_content(content):
    """
    Valide que le contenu publicitaire respecte les contraintes.
    
    Args:
        content (dict): Contenu publicitaire
        
    Returns:
        tuple: (est_valide, messages_erreur)
    """
    valid = True
    errors = []
    
    # Vérifier les titres courts
    for i, title in enumerate(content.get("short_titles", [])):
        if len(title) > 30:
            valid = False
            errors.append(f"Short title {i+1} exceeds 30 characters: {len(title)}")
    
    # Vérifier les titres longs
    for i, title in enumerate(content.get("long_titles", [])):
        if len(title) > 55:
            valid = False
            errors.append(f"Long title {i+1} exceeds 55 characters: {len(title)}")
    
    # Vérifier les descriptions longues
    ctas = ["abonnez-vous maintenant", "écoutez maintenant", 
            "like et abonnez-vous", "regardez maintenant"]
    for i, desc in enumerate(content.get("long_descriptions", [])):
        if len(desc) > 80:
            valid = False
            errors.append(f"Long description {i+1} exceeds 80 characters: {len(desc)}")
        
        # Vérifier que la description se termine par un call to action
        if not any(desc.endswith(cta) for cta in ctas):
            valid = False
            errors.append(f"Long description {i+1} does not end with a valid call to action")
    
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
        language = data.get("language", "fr")  # Français par défaut
        tone = data.get("tone", "engageant")  # Engageant par défaut
        if not genres:
            logger.error("Genres list is empty")
            return jsonify({"error": "At least one genre is required"}), 400
        genres_str = ", ".join(genres)  # Joindre les genres pour le prompt
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
        language_name = language_names.get(language, "French")  # Par défaut en français

        # Prompt mis à jour avec contraintes strictes
        prompt = f"""
You are a creative marketing expert specializing in music promotion. Your task is to generate compelling ad content for the following artist and genres:
- Artist: {artist}
- Genres: {genres_str}
- Bio: {bio if bio else "Not provided"}
- Lyrics sample: {lyrics if lyrics else "Not provided"}

CRITICAL REQUIREMENTS:
1. Generate EXACTLY 5 short titles, 5 long titles, and 5 long descriptions in {language_name}.
2. STRICT CHARACTER LIMITS:
   - Short titles: MAXIMUM 30 characters (MUST be complete phrases)
   - Long titles: MAXIMUM 55 characters (MUST be complete phrases)
   - Long descriptions: MAXIMUM 80 characters (MUST be complete sentences)
3. DO NOT exceed these limits under any circumstances.
4. NEVER truncate words or phrases abruptly - all content must be meaningful and complete.
5. Each long description MUST end with one of these calls to action (included in the 80-character limit):
   - "abonnez-vous maintenant"
   - "écoutez maintenant"
   - "like et abonnez-vous"
   - "regardez maintenant"

Style guidelines:
- Tone: {tone} (be creative, evocative, and tailored to {genres_str})
- Capitalization: Use lowercase except for proper nouns (e.g., "{artist}", song titles)
- Punctuation: Only use commas and periods (no !, ?, ;, /, or ...)
- Short titles: Include a call to action (e.g., "découvrez", "écoutez")
- Long titles: Highlight the artist's unique qualities
- Long descriptions: Evoke emotion and end with a call to action

Return ONLY the following JSON format:
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
            temperature=0.7  # Réduit pour plus de cohérence
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

        # Tronquer intelligemment
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

        # Valider le contenu
        content = {
            "short_titles": [item["title"] for item in formatted_short_titles],
            "long_titles": [item["title"] for item in formatted_long_titles],
            "long_descriptions": [item["description"] for item in formatted_long_descriptions]
        }
        valid, validation_errors = validate_ad_content(content)
        if not valid:
            logger.warning(f"Validation failed: {validation_errors}")
            # On pourrait réessayer ici, mais pour l'instant on logue et continue

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
