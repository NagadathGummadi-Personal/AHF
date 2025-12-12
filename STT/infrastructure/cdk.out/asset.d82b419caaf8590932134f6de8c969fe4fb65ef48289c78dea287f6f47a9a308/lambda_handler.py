"""
Lambda handler for Twilio Media Stream + ElevenLabs STT.
Buffers all audio until stream ends, then transcribes complete message.
"""

import json
import base64
import boto3
import os
import asyncio
import time
from datetime import datetime

try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False

# AWS
dynamodb = boto3.resource("dynamodb")
CONNECTIONS_TABLE = os.environ.get("CONNECTIONS_TABLE", "twilio-stream-connections")
TRANSCRIPTS_TABLE = os.environ.get("TRANSCRIPTS_TABLE", "twilio-stream-transcripts")

# ElevenLabs
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVENLABS_STT_URL = "wss://api.elevenlabs.io/v1/speech-to-text/realtime"

# Audio buffers (keyed by streamSid)
audio_buffers = {}


def lambda_handler(event, context):
    route_key = event.get("requestContext", {}).get("routeKey")
    connection_id = event.get("requestContext", {}).get("connectionId")
    
    if route_key == "$connect":
        return handle_connect(connection_id)
    elif route_key == "$disconnect":
        return handle_disconnect(connection_id)
    else:
        return handle_message(event, connection_id)


def handle_connect(connection_id):
    try:
        table = dynamodb.Table(CONNECTIONS_TABLE)
        table.put_item(Item={"connectionId": connection_id, "connectedAt": datetime.utcnow().isoformat()})
        return {"statusCode": 200, "body": "Connected"}
    except:
        return {"statusCode": 500, "body": "Error"}


def handle_disconnect(connection_id):
    try:
        table = dynamodb.Table(CONNECTIONS_TABLE)
        table.delete_item(Key={"connectionId": connection_id})
        return {"statusCode": 200, "body": "Disconnected"}
    except:
        return {"statusCode": 500, "body": "Error"}


def handle_message(event, connection_id):
    try:
        message = json.loads(event.get("body", "{}"))
        event_type = message.get("event")
        
        if event_type == "start":
            return handle_start(message)
        elif event_type == "media":
            return handle_media(message)
        elif event_type == "stop":
            return handle_stop(message, connection_id)
        return {"statusCode": 200, "body": "OK"}
    except Exception as e:
        print(f"ERROR | {e}")
        return {"statusCode": 500, "body": str(e)}


def handle_start(message):
    stream_sid = message.get("start", {}).get("streamSid")
    call_sid = message.get("start", {}).get("callSid")
    
    audio_buffers[stream_sid] = {
        "chunks": [],
        "start_time": time.time()
    }
    
    print(f"STREAM_START | stream={stream_sid} | call={call_sid}")
    return {"statusCode": 200, "body": "Started"}


def handle_media(message):
    stream_sid = message.get("streamSid")
    payload = message.get("media", {}).get("payload", "")
    chunk_num = int(message.get("media", {}).get("chunk", "0"))
    
    if stream_sid not in audio_buffers:
        audio_buffers[stream_sid] = {"chunks": [], "start_time": time.time()}
    
    # Just buffer - don't send yet
    audio_buffers[stream_sid]["chunks"].append(payload)
    
    # Log timing every 50 chunks
    if chunk_num % 50 == 0:
        elapsed = time.time() - audio_buffers[stream_sid]["start_time"]
        print(f"AUDIO_IN | chunk={chunk_num} | elapsed={elapsed:.2f}s | buffered={len(audio_buffers[stream_sid]['chunks'])}")
    
    return {"statusCode": 200, "body": "OK"}


def handle_stop(message, connection_id):
    stream_sid = message.get("streamSid")
    
    if stream_sid not in audio_buffers:
        return {"statusCode": 200, "body": "No buffer"}
    
    chunks = audio_buffers[stream_sid]["chunks"]
    start_time = audio_buffers[stream_sid]["start_time"]
    total_chunks = len(chunks)
    duration = total_chunks * 0.02  # ~20ms per chunk
    
    print(f"STREAM_END | stream={stream_sid} | chunks={total_chunks} | duration={duration:.1f}s")
    
    # Combine all audio and transcribe
    if chunks and ELEVENLABS_API_KEY and WEBSOCKETS_AVAILABLE:
        combined = combine_all_chunks(chunks)
        transcribe(combined, stream_sid, connection_id)
    
    del audio_buffers[stream_sid]
    return {"statusCode": 200, "body": "Stopped"}


def combine_all_chunks(chunks):
    combined = b""
    for chunk in chunks:
        try:
            combined += base64.b64decode(chunk)
        except:
            pass
    return base64.b64encode(combined).decode("utf-8")


def transcribe(audio_base64, stream_sid, connection_id):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(transcribe_elevenlabs(audio_base64, stream_sid, connection_id))
        loop.close()
    except Exception as e:
        print(f"TRANSCRIBE_ERROR | {e}")


async def transcribe_elevenlabs(audio_base64, stream_sid, connection_id):
    ws_url = f"{ELEVENLABS_STT_URL}?model_id=scribe_v2_realtime&encoding=ulaw&sample_rate=8000&language_code=en"
    headers = {"xi-api-key": ELEVENLABS_API_KEY}
    
    send_time = time.time()
    
    try:
        async with websockets.connect(ws_url, additional_headers=headers) as ws:
            # Wait for session
            await asyncio.wait_for(ws.recv(), timeout=5.0)
            
            # Send complete audio
            await ws.send(json.dumps({"audio_base_64": audio_base64}))
            await ws.send(json.dumps({"type": "commit"}))
            
            # Get transcript
            while True:
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=10.0)
                    data = json.loads(response)
                    msg_type = data.get("type", "")
                    
                    if msg_type == "committed_transcript":
                        latency_ms = (time.time() - send_time) * 1000
                        text = data.get("text", "").strip()
                        
                        if text:
                            print(f"TRANSCRIPT | latency={latency_ms:.0f}ms | text=\"{text}\"")
                            save_transcript(stream_sid, text, connection_id)
                        else:
                            print(f"TRANSCRIPT | latency={latency_ms:.0f}ms | (empty)")
                        break
                    
                    elif msg_type == "error":
                        print(f"11LABS_ERROR | {data.get('message', 'unknown')}")
                        break
                        
                except asyncio.TimeoutError:
                    print("11LABS_TIMEOUT")
                    break
                    
    except Exception as e:
        print(f"11LABS_ERROR | {e}")


def save_transcript(stream_sid, text, connection_id):
    try:
        table = dynamodb.Table(TRANSCRIPTS_TABLE)
        table.put_item(Item={
            "streamSid": stream_sid,
            "timestamp": datetime.utcnow().isoformat(),
            "transcript": text,
            "connectionId": connection_id,
        })
    except Exception as e:
        print(f"DB_ERROR | {e}")
