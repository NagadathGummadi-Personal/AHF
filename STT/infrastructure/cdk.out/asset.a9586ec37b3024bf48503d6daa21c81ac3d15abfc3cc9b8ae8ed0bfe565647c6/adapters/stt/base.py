"""
Base STT Adapter Interface.
All STT providers should implement this interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable, Optional, Any
import time


@dataclass
class STTConfig:
    """Common STT configuration settings."""
    
    # Audio settings
    sample_rate: int = 8000
    audio_format: str = "ulaw"  # Common formats: pcm, ulaw, mulaw
    language_code: str = "en"
    
    # Feature flags
    include_timestamps: bool = True
    include_language_detection: bool = True
    enable_logging: bool = True
    
    # VAD settings
    use_vad: bool = True
    vad_silence_threshold_secs: float = 0.5
    
    # Provider-specific settings (override in subclass)
    provider_config: dict = field(default_factory=dict)


@dataclass
class TranscriptResult:
    """Standardized transcript result from any STT provider."""
    
    text: str
    is_final: bool
    language_code: str = "en"
    confidence: float = 1.0
    
    # Timing info
    audio_start_ms: int = 0
    audio_end_ms: int = 0
    received_at_ms: int = 0
    
    # Word-level details (optional)
    words: list = field(default_factory=list)
    
    # Raw provider response (for debugging)
    raw_response: dict = field(default_factory=dict)


def ms_since(start_time: float) -> int:
    """Return milliseconds elapsed since start_time."""
    return int((time.time() - start_time) * 1000)


class STTAdapter(ABC):
    """
    Abstract base class for Speech-to-Text adapters.
    Implement this interface for each STT provider (ElevenLabs, Deepgram, AssemblyAI, etc.)
    """
    
    def __init__(self, config: STTConfig):
        self.config = config
        self.session_start: float = 0
        self.is_connected: bool = False
        
        # Callbacks
        self.on_transcript: Optional[Callable[[TranscriptResult], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        self.on_connected: Optional[Callable[[], None]] = None
        self.on_disconnected: Optional[Callable[[], None]] = None
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name (e.g., 'elevenlabs', 'deepgram')."""
        pass
    
    @abstractmethod
    async def connect(self, context: Optional[dict] = None) -> bool:
        """
        Connect to the STT WebSocket.
        
        Args:
            context: Optional dynamic context (call metadata, session info, etc.)
        
        Returns:
            True if connection successful, False otherwise.
        """
        pass
    
    @abstractmethod
    async def send_audio(self, audio_data: str) -> None:
        """
        Send audio data to the STT service.
        
        Args:
            audio_data: Base64 encoded audio chunk.
        """
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close the connection and cleanup."""
        pass
    
    @abstractmethod
    async def start_receiving(self) -> None:
        """Start the background task to receive transcriptions."""
        pass
    
    def set_callbacks(
        self,
        on_transcript: Optional[Callable[[TranscriptResult], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
        on_connected: Optional[Callable[[], None]] = None,
        on_disconnected: Optional[Callable[[], None]] = None,
    ) -> None:
        """Set callback functions for events."""
        if on_transcript:
            self.on_transcript = on_transcript
        if on_error:
            self.on_error = on_error
        if on_connected:
            self.on_connected = on_connected
        if on_disconnected:
            self.on_disconnected = on_disconnected

