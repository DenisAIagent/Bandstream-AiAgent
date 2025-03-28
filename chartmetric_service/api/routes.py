# Dans api/routes.py

def register_routes(app, chartmetric_client) :
    """
    Enregistre les routes de l'API pour FastAPI.
    
    Args:
        app: L'application FastAPI
        chartmetric_client: Le client Chartmetric
    """
    
    @app.get('/api/artist/{artist_id}')
    async def get_artist(artist_id: int):
        return await chartmetric_client.get_artist(artist_id)
    
    @app.get('/api/artist/{artist_id}/stats')
    async def get_artist_stats(artist_id: int):
        return await chartmetric_client.get_artist_stats(artist_id)
    
    # Ajoutez d'autres routes selon vos besoins
