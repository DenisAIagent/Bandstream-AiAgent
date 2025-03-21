import os
import json
import requests
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
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    logger.error("OPENAI_API_KEY is not set in environment variables")
    raise ValueError("OPENAI_API_KEY is required")
openai.api_key = openai_api_key

# Configurer RapidAPI
rapidapi_key = os.getenv("RAPIDAPI_KEY")
if not rapidapi_key:
    logger.error("RAPIDAPI_KEY is not set in environment variables")
    raise ValueError("RAPIDAPI_KEY is required")

# URL de l'API RapidAPI
RAPIDAPI_URL = "https://youtube-keywords-in-google-trends.p.rapidapi.com/youtube_keywords_in_google_trends"

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
        logger.info(f"Optimizing YouTube description for artist: {artist}, styles: {styles}, language: {language}, tone: {tone}")

        # Définir le nom de la langue pour le prompt
        language_names = {
            "fr": "French",
            "en": "English",
            "de": "German",
            "es": "Spanish",
            "pt": "Portuguese"
        }
        language_name = language_names.get(language, "French")

        # Étape 1 : Récupérer les termes de recherche via RapidAPI
        logger.info("Fetching long-tail search terms from RapidAPI")
        headers = {
            "X-RapidAPI-Key": rapidapi_key,
            "X-RapidAPI-Host": "youtube-keywords-in-google-trends.p.rapidapi.com"
        }
        querystring = {
            "keyword": styles_str.replace(", ", " "),  # Ex. "metal metal industriel electro-metal nu metal"
            "region": "FR",  # Région France
            "timeframe": "2025"  # Année cible
        }
        try:
            response = requests.get(RAPIDAPI_URL, headers=headers, params=querystring)
            response.raise_for_status()
            rapidapi_data = response.json()
            logger.info(f"RapidAPI response: {rapidapi_data}")
            # Supposons que l'API retourne une liste de termes dans "keywords" ou "data"
            search_terms = rapidapi_data.get("keywords", rapidapi_data.get("data", []))[:10]
            # S'assurer que chaque terme fait max 60 caractères
            search_terms = [term[:60] for term in search_terms]
            if not search_terms:
                logger.warning("No search terms returned from RapidAPI, using fallback")
                search_terms = [
                    "best metal song 2025", "top metal industriel 2025", "nu metal hits 2025",
                    "electro metal playlist 2025", "Sidilarsen new album", "metal français 2025",
                    "best metal bands 2025", "metal industriel live", "nu metal 2025 songs",
                    "Sidilarsen clips"
                ]
        except Exception as e:
            logger.error(f"RapidAPI call failed: {str(e)}")
            search_terms = [
                "best metal song 2025", "top metal industriel 2025", "nu metal hits 2025",
                "electro metal playlist 2025", "Sidilarsen new album", "metal français 2025",
                "best metal bands 2025", "metal industriel live", "nu metal 2025 songs",
                "Sidilarsen clips"
            ]

        # Étape 2 : Utiliser OpenAI pour trouver des artistes similaires basés sur les termes de recherche
        logger.info("Using OpenAI to find similar artists based on search terms")
        search_terms_str = ", ".join(search_terms)
        similar_artists_prompt = f"""
You are a music industry expert. Based on the following long-tail search terms related to the genres {styles_str}, identify artists that would likely appear in YouTube or Google search results for these terms in 2025:
- Search terms: {search_terms_str}

Generate the following:
- A list of 5 artists (just the names, no additional text) that are likely to appear in search results for these terms, excluding {artist}.

Return the response in the following JSON format:
{{
    "similar_artists": ["<artist1>", "<artist2>", "<artist3>", "<artist4>", "<artist5>"]
}}
"""
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "user", "content": similar_artists_prompt}],
                max_tokens=200,
                temperature=0.7
            )
            raw_text = response.choices[0].message.content.strip()
            logger.info(f"OpenAI response for similar artists: {raw_text}")
            similar_data = json.loads(raw_text)
            similar_artists = similar_data.get("similar_artists", ["Slipknot", "Korn", "Linkin Park", "Rammstein", "Marilyn Manson"])
        except Exception as e:
            logger.error(f"OpenAI API call for similar artists failed: {str(e)}")
            similar_artists = ["Slipknot", "Korn", "Linkin Park", "Rammstein", "Marilyn Manson"]

        # Étape 3 : Générer la description YouTube via OpenAI
        description_prompt = f"""
You are a YouTube marketing expert specializing in music promotion. Your task is to create an optimized YouTube description for the artist and genres below:
- Artist: {artist}
- Genres: {styles_str}
- Bio: {bio if bio else "Not provided"}
- Lyrics sample: {lyrics if lyrics else "Not provided"}

Generate the following in {language_name} with a {tone} tone:
1. A perfect YouTube description (max 2000 characters) structured like this:
   - Line 1: "{artist.upper()} - 'Adelphité' (clip officiel)" (use 'Adelphité' as default song title unless bio/lyrics suggest another).
   - Line 2: "Extrait de l’album : Que La Lumière Soit" (use 'Que La Lumière Soit' as default album unless bio suggests another).
   - Line 3: "▶ Commander / Écouter : XXXX".
   - Section "CRÉDITS" : List fictional credits (e.g., Réalisation, Chorégraphe) with Instagram placeholders (e.g., "Instagram: XXXX").
   - Section "➡️ Suivre {artist.upper()}" : List social media placeholders (e.g., "Facebook: XXXX", "Instagram: XXXX", "Youtube: XXXX", "TikTok: (rajoutez votre lien)", "Spotify: XXXX", "Site: XXXX").
   - Section "LYRICS" : Include the full lyrics sample if provided, otherwise a short placeholder (e.g., "Lyrics not available").
   - Use bio/lyrics to personalize (e.g., album title, song title) and reflect the {tone} tone.

Return the response in the following JSON format:
{{
    "description": "<description_text>"
}}
"""

        logger.info("Calling OpenAI to generate YouTube description")
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "user", "content": description_prompt}],
                max_tokens=1000,
                temperature=0.7
            )
            raw_text = response.choices[0].message.content.strip()
            logger.info(f"Raw response from OpenAI for description: {raw_text}")
        except Exception as e:
            logger.error(f"OpenAI API call for description failed: {str(e)}")
            raw_text = json.dumps({
                "description": f"{artist.upper()}\n'Default Song' (clip officiel)\nExtrait de l’album : Default Album\n\n▶ Commander / Écouter : XXXX\n\nCRÉDITS:\nRéalisation: Instagram: XXXX\n\n➡️ Suivre {artist.upper()}:\nFacebook: XXXX\nInstagram: XXXX\nYoutube: XXXX\nTikTok: (rajoutez votre lien)\nSpotify: XXXX\nSite: XXXX\n\nLYRICS:\nLyrics not available"
            })

        # Parsing sécurisé de la réponse JSON
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI response as JSON: {str(e)}")
            return jsonify({"error": "Invalid response format from OpenAI", "details": str(e)}), 500

        description = data.get("description", f"{artist.upper()}\n'Default Song' (clip officiel)\nExtrait de l’album : Default Album\n\n▶ Commander / Écouter : XXXX\n\nCRÉDITS:\nRéalisation: Instagram: XXXX\n\n➡️ Suivre {artist.upper()}:\nFacebook: XXXX\nInstagram: XXXX\nYoutube: XXXX\nTikTok: (rajoutez votre lien)\nSpotify: XXXX\nSite: XXXX\n\nLYRICS:\nLyrics not available")

        # Vérifier la longueur de la description
        if len(description) > 2000:
            logger.warning(f"Description exceeds 2000 characters, truncating")
            description = description[:1997] + "..."

        # Retourner la réponse
        return jsonify({
            "youtube_description": {
                "description": description,
                "search_terms": search_terms,
                "similar_artists": similar_artists
            }
        }), 200

    except Exception as e:
        logger.error(f"Error generating YouTube description: {str(e)}")
        return jsonify({"error": "Failed to generate YouTube description", "details": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
