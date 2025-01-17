from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from enum import Enum

class STTEngine(Enum):
    GOOGLE = "google"
    SPHINX = "sphinx"
    WIT = "wit"
    AZURE = "azure"
    WHISPER = "whisper"

class TTSEngine(Enum):
    PLAYHT = "playht"
    PYTTSX3 = "pyttsx3"
    GOOGLE = "google"
    AZURE = "azure"

@dataclass
class AudioConfig:
    """Shared audio configuration"""
    format: str = "mp3"
    sample_rate: int = 16000
    channels: int = 1
    bit_depth: int = 16

@dataclass
class CacheConfig:
    """Caching configuration"""
    enabled: bool = True
    max_size: int = 1000  # MB
    retention_days: int = 7
    compression: bool = True

@dataclass
class TTSConfig:
    """Text-to-speech specific configuration"""
    rate: int = 200
    volume: float = 1.0
    voice_id: Optional[str] = None
    preferred_engine: TTSEngine = TTSEngine.PLAYHT
    cache_dir: Optional[str] = None
    save_audio: bool = False
    
    # PlayHT specific
    playht_api_key: Optional[str] = None
    playht_user_id: Optional[str] = None
    playht_voice_id: Optional[str] = None
    playht_speed: float = 1.0
    playht_quality: str = "high"
    
    # Audio settings
    audio: AudioConfig = AudioConfig()
    cache: CacheConfig = CacheConfig()
    
    # Performance
    streaming: bool = True
    chunk_size: int = 1024
    buffer_size: int = 4096

@dataclass
class STTConfig:
    """Speech-to-text specific configuration"""
    energy_threshold: int = 300
    pause_threshold: float = 0.8
    phrase_threshold: float = 0.3
    dynamic_energy_threshold: bool = True
    max_retries: int = 3
    noise_adjustment: bool = True
    preferred_engine: STTEngine = STTEngine.GOOGLE
    
    # Wake word
    wake_word_enabled: bool = False
    wake_word: str = "hey rowan"
    wake_word_sensitivity: float = 0.5
    
    # Noise reduction
    noise_reduction: bool = True
    noise_reduction_level: float = 0.3
    
    # Stream settings
    stream_chunk_size: int = 1024
    stream_timeout: float = 2.0

@dataclass
class VoiceServiceConfig:
    """Combined configuration for voice services"""
    language: str = "en-US"
    timeout: Optional[int] = None
    api_keys: Dict[str, str] = None
    
    # Service-specific configs
    stt: STTConfig = STTConfig()
    tts: TTSConfig = TTSConfig()
    
    # Model parameters
    model_path: Optional[str] = None
    use_gpu: bool = True
    threads: int = 4
    
    def __post_init__(self):
        if self.api_keys is None:
            self.api_keys = {}
        self.validate()

    def validate(self) -> bool:
        if not self.language:
            raise ValueError("Language must be specified")
        if self.timeout and self.timeout < 0:
            raise ValueError("Timeout must be positive")
        if self.tts.preferred_engine == TTSEngine.PLAYHT:
            if not (self.api_keys.get("playht_api_key") and self.api_keys.get("playht_user_id")):
                raise ValueError("PlayHT requires API key and User ID")
        return True

    def get_api_key(self, service: str) -> Optional[str]:
        return self.api_keys.get(service)