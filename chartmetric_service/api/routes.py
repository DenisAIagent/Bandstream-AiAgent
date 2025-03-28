from fastapi import APIRouter, HTTPException, Query
import logging
import aiohttp

logger = logging.getLogger(__name__)

def register_routes(app, chartmetric_client):
    """
    Enregistre les routes API pour le service Chartmetric.
    
    Args:
        app (FastAPI): Instance de l'application FastAPI.
        chartmetric_client (ChartmetricClient): Client Chartmetric.
    """
    router = APIRouter()

    @router.get('/search/artist')
    async def search_artist(name: str = Query(...), limit: int = Query(5)):
        try:
            async with app.session() as session:
                result = await chartmetric_client.search_artist(session, name, limit)
                return {"success": True, "data": result}
        except Exception as e:
            logger.error(f"Erreur lors de la recherche d'artistes: {str(e)}")
            raise HTTPException(status_code=500, detail={"success": False, "error": str(e)})

    @router.get('/artist/{artist_id}')
    async def get_artist(artist_id: int):
        try:
            async with app.session() as session:
                result = await chartmetric_client.get_artist(session, artist_id)
                return {"success": True, "data": result}
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'artiste {artist_id}: {str(e)}")
            raise HTTPException(status_code=500, detail={"success": False, "error": str(e)})

    @router.get('/artist/{artist_id}/similar')
    async def get_similar_artists(artist_id: int, limit: int = Query(5)):
        try:
            async with app.session() as session:
                result = await chartmetric_client.get_similar_artists(session, artist_id, limit)
                return {"success": True, "data": result}
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des artistes similaires pour {artist_id}: {str(e)}")
            raise HTTPException(status_code=500, detail={"success": False, "error": str(e)})

    @router.get('/trends/genre/{genre}')
    async def get_trends_by_genre(genre: str):
        try:
            async with app.session() as session:
                result = await chartmetric_client.get_trends_by_genre(session, genre)
                return {"success": True, "data": result}
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des tendances pour le genre {genre}: {str(e)}")
            raise HTTPException(status_code=500, detail={"success": False, "error": str(e)})

    # Ajouter les routes à l'application FastAPI
    app.include_router(router, prefix='')

    # Ajouter une session HTTP persistante à l'application
    @app.on_event("startup")
    async def setup_session():
        app.session = aiohttp.ClientSession()

    @app.on_event("shutdown")
    async def teardown_session():
        await app.session.close()
