import pyttsx3
import pyht
from typing import Dict, Any, Optional
from pathlib import Path
import os
import time
from core.module_manager import ModuleInterface
from utils.logger import setup_logger
from config.voice_config import VoiceServiceConfig, TTSConfig, TTSEngine

class TextToSpeechModule(ModuleInterface):
    """Handles text-to-speech conversion"""
    
    SUPPORTED_ENGINES = {
        TTSEngine.PLAYHT: "playht", 
        TTSEngine.GOOGLE: "google", 
        TTSEngine.PYTTSX3: "pyttsx3",
        TTSEngine.AZURE: "azure"
    }

    AUDIO_FORMATS = {
        "mp3": ".mp3",
        "wav": ".wav",
        "ogg": ".ogg"
    }

    def __init__(self):
        self.logger = setup_logger(__name__)
        self.engine = None
        self.playht_client = None
        self.config: Optional[VoiceServiceConfig] = None
        self.initialized = False
        self.cache = {}
        self.retry_count = 3
        self.retry_delay = 1

    def initialize(self, config: Dict[str, Any]) -> bool:
        try:
            self.config = VoiceServiceConfig(**config)
            
            # Initialize engines based on priority
            for engine in [TTSEngine.PLAYHT, TTSEngine.AZURE, TTSEngine.GOOGLE, TTSEngine.PYTTSX3]:
                if self._initialize_engine(engine):
                    break
                    
            if not (self.playht_client or self.engine):
                raise ValueError("No TTS engine could be initialized")

            # Setup caching
            if self.config.tts.cache_dir:
                os.makedirs(self.config.tts.cache_dir, exist_ok=True)
                
            self.initialized = True
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize TTS: {str(e)}")
            return False

    def _initialize_engine(self, engine: TTSEngine) -> bool:
        """Initialize specific TTS engine"""
        try:
            if engine == TTSEngine.PLAYHT and self.config.tts.playht_api_key:
                return self._init_playht()
            elif engine == TTSEngine.AZURE and self.config.tts.azure_key:
                return self._init_azure()
            elif engine == TTSEngine.GOOGLE and self.config.tts.google_key:
                return self._init_google()
            elif engine == TTSEngine.PYTTSX3:
                return self._init_pyttsx3()
            return False
        except Exception as e:
            self.logger.warning(f"Failed to initialize {engine}: {str(e)}")
            return False

    def speak(self, text: str, voice_id: Optional[str] = None, 
              save_path: Optional[str] = None, 
              format: str = "mp3") -> Dict[str, Any]:
        """Enhanced speak method with voice selection and formats"""
        if not self.initialized:
            return {"success": False, "response": "Module not initialized"}
            
        try:
            # Try cache first
            cache_key = f"{text}_{voice_id}_{format}"
            if cache_key in self.cache:
                return self.cache[cache_key]

            for attempt in range(self.retry_count):
                try:
                    result = self._speak_with_engine(text, voice_id, save_path, format)
                    if result["success"]:
                        self.cache[cache_key] = result
                        return result
                except Exception as e:
                    if attempt == self.retry_count - 1:
                        raise
                    time.sleep(self.retry_delay)

            return {"success": False, "error": "All retry attempts failed"}

        except Exception as e:
            self.logger.error(f"Error in TTS: {str(e)}")
            return {"success": False, "error": str(e)}

    def _speak_with_engine(self, text: str, voice_id: Optional[str], 
                           save_path: Optional[str], format: str) -> Dict[str, Any]:
        """Internal method to handle speaking with the selected engine"""
        try:
            # PlayHT handling
            if self.config.tts.engine == TTSEngine.PLAYHT:
                options = {
                    "voice": voice_id or self.config.tts.playht_voice_id or "en-US-JennyNeural",
                    "speed": self.config.tts.rate / 100  # Convert rate to speed multiplier
                }
                
                if save_path and self.config.tts.save_audio:
                    audio_file = self.playht_client.text_to_speech(
                        text=text,
                        **options,
                        save_to_file=save_path
                    )
                    if Path(save_path).exists():
                        return {"success": True, "file_path": save_path}
                else:
                    # Stream audio directly
                    audio_stream = self.playht_client.text_to_speech(
                        text=text,
                        **options
                    )
                    # Play audio stream
                    audio_stream.play()
                    return {"success": True}
                    
            # Fallback pyttsx3 handling
            else:
                if save_path and self.config.tts.save_audio:
                    self.engine.save_to_file(text, save_path)
                    self.engine.runAndWait()
                    if Path(save_path).exists():
                        return {"success": True, "file_path": save_path}
                else:
                    self.engine.say(text)
                    self.engine.runAndWait()
                    return {"success": True}
                
        except Exception as e:
            self.logger.error(f"Error in text-to-speech: {str(e)}")
            return {"success": False, "error": str(e)}
            
    def shutdown(self) -> None:
        """Clean shutdown of TTS engine"""
        if self.engine:
            self.engine.stop()