import spotipy
from spotipy.oauth2 import SpotifyOAuth
from typing import Dict, Any, Optional, Tuple
import re
from core.module_manager import ModuleInterface 
from utils.logger import setup_logger
from config.spotify_config import SpotifyConfig

class SpotifySkill(ModuleInterface):
    """Spotify playback control module"""
    
    SCOPES = [
        'user-read-playback-state',
        'user-modify-playback-state', 
        'user-read-currently-playing',
        'playlist-read-private',
        'playlist-modify-public',
        'playlist-modify-private'
    ]

    COMMAND_PATTERNS = {
        "play": r"(?:can you |please |)(?:play|start|resume)(?:.*?(?:song|track|album|artist|playlist))?",
        "pause": r"(?:can you |please |)(?:pause|stop|halt)(?:\s+music|\s+playback)?",
        "next": r"(?:can you |please |)(?:next|skip|forward)(?:\s+song|track)?",
        "previous": r"(?:can you |please |)(?:previous|back|rewind)(?:\s+song|track)?",
        "current": r"(?:what's |what is |)(?:playing|current|now playing)(?:\s+song|track|music)?"
    }

    def __init__(self):
        super().__init__()
        self.logger = setup_logger(__name__)
        self.sp = None
        self.initialized = False
        self.command_handlers = {
            "play": self._handle_play,
            "pause": self._handle_pause,
            "next": self._handle_next,
            "previous": self._handle_previous,
            "current": self._handle_current
        }

    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize Spotify client"""
        try:
            # Use SpotifyConfig instead of raw config dict
            spotify_config = SpotifyConfig()
            
            self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
                client_id=spotify_config.SPOTIFY_CLIENT_ID,
                client_secret=spotify_config.SPOTIFY_CLIENT_SECRET,
                redirect_uri=spotify_config.SPOTIFY_REDIRECT_URI,
                scope=self.SCOPES
            ))
            self.initialized = True
            self.logger.info("Spotify module initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize Spotify: {str(e)}")
            return False

    def _parse_command(self, input_text: str) -> Tuple[Optional[str], str]:
        """Parse input text to determine command and parameters"""
        input_lower = input_text.lower()
        for cmd, pattern in self.COMMAND_PATTERNS.items():
            if re.search(pattern, input_lower):
                return cmd, input_text
        return None, input_text

    def _handle_play(self, input_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle play commands"""
        try:
            self.sp.start_playback()
            return {"success": True, "response": "Playback started"}
        except Exception as e:
            self.logger.error(f"Error in play command: {str(e)}")
            return {"success": False, "response": "Couldn't start playback"}

    def _handle_pause(self, input_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle pause commands"""
        try:
            self.sp.pause_playback()
            return {"success": True, "response": "Playback paused"}
        except Exception as e:
            self.logger.error(f"Error in pause command: {str(e)}")
            return {"success": False, "response": "Couldn't pause playback"}

    def _handle_next(self, input_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle next track commands"""
        try:
            self.sp.next_track()
            return {"success": True, "response": "Skipped to next track"}
        except Exception as e:
            self.logger.error(f"Error in next track: {str(e)}")
            return {"success": False, "response": "Couldn't skip track"}

    def _handle_previous(self, input_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle previous track commands"""
        try:
            self.sp.previous_track()
            return {"success": True, "response": "Returned to previous track"}
        except Exception as e:
            self.logger.error(f"Error in previous track: {str(e)}")
            return {"success": False, "response": "Couldn't go to previous track"}

    def _handle_current(self, input_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle current track info commands"""
        try:
            track = self.sp.current_user_playing_track()
            if track and track['item']:
                name = track['item']['name']
                artists = ", ".join([artist['name'] for artist in track['item']['artists']])
                return {"success": True, "response": f"Now playing: {name} by {artists}"}
            return {"success": True, "response": "Nothing is currently playing"}
        except Exception as e:
            self.logger.error(f"Error getting current track: {str(e)}")
            return {"success": False, "response": "Couldn't get current track info"}

    def process(self, input_data: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process Spotify commands"""
        if not self.initialized:
            return {
                "success": False,
                "response": "Spotify module not initialized properly"
            }

        try:
            command, params = self._parse_command(input_data)
            if not command:
                return {
                    "success": False,
                    "response": "Invalid Spotify command format"
                }

            handler = self.command_handlers.get(command)
            if not handler:
                return {
                    "success": False,
                    "response": "Unsupported Spotify operation"
                }

            self.logger.info(f"Processing Spotify command: {command}")
            return handler(params, context or {})

        except Exception as e:
            self.logger.error(f"Error processing Spotify command: {str(e)}")
            return {
                "success": False,
                "response": "Error processing Spotify request"
            }