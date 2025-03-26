from quart import Blueprint, jsonify, request
import logging

logger = logging.getLogger(__name__)

def register_routes(app, chartmetric_client):
    api_bp = Blueprint('api', __name__)

    @api_bp.route('/search/artist', methods=['GET'])
    async def search_artist():
        try:
            name = request.args.get('name')
            limit = request.args.get('limit', default=5, type=int)
            if not name:
                return jsonify({"success": False, "error": "Le paramètre 'name' est requis"}), 400
            async with app.session() as session:
                result = await chartmetric_client.search_artist(session, name, limit)
                return jsonify({"success": True, "data": result})
        except Exception as e:
            logger.error(f"Erreur lors de la recherche d'artistes: {str(e)}")
            return jsonify({"success": False, "error": str(e)}), 500

    @api_bp.route('/artist/<int:artist_id>', methods=['GET'])
    async def get_artist(artist_id):
        try:
            async with app.session() as session:
                result = await chartmetric_client.get_artist(session, artist_id)
                return jsonify({"success": True, "data": result})
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'artiste {artist_id}: {str(e)}")
            return jsonify({"success": False, "error": str(e)}), 500

    @api_bp.route('/artist/<int:artist_id>/similar', methods=['GET'])
    async def get_similar_artists(artist_id):
        try:
            limit = request.args.get('limit', default=5, type=int)
            async with app.session() as session:
                result = await chartmetric_client.get_similar_artists(session, artist_id, limit)
                return jsonify({"success": True, "data": result})
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des artistes similaires pour {artist_id}: {str(e)}")
            return jsonify({"success": False, "error": str(e)}), 500

    @api_bp.route('/trends/genre/<genre>', methods=['GET'])
    async def get_trends_by_genre(genre):
        try:
            async with app.session() as session:
                result = await chartmetric_client.get_trends_by_genre(session, genre)
                return jsonify({"success": True, "data": result})
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des tendances pour le genre {genre}: {str(e)}")
            return jsonify({"success": False, "error": str(e)}), 500

    app.register_blueprint(api_bp, url_prefix='/')
    @app.before_serving
    async def setup_session():
        app.session = aiohttp.ClientSession()
    @app.after_serving
    async def teardown_session():
        await app.session.close()
