import os
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
        prompt = f"Generate 3 advertising drafts for a musician. Use the following details:\n" \
                 f"- Artist: {artist}\n" \
                 f"- Genre: {genre}\n" \
                 f"- Lyrics (optional): {lyrics if lyrics else 'Not provided'}\n" \
                 f"- Bio (optional): {bio if bio else 'Not provided'}\n" \
                 "Each draft should include:\n" \
                 "- A short title (max 30 characters)\n" \
                 "- A description (max 90 characters)\n" \
                 "- A platform (Instagram, YouTube, or Google Ads)\n" \
                 "Return the drafts in JSON format."
        
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.7
        )
        
        # Supposons que GPT-4 renvoie un texte brut, on le parse manuellement ici
        # En pratique, on pourrait demander à GPT de retourner directement du JSON
        raw_text = response.choices[0].message.content.strip()
        logger.info(f"Raw response from OpenAI: {raw_text}")
        
        # Exemple de parsing simple (à adapter selon le format réel renvoyé par GPT)
        drafts = []
        lines = raw_text.split("\n")
        for i in range(0, len(lines), 4):
            if i + 2 < len(lines):
                title = lines[i].strip()[:30]
                desc = lines[i+1].strip()[:90]
                platform = lines[i+2].strip()
                drafts.append({
                    "title": title,
                    "content": desc,
                    "platform": platform,
                    "character_counts": {
                        "title": len(title),
                        "content": len(desc)
                    }
                })
        
        return drafts if drafts else [
            {"title": f"Discover {artist} Now!", "content": f"New {genre} hit awaits!", "platform": "Instagram", "character_counts": {"title": 20, "content": 22}},
            {"title": f"{artist} Rocks {genre}", "content": f"Feel the {genre} vibe with {artist}", "platform": "YouTube", "character_counts": {"title": 18, "content": 30}},
            {"title": f"{artist} New Single", "content": f"Top {genre} artist {artist} drops now", "platform": "Google Ads", "character_counts": {"title": 17, "content": 35}}
        ]
    except Exception as e:
        logger.error(f"Error generating ad drafts with OpenAI: {str(e)}")
        # Retourner des drafts par défaut en cas d'erreur
        return [
            {"title": f"Discover {artist} Now!", "content": f"New {genre} hit awaits!", "platform": "Instagram", "character_counts": {"title": 20, "content": 22}},
            {"title": f"{artist} Rocks {genre}", "content": f"Feel the {genre} vibe with {artist}", "platform": "YouTube", "character_counts": {"title": 18, "content": 30}},
            {"title": f"{artist} New Single", "content": f"Top {genre} artist {artist} drops now", "platform": "Google Ads", "character_counts": {"title": 17, "content": 35}}
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
