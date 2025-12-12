"""
Real-time Twilio Media Stream to STT Server.
Clean adapter-based architecture for easy provider switching.
"""

import os
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse

from adapters.telephony import TwilioAdapter
from adapters.stt import ElevenLabsAdapter
from adapters.stt.elevenlabs import ElevenLabsConfig


# Configuration - API key must be set via environment variable in production
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")

app = FastAPI(title="Realtime STT Server")


@app.get("/")
async def root():
    return {"status": "healthy", "service": "realtime-stt"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/twiml")
async def twiml_webhook(request: Request):
    """Generate TwiML to connect Twilio to our WebSocket."""
    host = request.headers.get("host", request.url.hostname)
    
    # Use wss for production, ws for localhost
    is_local = "localhost" in host or "127.0.0.1" in host
    protocol = "ws" if is_local else "wss"
    websocket_url = f"{protocol}://{host}/media-stream"
    
    twiml = TwilioAdapter.generate_twiml(
        websocket_url=websocket_url,
        greeting="Connected. Speak now and I will transcribe in real-time."
    )
    
    return HTMLResponse(content=twiml, media_type="application/xml")


@app.websocket("/media-stream")
async def media_stream(websocket: WebSocket):
    """Handle Twilio media stream with STT transcription."""
    
    # Create STT adapter with configuration
    stt_config = ElevenLabsConfig(
        api_key=ELEVENLABS_API_KEY,
        sample_rate=8000,
        audio_format="ulaw_8000",
        language_code="en",
        include_timestamps=True,
        include_language_detection=True,
        enable_logging=True,
        commit_strategy="vad",
    )
    stt_adapter = ElevenLabsAdapter(config=stt_config)
    
    # Create Twilio adapter with STT
    twilio_adapter = TwilioAdapter(stt_adapter=stt_adapter)
    
    # Dynamic context (can be set per-call)
    # You can pass custom context here based on call parameters
    dynamic_context = {
        # Add any dynamic parameters here
        # "custom_param": "value"
    }
    
    # Handle the connection
    await twilio_adapter.handle_connection(
        websocket=websocket,
        dynamic_context=dynamic_context if dynamic_context else None
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
