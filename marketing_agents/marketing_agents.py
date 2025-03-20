#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import requests
from flask import Flask, request, jsonify, render_template
import openai
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Configuration de l'application Flask
app = Flask(__name__, template_folder='.')
app.config['JSON_AS_ASCII'] = False

# Configuration d'OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

class MarketingAgent:
    def __init__(self):
        self.model = "gpt-4"  # Utiliser GPT-4 pour de meilleurs résultats

    def generate_ad_content(self, artist_name, single_name, similar_artists, genre=None, mood=None):
        """
        Génère du contenu publicitaire pour un artiste musical en utilisant OpenAI.
        
        Args:
            artist_name (str): Nom de l'artiste
            single_name (str): Nom du single
            similar_artists (list): Liste d'artistes similaires
            genre (str, optional): Genre musical
            mood (str, optional): Ambiance du morceau
            
        Returns:
            dict: Contenu publicitaire généré
        """
        # Construction du prompt pour OpenAI
        prompt = f"""
        En tant qu'expert en marketing musical, génère du contenu publicitaire pour:
        
        Artiste: {artist_name}
        Single: {single_name}
        Genre: {genre if genre else 'Non spécifié'}
        Ambiance: {mood if mood else 'Non spécifiée'}
        Artistes similaires: {', '.join(similar_artists)}
        
        Génère exactement:
        1. 5 titres courts accrocheurs (maximum 30 caractères)
        2. 5 titres longs plus descriptifs (maximum 90 caractères)
        3. 5 descriptions longues détaillées (environ 150-200 mots chacune)
        
        Les titres et descriptions doivent être optimisés pour Google Ads, respecter les règles publicitaires,
        et être conçus pour attirer les fans de musique qui apprécient des artistes similaires.
        
        Réponds uniquement au format JSON avec la structure suivante:
        {{"short_titles": [5 titres courts], "long_titles": [5 titres longs], "long_descriptions": [5 descriptions longues]}}
        """
        
        try:
            # Appel à l'API OpenAI
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Tu es un expert en marketing musical spécialisé dans la création d'annonces publicitaires optimisées pour Google Ads."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            # Extraction et parsing du contenu JSON
            content = response.choices[0].message.content.strip()
            # Extraction du JSON si la réponse contient d'autres éléments
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
                
            result = json.loads(content)
            
            # Vérification de la structure du résultat
            required_keys = ["short_titles", "long_titles", "long_descriptions"]
            for key in required_keys:
                if key not in result or len(result[key]) != 5:
                    raise ValueError(f"La clé {key} est manquante ou ne contient pas 5 éléments")
                    
            return result
            
        except Exception as e:
            print(f"Erreur lors de la génération du contenu: {str(e)}")
            # Retourner un contenu par défaut en cas d'erreur
            return {
                "short_titles": [
                    f"Découvrez {single_name}",
                    f"{artist_name} - Nouveau Single",
                    "Musique Fraîche",
                    "Son Unique",
                    "Écouter Maintenant"
                ],
                "long_titles": [
                    f"{artist_name} lance {single_name} - Le single qui va marquer 2025",
                    f"Fan de {similar_artists[0]}? Découvrez {artist_name}",
                    f"{single_name} - Une nouvelle dimension musicale par {artist_name}",
                    f"L'évolution musicale de {artist_name} avec {single_name}",
                    f"{single_name} - Le titre qui redéfinit le genre musical"
                ],
                "long_descriptions": [
                    f"Plongez dans l'univers musical de {artist_name} avec son dernier single {single_name}. Une fusion parfaite de rythmes entraînants et de paroles profondes qui résonnent avec l'âme. Inspiré par des artistes comme {', '.join(similar_artists[:2])}, mais avec une touche unique qui définit son style distinctif. Une expérience sonore qui captive dès la première écoute et vous transporte dans un voyage émotionnel inoubliable.",
                    f"{artist_name} repousse les limites avec {single_name}, un single qui explore de nouvelles dimensions sonores tout en restant fidèle à ses racines. La production impeccable met en valeur sa voix distinctive et ses talents d'écriture, créant une ambiance qui évoque les meilleurs moments de {similar_artists[0]} tout en établissant une identité artistique forte et personnelle.",
                    f"Avec {single_name}, {artist_name} nous offre une œuvre qui transcende les genres et capture l'essence de notre époque. Chaque note, chaque parole a été méticuleusement travaillée pour créer une expérience immersive qui résonne avec les fans de {', '.join(similar_artists)}. Un incontournable pour tout amateur de musique authentique et innovante.",
                    f"Le parcours artistique de {artist_name} atteint de nouveaux sommets avec {single_name}. Ce single représente l'évolution naturelle d'un talent en constante progression, influencé par des légendes comme {similar_artists[1]} mais définitivement tourné vers l'avenir. Une œuvre qui s'inscrit parfaitement dans l'air du temps tout en possédant une qualité intemporelle.",
                    f"{single_name} est bien plus qu'un simple morceau - c'est une déclaration artistique de {artist_name} qui reflète sa vision unique et son approche novatrice. Les arrangements sophistiqués et la production cristalline créent un paysage sonore qui captive l'auditeur du début à la fin. Pour les fans de {', '.join(similar_artists[1:3])}, cette découverte sera une révélation."
                ]
            }

    def get_artist_image_url(self, artist_name):
        """
        Tente de récupérer une URL d'image pour l'artiste.
        Dans une implémentation réelle, cela pourrait utiliser l'API Spotify ou une autre source.
        
        Args:
            artist_name (str): Nom de l'artiste
            
        Returns:
            str: URL de l'image de l'artiste ou None si non trouvée
        """
        # Ceci est un placeholder - dans une implémentation réelle, 
        # vous utiliseriez l'API Spotify ou une autre source
        return None

# Routes Flask
@app.route('/generate', methods=['POST'])
def generate():
    """
    Endpoint API pour générer du contenu publicitaire
    
    Exemple de requête:
    {
        "artist_name": "Nom de l'artiste",
        "single_name": "Nom du single",
        "similar_artists": ["Artiste similaire 1", "Artiste similaire 2", ...],
        "genre": "Genre musical",
        "mood": "Ambiance"
    }
    """
    try:
        data = request.json
        
        # Validation des données requises
        required_fields = ["artist_name", "single_name", "similar_artists"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Le champ '{field}' est requis"}), 400
                
        # Initialisation de l'agent marketing
        agent = MarketingAgent()
        
        # Génération du contenu
        content = agent.generate_ad_content(
            data["artist_name"],
            data["single_name"],
            data["similar_artists"],
            data.get("genre"),
            data.get("mood")
        )
        
        # Récupération de l'URL de l'image de l'artiste
        artist_image_url = agent.get_artist_image_url(data["artist_name"])
        
        # Préparation des données pour le template
        template_data = {
            "artist_name": data["artist_name"],
            "single_name": data["single_name"],
            "similar_artists": data["similar_artists"],
            "short_titles": content["short_titles"],
            "long_titles": content["long_titles"],
            "long_descriptions": content["long_descriptions"],
            "artist_image_url": artist_image_url
        }
        
        # Rendu du template HTML
        html_content = render_template('template.html', **template_data)
        
        # Retourner à la fois le HTML et les données JSON
        return jsonify({
            "html": html_content,
            "data": template_data
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/preview', methods=['GET'])
def preview():
    """
    Endpoint pour prévisualiser le template avec des données d'exemple
    """
    # Données d'exemple
    example_data = {
        "artist_name": "Melodic Horizon",
        "single_name": "Aurore Électrique",
        "similar_artists": ["Daft Punk", "Justice", "Air", "M83"],
        "short_titles": [
            "Aurore Électrique - Écoutez !",
            "Melodic Horizon - Nouveau Hit",
            "Son Électro Français Innovant",
            "Voyage Sonore Immersif",
            "La Révélation Électro 2025"
        ],
        "long_titles": [
            "Melodic Horizon lance Aurore Électrique - L'hymne électro de 2025",
            "Fan de Daft Punk ? Découvrez Melodic Horizon et son Aurore Électrique",
            "Aurore Électrique - Une nouvelle dimension électronique française",
            "L'évolution du son français avec Melodic Horizon - Aurore Électrique",
            "Aurore Électrique - Le titre qui redéfinit l'électro moderne"
        ],
        "long_descriptions": [
            "Plongez dans l'univers électronique de Melodic Horizon avec son dernier single Aurore Électrique Abonnez-vous dès maintenant. Une fusion parfaite de beats entraînants et de mélodies atmosphériques qui évoquent l'aube d'une nouvelle ère musicale. Inspiré par des légendes comme Daft Punk et Justice, mais avec une signature sonore distinctement contemporaine. Une expérience immersive qui captive dès la première écoute et vous transporte dans un voyage émotionnel à travers des paysages sonores futuristes.",
            "Melodic Horizon repousse les frontières de l'électro française avec Aurore Électrique, un single qui explore de nouvelles dimensions sonores tout en rendant hommage aux racines du genre. La production impeccable combine synthés vintage et techniques modernes, créant une ambiance qui évoque les meilleurs moments de M83 tout en établissant une identité artistique forte et personnelle.",
            "Avec Aurore Électrique, Melodic Horizon nous offre une œuvre qui transcende les genres et capture l'essence de la French Touch moderne. Chaque couche sonore a été méticuleusement travaillée pour créer une expérience immersive qui résonne avec les fans d'Air et de Justice. Un incontournable pour tout amateur d'électro authentique et innovante.",
            "Le parcours artistique de Melodic Horizon atteint de nouveaux sommets avec Aurore Électrique. Ce single représente l'évolution naturelle de l'électro française, influencé par des pionniers comme Daft Punk mais définitivement tourné vers l'avenir. Une œuvre qui s'inscrit parfaitement dans l'héritage électronique français tout en possédant une qualité intemporelle qui défie les tendances éphémères.",
            "Aurore Électrique est bien plus qu'un simple morceau - c'est une déclaration artistique de Melodic Horizon qui reflète sa vision unique de l'électro contemporaine. Les arrangements sophistiqués et la production cristalline créent un paysage sonore qui captive l'auditeur du début à la fin. Pour les fans de M83 et d'Air, cette découverte sera une révélation qui redéfinit les possibilités du genre."
        ],
        "artist_image_url": None
    }
    
    # Rendu du template HTML avec les données d'exemple
    return render_template('template.html', **example_data)

if __name__ == '__main__':
    # Vérifier si la clé API OpenAI est configurée
    if not os.getenv("OPENAI_API_KEY"):
        print("ATTENTION: La variable d'environnement OPENAI_API_KEY n'est pas définie.")
        print("Le service utilisera des réponses par défaut en cas d'erreur.")
    
    # Démarrer le serveur Flask
    app.run(host='0.0.0.0', port=5000, debug=True)
