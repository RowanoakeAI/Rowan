import os
from .email_config import EmailConfig

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

    # Email settings
    EMAIL_IMAP_SERVER = EmailConfig.EMAIL_IMAP_SERVER
    EMAIL_SMTP_SERVER = EmailConfig.EMAIL_SMTP_SERVER
    EMAIL_SMTP_PORT = EmailConfig.EMAIL_SMTP_PORT
    EMAIL_ADDRESS = EmailConfig.email