from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
from cachetools import TTLCache
import logging
import json
import re

app = Flask(__name__)

# Configuration des logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Chargement des variables d'environnement
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    logger.critical("OPENAI_API_KEY manquant")
    raise ValueError("OPENAI_API_KEY manquant")

# Détection de la version de l'API OpenAI et initialisation appropriée
try:
    # Tentative d'utilisation de l'API moderne (1.0.0+)
    from openai import OpenAI
    client = OpenAI()  # Utilise la variable d'environnement OPENAI_API_KEY automatiquement
    use_modern_api = True
    logger.info("Utilisation de l'API OpenAI moderne (1.0.0+)")
except (ImportError, TypeError):
    # Fallback sur l'API ancienne (0.28 et antérieure)
    import openai
    openai.api_key = openai_api_key
    use_modern_api = False
    logger.info("Utilisation de l'API OpenAI ancienne (0.28 et antérieure)")

# Cache avec TTL de 24h
cache = TTLCache(maxsize=100, ttl=86400)

# Endpoint de test pour vérifier que le serveur est accessible
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "message": "Marketing Agent is running"}), 200

def clean_description(description):
    generic_phrases = [
        r"Avec son style unique, .* rencontre un succès grandissant aux quatre coins du globe",
        r"With his unique style, .* is experiencing growing success across the globe",
        r"À chacune de ses sorties, il continue de surprendre et de créer l'engouement",
        r"With each release, .* continues to surprise his audience and build excitement",
        r"s'imposant comme une figure essentielle de la scène",
        r"cementing his place as a key figure in the .* scene"
    ]
    for phrase in generic_phrases:
        if re.search(phrase, description, re.IGNORECASE):
            description = re.sub(phrase, "", description, flags=re.IGNORECASE)
            description += "\nDécouvrez une expérience musicale authentique et vibrante !"
    return description.strip()

def validate_data(data):
    required_fields = ['artist', 'genres', 'language', 'promotion_type']
    missing_fields = [field for field in required_fields if not data.get(field)]
    if missing_fields:
        raise ValueError(f"Champs manquants : {missing_fields}")

    genres = data.get('genres', ['rock'])
    if not isinstance(genres, list):
        genres = [genres]
    if not genres:
        raise ValueError("Les genres ne peuvent pas être vides")

    lookalike_artists = data.get('lookalike_artists', [])
    if not lookalike_artists or not all(isinstance(artist, str) and artist and not artist.isspace() for artist in lookalike_artists):
        logger.warning("Lookalike artists invalides, utilisation des valeurs par défaut")
        primary_genre = genres[0].lower()
        default_lookalikes = {
            "rock": ["Nirvana", "Pearl Jam", "Soundgarden"],
            "punk": ["Green Day", "The Offspring", "Blink-182"],
            "grunge": ["Nirvana", "Alice in Chains", "Soundgarden"],
            "pop": ["Coldplay", "Imagine Dragons", "Maroon 5"],
            "metal": ["Metallica", "Rammstein", "Nightwish"],
            "metal symphonique": ["Nightwish", "Epica", "Within Temptation"],
            "metal indus": ["Rammstein", "Marilyn Manson", "Nine Inch Nails"],
            "default": ["Artiste 1", "Artiste 2", "Artiste 3"]
        }
        data['lookalike_artists'] = default_lookalikes.get(primary_genre, default_lookalikes["default"])[:3]

    return data

@app.route('/generate_ads', methods=['POST'])
def generate_ads():
    try:
        data = request.get_json()
        if not data:
            logger.error("Aucune donnée JSON fournie")
            return jsonify({"error": "Aucune donnée fournie"}), 400

        # Log des données reçues pour le débogage
        logger.info(f"Données reçues : {data}")

        # Validation des données d'entrée
        try:
            data = validate_data(data)
        except Exception as e:
            logger.error(f"Erreur de validation des données : {str(e)}")
            return jsonify({"error": f"Erreur de validation des données : {str(e)}"}), 400

        # Clé de cache
        cache_key = "_".join([str(data.get(field, '')) for field in ['artist', 'genres', 'language', 'promotion_type', 'song', 'tone']])
        logger.info(f"Clé de cache : {cache_key}")

        # Vérification du cache
        if cache_key in cache:
            logger.info(f"Réponse trouvée dans le cache pour : {cache_key}")
            cached_result = cache[cache_key]
            if not cached_result or "short_titles" not in cached_result:
                logger.warning(f"Données en cache vides ou corrompues pour : {cache_key}")
                cache.pop(cache_key)
            else:
                return jsonify(cached_result)

        # Génération du prompt
        prompt = generate_prompt(data)
        logger.info("Prompt généré avec succès")

        # Appel à l'API OpenAI avec détection automatique de la version
        try:
            logger.info("Appel à l'API OpenAI...")
            if use_modern_api:
                # Version moderne (1.0.0+)
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=2000,
                    temperature=0.7
                )
                result = response.choices[0].message.content
            else:
                # Version ancienne (0.28 et antérieure)
                response = openai.ChatCompletion.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=2000,
                    temperature=0.7
                )
                result = response.choices[0].message.content
            logger.info("Réponse OpenAI reçue avec succès")
        except Exception as e:
            logger.error(f"Erreur lors de l'appel à l'API OpenAI : {str(e)}")
            return jsonify({"error": f"Erreur lors de l'appel à l'API OpenAI : {str(e)}"}), 500

        # Nettoyer la réponse pour enlever les balises ```json ... ```
        result_cleaned = re.sub(r'^```json\n|\n```$', '', result).strip()

        # Vérification que la réponse est un JSON valide
        try:
            result_json = json.loads(result_cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"Réponse OpenAI non-JSON après nettoyage : {result_cleaned}")
            return jsonify({"error": "La génération a échoué : réponse non-JSON"}), 500

        # Vérification des clés attendues
        required_keys = ["short_titles", "long_titles", "long_descriptions", "youtube_description_short", "youtube_description_full", "analysis"]
        missing_keys = [key for key in required_keys if key not in result_json]
        if missing_keys:
            logger.error(f"Clés manquantes dans la réponse JSON : {missing_keys}")
            return jsonify({"error": f"Clés manquantes dans la réponse : {missing_keys}"}), 500

        # Vérification du nombre d'éléments
        if len(result_json["short_titles"]) != 5:
            logger.error(f"Nombre incorrect de short_titles : {len(result_json['short_titles'])}")
            return jsonify({"error": "Nombre incorrect de short_titles"}), 500
        if len(result_json["long_titles"]) != 5:
            logger.error(f"Nombre incorrect de long_titles : {len(result_json['long_titles'])}")
            return jsonify({"error": "Nombre incorrect de long_titles"}), 500
        if len(result_json["long_descriptions"]) != 5:
            logger.error(f"Nombre incorrect de long_descriptions : {len(result_json['long_descriptions'])}")
            return jsonify({"error": "Nombre incorrect de long_descriptions"}), 500

        # Nettoyer la description YouTube pour éviter les phrases génériques
        result_json["youtube_description_full"]["description"] = clean_description(result_json["youtube_description_full"]["description"])
        result_json["youtube_description_full"]["character_count"] = len(result_json["youtube_description_full"]["description"])

        # Mise en cache et réponse
        cache[cache_key] = result_json
        logger.info(f"Contenu généré et mis en cache pour : {cache_key}")
        return jsonify(result_json)

    except Exception as e:
        logger.error(f"Erreur inattendue : {str(e)}")
        return jsonify({"error": f"Erreur interne : {str(e)}"}), 500

def generate_prompt(data):
    artist = data.get('artist', 'Artiste Inconnu')
    song = data.get('song', '')
    genres = data.get('genres', ['rock']) if isinstance(data.get('genres'), list) else [data.get('genres', 'rock')]
    language = data.get('language', 'français')
    tone = data.get('tone', 'authentique')
    promotion_type = data.get('promotion_type', 'sortie')
    song_link = data.get('song_link', '[insert link]')
    bio_summary = data.get('bio', f"Artiste passionné par {genres[0]} avec une approche unique.")
    bio_tone = data.get('bio_tone', 'authentique')
    bio_themes = data.get('bio_themes', 'émotion, créativité')
    target_audience = data.get('target_audience', 'tous publics')
    announcement_style = data.get('announcement_style', 'Sérieux')
    song_lyrics = data.get('song_lyrics', '')

    selected_lookalikes = data.get('lookalike_artists', [])
    selected_trends = data.get('trends', [])

    prompt = f"""
OBJECTIF :
Générer du contenu marketing pour promouvoir la {promotion_type} de l'artiste {artist} autour de la chanson "{song}". Le contenu doit être rédigé en {language} et refléter l'ambiance et le style de {genres[0]} avec un ton {bio_tone}. La réponse devra être un objet JSON structuré, prêt à intégrer dans une page web, en respectant strictement les limites de caractères indiquées.

IMPORTANT :
- Utilisez systématiquement le nom complet de l'artiste dans tous les éléments (titres, descriptions, etc.) sans abréviation.
- La description YouTube complète doit être entièrement personnalisée pour chaque campagne.

VARIABLES :
- promotion_type : "{promotion_type}"
- artiste : "{artist}"
- chanson : "{song}"
- genres : "{', '.join(genres)}"
- langue : "{language}"
- ton général : "{tone}"
- lien chanson : "{song_link}"
- biographie : "{bio_summary}" (thèmes : {bio_themes})
- public cible : "{target_audience}"
- style des annonces : "{announcement_style}"
- paroles : "{song_lyrics}"

INSTRUCTIONS :

1. TITRES COURTS (max 30 caractères)
   Exemples :
   - "Nouveau Clip Jeanne Cherhal"
   - "Jeanne Cherhal avec Dedienne"
   - "Jeanne Cherhal présente Jean"
   - "Jeanne Cherhal duo complice"
   - "Jeanne Cherhal et Jean"
   Utilisez le nom complet de l'artiste dans chaque titre.

2. TITRES LONGS (max 90 caractères)
   Exemples :
   - "Nouveau Clip Jeanne Cherhal avec l'irrésistible Vincent Dedienne à ses côtés dans Jean"
   - "Jeanne Cherhal dévoile Jean accompagnée par Vincent Dedienne un clip drôle et charmant"
   - "Jeanne Cherhal et Vincent Dedienne ensemble dans Jean un moment pétillant à découvrir"
   - "Jean par Jeanne Cherhal avec Vincent Dedienne une complicité qui fait plaisir à voir"
   - "Découvrez Jean, le nouveau clip joyeux de Jeanne Cherhal avec le brillant Vincent Dedienne"
   Veillez à utiliser systématiquement le nom complet de l'artiste.

3. DESCRIPTIONS AVEC CALL TO ACTION
   Exemples :
   - "Qui est Jean ? Jeanne Cherhal répond avec humour aux côtés du talentueux Vincent Dedienne"
   - "Jeanne Cherhal réalise son rêve avec Vincent Dedienne dans son nouveau clip Jean"
   - "Le nouveau clip Jean de Jeanne Cherhal, complice et drôle avec Vincent Dedienne"
   - "Découvrez la belle complicité entre Jeanne Cherhal et Vincent Dedienne dans le clip Jean"
   - "À découvrir dès maintenant, le clip de Jean par Jeanne Cherhal et Vincent Dedienne"

4. DESCRIPTION YOUTUBE
   - Courte (max 120 caractères) : Exemple "Plongez dans le chaos musical avec Silver Dust !"
     - Inclure le nom complet de l'artiste ({artist}), le titre de la chanson ({song}), et un mot-clé lié au genre ({genres[0]}).
     - Ajouter un appel à l'action (ex. "Découvrez maintenant !").
   - Complète (max 5000 caractères) :
     Structure suggérée :
       • Introduction (1-2 phrases) : Une accroche captivante mentionnant {artist}, {song}, et un élément clé de {bio_summary}.
       • Corps :
         - Contexte biographique ({bio_summary}).
         - Description de la sortie ({song}, {promotion_type}, lien avec {genres} et {bio_themes}).
         - Intégrer une référence aux tendances ({json.dumps(selected_trends)}) et aux artistes similaires ({json.dumps(selected_lookalikes)}).
       • Conclusion : Inclure un appel à l'action (ex. "Regardez maintenant sur {song_link} ! Likez, commentez et abonnez-vous !").
     Mise en Page :
       - Utiliser des sauts de ligne (\\n) pour aérer le texte.
       - Séparer les sections avec des emojis (ex. 🔔 pour les abonnements, 📌 pour les crédits).
       - Inclure des placeholders pour les liens.
       - Ajouter des liens sociaux (Instagram, TikTok, site web) avec des placeholders.
       - Ajouter 3-5 hashtags pertinents à la fin (ex. #{artist}, #{song}, #{genres[0]}).
     SEO :
       - Inclure {artist}, {song}, et {genres} dans les premières lignes.
       - Intégrer les tendances ({json.dumps(selected_trends)}) pour capter les recherches spécifiques.
       - Mentionner les artistes similaires ({json.dumps(selected_lookalikes)}) pour apparaître dans les recherches associées.
       - Encourager l'engagement (ex. "Abonnez-vous", "Likez", "Commentez").

5. ANALYSE
   - "trends" : Utiliser la liste fournie : {json.dumps(selected_trends)}.
   - "lookalike_artists" : Utiliser la liste fournie : {json.dumps(selected_lookalikes)}.
   - "artist_image_url" : Générer une URL fictive au format "https://example.com/{artist.lower()  .replace(' ', '-')}.jpg".

FORMAT DE SORTIE ATTENDU (objet JSON) :
{{
  "short_titles": ["titre1", "titre2", "titre3", "titre4", "titre5"],
  "long_titles": ["titre1", "titre2", "titre3", "titre4", "titre5"],
  "long_descriptions": [
    {{"description": "desc1", "character_count": 37}},
    {{"description": "desc2", "character_count": 41}},
    {{"description": "desc3", "character_count": 38}},
    {{"description": "desc4", "character_count": 34}},
    {{"description": "desc5", "character_count": 41}}
  ],
  "youtube_description_short": {{"description": "desc", "character_count": 41}},
  "youtube_description_full": {{"description": "desc", "character_count": 200}},
  "analysis": {{
    "trends": {json.dumps(selected_trends)},
    "lookalike_artists": {json.dumps(selected_lookalikes)},
    "artist_image_url": "https://example.com/{artist.lower()  .replace(' ', '-')}.jpg"
  }}
}}
"""
    return prompt

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
