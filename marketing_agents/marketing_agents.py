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

# Fonction pour générer des drafts d'annonces avec OpenAI
def generate_ad_drafts(artist, genre, lyrics="", bio=""):
    try:
        prompt = f"""
        You are a marketing assistant for musicians. Generate 3 advertising drafts for the following artist:
        - Artist: {artist}
        - Genre: {genre}
        - Lyrics (optional): {lyrics if lyrics else 'Not provided'}
        - Bio (optional): {bio if bio else 'Not provided'}

        Each draft must include:
        - A short title (max 30 characters)
        - A description (max 90 characters)
        - A platform (choose between Instagram, YouTube, or Google Ads)

        Return the response in the following JSON format:
        [
            {{"title": "<title>", "content": "<description>", "platform": "<platform>"}},
            {{"title": "<title>", "content": "<description>", "platform": "<platform>"}},
            {{"title": "<title>", "content": "<description>", "platform": "<platform>"}}
        ]
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.7
        )
        
        raw_text = response.choices[0].message.content.strip()
        logger.info(f"Raw response from OpenAI: {raw_text}")
        
        # Parser la réponse JSON
        drafts = json.loads(raw_text)
        
        # Ajouter les character_counts pour chaque draft
        for draft in drafts:
            draft["character_counts"] = {
                "title": len(draft["title"]),
                "content": len(draft["content"])
            }
        
        return drafts
    except Exception as e:
        logger.error(f"Error generating ad drafts with OpenAI: {str(e)}")
        # Retourner des drafts par défaut en cas d'erreur
        return [
            {"title": f"Discover {artist}!", "content": f"New {genre} hit awaits!", "platform": "Instagram", "character_counts": {"title": 14 + len(artist), "content": 22}},
            {"title": f"{artist} Rocks", "content": f"Feel the {genre} vibe with {artist}!", "platform": "YouTube", "character_counts": {"title": 10 + len(artist), "content": 28 + len(artist)}},
            {"title": f"{artist} New Hit", "content": f"Top {genre} artist {artist} drops now!", "platform": "Google Ads", "character_counts": {"title": 11 + len(artist), "content": 31 + len(artist)}}
        ]

# Endpoint principal pour générer les drafts
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
    
    logger.info(f"Generating ads for artist: {artist}, genre: {genre}")
    drafts = generate_ad_drafts(artist, genre, lyrics, bio)
    
    return jsonify({"drafts": drafts}), 200

# Endpoint de prévisualisation (optionnel)
@app.route('/preview', methods=['GET'])
def preview():
    drafts = generate_ad_drafts("Sample Artist", "Rock")
    return jsonify({"drafts": drafts}), 200

# Endpoint de santé pour Railway
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "message": "Marketing Agents is running"}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
