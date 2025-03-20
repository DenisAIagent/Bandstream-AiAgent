import openai
from flask import Flask, request, jsonify
import os
import requests
import logging
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

app = Flask(__name__)

# Configuration de l'API OpenAI
openai.api_key = os.getenv('OPENAI_API_KEY')

# Configuration de l'API centrale
API_SERVER_URL = os.getenv('API_SERVER_URL', 'https://votre-api-server.railway.app') 

# Mots-clés interdits et caractères spéciaux à éviter
FORBIDDEN_KEYWORDS = ["gratuit", "téléchargement", "streaming illégal", "offert"]
FORBIDDEN_CHARS = ["%", "$", "€", "£", "¥", "©", "®", "™", "😀", "👍", "🎵", "🎸", "🎧","!',"?""/","$"]

def get_lookalike_artists():
    """Récupère les artistes similaires depuis l'API centrale"""
    try:
        response = requests.get(f"{API_SERVER_URL}/get/lookalike_artists")
        if response.status_code == 200:
            data = response.json()
            return data.get("data", [])
        return []
    except Exception as e:
        logging.error(f"Erreur lors de la récupération des artistes similaires: {str(e)}")
        return []

def get_campaign_insights():
    """Récupère les insights de la campagne depuis l'API centrale"""
    try:
        response = requests.get(f"{API_SERVER_URL}/get/campaign_insights")
        if response.status_code == 200:
            data = response.json()
            return data.get("data", {})
        return {}
    except Exception as e:
        logging.error(f"Erreur lors de la récupération des insights: {str(e)}")
        return {}

def generate_ai_ads(artist_name, genre, lookalike_artists, insights):
    """Génère des annonces en utilisant l'API OpenAI"""
    try:
        # Préparer le contexte pour l'IA
        lookalike_str = ", ".join(lookalike_artists) if lookalike_artists else "aucun artiste similaire trouvé"
        
        prompt = f"""
        Génère 3 annonces publicitaires pour l'artiste musical {artist_name} ({genre}).
        
        Informations importantes:
        - Artistes similaires: {lookalike_str}
        - Insights: {insights}
        
        Règles strictes à respecter:
        1. Titre: Exactement 30 caractères maximum (pas un de plus)
        2. Contenu: Exactement 90 caractères maximum (pas un de plus)
        3. Ne pas utiliser les mots: gratuit, téléchargement, streaming illégal, offert
        4. Ne pas utiliser de caractères spéciaux comme %, $, €, £, ¥, ©, ®, ™ ou des émojis
        5. Créer un sentiment d'urgence (FOMO: Fear Of Missing Out)
        6. Mentionner au moins un artiste similaire dans chaque annonce
        7. Chaque annonce doit être pour une plateforme différente (Instagram, Facebook, YouTube)
        
        Format de réponse (JSON):
        [
          {{
            "titre": "Titre de l'annonce 1",
            "contenu": "Contenu de l'annonce 1",
            "plateforme": "Instagram"
          }},
          {{
            "titre": "Titre de l'annonce 2",
            "contenu": "Contenu de l'annonce 2",
            "plateforme": "Facebook"
          }},
          {{
            "titre": "Titre de l'annonce 3",
            "contenu": "Contenu de l'annonce 3",
            "plateforme": "YouTube"
          }}
        ]
        """
        
        # Appel à l'API OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-4",  # ou un autre modèle disponible
            messages=[
                {"role": "system", "content": "Tu es un expert en marketing musical qui crée des annonces publicitaires percutantes et respectant strictement les contraintes."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        # Extraire et parser la réponse
        content = response.choices[0].message.content
        import json
        try:
            ads = json.loads(content)
            # Vérifier et tronquer si nécessaire
            for ad in ads:
                if len(ad["titre"]) > 30:
                    ad["titre"] = ad["titre"][:30]
                if len(ad["contenu"]) > 90:
                    ad["contenu"] = ad["contenu"][:90]
            return ads
        except json.JSONDecodeError:
            logging.error("Erreur lors du parsing de la réponse OpenAI")
            return []
            
    except Exception as e:
        logging.error(f"Erreur lors de la génération des annonces avec OpenAI: {str(e)}")
        return []

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "success", "message": "Marketing Agents is running"}), 200

@app.route('/generate_ads', methods=['POST'])
def generate_ads():
    try:
        data = request.get_json()
        artist_name = data.get('artist_name', '')
        genre = data.get('genre', '')
        
        if not artist_name:
            return jsonify({"error": "Artist name is required"}), 400
            
        # Récupérer les artistes similaires et les insights
        lookalike_artists = get_lookalike_artists()
        insights = get_campaign_insights()
        
        # Générer les annonces avec OpenAI
        ads = generate_ai_ads(artist_name, genre, lookalike_artists, insights)
        
        # Envoyer les annonces à l'API centrale
        try:
            response = requests.post(
                f"{API_SERVER_URL}/store/ad_draft", 
                json={"drafts": ads}
            )
        except Exception as e:
            logging.error(f"Erreur lors de l'envoi des annonces à l'API centrale: {str(e)}")
        
        return jsonify({
            "status": "success",
            "drafts": ads
        }), 200
        
    except Exception as e:
        logging.error(f"Erreur lors de la génération des annonces: {str(e)}")
        return jsonify({
            "status": "error", 
            "message": f"Error generating ad drafts: {str(e)}"
        }), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5003))
    app.run(host="0.0.0.0", port=port)
