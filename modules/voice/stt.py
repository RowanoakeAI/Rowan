import speech_recognition as sr
from typing import Dict, Any, Optional, List
from pathlib import Path
import wave
import os
import time
from core.module_manager import ModuleInterface
from utils.logger import setup_logger
from config.voice_config import VoiceServiceConfig, STTConfig, STTEngine

class SpeechToTextModule(ModuleInterface):
    """Handles speech recognition and audio transcription"""
    
    SUPPORTED_ENGINES = {
        STTEngine.GOOGLE: "recognize_google",
        STTEngine.SPHINX: "recognize_sphinx",
        STTEngine.WIT: "recognize_wit", 
        STTEngine.AZURE: "recognize_azure",
    }

    def __init__(self):
        self.logger = setup_logger(__name__)
        self.recognizer = sr.Recognizer()
        self.config: Optional[VoiceServiceConfig] = None
        self.initialized = False

    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize speech recognition with config"""
        try:
            self.config = VoiceServiceConfig(**config)
            self.recognizer.energy_threshold = self.config.stt.energy_threshold
            self.recognizer.pause_threshold = self.config.stt.pause_threshold
            self.recognizer.phrase_threshold = self.config.stt.phrase_threshold
            self.recognizer.dynamic_energy_threshold = self.config.stt.dynamic_energy_threshold
            
            # Set API keys if needed
            if self.config.api_keys:
                for service, key in self.config.api_keys.items():
                    setattr(self.recognizer, f"{service}_key", key)
            
            self.initialized = True
            self.logger.info("Speech-to-text module initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize speech-to-text: {str(e)}")
            return False

    def _recognize_with_retry(self, audio: sr.AudioData) -> Dict[str, Any]:
        """Attempt recognition with retry logic"""
        if not self.config:
            raise RuntimeError("Module not configured")
            
        errors: List[str] = []
        engine = self.SUPPORTED_ENGINES.get(self.config.stt.preferred_engine)
        
        if not engine:
            raise ValueError(f"Unsupported engine: {self.config.stt.preferred_engine}")
            
        for attempt in range(self.config.stt.max_retries):
            try:
                recognition_func = getattr(self.recognizer, engine)
                api_key = self.config.get_api_key(engine)
                kwargs = {"language": self.config.language}
                if api_key:
                    kwargs["key"] = api_key
                text = recognition_func(audio, **kwargs)
                return {"success": True, "text": text}
            except sr.RequestError as e:
                errors.append(f"API error: {str(e)}")
                time.sleep(1)  # Back off before retry
            except sr.UnknownValueError:
                errors.append("Speech not understood")
            except Exception as e:
                errors.append(str(e))
                
        return {
            "success": False,
            "error": f"Recognition failed after {self.config.stt.max_retries} attempts",
            "details": errors
        }

    def process_audio(self, audio_path: str) -> Dict[str, Any]:
        """Process audio file and convert to text"""
        if not self.initialized:
            return {"success": False, "response": "Module not initialized"}
            
        try:
            if not Path(audio_path).exists():
                raise FileNotFoundError(f"Audio file not found: {audio_path}")
                
            with sr.AudioFile(audio_path) as source:
                if self.config and self.config.noise_adjustment:
                    self.recognizer.adjust_for_ambient_noise(source)
                audio = self.recognizer.record(source)
                
                result = self._recognize_with_retry(audio)
                if result["success"]:
                    result["duration"] = self._get_audio_duration(audio_path)
                return result
                
        except Exception as e:
            self.logger.error(f"Error processing audio: {str(e)}")
            return {"success": False, "error": str(e)}

    def listen(self, timeout: Optional[int] = None) -> Dict[str, Any]:
        """Listen for speech input from microphone"""
        if not self.initialized:
            return {"success": False, "response": "Module not initialized"}
            
        try:
            with sr.Microphone() as source:
                self.logger.info("Listening for speech input...")
                if self.config and self.config.noise_adjustment:
                    self.recognizer.adjust_for_ambient_noise(source)
                    
                timeout = timeout or self.config.timeout if self.config else None
                audio = self.recognizer.listen(source, timeout=timeout)
                return self._recognize_with_retry(audio)
                
        except Exception as e:
            self.logger.error(f"Error listening for speech: {str(e)}")
            return {"success": False, "error": str(e)}
            
    def _get_audio_duration(self, audio_path: str) -> float:
        """Get duration of audio file in seconds"""
        with wave.open(audio_path, 'rb') as audio:
            frames = audio.getnframes()
            rate = audio.getframerate()
            return frames / float(rate)