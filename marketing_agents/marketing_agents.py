from flask import Flask, request
import openai
import os
from dotenv import load_dotenv
from cachetools import TTLCache

# Initialisation de l'application Flask
app = Flask(__name__)

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
        return {"error": "Missing required fields"}, 400

    # Clé pour le cache
    cache_key = f"{artist}_{genres[0]}_{language}_{tone}_{promotion_type}_{song}"

    # Vérifier si le résultat est en cache
    if cache_key in cache:
        print(f"Using cached OpenAI response for key: {cache_key}")
        return cache[cache_key]

    # Générer le prompt avec la partie optimisée pour la description YouTube
    prompt = f"""
    Generate marketing content for a campaign promoting the {promotion_type} of artist {artist} with song {song} (genres: {genres}). Use language {language} and tone {tone}.

    1. **5 Short Titles (max 30 characters each)**:
       - Create catchy, varied titles that grab attention.
       - Include at least 2 calls to action (e.g., "Discover", "Listen").
       - Mention the song {song} in at least 2 titles.
       - Avoid repeating the artist's name in every title.

    2. **5 Long Titles (max 55 characters each)**:
       - Create descriptive titles that evoke emotion or curiosity.
       - Include at least 2 calls to action (e.g., "Dive in", "Experience").
       - Mention the song {song} in at least 2 titles.
       - Avoid repetition of the artist's name in every title.

    3. **5 Long Descriptions (max 80 characters each)**:
       - Create engaging descriptions that evoke the song's mood or genre.
       - Include at least 3 calls to action (e.g., "Stream now", "Watch now", "Join the vibe").
       - Mention the song {song} in at least 2 descriptions.
       - Avoid repetition of the artist's name in every description.

    4. **YouTube Description**:
       - **Short (max 120 characters)**: A vibrant, engaging hook that sparks excitement about the artist {artist} and song {song}, ending with a strong call to action (e.g., "Stream now!", "Discover today!"). Example: "Uncover the magic of {song} by {artist}! Stream now!".
       - **Full (max 5000 characters)**: A captivating and structured description to promote the song {song} by artist {artist}, designed to draw listeners in and make them eager to discover the artist, including:
         - A warm, inviting introduction (1-2 sentences) about {artist}, mentioning their unique style, legacy, or appeal, and introducing the song {song} with the genre {genres} (e.g., "Join {artist}, a beloved icon of {genres}, as they unveil their latest masterpiece, {song}!").
         - A compelling description (2-3 sentences) of the song {song}, focusing on its emotional impact, themes, or what makes it special, to create a connection with the listener (e.g., "This track blends heartfelt lyrics with {tone} melodies, evoking a sense of nostalgia and joy.").
         - A clear and enthusiastic call to action with the song link (e.g., "Stream {song} now: {song_link}", "Subscribe to catch every new release, live performance, and exclusive moment!").
         - Hashtags to boost visibility (e.g., #{artist.replace(' ', '')} #{song.replace(' ', '')} #{genres[0].replace(' ', '')}).
         - Avoid repetition of phrases or the artist's name within sentences for variety.
         - Use a tone that radiates excitement, warmth, and connection, making listeners eager to discover the artist and song.
    """

    try:
        # Appeler OpenAI pour générer les contenus
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000
        )
        raw_response = response.choices[0].message.content
        print(f"Raw response from OpenAI: {raw_response}")

        # Parsing robuste de la réponse d’OpenAI
        import json
        try:
            ad_data = json.loads(raw_response)
        except json.JSONDecodeError:
            # Si la réponse n'est pas un JSON valide, parser manuellement
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
                    desc = line.split(": ")[1].split(" (")[0]
                    char_count = int(line.split("(")[1].split(" /")[0])
                    ad_data["youtube_description_short"] = {"description": desc, "character_count": char_count}
                elif "Full" in line and current_section == "youtube_description":
                    desc = line.split(": ")[1].split(" (")[0]
                    char_count = int(line.split("(")[1].split(" /")[0])
                    ad_data["youtube_description_full"] = {"description": desc, "character_count": char_count}
                elif line.startswith("- ") and current_section in ["short_titles", "long_titles"]:
                    title = line[2:].split(" (")[0]
                    ad_data[current_section].append(title)
                elif line.startswith("- ") and current_section == "long_descriptions":
                    desc = line[2:].split(" (")[0]
                    char_count = int(line.split("(")[1].split(" /")[0])
                    ad_data[current_section].append({"description": desc, "character_count": char_count})

        # Ajouter le lien de la chanson à la description YouTube complète
        if ad_data["youtube_description_full"]["description"]:
            ad_data["youtube_description_full"]["description"] = ad_data["youtube_description_full"]["description"].replace(
                "[insert link]", song_link
            )

        # Mettre en cache le résultat
        cache[cache_key] = ad_data

        return ad_data

    except Exception as e:
        print(f"OpenAI error: {e}")
        return {"error": "Failed to generate ads"}, 500

# Point d'entrée pour Gunicorn
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
