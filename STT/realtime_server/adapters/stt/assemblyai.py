"""
AssemblyAI STT Adapter.
Implements the STT interface for AssemblyAI Universal Streaming v3 API.
Uses the official AssemblyAI SDK for reliable streaming.
See: https://www.assemblyai.com/docs/speech-to-text/universal-streaming
"""

import os
import asyncio
import base64
import threading
import queue
from dataclasses import dataclass, field
from typing import Optional

from .base import STTAdapter, STTConfig, TranscriptResult, ms_since


# U-law to PCM conversion table
ULAW_DECODE = [
    -32124, -31100, -30076, -29052, -28028, -27004, -25980, -24956,
    -23932, -22908, -21884, -20860, -19836, -18812, -17788, -16764,
    -15996, -15484, -14972, -14460, -13948, -13436, -12924, -12412,
    -11900, -11388, -10876, -10364, -9852, -9340, -8828, -8316,
    -7932, -7676, -7420, -7164, -6908, -6652, -6396, -6140,
    -5884, -5628, -5372, -5116, -4860, -4604, -4348, -4092,
    -3900, -3772, -3644, -3516, -3388, -3260, -3132, -3004,
    -2876, -2748, -2620, -2492, -2364, -2236, -2108, -1980,
    -1884, -1820, -1756, -1692, -1628, -1564, -1500, -1436,
    -1372, -1308, -1244, -1180, -1116, -1052, -988, -924,
    -876, -844, -812, -780, -748, -716, -684, -652,
    -620, -588, -556, -524, -492, -460, -428, -396,
    -372, -356, -340, -324, -308, -292, -276, -260,
    -244, -228, -212, -196, -180, -164, -148, -132,
    -120, -112, -104, -96, -88, -80, -72, -64,
    -56, -48, -40, -32, -24, -16, -8, 0,
    32124, 31100, 30076, 29052, 28028, 27004, 25980, 24956,
    23932, 22908, 21884, 20860, 19836, 18812, 17788, 16764,
    15996, 15484, 14972, 14460, 13948, 13436, 12924, 12412,
    11900, 11388, 10876, 10364, 9852, 9340, 8828, 8316,
    7932, 7676, 7420, 7164, 6908, 6652, 6396, 6140,
    5884, 5628, 5372, 5116, 4860, 4604, 4348, 4092,
    3900, 3772, 3644, 3516, 3388, 3260, 3132, 3004,
    2876, 2748, 2620, 2492, 2364, 2236, 2108, 1980,
    1884, 1820, 1756, 1692, 1628, 1564, 1500, 1436,
    1372, 1308, 1244, 1180, 1116, 1052, 988, 924,
    876, 844, 812, 780, 748, 716, 684, 652,
    620, 588, 556, 524, 492, 460, 428, 396,
    372, 356, 340, 324, 308, 292, 276, 260,
    244, 228, 212, 196, 180, 164, 148, 132,
    120, 112, 104, 96, 88, 80, 72, 64,
    56, 48, 40, 32, 24, 16, 8, 0,
]


def ulaw_to_pcm(ulaw_data: bytes) -> bytes:
    """Convert u-law encoded audio to 16-bit PCM."""
    pcm_data = bytearray()
    for byte in ulaw_data:
        sample = ULAW_DECODE[byte]
        pcm_data.extend(sample.to_bytes(2, byteorder='little', signed=True))
    return bytes(pcm_data)


def resample_8k_to_16k(pcm_8k: bytes) -> bytes:
    """Upsample PCM audio from 8kHz to 16kHz using linear interpolation."""
    samples = []
    for i in range(0, len(pcm_8k), 2):
        if i + 1 < len(pcm_8k):
            sample = int.from_bytes(pcm_8k[i:i+2], byteorder='little', signed=True)
            samples.append(sample)
    
    resampled = bytearray()
    for i in range(len(samples)):
        resampled.extend(samples[i].to_bytes(2, byteorder='little', signed=True))
        if i < len(samples) - 1:
            interpolated = (samples[i] + samples[i + 1]) // 2
            resampled.extend(interpolated.to_bytes(2, byteorder='little', signed=True))
        else:
            resampled.extend(samples[i].to_bytes(2, byteorder='little', signed=True))
    
    return bytes(resampled)


@dataclass
class AssemblyAIConfig(STTConfig):
    """AssemblyAI-specific configuration."""
    
    api_key: str = ""
    sample_rate: int = 16000
    input_sample_rate: int = 8000
    language: str = "en"
    format_turns: bool = True
    end_of_turn_confidence_threshold: float = 0.7
    min_end_of_turn_silence_when_confident: int = 160
    max_turn_silence: int = 2400


class AssemblyAIAdapter(STTAdapter):
    """AssemblyAI Universal Streaming v3 STT adapter using official SDK."""
    
    def __init__(self, config: Optional[AssemblyAIConfig] = None):
        if config is None:
            config = AssemblyAIConfig()
        
        if not config.api_key:
            config.api_key = os.getenv("ASSEMBLYAI_API_KEY", "")
        
        super().__init__(config)
        self.config: AssemblyAIConfig = config
        
        # SDK client (will be created in thread)
        self._client = None
        self._stream_thread: Optional[threading.Thread] = None
        self._audio_queue: queue.Queue = queue.Queue()
        self._stop_event = threading.Event()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        
        # Tracking
        self.audio_state = {"chunks": 0, "audio_ms": 0}
        self.last_text = ""
        self.session_id = ""
        
        # Audio buffer
        self.audio_buffer = bytearray()
        self.buffer_size = 3200  # ~100ms at 16kHz
    
    @property
    def provider_name(self) -> str:
        return "assemblyai"
    
    def _audio_generator(self):
        """Generator that yields audio chunks from the queue."""
        while not self._stop_event.is_set():
            try:
                audio_data = self._audio_queue.get(timeout=0.1)
                if audio_data is None:  # Poison pill
                    break
                yield audio_data
            except queue.Empty:
                continue
    
    def _stream_worker(self):
        """Worker thread that runs the AssemblyAI SDK streaming client."""
        try:
            from assemblyai.streaming.v3 import (
                StreamingClient,
                StreamingClientOptions,
                StreamingEvents,
                StreamingParameters,
            )
            
            client = StreamingClient(
                StreamingClientOptions(
                    api_key=self.config.api_key,
                    api_host="streaming.assemblyai.com",
                )
            )
            self._client = client
            
            # Set up event handlers
            def on_begin(cli, event):
                self.session_id = event.id
                wall_clock_ms = ms_since(self.session_start)
                print(f"[{wall_clock_ms:6d}ms] ASSEMBLYAI SESSION_START | ID: {self.session_id[:16] if self.session_id else 'N/A'}...")
            
            def on_turn(cli, event):
                wall_clock_ms = ms_since(self.session_start)
                audio_sent_ms = self.audio_state.get("audio_ms", 0)
                latency = wall_clock_ms - audio_sent_ms
                
                text = event.transcript.strip() if event.transcript else ""
                if not text:
                    return
                
                if event.end_of_turn:
                    # Final result
                    result = TranscriptResult(
                        text=text,
                        is_final=True,
                        received_at_ms=wall_clock_ms,
                        raw_response={"transcript": text, "end_of_turn": True}
                    )
                    
                    formatted = getattr(event, 'turn_is_formatted', False)
                    print(f"[{wall_clock_ms:6d}ms] FINAL | \"{text}\" | Audio: {audio_sent_ms}ms | Latency: {latency}ms | Formatted: {formatted}")
                    
                    self.last_text = ""
                    
                    if self.on_transcript and self._loop:
                        asyncio.run_coroutine_threadsafe(
                            self._emit_transcript(result),
                            self._loop
                        )
                else:
                    # Partial result
                    new_text = text[len(self.last_text):].strip() if text.startswith(self.last_text) else text
                    self.last_text = text
                    
                    result = TranscriptResult(
                        text=text,
                        is_final=False,
                        received_at_ms=wall_clock_ms,
                        raw_response={"transcript": text, "end_of_turn": False}
                    )
                    
                    print(f"[{wall_clock_ms:6d}ms] PARTIAL | \"{new_text}\" | Audio: {audio_sent_ms}ms | Latency: {latency}ms")
                    
                    if self.on_transcript and self._loop:
                        asyncio.run_coroutine_threadsafe(
                            self._emit_transcript(result),
                            self._loop
                        )
            
            def on_terminated(cli, event):
                wall_clock_ms = ms_since(self.session_start)
                duration = getattr(event, 'audio_duration_seconds', 0)
                print(f"[{wall_clock_ms:6d}ms] ASSEMBLYAI TERMINATED | Audio: {duration:.2f}s")
            
            def on_error(cli, error):
                wall_clock_ms = ms_since(self.session_start)
                print(f"[{wall_clock_ms:6d}ms] ASSEMBLYAI ERROR | {error}")
                if self.on_error:
                    self.on_error(f"AssemblyAI error: {error}")
            
            client.on(StreamingEvents.Begin, on_begin)
            client.on(StreamingEvents.Turn, on_turn)
            client.on(StreamingEvents.Termination, on_terminated)
            client.on(StreamingEvents.Error, on_error)
            
            # Connect
            client.connect(
                StreamingParameters(
                    sample_rate=self.config.sample_rate,
                    format_turns=self.config.format_turns,
                    end_of_turn_confidence_threshold=self.config.end_of_turn_confidence_threshold,
                    min_end_of_turn_silence_when_confident=self.config.min_end_of_turn_silence_when_confident,
                    max_turn_silence=self.config.max_turn_silence,
                    language=self.config.language,
                )
            )
            
            # Stream audio using the generator
            try:
                client.stream(self._audio_generator())
            finally:
                client.disconnect(terminate=True)
            
        except Exception as e:
            if self.on_error:
                self.on_error(f"Stream worker error: {e}")
    
    async def _emit_transcript(self, result: TranscriptResult):
        """Emit transcript to callback (called from thread)."""
        if self.on_transcript:
            self.on_transcript(result)
    
    async def connect(self, context: Optional[dict] = None) -> bool:
        """Connect to AssemblyAI using the SDK in a background thread."""
        import time
        self.session_start = time.time()
        
        if not self.config.api_key:
            if self.on_error:
                self.on_error("ASSEMBLYAI_API_KEY not set")
            return False
        
        try:
            # Store event loop for cross-thread callbacks
            self._loop = asyncio.get_running_loop()
            
            # Start the streaming thread
            self._stop_event.clear()
            self._stream_thread = threading.Thread(target=self._stream_worker, daemon=True)
            self._stream_thread.start()
            
            # Wait a bit for connection
            await asyncio.sleep(0.5)
            
            connect_time = ms_since(self.session_start)
            self.is_connected = True
            
            print(f"[{connect_time:6d}ms] STT_CONNECT | Provider: {self.provider_name} | SDK Mode | Connect: {connect_time}ms")
            
            if self.on_connected:
                self.on_connected()
            
            return True
            
        except Exception as e:
            if self.on_error:
                self.on_error(f"Connection failed: {e}")
            return False
    
    async def send_audio(self, audio_data: str) -> None:
        """Send audio chunk to AssemblyAI via the queue."""
        if not self.is_connected:
            return
        
        self.audio_state["chunks"] += 1
        self.audio_state["audio_ms"] = self.audio_state["chunks"] * 20
        
        try:
            # Decode and convert audio
            ulaw_bytes = base64.b64decode(audio_data)
            pcm_8k = ulaw_to_pcm(ulaw_bytes)
            pcm_16k = resample_8k_to_16k(pcm_8k)
            
            # Buffer audio
            self.audio_buffer.extend(pcm_16k)
            
            # Send when buffer is full
            if len(self.audio_buffer) >= self.buffer_size:
                self._audio_queue.put(bytes(self.audio_buffer))
                self.audio_buffer = bytearray()
                
        except Exception as e:
            if self.on_error:
                self.on_error(f"Audio send error: {e}")
    
    async def start_receiving(self) -> None:
        """Receiving is handled by SDK callbacks in the thread."""
        pass
    
    async def close(self) -> None:
        """Close the connection."""
        # Send remaining audio
        if self.audio_buffer:
            self._audio_queue.put(bytes(self.audio_buffer))
            self.audio_buffer = bytearray()
        
        # Signal thread to stop
        self._stop_event.set()
        self._audio_queue.put(None)  # Poison pill
        
        # Wait for thread to finish
        if self._stream_thread and self._stream_thread.is_alive():
            self._stream_thread.join(timeout=2.0)
        
        self.is_connected = False
        
        audio_ms = self.audio_state.get("audio_ms", 0)
        total_ms = ms_since(self.session_start)
        print(f"[{total_ms:6d}ms] STT_CLOSE | Duration: {total_ms}ms | Audio: {audio_ms}ms")
        
        if self.on_disconnected:
            self.on_disconnected()
