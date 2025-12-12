"""
Twilio Telephony Adapter.
Handles Twilio Media Streams WebSocket connection.
"""

import json
import time
from dataclasses import dataclass
from typing import Callable, Optional
from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

from ..stt import STTAdapter


@dataclass
class CallContext:
    """Context information about the current call."""
    call_sid: str = ""
    stream_sid: str = ""
    from_number: str = ""
    to_number: str = ""
    start_time: float = 0
    
    # Custom metadata
    metadata: dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


def ms_since(start_time: float) -> int:
    """Return milliseconds elapsed since start_time."""
    return int((time.time() - start_time) * 1000)


class TwilioAdapter:
    """
    Twilio Media Streams adapter.
    Handles WebSocket connection from Twilio and forwards audio to STT.
    """
    
    def __init__(self, stt_adapter: STTAdapter):
        """
        Initialize Twilio adapter.
        
        Args:
            stt_adapter: STT adapter instance to send audio to.
        """
        self.stt = stt_adapter
        self.context: Optional[CallContext] = None
        self.session_start: float = 0
        self.chunk_count: int = 0
        self.total_bytes: int = 0
        
        # Callbacks
        self.on_call_start: Optional[Callable[[CallContext], None]] = None
        self.on_call_end: Optional[Callable[[CallContext], None]] = None
    
    async def handle_connection(self, websocket: WebSocket, dynamic_context: Optional[dict] = None) -> None:
        """
        Handle incoming Twilio WebSocket connection.
        
        Args:
            websocket: FastAPI WebSocket connection.
            dynamic_context: Optional context to pass to STT (e.g., prompt, metadata).
        """
        await websocket.accept()
        self.session_start = time.time()
        self.context = CallContext(start_time=self.session_start)
        
        print(f"[{ms_since(self.session_start):6d}ms] CALL_CONNECT | Twilio WebSocket connected")
        
        try:
            # Connect to STT with dynamic context
            connected = await self.stt.connect(context=dynamic_context)
            if not connected:
                print(f"[{ms_since(self.session_start):6d}ms] ERROR | Failed to connect to STT")
                return
            
            # Start receiving transcriptions
            await self.stt.start_receiving()
            
            # Process Twilio messages
            async for message in websocket.iter_text():
                if not message:
                    continue
                
                await self._handle_twilio_message(message)
                
        except WebSocketDisconnect:
            print(f"[{ms_since(self.session_start):6d}ms] CALL_DISCONNECT | Twilio WebSocket disconnected")
        except Exception as e:
            print(f"[{ms_since(self.session_start):6d}ms] ERROR | {e}")
        finally:
            await self._cleanup()
    
    async def _handle_twilio_message(self, message: str) -> None:
        """Handle incoming message from Twilio."""
        try:
            data = json.loads(message)
            event_type = data.get("event")
            
            if event_type == "start":
                self._handle_start(data)
                
            elif event_type == "media":
                await self._handle_media(data)
                
            elif event_type == "stop":
                self._handle_stop()
                
        except json.JSONDecodeError:
            pass
    
    def _handle_start(self, data: dict) -> None:
        """Handle stream start event."""
        start_data = data.get("start", {})
        
        self.context.stream_sid = start_data.get("streamSid", "")
        self.context.call_sid = start_data.get("callSid", "")
        
        # Extract custom parameters if available
        custom_params = start_data.get("customParameters", {})
        self.context.metadata.update(custom_params)
        
        print(f"[{ms_since(self.session_start):6d}ms] STREAM_START | Call: {self.context.call_sid[:16]}...")
        
        if self.on_call_start:
            self.on_call_start(self.context)
    
    async def _handle_media(self, data: dict) -> None:
        """Handle media event (audio chunk)."""
        payload = data.get("media", {}).get("payload", "")
        if payload and self.stt:
            self.chunk_count += 1
            self.total_bytes += len(payload)
            await self.stt.send_audio(payload)
    
    def _handle_stop(self) -> None:
        """Handle stream stop event."""
        audio_ms = self.chunk_count * 20
        print(f"[{ms_since(self.session_start):6d}ms] STREAM_STOP | Chunks: {self.chunk_count} | Audio: {audio_ms}ms | Bytes: {self.total_bytes}")
        
        if self.on_call_end:
            self.on_call_end(self.context)
    
    async def _cleanup(self) -> None:
        """Cleanup resources."""
        if self.stt:
            await self.stt.close()
        
        total_ms = ms_since(self.session_start)
        audio_ms = self.chunk_count * 20
        print(f"[{total_ms:6d}ms] CALL_END | Duration: {total_ms}ms | Audio: {audio_ms}ms | Bytes: {self.total_bytes}")
    
    @staticmethod
    def generate_twiml(websocket_url: str, greeting: str = "Connected. Speak now.") -> str:
        """
        Generate TwiML response for Twilio.
        
        Args:
            websocket_url: WebSocket URL for media stream.
            greeting: Optional greeting message.
        
        Returns:
            TwiML XML string.
        """
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">{greeting}</Say>
    <Connect>
        <Stream url="{websocket_url}" />
    </Connect>
</Response>"""

