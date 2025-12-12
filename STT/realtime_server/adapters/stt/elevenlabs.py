"""
ElevenLabs STT Adapter.
Implements the STT interface for ElevenLabs Scribe realtime API.
See: https://elevenlabs.io/docs/api-reference/speech-to-text/v-1-speech-to-text-realtime
"""

import os
import json
import asyncio
from dataclasses import dataclass, field
from typing import Optional
import websockets

from .base import STTAdapter, STTConfig, TranscriptResult, ms_since


@dataclass
class ElevenLabsConfig(STTConfig):
    """ElevenLabs-specific configuration."""
    
    # API settings
    api_key: str = ""
    base_url: str = "wss://api.elevenlabs.io/v1/speech-to-text/realtime"
    
    # Model settings
    model_id: str = "scribe_v2_realtime"
    
    # Audio format mapping (Twilio sends ulaw 8kHz)
    audio_format: str = "ulaw_8000"
    
    # VAD settings
    commit_strategy: str = "vad"  # "vad" or "manual"
    vad_silence_threshold_secs: float = 0.5
    vad_threshold: float = 0.5
    min_speech_duration_ms: int = 100
    min_silence_duration_ms: int = 500


class ElevenLabsAdapter(STTAdapter):
    """ElevenLabs Scribe realtime STT adapter."""
    
    def __init__(self, config: Optional[ElevenLabsConfig] = None):
        if config is None:
            config = ElevenLabsConfig()
        
        # Set API key from env if not provided
        if not config.api_key:
            config.api_key = os.getenv("ELEVENLABS_API_KEY", "")
        
        super().__init__(config)
        self.config: ElevenLabsConfig = config
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.receive_task: Optional[asyncio.Task] = None
        self.session_id: str = ""
        
        # Tracking
        self.audio_state = {"chunks": 0, "audio_ms": 0}
        self.last_text = ""
        self.utterance_start_time: Optional[float] = None
    
    @property
    def provider_name(self) -> str:
        return "elevenlabs"
    
    def _build_ws_url(self, context: Optional[dict] = None) -> str:
        """Build the WebSocket URL with all parameters."""
        params = [
            f"model_id={self.config.model_id}",
            f"audio_format={self.config.audio_format}",
            f"language_code={self.config.language_code}",
            f"commit_strategy={self.config.commit_strategy}",
            f"include_timestamps={str(self.config.include_timestamps).lower()}",
            f"include_language_detection={str(self.config.include_language_detection).lower()}",
            f"enable_logging={str(self.config.enable_logging).lower()}",
        ]
        
        # Add VAD settings if using VAD
        if self.config.commit_strategy == "vad":
            params.extend([
                f"vad_silence_threshold_secs={self.config.vad_silence_threshold_secs}",
                f"vad_threshold={self.config.vad_threshold}",
                f"min_speech_duration_ms={self.config.min_speech_duration_ms}",
                f"min_silence_duration_ms={self.config.min_silence_duration_ms}",
            ])
        
        # Add any context-specific parameters
        if context:
            for key, value in context.items():
                params.append(f"{key}={value}")
        
        return f"{self.config.base_url}?{'&'.join(params)}"
    
    async def connect(self, context: Optional[dict] = None) -> bool:
        """Connect to ElevenLabs WebSocket."""
        import time
        self.session_start = time.time()
        
        if not self.config.api_key:
            if self.on_error:
                self.on_error("ELEVENLABS_API_KEY not set")
            return False
        
        try:
            ws_url = self._build_ws_url(context)
            headers = {"xi-api-key": self.config.api_key}
            
            connect_start = time.time()
            self.ws = await websockets.connect(ws_url, additional_headers=headers)
            connect_time = ms_since(connect_start)
            
            # Wait for session start
            session_msg = await asyncio.wait_for(self.ws.recv(), timeout=5.0)
            session_data = json.loads(session_msg)
            
            # Check for errors
            msg_type = session_data.get("message_type", "")
            if msg_type in ["error", "auth_error", "invalid_request"]:
                error = session_data.get("error", "Unknown error")
                if self.on_error:
                    self.on_error(f"ElevenLabs error: {error}")
                return False
            
            self.session_id = session_data.get("session_id", "")
            self.is_connected = True
            
            print(f"[{ms_since(self.session_start):6d}ms] STT_CONNECT | Provider: {self.provider_name} | Session: {self.session_id[:16]}... | Connect: {connect_time}ms")
            
            if self.on_connected:
                self.on_connected()
            
            return True
            
        except Exception as e:
            if self.on_error:
                self.on_error(f"Connection failed: {e}")
            return False
    
    async def send_audio(self, audio_data: str) -> None:
        """Send audio chunk to ElevenLabs."""
        if not self.ws or not self.is_connected:
            return
        
        self.audio_state["chunks"] += 1
        self.audio_state["audio_ms"] = self.audio_state["chunks"] * 20  # ~20ms per chunk
        
        msg = {
            "message_type": "input_audio_chunk",
            "audio_base_64": audio_data,
            "commit": False,
            "sample_rate": self.config.sample_rate
        }
        await self.ws.send(json.dumps(msg))
    
    async def close(self) -> None:
        """Close the connection."""
        if self.receive_task:
            self.receive_task.cancel()
            try:
                await self.receive_task
            except asyncio.CancelledError:
                pass
        
        if self.ws:
            # Send final commit
            try:
                await self.ws.send(json.dumps({
                    "message_type": "input_audio_chunk",
                    "audio_base_64": "",
                    "commit": True,
                    "sample_rate": self.config.sample_rate
                }))
                await self.ws.close()
            except:
                pass
        
        self.is_connected = False
        
        audio_ms = self.audio_state.get("audio_ms", 0)
        total_ms = ms_since(self.session_start)
        print(f"[{total_ms:6d}ms] STT_CLOSE | Duration: {total_ms}ms | Audio: {audio_ms}ms")
        
        if self.on_disconnected:
            self.on_disconnected()
    
    async def start_receiving(self) -> None:
        """Start background task to receive transcriptions."""
        self.receive_task = asyncio.create_task(self._receive_loop())
    
    async def _receive_loop(self) -> None:
        """Background loop to receive and process messages."""
        try:
            while self.is_connected and self.ws:
                try:
                    response = await asyncio.wait_for(self.ws.recv(), timeout=30.0)
                    await self._handle_message(response)
                except asyncio.TimeoutError:
                    continue
        except asyncio.CancelledError:
            pass
        except Exception as e:
            if self.on_error:
                self.on_error(f"Receive error: {e}")
    
    async def _handle_message(self, response: str) -> None:
        """Handle incoming message from ElevenLabs."""
        import time
        
        data = json.loads(response)
        msg_type = data.get("message_type", "")
        wall_clock_ms = ms_since(self.session_start)
        audio_sent_ms = self.audio_state.get("audio_ms", 0)
        
        if msg_type == "partial_transcript":
            text = data.get("text", "").strip()
            if text and text != self.last_text:
                if self.utterance_start_time is None:
                    self.utterance_start_time = time.time()
                
                # Calculate latency
                latency = wall_clock_ms - audio_sent_ms
                
                new_text = text[len(self.last_text):].strip() if text.startswith(self.last_text) else text
                self.last_text = text
                
                result = TranscriptResult(
                    text=text,
                    is_final=False,
                    received_at_ms=wall_clock_ms,
                    raw_response=data
                )
                
                print(f"[{wall_clock_ms:6d}ms] PARTIAL | \"{new_text}\" | Audio: {audio_sent_ms}ms | Latency: {latency}ms")
                
                if self.on_transcript:
                    self.on_transcript(result)
        
        elif msg_type == "committed_transcript_with_timestamps":
            text = data.get("text", "").strip()
            if text:
                lang = data.get("language_code", "en")
                words = data.get("words", [])
                
                latency = wall_clock_ms - audio_sent_ms
                
                # Extract word timing
                word_list = []
                audio_start = 0
                audio_end = 0
                
                if words:
                    word_items = [w for w in words if w.get("type") == "word"]
                    if word_items:
                        audio_start = int(word_items[0].get("start", 0) * 1000)
                        audio_end = int(word_items[-1].get("end", 0) * 1000)
                    
                    for w in word_items:
                        word_list.append({
                            "text": w.get("text", ""),
                            "start_ms": int(w.get("start", 0) * 1000),
                            "end_ms": int(w.get("end", 0) * 1000),
                            "confidence": 1.0 - abs(w.get("logprob", 0))
                        })
                
                result = TranscriptResult(
                    text=text,
                    is_final=True,
                    language_code=lang,
                    audio_start_ms=audio_start,
                    audio_end_ms=audio_end,
                    received_at_ms=wall_clock_ms,
                    words=word_list,
                    raw_response=data
                )
                
                print(f"[{wall_clock_ms:6d}ms] FINAL [{lang}] | \"{text}\" | Audio: {audio_sent_ms}ms | Latency: {latency}ms")
                
                # Print word-level details
                if words:
                    for w in [w for w in words if w.get("type") == "word"]:
                        start_ms = int(w.get("start", 0) * 1000)
                        end_ms = int(w.get("end", 0) * 1000)
                        word_latency = wall_clock_ms - end_ms
                        print(f"         └─ [{start_ms:5d}ms → {end_ms:5d}ms] \"{w.get('text', '')}\" | Latency: {word_latency}ms")
                
                # Reset for next utterance
                self.last_text = ""
                self.utterance_start_time = None
                
                if self.on_transcript:
                    self.on_transcript(result)
        
        elif msg_type == "committed_transcript":
            # Skip - we use committed_transcript_with_timestamps
            pass
        
        elif msg_type == "session_started":
            pass
        
        elif msg_type in ["error", "auth_error", "input_error", "transcriber_error"]:
            error = data.get("error", "Unknown error")
            print(f"[{wall_clock_ms:6d}ms] STT_ERROR | {msg_type}: {error}")
            if self.on_error:
                self.on_error(f"{msg_type}: {error}")

