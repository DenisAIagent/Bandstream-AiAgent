from flask import Flask, request
import openai
import os
from dotenv import load_dotenv
from cachetools import TTLCache
import json
import logging

# Initialisation de l'application Flask
app = Flask(__name__)

# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration des clés API (via variables d'environnement)
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Cache pour les résultats (24h)
cache = TTLCache(maxsize=100, ttl=86400)

@app.route('/generate_ads', methods=['POST'])
def generate_ads():
    # Récupérer les données de la requête
    data = request.get_json()
    artist = data.get('artist')
    genres = data.get('genres')
    language = data.get('language')
    tone = data.get('tone')
    promotion_type = data.get('promotion_type')
    song = data.get('song', '')  # Ajout du champ song
    song_link = data.get('song_link', '[insert link]')  # Récupérer le lien de la chanson

    if not artist or not genres or not language or not tone or not promotion_type:
        logger.error("Missing required fields in request")
        return {"error": "Missing required fields"}, 400

    # Clé pour le cache
    cache_key = f"{artist}_{genres[0]}_{language}_{tone}_{promotion_type}_{song}"
    logger.info(f"Generated cache key: {cache_key}")

    # Vérifier si le résultat est en cache
    if cache_key in cache:
        logger.info(f"Using cached OpenAI response for key: {cache_key}")
        return cache[cache_key]

    # Générer le prompt avec la partie optimisée
    prompt = f"""
    Generate marketing content for a campaign promoting the {promotion_type} of artist {artist} with song {song} (genres: {genres}). Use language {language} and tone {tone}. The artist is a French band formed in 1997, known for blending metal with electro-industrial influences, creating a powerful and energetic sound. The song's lyrics are a mix of French and English, reflecting a duality in themes or emotions, such as tension, rebellion, or inner conflict. Ensure all generated content, including titles, descriptions, and YouTube description, is strictly in {language} to match the selected language. Do not use English if {language} is French.

    1. **5 Short Titles (max 30 characters each)**:
       - Create bold, energetic titles that reflect the {genres} style (e.g., heavy riffs, industrial beats, electro-metal energy).
       - Include at least 2 calls to action (e.g., "Écoutez maintenant", "Plongez dans le son").
       - Mention the song {song} in at least 2 titles.
       - Avoid repeating the artist's name in every title.
       - Use a tone that matches the intensity of metal music.
       - Ensure all titles are in {language}.

    2. **5 Long Titles (max 55 characters each)**:
       - Create descriptive titles that evoke the raw energy and duality of the {genres} style.
       - Include at least 2 calls to action (e.g., "Découvrez l’énergie", "Vibrez avec le son").
       - Mention the song {song} in at least 2 titles.
       - Avoid repetition of the artist's name in every title.
       - Highlight the industrial and electro-metal vibe.
       - Ensure all titles are in {language}.

    3. **5 Long Descriptions (max 80 characters each)**:
       - Create descriptions that capture the song's mood, blending the {genres} style with the French/English lyrical duality.
       - Include at least 3 calls to action (e.g., "Écoutez maintenant", "Regardez le clip", "Vibrez avec nous").
       - Mention the song {song} in at least 2 descriptions.
       - Avoid repetition of the artist's name in every description.
       - Reflect the song's themes (e.g., tension, rebellion, inner conflict) based on the mixed French/English lyrics.
       - Ensure all descriptions are in {language}.

    4. **YouTube Description**:
       - **Short (max 120 characters)**: A bold, engaging hook that highlights the {genres} style and the song {song}, ending with a strong call to action (e.g., "Écoutez maintenant!"). Example: "Plongez dans l’énergie de {song} par {artist}! Écoutez maintenant!".
       - **Full (max 5000 characters)**: A captivating and structured description to promote the song {song} by artist {artist}, designed to draw listeners in and make them eager to discover the artist, including:
         - A powerful introduction (1-2 sentences) about {artist}, mentioning their legacy as a French band formed in 1997, their unique blend of {genres}, and introducing the song {song} (e.g., "Depuis 1997, {artist} fusionne metal et électro dans un style {genres} unique avec leur nouveau titre {song}!").
         - A vivid description (2-3 sentences) of the song {song}, focusing on its emotional impact, themes (inspired by the French/English lyrical duality, such as tension, rebellion, or inner conflict), and the {genres} style (e.g., "Ce titre mêle riffs lourds et beats électro, avec des paroles en français et anglais qui explorent une tension émotionnelle.").
         - A clear and enthusiastic call to action with the song link (e.g., "Écoutez {song} maintenant: {song_link}", "Abonnez-vous pour plus de musique et de performances live!").
         - Hashtags to boost visibility (e.g., #{artist.replace(' ', '')} #{song.replace(' ', '')} #{genres[0].replace(' ', '')}).
         - Avoid repetition of phrases or the artist's name within sentences for variety.
         - Use a tone that radiates intensity, energy, and connection, matching the {genres} style.
         - Ensure all content is in {language}.
    """

    try:
        # Appeler OpenAI pour générer les contenus
        logger.info("Calling OpenAI API")
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000
        )
        raw_response = response.choices[0].message.content
        logger.info(f"Raw response from OpenAI: {raw_response}")

        # Parsing robuste de la réponse d’OpenAI
        try:
            ad_data = json.loads(raw_response)
        except json.JSONDecodeError:
            logger.warning("OpenAI response is not a valid JSON, attempting manual parsing")
            ad_data = {
                "short_titles": [],
                "long_titles": [],
                "long_descriptions": [],
                "youtube_description_short": {"description": "", "character_count": 0},
                "youtube_description_full": {"description": "", "character_count": 0}
            }
            lines = raw_response.split("\n")
            current_section = None
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if "Short Titles" in line:
                    current_section = "short_titles"
                elif "Long Titles" in line:
                    current_section = "long_titles"
                elif "Long Descriptions" in line:
                    current_section = "long_descriptions"
                elif "YouTube Description" in line:
                    current_section = "youtube_description"
                elif "Short" in line and current_section == "youtube_description":
                    try:
                        desc = line.split(": ")[1].split(" (")[0]
                        char_count = int(line.split("(")[1].split(" /")[0])
                        ad_data["youtube_description_short"] = {"description": desc, "character_count": char_count}
                    except (IndexError, ValueError) as e:
                        logger.error(f"Error parsing YouTube short description: {e}")
                        ad_data["youtube_description_short"] = {"description": f"Plongez dans l’énergie de {song} par {artist}! Écoutez maintenant!", "character_count": len(f"Plongez dans l’énergie de {song} par {artist}! Écoutez maintenant!")}
                elif "Full" in line and current_section == "youtube_description":
                    try:
                        desc = line.split(": ")[1].split(" (")[0]
                        char_count = int(line.split("(")[1].split(" /")[0])
                        ad_data["youtube_description_full"] = {"description": desc, "character_count": char_count}
                    except (IndexError, ValueError) as e:
                        logger.error(f"Error parsing YouTube full description: {e}")
                        ad_data["youtube_description_full"] = {
                            "description": f"Depuis 1997, {artist} fusionne metal et électro dans un style {genres[0]} unique avec leur nouveau titre {song}! Ce titre mêle riffs lourds et beats électro, avec des paroles en français et anglais qui explorent une tension émotionnelle. Écoutez {song} maintenant: {song_link}. Abonnez-vous pour plus de musique et de performances live! #{artist.replace(' ', '')} #{song.replace(' ', '')} #{genres[0].replace(' ', '')}",
                            "character_count": len(f"Depuis 1997, {artist} fusionne metal et électro dans un style {genres[0]} unique avec leur nouveau titre {song}! Ce titre mêle riffs lourds et beats électro, avec des paroles en français et anglais qui explorent une tension émotionnelle. Écoutez {song} maintenant: {song_link}. Abonnez-vous pour plus de musique et de performances live! #{artist.replace(' ', '')} #{song.replace(' ', '')} #{genres[0].replace(' ', '')}")
                        }
                elif line.startswith("- ") and current_section in ["short_titles", "long_titles"]:
                    title = line[2:].split(" (")[0]
                    ad_data[current_section].append(title)
                elif line.startswith("- ") and current_section == "long_descriptions":
                    try:
                        desc = line[2:].split(" (")[0]
                        char_count = int(line.split("(")[1].split(" /")[0])
                        ad_data[current_section].append({"description": desc, "character_count": char_count})
                    except (IndexError, ValueError) as e:
                        logger.error(f"Error parsing long description: {e}")

        # Vérifier que les données générées sont cohérentes avec l’artiste et la chanson
        if not ad_data["short_titles"] or not ad_data["long_titles"] or not ad_data["long_descriptions"]:
            logger.error("OpenAI response did not contain expected data, generating fallback content")
            ad_data = {
                "short_titles": [
                    f"Énergie pure avec {song}! (25 / 30)",
                    "Plongez dans le metal ! (23 / 30)",
                    f"Découvrez {song} ! (17 / 30)",
                    "Riffs lourds à fond ! (21 / 30)",
                    "Écoutez maintenant ! (20 / 30)"
                ],
                "long_titles": [
                    f"Découvrez {song}, un choc metal ! (32 / 55)",
                    "Plongez dans l’univers électro-metal ! (38 / 55)",
                    f"Vibrez avec {song} et ses riffs ! (32 / 55)",
                    "Un son industriel qui déchire ! (31 / 55)",
                    "Énergie pure, écoutez maintenant ! (34 / 55)"
                ],
                "long_descriptions": [
                    {"description": f"{song} : riffs lourds et électro ! Écoutez ! (43 / 80)", "character_count": 43},
                    {"description": "Un son qui déchire, vibrez avec nous ! (37 / 80)", "character_count": 37},
                    {"description": f"Découvrez {song}, un choc metal ! Regardez ! (42 / 80)", "character_count": 42},
                    {"description": "Énergie brute et dualité ! Écoutez maintenant ! (46 / 80)", "character_count": 46},
                    {"description": "Metal industriel à fond ! Plongez dedans ! (41 / 80)", "character_count": 41}
                ],
                "youtube_description_short": ad_data["youtube_description_short"],
                "youtube_description_full": ad_data["youtube_description_full"]
            }

        # Mettre en cache le résultat
        logger.info(f"Caching OpenAI response for key: {cache_key}")
        cache[cache_key] = ad_data

        return ad_data

    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        cache.pop(cache_key, None)  # Invalider le cache en cas d’erreur
        return {"error": "Failed to generate ads"}, 500

# Point d’entrée pour Gunicorn
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
