def get_similar_artists_musicbrainz(artist):
    lookalike_artists = []
    artist_image_url = "https://via.placeholder.com/120?text=Artist"
    
    try:
        result = musicbrainzngs.search_artists(artist=artist, limit=1)
        if "artist-list" not in result or not result["artist-list"]:
            return lookalike_artists, artist_image_url
        
        artist_data = result["artist-list"][0]
        artist_id = artist_data["id"]
        
        time.sleep(1.0)
        
        relations = musicbrainzngs.get_artist_by_id(artist_id, includes=["artist-rels"])
        if "artist" in relations and "artist-relation-list" in relations["artist"]:
            for relation in relations["artist"]["artist-relation-list"]:
                if relation["type"] in ["associated with", "influenced by", "collaborates with"]:
                    if "artist" in relation and "name" in relation["artist"]:
                        lookalike_artists.append(relation["artist"]["name"])
        lookalike_artists = lookalike_artists[:10]
        
        time.sleep(1.0)
        
        releases = musicbrainzngs.get_artist_by_id(artist_id, includes=["release-groups"])
        if "artist" in releases and "release-group-list" in releases["artist"]:
            for release_group in releases["artist"]["release-group-list"]:
                release_group_id = release_group["id"]
                try:
                    time.sleep(1.0)
                    cover_art = musicbrainzngs.get_release_group_image_list(release_group_id)
                    if "images" in cover_art and cover_art["images"]:
                        artist_image_url = cover_art["images"][0]["image"]
                        artist_image_url = artist_image_url.rstrip(';').strip()  # Nettoyage du ';'
                        break
                except musicbrainzngs.ResponseError:
                    continue
        
        return lookalike_artists, artist_image_url
    except Exception as e:
        logger.error(f"Error fetching similar artists or image from MusicBrainz: {str(e)}")
        return [], "https://via.placeholder.com/120?text=Artist"
