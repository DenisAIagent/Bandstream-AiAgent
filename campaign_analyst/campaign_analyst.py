import os
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
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    logger.error("OPENAI_API_KEY is not set in environment variables")
    raise ValueError("OPENAI_API_KEY is required")

# Fonction pour obtenir les tendances et artistes similaires avec OpenAI
def get_trends_and_lookalikes(artist, style):
    try:
        prompt = f"""
        You are a music industry expert. Provide information for the following artist and genre:
        - Artist: {artist}
        - Genre: {style}

        Generate the following:
        - A list of 2 current trends in the {style} genre (short phrases, max 50 characters each).
        - A list of 15 trending artists in the {style} genre (just the artist names, no additional text).

        Return the response in the following JSON format:
        {{
            "trends": ["<trend1>", "<trend2>"],
            "lookalike_artists": ["<artist1>", "<artist2>", ..., "<artist15>"]
        }}
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
        data = json.loads(raw_text)
        
        return {
            "trends": data.get("trends", ["No trends found"]),
            "lookalike_artists": data.get("lookalike_artists", ["No similar artists found"])
        }
    except Exception as e:
        logger.error(f"Error fetching trends and lookalikes with OpenAI: {str(e)}")
        return {
            "trends": ["Trend 1", "Trend 2"],
            "lookalike_artists": ["Artist 1", "Artist 2"]
        }  # Fallback

# Endpoint principal
@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.get_json()
    if not data or "artist" not in data or "style" not in data:
        logger.error("Missing required fields 'artist' or 'style' in request")
        return jsonify({"error": "Missing required fields 'artist' or 'style'"}), 400
    
    artist = data.get("artist")
    style = data.get("style")
    
    logger.info(f"Analyzing trends and lookalike artists for artist: {artist}, style: {style}")
    
    # Obtenir les tendances et artistes similaires
    result = get_trends_and_lookalikes(artist, style)
    trends = result["trends"]
    lookalike_artists = result["lookalike_artists"]
    
    # Stocker les données dans api_server
    try:
        requests.post(f"{os.getenv('API_SERVER_URL', 'https://api-server-production-e858.up.railway.app')}/store/trending_artists", json={"trends": trends})
        requests.post(f"{os.getenv('API_SERVER_URL', 'https://api-server-production-e858.up.railway.app')}/store/lookalike_artists", json={"lookalike_artists": lookalike_artists})
    except Exception as e:
        logger.error(f"Error storing data in api_server: {str(e)}")
    
    return jsonify({
        "trends": trends,
        "lookalike_artists": lookalike_artists,
        "style": style
    }), 200

# Endpoint de santé
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "message": "Campaign Analyst is running"}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
