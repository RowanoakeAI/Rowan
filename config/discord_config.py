"""
Discord bot configuration settings.
"""
from typing import List, Optional
from dotenv import load_dotenv
import os

load_dotenv()

class DiscordConfig:
    """Configuration settings for Discord bot module."""
    
    # Bot settings
    DISCORD_TOKEN: str = os.getenv('DISCORD_TOKEN', '')
    COMMAND_PREFIX: str = ".r"
    OWNER_ID: int = 348490841339330561  # Mini's user ID
    
    # Server settings
    MAIN_SERVER_ID: int = 1327162631148277860  # Rowan's server ID
    ALLOWED_CHANNELS: List[str] = []  # Empty means all channels
    REQUIRED_PERMISSIONS: int = 326417514560  # Basic bot permissions
    
    # Message settings
    MAX_RESPONSE_LENGTH: int = 2000
    MEMORY_SEARCH_LIMIT: int = 5
    DELETE_COMMAND_AFTER: bool = True
    
    # Resource files
    EMOJI_AND_FORMATTING_FILE: str = "modules/discord/emojibank.json"
    
    @classmethod
    def validate(cls) -> bool:
        """Validate configuration settings."""
        if not cls.DISCORD_TOKEN:
            raise ValueError("DISCORD_TOKEN must be set in .env file")
        return True