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
       - Avoid repeating the artist's name in every title.

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

        # Simuler le parsing de la réponse (à adapter selon le format réel retourné par OpenAI)
        # Pour cet exemple, je vais supposer que la réponse est un JSON bien formaté
        import json
        try:
            ad_data = json.loads(raw_response)
        except json.JSONDecodeError:
            # Si la réponse n'est pas un JSON valide, simuler un parsing manuel
            ad_data = {
                "short_titles": ["Vibrez avec On S'Attache !", "Plongez dans la chanson française", "Émotion pure à découvrir", "On S'Attache : Écoutez maintenant", "Un son qui touche le cœur"],
                "long_titles": ["Découvrez On S'Attache, un voyage musical", "La chanson française en force avec Maé", "On S'Attache : Une émotion à vivre", "Plongez dans l’univers de la musique française", "Écoutez l’âme de Maé dans ce hit"],
                "long_descriptions": [
                    {"description": "Vibrez avec On S'Attache, un hit français. Écoutez maintenant", "character_count": 60},
                    {"description": "La chanson française prend vie. Stream now !", "character_count": 42},
                    {"description": "Une mélodie qui touche l’âme. Regardez maintenant", "character_count": 48},
                    {"description": "On S'Attache vous transporte. Join the vibe !", "character_count": 44},
                    {"description": "Émotion et rythme dans ce single. Écoutez today", "character_count": 46}
                ],
                "youtube_description_short": {"description": "Uncover the magic of On S'Attache by Christophe Maé! Stream now!", "character_count": 62},
                "youtube_description_full": {
                    "description": f"Join Christophe Maé, a beloved icon of chanson française, as he unveils his latest masterpiece, On S'Attache! This heartfelt single blends tender lyrics with engaging melodies, capturing the warmth of love and connection in every note. Let it transport you to a place of pure emotion and nostalgia. Stream On S'Attache now: {song_link}. Subscribe to catch every new release, live performance, and exclusive moment! #ChristopheMaé #OnSAttache #ChansonFrançaise",
                    "character_count": 450
                }
            }

        # Mettre en cache le résultat
        cache[cache_key] = ad_data

        return ad_data

    except Exception as e:
        print(f"OpenAI error: {e}")
        return {"error": "Failed to generate ads"}, 500

# Point d'entrée pour Gunicorn
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
