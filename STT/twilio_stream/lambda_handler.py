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
    # ElevenLabs STT realtime expects: ulaw 8kHz (Twilio's format)
    ws_url = f"{ELEVENLABS_STT_URL}?model_id=scribe_v1&encoding=ulaw&sample_rate=8000&language_code=en"
    headers = {"xi-api-key": ELEVENLABS_API_KEY}
    
    audio_size_kb = len(audio_base64) / 1024
    print(f"11LABS_CONNECT | audio_size={audio_size_kb:.1f}KB | url={ws_url}")
    
    send_time = time.time()
    
    try:
        async with websockets.connect(ws_url, additional_headers=headers) as ws:
            # Wait for session started
            session_msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
            print(f"11LABS_SESSION | {session_msg[:300]}")
            
            # Send audio in chunks (like the reference implementation)
            # Break into ~32KB chunks to avoid overwhelming the connection
            chunk_size = 32000  # characters of base64
            total_sent = 0
            for i in range(0, len(audio_base64), chunk_size):
                chunk = audio_base64[i:i + chunk_size]
                await ws.send(json.dumps({"audio_base_64": chunk}))
                total_sent += len(chunk)
            
            print(f"11LABS_SENT | sent {total_sent} bytes in {(total_sent // chunk_size) + 1} chunks")
            
            # Signal end of stream
            await ws.send(json.dumps({"type": "eos"}))
            print(f"11LABS_EOS | sent")
            
            # Collect transcripts
            transcript_text = ""
            msg_count = 0
            while True:
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=30.0)
                    msg_count += 1
                    
                    # Log raw response (truncated)
                    print(f"11LABS_RAW | {response[:500]}")
                    
                    data = json.loads(response)
                    msg_type = data.get("message_type", data.get("type", ""))
                    
                    # Extract text from various possible fields
                    text = data.get("text", "") or data.get("transcript", "") or ""
                    text = text.strip()
                    
                    if text:
                        transcript_text = text
                        print(f"11LABS_TEXT | \"{text}\"")
                    
                    # Check for terminal message types
                    if msg_type in ["final_transcript", "done", "session_end", "eos_received"]:
                        latency_ms = (time.time() - send_time) * 1000
                        if transcript_text:
                            print(f"TRANSCRIPT | latency={latency_ms:.0f}ms | text=\"{transcript_text}\"")
                            save_transcript(stream_sid, transcript_text, connection_id)
                        else:
                            print(f"11LABS_END | {msg_type} | no text | msgs={msg_count}")
                        
                        # If eos_received, keep waiting for actual transcript
                        if msg_type == "eos_received":
                            continue
                        break
                    
                    elif msg_type == "error":
                        print(f"11LABS_ERROR | {data}")
                        break
                        
                except asyncio.TimeoutError:
                    latency_ms = (time.time() - send_time) * 1000
                    if transcript_text:
                        print(f"TRANSCRIPT | latency={latency_ms:.0f}ms | text=\"{transcript_text}\" (timeout)")
                        save_transcript(stream_sid, transcript_text, connection_id)
                    else:
                        print(f"11LABS_TIMEOUT | no response in 30s | msgs={msg_count}")
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
