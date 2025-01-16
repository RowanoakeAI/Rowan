import os
from dotenv import load_dotenv

load_dotenv()

class SpotifyConfig:
    """Configuration settings for Spotify integration."""
    
    # Spotify API credentials
    SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID', '')
    SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET', '')
    SPOTIFY_REDIRECT_URI = 'http://localhost:8888/callback'