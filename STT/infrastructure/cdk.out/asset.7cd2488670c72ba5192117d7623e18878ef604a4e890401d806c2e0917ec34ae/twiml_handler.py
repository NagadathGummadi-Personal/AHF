"""
Lambda handler for Twilio webhook - returns TwiML to start media stream.
This is called when Twilio receives an incoming call.
"""

import os


def lambda_handler(event, context):
    """
    Returns TwiML that tells Twilio to:
    1. Stream audio to our WebSocket API Gateway
    2. Play a greeting message
    
    This Lambda is triggered by Twilio's webhook when a call comes in.
    """
    # Get the WebSocket URL from environment variable
    websocket_url = os.environ.get("WEBSOCKET_URL", "")
    
    # Remove https:// and replace with wss:// for WebSocket
    if websocket_url.startswith("https://"):
        websocket_url = "wss://" + websocket_url[8:]
    elif not websocket_url.startswith("wss://"):
        websocket_url = "wss://" + websocket_url
    
    print(f"WebSocket URL: {websocket_url}")
    
    # TwiML response that starts the media stream
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">Hello! This call is being streamed for processing. Please speak after the beep.</Say>
    <Start>
        <Stream url="{websocket_url}" track="inbound_track">
            <Parameter name="caller" value="{{{{From}}}}" />
            <Parameter name="called" value="{{{{To}}}}" />
        </Stream>
    </Start>
    <Say voice="alice">You can now speak. The audio is being streamed in real-time.</Say>
    <Pause length="60"/>
    <Say voice="alice">Thank you for calling. Goodbye!</Say>
</Response>"""
    
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/xml",
        },
        "body": twiml,
    }

