from quart import Quart, request, jsonify
import openai
import os
from dotenv import load_dotenv
import logging

app = Quart(__name__)

# Configuration des logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Chargement des variables d'environnement
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    logger.critical("OPENAI_API_KEY manquant")
    raise ValueError("OPENAI_API_KEY manquant")

@app.route('/analyze', methods=['POST'])
async def analyze():
    try:
        data = await request.get_json()
        if not data:
            logger.error("Aucune donnée JSON fournie")
            return jsonify({"error": "Aucune donnée fournie"}), 400

        # Validation des champs obligatoires
        required_fields = ['artist', 'song', 'genres']
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            logger.error(f"Champs manquants : {missing_fields}")
            return jsonify({"error": f"Champs manquants : {missing_fields}"}), 400

        artist = data.get('artist')
        song = data.get('song')
        genres = data.get('genres')

        # Appel à l'API OpenAI pour analyser les données (exemple simplifié)
        client = openai.OpenAI(api_key=openai.api_key)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Tu es un analyste musical. Analyse les données suivantes et renvoie les styles, une URL d'image fictive, et des tendances."},
                {"role": "user", "content": f"Artiste : {artist}, Chanson : {song}, Genres : {', '.join(genres)}"}
            ],
            max_tokens=500,
            temperature=0.7
        )
        result = response.choices[0].message.content

        # Simuler une réponse (à adapter selon la logique réelle)
        analysis_data = {
            "artist": artist,
            "song": song,
            "styles": genres,  # Utiliser les genres fournis
            "artist_image_url": f"https://example.com/{artist.lower().replace(' ', '-')}.jpg",
            "lookalike_artists": [],  # Ne pas inclure ici, géré par l'Optimizer
            "trends": []  # Ne pas inclure ici, géré par l'Optimizer
        }

        return jsonify(analysis_data), 200

    except openai.APIError as e:
        logger.error(f"Erreur OpenAI : {str(e)}")
        return jsonify({"error": f"Erreur OpenAI : {str(e)}"}), 500
    except Exception as e:
        logger.error(f"Erreur inattendue : {str(e)}")
        return jsonify({"error": f"Erreur interne : {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=8080)
