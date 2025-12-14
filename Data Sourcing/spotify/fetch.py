from schema.records import record

def search_ALBUMS_by_artists(sp, query, artist_lim):
    artist_results = sp.search(q = query, type = "artist", limit = artist_lim)
    records = []

    for artist in artist_results["artists"]["items"]:
        artist_id = artist["id"]
        artist_name = artist["name"]
        artist_genres = artist.get("genres", [])

        albums = sp.artist_albums(artist_id, album_type = "album", limit = 1)
        if albums["items"]:
            album = albums["items"][0]
            album_data = {
                "name": album["name"],
                "release_date": album["release_date"],
                "total_tracks": album["total_tracks"],
                "artist_genre": artist_genres[0] if artist_genres else "Unknown",
                "artist_name": artist_name,
                "artist_id": artist_id
            }

            r = record(album_data)
            r.artist_id = artist_id
            records.append(r)
    return records