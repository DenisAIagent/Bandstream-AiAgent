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

# Fonction pour générer les contenus avec OpenAI
def generate_ad_content(artist, genre, lyrics="", bio=""):
    try:
        prompt = f"""
        You are a marketing assistant for musicians. Generate advertising content for the following artist:
        - Artist: {artist}
        - Genre: {genre}
        - Lyrics (optional): {lyrics if lyrics else 'Not provided'}
        - Bio (optional): {bio if bio else 'Not provided'}

        Generate the following:
        - 5 short titles (max 30 characters each)
        - 5 long titles (more descriptive, around 50-70 characters)
        - 5 long descriptions (detailed, max 90 characters each, exploring influences, lyrics, production, cultural impact, etc.)

        Return the response in the following JSON format:
        {{
            "short_titles": ["<title1>", "<title2>", "<title3>", "<title4>", "<title5>"],
            "long_titles": ["<title1>", "<title2>", "<title3>", "<title4>", "<title5>"],
            "long_descriptions": ["<desc1>", "<desc2>", "<desc3>", "<desc4>", "<desc5>"]
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
        
        # Parser la réponse JSON
        content = json.loads(raw_text)
        
        # Ajouter les character_counts pour les short_titles
        for i in range(len(content["short_titles"])):
            content["short_titles"][i] = {
                "title": content["short_titles"][i],
                "character_count": len(content["short_titles"][i])
            }
        
        # Ajouter les character_counts pour les long_titles
        for i in range(len(content["long_titles"])):
            content["long_titles"][i] = {
                "title": content["long_titles"][i],
                "character_count": len(content["long_titles"][i])
            }
        
        # Ajouter les character_counts pour les long_descriptions
        for i in range(len(content["long_descriptions"])):
            content["long_descriptions"][i] = {
                "description": content["long_descriptions"][i][:90],  # S'assurer que la description ne dépasse pas 90 caractères
                "character_count": len(content["long_descriptions"][i][:90])
            }
        
        return content
    except Exception as e:
        logger.error(f"Error generating ad content with OpenAI: {str(e)}")
        # Retourner des données par défaut en cas d'erreur
        return {
            "short_titles": [
                {"title": f"Discover {artist} Now!", "character_count": 14 + len(artist)},
                {"title": f"{artist} Rocks {genre}!", "character_count": 10 + len(artist) + len(genre)},
                {"title": f"Feel {artist}'s Beat", "character_count": 12 + len(artist)},
                {"title": f"{artist} New Hit Out!", "character_count": 12 + len(artist)},
                {"title": f"Join {artist}'s Vibe", "character_count": 12 + len(artist)}
            ],
            "long_titles": [
                {"title": f"Experience the Raw Power of {artist}'s {genre} Sound", "character_count": 28 + len(artist) + len(genre)},
                {"title": f"{artist} Redefines {genre} with a Bold New Single", "character_count": 25 + len(artist) + len(genre)},
                {"title": f"Dive into {artist}'s Latest {genre} Masterpiece", "character_count": 24 + len(artist) + len(genre)},
                {"title": f"{artist}'s {genre} Journey: A New Chapter Begins", "character_count": 26 + len(artist) + len(genre)},
                {"title": f"Unleash Your Inner Fan with {artist}'s {genre} Hit", "character_count": 27 + len(artist) + len(genre)}
            ],
            "long_descriptions": [
                {"description": f"Explore {artist}'s {genre} single, a blend of energy!", "character_count": 37 + len(artist) + len(genre)},
                {"description": f"{artist}'s {genre} hit mixes deep lyrics and power!", "character_count": 35 + len(artist) + len(genre)},
                {"description": f"With {genre}, {artist} proves their music mastery!", "character_count": 34 + len(artist) + len(genre)},
                {"description": f"{artist}'s {genre} track is a cultural milestone!", "character_count": 34 + len(artist) + len(genre)},
                {"description": f"Join {genre} with {artist}'s latest single now!", "character_count": 32 + len(artist) + len(genre)}
            ]
        }

# Endpoint principal pour générer les contenus
@app.route('/generate_ads', methods=['POST'])
def generate_ads():
    data = request.get_json()
    if not data or "artist" not in data or "genre" not in data:
        logger.error("Missing required fields 'artist' or 'genre' in request")
        return jsonify({"error": "Missing required fields 'artist' or 'genre'"}), 400
    
    artist = data.get("artist")
    genre = data.get("genre")
    lyrics = data.get("lyrics", "")
    bio = data.get("bio", "")
    
    logger.info(f"Generating ad content for artist: {artist}, genre: {genre}")
    content = generate_ad_content(artist, genre, lyrics, bio)
    
    return jsonify(content), 200

# Endpoint de prévisualisation (optionnel)
@app.route('/preview', methods=['GET'])
def preview():
    content = generate_ad_content("Sample Artist", "Rock")
    return jsonify(content), 200

# Endpoint de santé pour Railway
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "message": "Marketing Agents is running"}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
