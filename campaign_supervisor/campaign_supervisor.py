# Étape 2 : Envoyer les données à marketing_agents
try:
    logger.info(f"Sending request to marketing_agents at {MARKETING_URL}/generate_ads with data: {{'artist': {artist}, 'genre': {style}, 'lyrics': {lyrics}, 'bio': {bio}}}")
    marketing_response = requests.post(f"{MARKETING_URL}/generate_ads", json={
        "artist": artist,
        "genre": style,
        "lyrics": lyrics,
        "bio": bio
    })
    marketing_response.raise_for_status()
    ad_content = marketing_response.json()
    short_titles = ad_content.get('short_titles', [])
    long_titles = ad_content.get('long_titles', [])
    long_descriptions = ad_content.get('long_descriptions', [])
    logger.info(f"Received response from marketing_agents: {ad_content}")
except requests.exceptions.RequestException as e:
    logger.error(f"Error communicating with marketing_agents: {str(e)}")
    return jsonify({"error": "Failed to communicate with marketing_agents", "details": str(e)}), 500

# Étape 3 : Envoyer les données à campaign_optimizer
try:
    logger.info(f"Sending request to campaign_optimizer at {OPTIMIZER_URL}/optimize with data: {{'artist': {artist}}}")
    optimizer_response = requests.post(f"{OPTIMIZER_URL}/optimize", json={
        "artist": artist
    })
    optimizer_response.raise_for_status()
    strategy = optimizer_response.json().get('strategy', {})
    logger.info(f"Received response from campaign_optimizer: {strategy}")
except requests.exceptions.RequestException as e:
    logger.error(f"Error communicating with campaign_optimizer: {str(e)}")
    return jsonify({"error": "Failed to communicate with campaign_optimizer", "details": str(e)}), 500

# Rendre les résultats
try:
    logger.info(f"Rendering results.html with artist={artist}, style={style}, analysis_data={analysis_data}, short_titles={short_titles}, long_titles={long_titles}, long_descriptions={long_descriptions}, strategy={strategy}")
    return render_template('results.html', artist=artist, style=style, analysis=analysis_data, short_titles=short_titles, long_titles=long_titles, long_descriptions=long_descriptions, strategy=strategy)
except Exception as e:
    logger.error(f"Error rendering results.html: {str(e)}")
    return jsonify({"error": "Failed to render results page", "details": str(e)}), 500
