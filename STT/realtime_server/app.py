"""
Real-time Twilio Media Stream to STT Server.
Clean adapter-based architecture for easy provider switching.
Supports: ElevenLabs, AssemblyAI, Deepgram

Features:
- Single provider mode: Test one provider at a time
- Comparison mode: Send same audio to ALL providers simultaneously for latency comparison
"""

import os
from typing import Optional, List
from fastapi import FastAPI, WebSocket, Request, Query
from fastapi.responses import HTMLResponse

from adapters.telephony import TwilioAdapter
from adapters.stt import (
    STTAdapter,
    ElevenLabsAdapter, ElevenLabsConfig,
    AssemblyAIAdapter, AssemblyAIConfig,
    DeepgramAdapter, DeepgramConfig,
    MultiProviderAdapter,
)


# Configuration - API keys from environment variables
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY", "")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")

# Default provider
DEFAULT_PROVIDER = os.getenv("STT_PROVIDER", "elevenlabs")

app = FastAPI(title="Realtime STT Server - Multi-Provider Comparison")


def create_stt_adapter(provider: str) -> STTAdapter:
    """
    Create an STT adapter for the specified provider.
    
    Args:
        provider: One of "elevenlabs", "assemblyai", "deepgram"
    
    Returns:
        Configured STTAdapter instance
    """
    provider = provider.lower().strip()
    
    if provider == "elevenlabs":
        config = ElevenLabsConfig(
            api_key=ELEVENLABS_API_KEY,
            sample_rate=8000,
            audio_format="ulaw_8000",
            language_code="en",
            include_timestamps=True,
            include_language_detection=True,
            enable_logging=True,
            commit_strategy="vad",
        )
        return ElevenLabsAdapter(config=config)
    
    elif provider == "assemblyai":
        config = AssemblyAIConfig(
            api_key=ASSEMBLYAI_API_KEY,
            sample_rate=16000,  # AssemblyAI requires 16kHz
            input_sample_rate=8000,  # Twilio sends 8kHz
            language="multi",  # Auto-detect language
            format_turns=True,
            end_of_turn_confidence_threshold=0.7,
            min_end_of_turn_silence_when_confident=160,
            max_turn_silence=2400,
        )
        return AssemblyAIAdapter(config=config)
    
    elif provider == "deepgram":
        config = DeepgramConfig(
            api_key=DEEPGRAM_API_KEY,
            model="nova-3",
            encoding="mulaw",
            sample_rate=8000,
            language_code="en",
            punctuate=True,
            smart_format=True,
            interim_results=True,
            utterance_end_ms=1000,
            vad_events=True,
            endpointing=300,
            numerals=True,
        )
        return DeepgramAdapter(config=config)
    
    else:
        raise ValueError(f"Unknown provider: {provider}. Use 'elevenlabs', 'assemblyai', or 'deepgram'")


def create_multi_provider_adapter(providers: Optional[List[str]] = None) -> MultiProviderAdapter:
    """
    Create a multi-provider adapter that sends audio to all specified providers.
    
    Args:
        providers: List of provider names. If None, uses all available (with API keys).
    
    Returns:
        MultiProviderAdapter instance
    """
    adapters = []
    
    # Determine which providers to use
    available_providers = []
    if ELEVENLABS_API_KEY:
        available_providers.append("elevenlabs")
    if ASSEMBLYAI_API_KEY:
        available_providers.append("assemblyai")
    if DEEPGRAM_API_KEY:
        available_providers.append("deepgram")
    
    # Use specified providers or all available
    target_providers = providers if providers else available_providers
    
    for provider in target_providers:
        if provider in available_providers:
            try:
                adapter = create_stt_adapter(provider)
                adapters.append(adapter)
            except Exception as e:
                print(f"Warning: Could not create {provider} adapter: {e}")
    
    if not adapters:
        raise ValueError("No STT providers available. Please set at least one API key.")
    
    return MultiProviderAdapter(adapters=adapters)


@app.get("/")
async def root():
    # Check which providers have API keys configured
    available = []
    if ELEVENLABS_API_KEY:
        available.append("elevenlabs")
    if ASSEMBLYAI_API_KEY:
        available.append("assemblyai")
    if DEEPGRAM_API_KEY:
        available.append("deepgram")
    
    return {
        "status": "healthy",
        "service": "realtime-stt-comparison",
        "providers_available": available,
        "default_provider": DEFAULT_PROVIDER,
        "endpoints": {
            "single_provider": "/twiml/{provider}",
            "comparison_mode": "/twiml/compare",
        }
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/twiml")
async def twiml_webhook(
    request: Request,
    provider: Optional[str] = Query(default=None, description="STT provider to use")
):
    """Generate TwiML to connect Twilio to our WebSocket."""
    host = request.headers.get("host", request.url.hostname)
    
    # Use wss for production, ws for localhost
    is_local = "localhost" in host or "127.0.0.1" in host
    protocol = "ws" if is_local else "wss"
    
    # Add provider to WebSocket URL if specified
    provider_param = f"?provider={provider}" if provider else f"?provider={DEFAULT_PROVIDER}"
    websocket_url = f"{protocol}://{host}/media-stream{provider_param}"
    
    twiml = TwilioAdapter.generate_twiml(
        websocket_url=websocket_url,
        greeting="Connected. Speak now and I will transcribe in real-time."
    )
    
    return HTMLResponse(content=twiml, media_type="application/xml")


@app.post("/twiml/{provider}")
async def twiml_webhook_provider(request: Request, provider: str):
    """Generate TwiML for a specific provider (path-based routing)."""
    host = request.headers.get("host", request.url.hostname)
    
    is_local = "localhost" in host or "127.0.0.1" in host
    protocol = "ws" if is_local else "wss"
    websocket_url = f"{protocol}://{host}/media-stream/{provider}"
    
    twiml = TwilioAdapter.generate_twiml(
        websocket_url=websocket_url,
        greeting=f"Connected to {provider}. Speak now."
    )
    
    return HTMLResponse(content=twiml, media_type="application/xml")


@app.websocket("/media-stream")
async def media_stream(
    websocket: WebSocket,
    provider: Optional[str] = Query(default=None)
):
    """Handle Twilio media stream with configurable STT provider."""
    
    selected_provider = provider or DEFAULT_PROVIDER
    print(f"\n{'='*60}")
    print(f"Starting STT session with provider: {selected_provider.upper()}")
    print(f"{'='*60}\n")
    
    try:
        stt_adapter = create_stt_adapter(selected_provider)
    except ValueError as e:
        print(f"Error: {e}")
        return
    
    # Create Twilio adapter with STT
    twilio_adapter = TwilioAdapter(stt_adapter=stt_adapter)
    
    # Handle the connection
    await twilio_adapter.handle_connection(websocket=websocket)


@app.websocket("/media-stream/{provider}")
async def media_stream_provider(websocket: WebSocket, provider: str):
    """Handle Twilio media stream for a specific provider (path-based routing)."""
    
    # Special case: "compare" triggers comparison mode
    if provider.lower() == "compare":
        await media_stream_compare(websocket)
        return
    
    print(f"\n{'='*60}")
    print(f"Starting STT session with provider: {provider.upper()}")
    print(f"{'='*60}\n")
    
    try:
        stt_adapter = create_stt_adapter(provider)
    except ValueError as e:
        print(f"Error: {e}")
        return
    
    twilio_adapter = TwilioAdapter(stt_adapter=stt_adapter)
    await twilio_adapter.handle_connection(websocket=websocket)


# =============================================================================
# COMPARISON MODE ENDPOINTS
# =============================================================================

@app.post("/twiml/compare")
async def twiml_compare_webhook(request: Request):
    """
    Generate TwiML for COMPARISON MODE.
    Audio will be sent to ALL available STT providers simultaneously.
    """
    host = request.headers.get("host", request.url.hostname)
    
    is_local = "localhost" in host or "127.0.0.1" in host
    protocol = "ws" if is_local else "wss"
    websocket_url = f"{protocol}://{host}/media-stream/compare"
    
    # Check available providers
    available = []
    if ELEVENLABS_API_KEY:
        available.append("ElevenLabs")
    if ASSEMBLYAI_API_KEY:
        available.append("AssemblyAI")
    if DEEPGRAM_API_KEY:
        available.append("Deepgram")
    
    greeting = f"Comparison mode activated. Testing {', '.join(available)}. Speak now."
    
    twiml = TwilioAdapter.generate_twiml(
        websocket_url=websocket_url,
        greeting=greeting
    )
    
    return HTMLResponse(content=twiml, media_type="application/xml")


@app.websocket("/media-stream/compare")
async def media_stream_compare(websocket: WebSocket):
    """
    Handle Twilio media stream in COMPARISON MODE.
    Sends the same audio to all available STT providers simultaneously.
    """
    print(f"\n{'='*70}")
    print(f"🔬 COMPARISON MODE - Testing ALL providers with same audio stream")
    print(f"{'='*70}\n")
    
    try:
        multi_adapter = create_multi_provider_adapter()
        print(f"Providers: {[a.provider_name for a in multi_adapter.adapters]}")
    except ValueError as e:
        print(f"Error: {e}")
        return
    
    twilio_adapter = TwilioAdapter(stt_adapter=multi_adapter)
    await twilio_adapter.handle_connection(websocket=websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
