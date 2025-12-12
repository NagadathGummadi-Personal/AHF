"""
Deepgram STT Adapter.
Implements the STT interface for Deepgram's Live Streaming API.
See: https://developers.deepgram.com/reference/speech-to-text/listen-streaming
"""

import os
import json
import asyncio
import base64
from dataclasses import dataclass, field
from typing import Optional
import websockets

from .base import STTAdapter, STTConfig, TranscriptResult, ms_since


@dataclass
class DeepgramConfig(STTConfig):
    """Deepgram-specific configuration."""
    
    # API settings
    api_key: str = ""
    base_url: str = "wss://api.deepgram.com/v1/listen"
    
    # Model settings - nova-3 is the latest and fastest
    model: str = "nova-3"
    
    # Audio format - Twilio sends mulaw 8kHz
    encoding: str = "mulaw"
    sample_rate: int = 8000
    channels: int = 1
    
    # Features
    punctuate: bool = True
    diarize: bool = False
    smart_format: bool = True
    interim_results: bool = True
    utterance_end_ms: int = 1000  # Silence duration to end utterance
    vad_events: bool = True
    endpointing: int = 300  # VAD sensitivity in ms
    
    # Language
    language_code: str = "en"
    
    # Keywords for better accuracy (optional)
    keywords: list = field(default_factory=list)
    
    # Other settings
    profanity_filter: bool = False
    redact: bool = False
    numerals: bool = True
    multichannel: bool = False


class DeepgramAdapter(STTAdapter):
    """Deepgram Live Streaming STT adapter."""
    
    def __init__(self, config: Optional[DeepgramConfig] = None):
        if config is None:
            config = DeepgramConfig()
        
        # Set API key from env if not provided
        if not config.api_key:
            config.api_key = os.getenv("DEEPGRAM_API_KEY", "")
        
        super().__init__(config)
        self.config: DeepgramConfig = config
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.receive_task: Optional[asyncio.Task] = None
        self.request_id: str = ""
        
        # Tracking
        self.audio_state = {"chunks": 0, "audio_ms": 0}
        self.last_text = ""
        self.utterance_start_time: Optional[float] = None
        self.metadata_received: bool = False
    
    @property
    def provider_name(self) -> str:
        return "deepgram"
    
    def _build_ws_url(self, context: Optional[dict] = None) -> str:
        """Build the WebSocket URL with all parameters."""
        params = [
            f"model={self.config.model}",
            f"encoding={self.config.encoding}",
            f"sample_rate={self.config.sample_rate}",
            f"channels={self.config.channels}",
            f"language={self.config.language_code}",
            f"punctuate={str(self.config.punctuate).lower()}",
            f"smart_format={str(self.config.smart_format).lower()}",
            f"interim_results={str(self.config.interim_results).lower()}",
            f"utterance_end_ms={self.config.utterance_end_ms}",
            f"vad_events={str(self.config.vad_events).lower()}",
            f"endpointing={self.config.endpointing}",
            f"numerals={str(self.config.numerals).lower()}",
        ]
        
        if self.config.diarize:
            params.append(f"diarize=true")
        
        if self.config.profanity_filter:
            params.append(f"profanity_filter=true")
        
        if self.config.multichannel:
            params.append(f"multichannel=true")
        
        if self.config.keywords:
            for keyword in self.config.keywords:
                params.append(f"keywords={keyword}")
        
        # Add any context-specific parameters
        if context:
            for key, value in context.items():
                params.append(f"{key}={value}")
        
        return f"{self.config.base_url}?{'&'.join(params)}"
    
    async def connect(self, context: Optional[dict] = None) -> bool:
        """Connect to Deepgram WebSocket."""
        import time
        self.session_start = time.time()
        
        if not self.config.api_key:
            if self.on_error:
                self.on_error("DEEPGRAM_API_KEY not set")
            return False
        
        try:
            ws_url = self._build_ws_url(context)
            headers = {
                "Authorization": f"Token {self.config.api_key}"
            }
            
            connect_start = time.time()
            self.ws = await websockets.connect(ws_url, additional_headers=headers)
            connect_time = ms_since(connect_start)
            
            self.is_connected = True
            
            print(f"[{ms_since(self.session_start):6d}ms] STT_CONNECT | Provider: {self.provider_name} | Model: {self.config.model} | Connect: {connect_time}ms")
            
            if self.on_connected:
                self.on_connected()
            
            return True
            
        except websockets.exceptions.InvalidStatusCode as e:
            error_msg = f"Connection failed with status {e.status_code}"
            if self.on_error:
                self.on_error(error_msg)
            return False
        except Exception as e:
            if self.on_error:
                self.on_error(f"Connection failed: {e}")
            return False
    
    async def send_audio(self, audio_data: str) -> None:
        """Send audio chunk to Deepgram."""
        if not self.ws or not self.is_connected:
            return
        
        self.audio_state["chunks"] += 1
        self.audio_state["audio_ms"] = self.audio_state["chunks"] * 20  # ~20ms per chunk
        
        try:
            # Decode base64 audio and send as binary
            audio_bytes = base64.b64decode(audio_data)
            await self.ws.send(audio_bytes)
        except Exception as e:
            if self.on_error:
                self.on_error(f"Audio send error: {e}")
    
    async def close(self) -> None:
        """Close the connection."""
        if self.receive_task:
            self.receive_task.cancel()
            try:
                await self.receive_task
            except asyncio.CancelledError:
                pass
        
        if self.ws:
            try:
                # Send CloseStream message
                await self.ws.send(json.dumps({"type": "CloseStream"}))
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
                    # Send KeepAlive to prevent disconnect
                    if self.ws and self.is_connected:
                        try:
                            await self.ws.send(json.dumps({"type": "KeepAlive"}))
                        except:
                            pass
                    continue
        except asyncio.CancelledError:
            pass
        except Exception as e:
            if self.on_error:
                self.on_error(f"Receive error: {e}")
    
    async def _handle_message(self, response: str) -> None:
        """Handle incoming message from Deepgram."""
        import time
        
        data = json.loads(response)
        msg_type = data.get("type", "")
        wall_clock_ms = ms_since(self.session_start)
        audio_sent_ms = self.audio_state.get("audio_ms", 0)
        
        if msg_type == "Results":
            channel = data.get("channel", {})
            alternatives = channel.get("alternatives", [])
            
            if alternatives:
                alt = alternatives[0]
                text = alt.get("transcript", "").strip()
                is_final = data.get("is_final", False)
                speech_final = data.get("speech_final", False)
                
                if text:
                    if self.utterance_start_time is None:
                        self.utterance_start_time = time.time()
                    
                    # Calculate latency
                    audio_start = data.get("start", 0) * 1000
                    audio_duration = data.get("duration", 0) * 1000
                    audio_end = audio_start + audio_duration
                    latency = wall_clock_ms - audio_sent_ms
                    
                    # Extract word-level details
                    words = alt.get("words", [])
                    word_list = []
                    for w in words:
                        word_list.append({
                            "text": w.get("punctuated_word", w.get("word", "")),
                            "start_ms": int(w.get("start", 0) * 1000),
                            "end_ms": int(w.get("end", 0) * 1000),
                            "confidence": w.get("confidence", 1.0),
                            "speaker": w.get("speaker", None)
                        })
                    
                    # Get language
                    lang = self.config.language_code
                    if words and "language" in words[0]:
                        lang = words[0].get("language", lang)
                    
                    confidence = alt.get("confidence", 1.0)
                    
                    if is_final or speech_final:
                        # Final result
                        result = TranscriptResult(
                            text=text,
                            is_final=True,
                            language_code=lang,
                            confidence=confidence,
                            audio_start_ms=int(audio_start),
                            audio_end_ms=int(audio_end),
                            received_at_ms=wall_clock_ms,
                            words=word_list,
                            raw_response=data
                        )
                        
                        print(f"[{wall_clock_ms:6d}ms] FINAL [{lang}] | \"{text}\" | Audio: {audio_sent_ms}ms | Latency: {latency}ms | Conf: {confidence:.2f}")
                        
                        # Print word-level details
                        for w in word_list:
                            word_latency = wall_clock_ms - w["end_ms"]
                            print(f"         └─ [{w['start_ms']:5d}ms → {w['end_ms']:5d}ms] \"{w['text']}\" | Latency: {word_latency}ms | Conf: {w['confidence']:.2f}")
                        
                        # Reset for next utterance
                        self.last_text = ""
                        self.utterance_start_time = None
                        
                        if self.on_transcript:
                            self.on_transcript(result)
                    else:
                        # Partial/interim result
                        new_text = text[len(self.last_text):].strip() if text.startswith(self.last_text) else text
                        self.last_text = text
                        
                        result = TranscriptResult(
                            text=text,
                            is_final=False,
                            language_code=lang,
                            confidence=confidence,
                            audio_start_ms=int(audio_start),
                            audio_end_ms=int(audio_end),
                            received_at_ms=wall_clock_ms,
                            words=word_list,
                            raw_response=data
                        )
                        
                        print(f"[{wall_clock_ms:6d}ms] PARTIAL | \"{new_text}\" | Audio: {audio_sent_ms}ms | Latency: {latency}ms")
                        
                        if self.on_transcript:
                            self.on_transcript(result)
        
        elif msg_type == "Metadata":
            self.request_id = data.get("request_id", "")
            model_info = data.get("model_info", {})
            self.metadata_received = True
            print(f"[{wall_clock_ms:6d}ms] METADATA | Request: {self.request_id[:16] if self.request_id else 'N/A'}... | Model: {model_info.get('name', 'unknown')}")
        
        elif msg_type == "UtteranceEnd":
            last_word_end = data.get("last_word_end", 0) * 1000
            print(f"[{wall_clock_ms:6d}ms] UTTERANCE_END | Last word: {last_word_end:.0f}ms")
            
            # Reset for next utterance
            self.last_text = ""
            self.utterance_start_time = None
        
        elif msg_type == "SpeechStarted":
            timestamp = data.get("timestamp", 0) * 1000
            print(f"[{wall_clock_ms:6d}ms] SPEECH_STARTED | At: {timestamp:.0f}ms")
        
        elif msg_type == "Error" or "error" in data:
            error = data.get("error", data.get("message", "Unknown error"))
            print(f"[{wall_clock_ms:6d}ms] STT_ERROR | {error}")
            if self.on_error:
                self.on_error(f"Error: {error}")

