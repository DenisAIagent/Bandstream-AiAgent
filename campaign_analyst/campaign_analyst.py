from quart import Quart, render_template, request
import aiohttp

app = Quart(__name__)

@app.route('/generate_campaign', methods=['POST'])
async def generate_campaign():
    form_data = await request.form
    artist = form_data.get('artist')
    song = form_data.get('song')
    styles = form_data.get('style')
    # Autres champs...

    # Appeler Campaign Analyst
    async with aiohttp.ClientSession() as session:
        async with session.post('http://campaign-analyst:8000/analyze', json={
            'artist': artist,
            'styles': styles
        }) as response:
            analyst_data = await response.json()

    # Appeler Campaign Optimizer et Marketing Agent (simplifié ici)
    # Supposons que ces appels renvoient des données
    optimizer_data = {"strategy": "example strategy"}  # À remplacer par un vrai appel
    marketing_data = {
        "short_titles": ["Title 1", "Title 2"],
        "long_titles": ["Long Title 1", "Long Title 2"],
        "long_descriptions": [{"description": "Desc 1", "character_count": 50}],
        "youtube_description_short": {"description": "Short Desc", "character_count": 100},
        "youtube_description_full": {"description": "Full Desc", "character_count": 200}
    }

    # Rendre le template results.html
    return await render_template('results.html',
                                 artist=artist,
                                 song=song,
                                 style=styles,
                                 analysis=analyst_data,  # Contient artist_image_url
                                 short_titles=marketing_data["short_titles"],
                                 long_titles=marketing_data["long_titles"],
                                 long_descriptions=marketing_data["long_descriptions"],
                                 youtube_description_short=marketing_data["youtube_description_short"],
                                 youtube_description_full=marketing_data["youtube_description_full"])

# Autres routes...
