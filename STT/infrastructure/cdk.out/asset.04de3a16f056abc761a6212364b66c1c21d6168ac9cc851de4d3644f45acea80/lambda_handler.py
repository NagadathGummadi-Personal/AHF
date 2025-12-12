"""
Lambda handler for Twilio Media Stream via API Gateway WebSocket.
Receives real-time audio from Twilio phone calls and transcribes using ElevenLabs.
"""

import json
import base64
import boto3
import os
import asyncio
from datetime import datetime
from typing import Optional
from decimal import Decimal

# Import websockets for ElevenLabs connection
try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    print("websockets library not available - will buffer audio only")

# Initialize clients
dynamodb = boto3.resource("dynamodb")
s3 = boto3.client("s3")

# Environment variables
CONNECTIONS_TABLE = os.environ.get("CONNECTIONS_TABLE", "twilio-stream-connections")
AUDIO_BUCKET = os.environ.get("AUDIO_BUCKET", "twilio-audio-streams")
TRANSCRIPTS_TABLE = os.environ.get("TRANSCRIPTS_TABLE", "twilio-stream-transcripts")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")

# ElevenLabs WebSocket URL for real-time STT
ELEVENLABS_STT_URL = "wss://api.elevenlabs.io/v1/speech-to-text/realtime"

# Audio buffer settings
# Buffer audio chunks and send to ElevenLabs every N chunks (~20ms each)
CHUNKS_PER_BATCH = 25  # ~500ms of audio per batch


# In-memory audio buffer (per stream)
# Note: In production, use Redis/ElastiCache for shared state across Lambda invocations
audio_buffers: dict = {}
transcription_sessions: dict = {}


def lambda_handler(event, context):
    """
    Main handler for API Gateway WebSocket events.
    Routes: $connect, $disconnect, $default (for Twilio media messages)
    """
    route_key = event.get("requestContext", {}).get("routeKey")
    connection_id = event.get("requestContext", {}).get("connectionId")
    
    print(f"Route: {route_key}, ConnectionId: {connection_id}")
    
    handlers = {
        "$connect": handle_connect,
        "$disconnect": handle_disconnect,
        "$default": handle_message,
    }
    
    handler = handlers.get(route_key, handle_message)
    return handler(event, context)


def handle_connect(event, context):
    """Handle new WebSocket connection from Twilio."""
    connection_id = event["requestContext"]["connectionId"]
    
    try:
        table = dynamodb.Table(CONNECTIONS_TABLE)
        table.put_item(
            Item={
                "connectionId": connection_id,
                "connectedAt": datetime.utcnow().isoformat(),
                "streamSid": None,
                "callSid": None,
            }
        )
        print(f"Connected: {connection_id}")
        return {"statusCode": 200, "body": "Connected"}
    except Exception as e:
        print(f"Connect error: {e}")
        return {"statusCode": 500, "body": f"Failed to connect: {str(e)}"}


def handle_disconnect(event, context):
    """Handle WebSocket disconnection."""
    connection_id = event["requestContext"]["connectionId"]
    
    try:
        table = dynamodb.Table(CONNECTIONS_TABLE)
        table.delete_item(Key={"connectionId": connection_id})
        print(f"Disconnected: {connection_id}")
        return {"statusCode": 200, "body": "Disconnected"}
    except Exception as e:
        print(f"Disconnect error: {e}")
        return {"statusCode": 500, "body": f"Failed to disconnect: {str(e)}"}


def handle_message(event, context):
    """
    Handle incoming Twilio Media Stream messages.
    
    Message types from Twilio:
    - connected: Initial connection confirmation
    - start: Stream metadata (call info, media format)
    - media: Audio payload (base64 encoded mulaw/8000Hz)
    - stop: Stream ended
    """
    connection_id = event["requestContext"]["connectionId"]
    
    try:
        body = event.get("body", "{}")
        message = json.loads(body)
        event_type = message.get("event")
        
        if event_type == "connected":
            return handle_connected(connection_id, message)
        
        elif event_type == "start":
            return handle_start(connection_id, message)
        
        elif event_type == "media":
            return handle_media(connection_id, message)
        
        elif event_type == "stop":
            return handle_stop(connection_id, message)
        
        elif event_type == "mark":
            return {"statusCode": 200, "body": "Mark received"}
        
        else:
            print(f"Unknown event type: {event_type}")
            return {"statusCode": 200, "body": "Unknown event"}
            
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        return {"statusCode": 400, "body": "Invalid JSON"}
    except Exception as e:
        print(f"Message handling error: {e}")
        return {"statusCode": 500, "body": str(e)}


def handle_connected(connection_id: str, message: dict):
    """Handle Twilio 'connected' event."""
    protocol = message.get("protocol", "Unknown")
    version = message.get("version", "Unknown")
    print(f"Twilio connected - Protocol: {protocol}, Version: {version}")
    return {"statusCode": 200, "body": "Connected event processed"}


def handle_start(connection_id: str, message: dict):
    """
    Handle Twilio 'start' event - contains stream metadata.
    Initialize audio buffer and ElevenLabs session for this stream.
    """
    start_data = message.get("start", {})
    stream_sid = start_data.get("streamSid")
    call_sid = start_data.get("callSid")
    account_sid = start_data.get("accountSid")
    media_format = start_data.get("mediaFormat", {})
    
    print(f"Stream started - StreamSid: {stream_sid}, CallSid: {call_sid}")
    print(f"Media format: {media_format}")
    
    # Initialize audio buffer for this stream
    audio_buffers[stream_sid] = {
        "chunks": [],
        "call_sid": call_sid,
        "connection_id": connection_id,
        "started_at": datetime.utcnow().isoformat(),
        "total_chunks": 0,
    }
    
    # Update connection with stream info
    try:
        table = dynamodb.Table(CONNECTIONS_TABLE)
        table.update_item(
            Key={"connectionId": connection_id},
            UpdateExpression="SET streamSid = :s, callSid = :c, accountSid = :a, mediaFormat = :m, startedAt = :t",
            ExpressionAttributeValues={
                ":s": stream_sid,
                ":c": call_sid,
                ":a": account_sid,
                ":m": media_format,
                ":t": datetime.utcnow().isoformat(),
            },
        )
    except Exception as e:
        print(f"Error updating connection: {e}")
    
    return {"statusCode": 200, "body": "Start event processed"}


def handle_media(connection_id: str, message: dict):
    """
    Handle Twilio 'media' event - contains audio payload.
    Buffer audio and send to ElevenLabs for transcription.
    
    Audio format from Twilio: mulaw, 8000Hz, mono (~20ms per chunk)
    """
    media_data = message.get("media", {})
    payload = media_data.get("payload", "")  # Base64 encoded audio
    stream_sid = message.get("streamSid")
    chunk_num = int(media_data.get("chunk", "0"))
    
    if not stream_sid or stream_sid not in audio_buffers:
        # Initialize buffer if not exists
        audio_buffers[stream_sid] = {
            "chunks": [],
            "call_sid": None,
            "connection_id": connection_id,
            "started_at": datetime.utcnow().isoformat(),
            "total_chunks": 0,
        }
    
    # Add chunk to buffer
    audio_buffers[stream_sid]["chunks"].append(payload)
    audio_buffers[stream_sid]["total_chunks"] += 1
    
    # Process buffer when we have enough chunks
    if len(audio_buffers[stream_sid]["chunks"]) >= CHUNKS_PER_BATCH:
        # Combine chunks and send to ElevenLabs
        combined_audio = combine_audio_chunks(audio_buffers[stream_sid]["chunks"])
        audio_buffers[stream_sid]["chunks"] = []  # Clear buffer
        
        # Send to ElevenLabs for transcription
        if ELEVENLABS_API_KEY and WEBSOCKETS_AVAILABLE:
            try:
                transcript = asyncio.get_event_loop().run_until_complete(
                    transcribe_with_elevenlabs(combined_audio, stream_sid)
                )
                if transcript:
                    save_transcript(stream_sid, transcript, connection_id)
            except RuntimeError:
                # No event loop, create new one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    transcript = loop.run_until_complete(
                        transcribe_with_elevenlabs(combined_audio, stream_sid)
                    )
                    if transcript:
                        save_transcript(stream_sid, transcript, connection_id)
                finally:
                    loop.close()
    
    # Log progress every 50 chunks
    if chunk_num % 50 == 0:
        print(f"Processed chunk {chunk_num} for stream {stream_sid}")
    
    return {"statusCode": 200, "body": "Media processed"}


def combine_audio_chunks(chunks: list) -> str:
    """
    Combine multiple base64 audio chunks into one.
    Returns combined base64 string.
    """
    combined_bytes = b""
    for chunk in chunks:
        try:
            combined_bytes += base64.b64decode(chunk)
        except Exception as e:
            print(f"Error decoding chunk: {e}")
    
    return base64.b64encode(combined_bytes).decode("utf-8")


async def transcribe_with_elevenlabs(audio_base64: str, stream_sid: str) -> Optional[str]:
    """
    Send audio to ElevenLabs Realtime STT and get transcript.
    
    ElevenLabs Realtime STT supports:
    - μ-law encoding (audio/x-mulaw) - exactly what Twilio sends!
    - Sample rate: 8000Hz
    
    Reference: https://elevenlabs.io/docs/api-reference/speech-to-text/v-1-speech-to-text-realtime
    """
    if not ELEVENLABS_API_KEY:
        print("ElevenLabs API key not configured")
        return None
    
    # Build WebSocket URL with query parameters
    ws_url = (
        f"{ELEVENLABS_STT_URL}"
        f"?model_id=scribe_v2_realtime"
        f"&encoding=ulaw"  # μ-law encoding from Twilio
        f"&sample_rate=8000"  # Twilio's sample rate
        f"&language_code=en"  # English
    )
    
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
    }
    
    transcript_text = ""
    
    try:
        async with websockets.connect(ws_url, extra_headers=headers) as ws:
            # Wait for session started
            session_msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
            session_data = json.loads(session_msg)
            print(f"ElevenLabs session: {session_data.get('type', 'unknown')}")
            
            # Send audio chunk
            audio_message = {
                "audio_base_64": audio_base64,
            }
            await ws.send(json.dumps(audio_message))
            
            # Send commit to finalize transcription
            await ws.send(json.dumps({"type": "commit"}))
            
            # Receive transcripts with timeout
            try:
                while True:
                    response = await asyncio.wait_for(ws.recv(), timeout=3.0)
                    data = json.loads(response)
                    msg_type = data.get("type", "")
                    
                    if msg_type == "partial_transcript":
                        partial = data.get("text", "")
                        if partial:
                            print(f"[Partial] {partial}")
                    
                    elif msg_type == "committed_transcript":
                        committed = data.get("text", "")
                        if committed:
                            transcript_text = committed
                            print(f"[Committed] {committed}")
                        break  # Got final transcript
                    
                    elif msg_type == "error":
                        error_msg = data.get("message", "Unknown error")
                        print(f"ElevenLabs error: {error_msg}")
                        break
                        
            except asyncio.TimeoutError:
                print("Timeout waiting for transcript")
                
    except websockets.exceptions.WebSocketException as e:
        print(f"WebSocket error: {e}")
    except Exception as e:
        print(f"ElevenLabs transcription error: {e}")
    
    return transcript_text if transcript_text else None


def save_transcript(stream_sid: str, transcript: str, connection_id: str):
    """Save transcript to DynamoDB."""
    try:
        table = dynamodb.Table(TRANSCRIPTS_TABLE)
        timestamp = datetime.utcnow().isoformat()
        
        table.put_item(
            Item={
                "streamSid": stream_sid,
                "timestamp": timestamp,
                "transcript": transcript,
                "connectionId": connection_id,
            }
        )
        print(f"Saved transcript: '{transcript}' for stream {stream_sid}")
        
    except Exception as e:
        print(f"Error saving transcript: {e}")
        # Log to CloudWatch even if DynamoDB fails
        print(f"TRANSCRIPT [{stream_sid}]: {transcript}")


def handle_stop(connection_id: str, message: dict):
    """
    Handle Twilio 'stop' event - stream has ended.
    Process any remaining buffered audio.
    """
    stop_data = message.get("stop", {})
    call_sid = stop_data.get("callSid")
    stream_sid = message.get("streamSid")
    
    print(f"Stream stopped - CallSid: {call_sid}, StreamSid: {stream_sid}")
    
    # Process remaining buffered audio
    if stream_sid and stream_sid in audio_buffers:
        remaining_chunks = audio_buffers[stream_sid]["chunks"]
        
        if remaining_chunks and ELEVENLABS_API_KEY and WEBSOCKETS_AVAILABLE:
            print(f"Processing {len(remaining_chunks)} remaining chunks")
            combined_audio = combine_audio_chunks(remaining_chunks)
            
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    transcript = loop.run_until_complete(
                        transcribe_with_elevenlabs(combined_audio, stream_sid)
                    )
                    if transcript:
                        save_transcript(stream_sid, transcript, connection_id)
                finally:
                    loop.close()
            except Exception as e:
                print(f"Error processing final audio: {e}")
        
        # Log summary
        total = audio_buffers[stream_sid]["total_chunks"]
        duration_sec = total * 0.02  # ~20ms per chunk
        print(f"Stream {stream_sid} complete: {total} chunks (~{duration_sec:.1f}s audio)")
        
        # Clean up buffer
        del audio_buffers[stream_sid]
    
    return {"statusCode": 200, "body": "Stop event processed"}


def send_to_connection(connection_id: str, domain_name: str, stage: str, message: dict):
    """
    Send a message back to the WebSocket client (Twilio).
    Useful for sending 'mark' events or other responses.
    """
    api_client = boto3.client(
        "apigatewaymanagementapi",
        endpoint_url=f"https://{domain_name}/{stage}"
    )
    
    try:
        api_client.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(message).encode("utf-8")
        )
        return True
    except Exception as e:
        print(f"Error sending to connection: {e}")
        return False
