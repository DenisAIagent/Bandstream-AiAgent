import asyncio
import logging
from flask import Flask, render_template, request, jsonify
import aiohttp
from jinja2 import Environment, FileSystemLoader

app = Flask(__name__)

# Configuration des logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration de Jinja2
env = Environment(loader=FileSystemLoader('templates'))

async def fetch_data(session, url, data, retries=5):
    for attempt in range(retries):
        try:
            async with session.post(url, json=data, timeout=10) as response:
                response.raise_for_status()
                return await response.json()
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1}/{retries} failed for {url}: {str(e)}")
            if attempt + 1 == retries:
                raise Exception(f"Failed to call {url} after {retries} attempts: {str(e)}. Please try again later.")
            await asyncio.sleep(2 ** attempt)

@app.route('/')
def index():
    template = env.get_template('index.html')
    return template.render()

@app.route('/generate_campaign', methods=['POST'])
async def generate_campaign():
    try:
        data = request.get_json()
        if not data:
            logger.error("Aucune donnée JSON fournie")
            return jsonify({"error": "Aucune donnée fournie"}), 400

        artist = data.get('artist')
        song = data.get('song', 'Unknown Song')  # Valeur par défaut si manquante
        genres = data.get('genres', ['rock'])  # Valeur par défaut si manquante
        if not isinstance(genres, list):
            genres = [genres]

        # Ajouter des champs supplémentaires pour l'Agent Marketing
        campaign_data = {
            "artist": artist,
            "song": song,
            "genres": genres,
            "language": data.get('language', 'français'),
            "promotion_type": data.get('promotion_type', 'clip'),
            "tone": data.get('tone', 'engageant'),
            "bio": data.get('bio', f"Artiste passionné par {genres[0]} avec une approche unique."),
            "bio_tone": data.get('bio_tone', 'authentique'),
            "bio_themes": data.get('bio_themes', 'émotion, créativité'),
            "target_audience": data.get('target_audience', 'tous publics'),
            "announcement_style": data.get('announcement_style', 'Engageant'),
            "song_link": data.get('song_link', '[insert link]'),
            "song_lyrics": data.get('song_lyrics', '')
        }

        async with aiohttp.ClientSession() as session:
            # Appels simultanés aux différents services
            analysis_task = fetch_data(session, "https://analyst-production.up.railway.app/analyze", {
                "artist": artist,
                "song": song,
                "genres": genres
            })
            optimizer_task = fetch_data(session, "https://optimizer-production.up.railway.app/optimize", {
                "artist": artist,
                "song": song,
                "genres": genres
            })
            analysis_data, optimizer_data = await asyncio.gather(analysis_task, optimizer_task)

            # Ajouter les lookalike_artists et trends à campaign_data pour l'Agent Marketing
            campaign_data["lookalike_artists"] = optimizer_data["analysis"].get("lookalike_artists", [])
            campaign_data["trends"] = optimizer_data["analysis"].get("trends", [])

            # Appeler l'Agent Marketing
            marketing_task = fetch_data(session, "https://marketing-agent-production.up.railway.app/generate_ads", campaign_data)
            ad_data = await marketing_task

        # Combiner les données pour le rendu
        result = {
            "analysis": analysis_data,
            "ads": ad_data,
            "strategy": optimizer_data["strategy"]
        }

        template = env.get_template('result.html')
        return template.render(**result)

    except Exception as e:
        logger.error(f"Error in generate_campaign: {str(e)}")
        template = env.get_template('error.html')
        return template.render(error=str(e)), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
