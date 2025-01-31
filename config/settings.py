import os
from typing import Optional
from .email_config import EmailConfig
from .calendar_config import CalendarConfig

# config/settings.py
class Settings:
    VERSION = "0.1.0"
    DEBUG = True
    LOG_LEVEL = "INFO"
    
    # Paths
    DATA_DIR = r"G:\Shared\Rowan\data"
    MEMORY_DIR = os.path.join(DATA_DIR, "memory")
    MODELS_DIR = os.path.join(DATA_DIR, "models")
    LOG_DIR = os.path.join(DATA_DIR, "logs")
    
    # Module settings
    DEFAULT_MODULE = "conversation"
    ENABLED_MODULES = [
        "conversation",
        "discord",
        #"voice",
        "calendar_skill",
        "spotify"
        #"task_skill"
    ]

    # Email Configuration
    _email_config: Optional[EmailConfig] = None
    
    @classmethod
    def get_email_config(cls) -> EmailConfig:
        """Get or create EmailConfig instance"""
        if not cls._email_config:
            cls._email_config = EmailConfig()
        return cls._email_config
    
    @property
    def email_settings(self):
        """Get email settings as a dictionary"""
        config = self.get_email_config()
        return {
            'imap_server': config.EMAIL_IMAP_SERVER,
            'smtp_server': config.EMAIL_SMTP_SERVER,
            'smtp_port': config.EMAIL_SMTP_PORT,
            'email': config.email
        }
    
    # Calendar Configuration
    _calendar_config: Optional[CalendarConfig] = None
    
    @classmethod
    def get_calendar_config(cls) -> CalendarConfig:
        """Get or create CalendarConfig instance"""
        if not cls._calendar_config:
            cls._calendar_config = CalendarConfig(
                client_id="339870206772-0s4785kprlqhfjg2rj2255c2pf5hfg1c.apps.googleusercontent.com",
                client_secret="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",
                scopes=[
                    'https://www.googleapis.com/auth/calendar',
                    'https://www.googleapis.com/auth/calendar.events'
                ],
                credentials_file='credentials.json',
                token_file='token.pickle'
            )
        return cls._calendar_config
    
    # Model Settings
    DEFAULT_MODEL = "Rowan"
    MODEL_NAME = DEFAULT_MODEL  #  maintain compatibility
    MODEL_BASE_URL = "http://localhost:11434"
    MODEL_CONFIG = {
        "name": "Rowan",
        "base_url": "http://localhost:11434",
        "parameters": {
            "temperature": 0.8,
            "top_p": 0.92,
            "repeat_penalty": 1.3
        }
    }