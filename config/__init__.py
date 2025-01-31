"""
Configuration package.
"""
from .settings import Settings
from .memory_config import MemoryConfig
from .email_config import EmailConfig
from .spotify_config import SpotifyConfig
from .constants import GMAIL_SCOPES, EMAIL_DEFAULTS
# from .api_config import ApiConfig
# from .weather_config import WeatherConfig
# from .news_config import NewsConfig
# from .voice_config import VoiceConfig

__all__ = ['Settings', 'MemoryConfig', 'EmailConfig', 'SpotifyConfig', 'ApiConfig', 'VoiceConfig', 'GMAIL_SCOPES', 'EMAIL_DEFAULTS']