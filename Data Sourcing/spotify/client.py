import spotipy  # Spotify Web API Wrapper
from spotipy.oauth2 import SpotifyClientCredentials     # Handles Spotify Authentication

#My Spotify Credentials (Allows access to Spotify API)
def get_spotify_client():
    client_id = "c1bcc5dc7afa479882fa211d46c95ab2"
    client_secret = "469225b99f074ff49919e2f75191a5db"

    # Get authenticated client
    auth_manager = SpotifyClientCredentials(
        client_id=client_id,
        client_secret=client_secret
    )

    return spotipy.Spotify(auth_manager=auth_manager)