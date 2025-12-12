"""
Real-time Twilio Media Stream to ElevenLabs STT Server.
Uses persistent WebSocket connections for true real-time transcription.
"""

import os
import json
import base64
import asyncio
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse
from starlette.websockets import WebSocketDisconnect
import websockets

# Configuration
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_STT_URL = "wss://api.elevenlabs.io/v1/speech-to-text/realtime"

app = FastAPI(title="Twilio-ElevenLabs Real-time STT")


@app.get("/")
async def root():
    return {"status": "healthy", "service": "twilio-elevenlabs-stt"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/twiml")
async def twiml_webhook(request: Request):
    """Generate TwiML to stream audio to our WebSocket endpoint."""
    host = request.headers.get("host", request.url.hostname)
    
    # Use wss for production (default), ws only for localhost
    is_local = "localhost" in host or "127.0.0.1" in host
    protocol = "ws" if is_local else "wss"
    websocket_url = f"{protocol}://{host}/media-stream"
    
    print(f"TwiML webhook called, WebSocket URL: {websocket_url}")
    
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">Connected. Speak now and I will transcribe in real-time.</Say>
    <Connect>
        <Stream url="{websocket_url}" />
    </Connect>
</Response>"""
    
    return HTMLResponse(content=twiml, media_type="application/xml")


@app.websocket("/media-stream")
async def media_stream(websocket: WebSocket):
    """Handle Twilio media stream with real-time ElevenLabs transcription."""
    await websocket.accept()
    print("Twilio WebSocket connected")
    
    stream_sid = None
    elevenlabs_ws = None
    receive_task = None
    
    try:
        # Connect to ElevenLabs STT (scribe_v2 realtime model)
        ws_url = f"{ELEVENLABS_STT_URL}?model_id=scribe_v2&encoding=ulaw&sample_rate=8000&language_code=en"
        headers = {"xi-api-key": ELEVENLABS_API_KEY}
        
        print(f"Connecting to ElevenLabs: {ws_url}")
        elevenlabs_ws = await websockets.connect(ws_url, additional_headers=headers)
        
        # Wait for session start
        session_msg = await asyncio.wait_for(elevenlabs_ws.recv(), timeout=5.0)
        session_data = json.loads(session_msg)
        print(f"ElevenLabs session started: {session_data.get('session_id', 'unknown')}")
        
        # Start background task to receive transcriptions
        receive_task = asyncio.create_task(
            receive_transcriptions(elevenlabs_ws, websocket, stream_sid)
        )
        
        # Process Twilio messages
        async for message in websocket.iter_text():
            if not message:
                continue
                
            try:
                data = json.loads(message)
                event_type = data.get("event")
                
                if event_type == "start":
                    stream_sid = data.get("start", {}).get("streamSid")
                    call_sid = data.get("start", {}).get("callSid")
                    print(f"STREAM_START | stream={stream_sid} | call={call_sid}")
                    
                elif event_type == "media":
                    # Forward audio to ElevenLabs in real-time
                    payload = data.get("media", {}).get("payload", "")
                    if payload and elevenlabs_ws:
                        await elevenlabs_ws.send(json.dumps({
                            "audio_base_64": payload
                        }))
                        
                elif event_type == "stop":
                    print(f"STREAM_STOP | stream={stream_sid}")
                    # Signal end of stream to ElevenLabs
                    if elevenlabs_ws:
                        await elevenlabs_ws.send(json.dumps({"type": "eos"}))
                    break
                    
            except json.JSONDecodeError:
                print(f"Invalid JSON: {message[:100]}")
                
    except WebSocketDisconnect:
        print("Twilio WebSocket disconnected")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Cleanup
        if receive_task:
            receive_task.cancel()
            try:
                await receive_task
            except asyncio.CancelledError:
                pass
                
        if elevenlabs_ws:
            try:
                await elevenlabs_ws.close()
            except:
                pass
                
        print("Connection closed")


async def receive_transcriptions(elevenlabs_ws, twilio_ws, stream_sid):
    """Background task to receive and log transcriptions from ElevenLabs."""
    try:
        while True:
            try:
                response = await asyncio.wait_for(elevenlabs_ws.recv(), timeout=30.0)
                data = json.loads(response)
                
                msg_type = data.get("message_type", data.get("type", ""))
                
                # Handle different message types
                if msg_type in ["transcript", "partial_transcript"]:
                    text = data.get("text", "").strip()
                    if text:
                        print(f"PARTIAL | \"{text}\"")
                        
                elif msg_type in ["final_transcript", "utterance_end"]:
                    text = data.get("text", "").strip()
                    if text:
                        print(f"FINAL | \"{text}\"")
                        # Optionally send back to Twilio or store in DB
                        
                elif msg_type == "error":
                    print(f"11LABS_ERROR | {data}")
                    
                elif msg_type in ["session_end", "done"]:
                    print("ElevenLabs session ended")
                    break
                    
            except asyncio.TimeoutError:
                # No message for 30s, continue waiting
                continue
                
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"Transcription receive error: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


