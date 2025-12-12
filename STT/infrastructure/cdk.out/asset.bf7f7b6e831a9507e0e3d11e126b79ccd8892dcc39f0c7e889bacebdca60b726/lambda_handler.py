"""
Lambda handler for Twilio Media Stream via API Gateway WebSocket.
Receives real-time audio from Twilio phone calls.
"""

import json
import base64
import boto3
import os
from datetime import datetime

# Initialize clients
dynamodb = boto3.resource("dynamodb")
s3 = boto3.client("s3")

# Environment variables
CONNECTIONS_TABLE = os.environ.get("CONNECTIONS_TABLE", "twilio-stream-connections")
AUDIO_BUCKET = os.environ.get("AUDIO_BUCKET", "twilio-audio-streams")


def lambda_handler(event, context):
    """
    Main handler for API Gateway WebSocket events.
    Routes: $connect, $disconnect, $default (for Twilio media messages)
    """
    route_key = event.get("requestContext", {}).get("routeKey")
    connection_id = event.get("requestContext", {}).get("connectionId")
    
    print(f"Route: {route_key}, ConnectionId: {connection_id}")
    print(f"Event: {json.dumps(event)}")
    
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
        
        print(f"Message type: {event_type}")
        
        if event_type == "connected":
            return handle_connected(connection_id, message)
        
        elif event_type == "start":
            return handle_start(connection_id, message)
        
        elif event_type == "media":
            return handle_media(connection_id, message)
        
        elif event_type == "stop":
            return handle_stop(connection_id, message)
        
        elif event_type == "mark":
            # Mark events are acknowledgments, just log them
            print(f"Mark event: {message}")
            return {"statusCode": 200, "body": "Mark received"}
        
        else:
            print(f"Unknown event type: {event_type}")
            return {"statusCode": 200, "body": "Unknown event"}
            
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}, body: {event.get('body')}")
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
    
    Example start message:
    {
        "event": "start",
        "sequenceNumber": "1",
        "start": {
            "streamSid": "MZ...",
            "accountSid": "AC...",
            "callSid": "CA...",
            "tracks": ["inbound"],
            "mediaFormat": {
                "encoding": "audio/x-mulaw",
                "sampleRate": 8000,
                "channels": 1
            }
        }
    }
    """
    start_data = message.get("start", {})
    stream_sid = start_data.get("streamSid")
    call_sid = start_data.get("callSid")
    account_sid = start_data.get("accountSid")
    media_format = start_data.get("mediaFormat", {})
    tracks = start_data.get("tracks", [])
    
    print(f"Stream started - StreamSid: {stream_sid}, CallSid: {call_sid}")
    print(f"Media format: {media_format}, Tracks: {tracks}")
    
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
    
    Example media message:
    {
        "event": "media",
        "sequenceNumber": "2",
        "media": {
            "track": "inbound",
            "chunk": "1",
            "timestamp": "5",
            "payload": "<base64 encoded audio>"
        }
    }
    
    Audio format: mulaw, 8000Hz, mono
    Each chunk is ~20ms of audio
    """
    media_data = message.get("media", {})
    payload = media_data.get("payload", "")
    track = media_data.get("track", "unknown")
    chunk = media_data.get("chunk", "0")
    timestamp = media_data.get("timestamp", "0")
    
    # Decode the base64 audio payload
    try:
        audio_bytes = base64.b64decode(payload)
        audio_length = len(audio_bytes)
        
        # Log every 50th chunk to avoid log spam
        if int(chunk) % 50 == 0:
            print(f"Media chunk {chunk} - Track: {track}, Timestamp: {timestamp}ms, Size: {audio_length} bytes")
        
        # ============================================
        # PROCESS AUDIO HERE
        # ============================================
        # The audio is in mulaw format, 8000Hz, mono
        # You can:
        # 1. Send to Amazon Transcribe for real-time STT
        # 2. Buffer and save to S3
        # 3. Forward to another service
        # 4. Process with custom audio analysis
        #
        # Example: Forward to Transcribe Streaming
        # process_with_transcribe(audio_bytes, connection_id)
        #
        # Example: Buffer and save periodically
        # buffer_audio(connection_id, audio_bytes, chunk)
        # ============================================
        
        return {"statusCode": 200, "body": "Media processed"}
        
    except Exception as e:
        print(f"Error processing media: {e}")
        return {"statusCode": 500, "body": str(e)}


def handle_stop(connection_id: str, message: dict):
    """
    Handle Twilio 'stop' event - stream has ended.
    
    Example stop message:
    {
        "event": "stop",
        "sequenceNumber": "100",
        "stop": {
            "accountSid": "AC...",
            "callSid": "CA..."
        }
    }
    """
    stop_data = message.get("stop", {})
    call_sid = stop_data.get("callSid")
    
    print(f"Stream stopped - CallSid: {call_sid}")
    
    # Finalize any audio processing here
    # e.g., save buffered audio to S3, close Transcribe stream, etc.
    
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

