import os

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
        "discord"
    #    "voice",
        "calendar_skill",
        "spotify"
    #    "task_skill"
    ]

    # Model Settings
    DEFAULT_MODEL = "Rowan"
    MODEL_CONFIG = {
        "name": "Rowan",
        "base_url": "http://localhost:11434",
        "parameters": {
            "temperature": 0.8,
            "top_p": 0.92,
            "repeat_penalty": 1.3
        }
    }