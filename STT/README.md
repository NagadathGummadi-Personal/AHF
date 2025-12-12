# Twilio Real-Time Audio Streaming with AWS

Stream real-time audio from Twilio phone calls to AWS via WebSocket API Gateway and Lambda.

## Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│   Caller    │────▶│  Twilio Number   │────▶│  REST API Gateway   │
│  (Phone)    │     │   (+1 XXX-XXX)   │     │   (TwiML Webhook)   │
└─────────────┘     └──────────────────┘     └──────────┬──────────┘
                                                        │
                                                        ▼
                                            ┌─────────────────────┐
                                            │  TwiML Lambda       │
                                            │  (Returns Stream    │
                                            │   Instructions)     │
                                            └──────────┬──────────┘
                                                        │
                    ┌───────────────────────────────────┘
                    │ WebSocket URL
                    ▼
┌──────────────────────────────────────────────────────────────────┐
│                    WebSocket API Gateway                          │
│                                                                   │
│  $connect ─────▶ Lambda Handler                                   │
│  $disconnect ──▶ Lambda Handler                                   │
│  $default ─────▶ Lambda Handler (processes audio)                 │
└──────────────────────────────────────────────────────────────────┘
                    │
                    ▼
          ┌─────────────────┐
          │  DynamoDB       │     ┌─────────────────┐
          │  (Connections)  │     │  S3 Bucket      │
          └─────────────────┘     │  (Audio Store)  │
                                  └─────────────────┘
```

## Prerequisites

- AWS CLI configured with credentials
- Node.js (for AWS CDK)
- Python 3.12+
- Twilio account with a phone number

## Deployment

### Windows (PowerShell)

```powershell
.\deploy.ps1
```

### Linux/macOS

```bash
chmod +x deploy.sh
./deploy.sh
```

### Manual Deployment

```bash
cd infrastructure
python -m venv .venv
.venv\Scripts\Activate.ps1  # Windows
# source .venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
cdk bootstrap
cdk deploy
```

## Configure Twilio

After deployment, you'll see two output URLs:

1. **WebSocketURL**: `wss://xxxx.execute-api.region.amazonaws.com/prod`
2. **TwiMLWebhookURL**: `https://xxxx.execute-api.region.amazonaws.com/prod/twiml`

### Set Up Your Twilio Phone Number

1. Go to [Twilio Console](https://console.twilio.com/)
2. Navigate to **Phone Numbers** → **Manage** → **Active Numbers**
3. Click on your +1 phone number
4. Under **Voice Configuration**:
   - Set **"A Call Comes In"** to **Webhook**
   - Paste the **TwiMLWebhookURL**
   - Set HTTP method to **POST**
5. Click **Save Configuration**

## How It Works

### 1. Incoming Call
When someone calls your Twilio number, Twilio sends a webhook to your TwiML Lambda.

### 2. TwiML Response
The TwiML Lambda returns XML instructions telling Twilio to:
- Play a greeting message
- Start streaming audio to your WebSocket URL

### 3. WebSocket Stream
Twilio opens a WebSocket connection and sends:
- **connected**: Initial handshake
- **start**: Stream metadata (call info, audio format)
- **media**: Audio chunks (base64 encoded μ-law, 8kHz, mono)
- **stop**: Stream ended

### 4. Audio Processing
The Lambda receives audio in ~20ms chunks. You can:
- Send to Amazon Transcribe for real-time STT
- Buffer and save to S3
- Forward to another service
- Process with custom audio analysis

## Audio Format

Twilio streams audio as:
- **Encoding**: μ-law (audio/x-mulaw)
- **Sample Rate**: 8000 Hz
- **Channels**: Mono (1 channel)
- **Chunk Duration**: ~20ms

## Extending the Lambda

Edit `twilio_stream/lambda_handler.py` to add custom audio processing:

```python
def handle_media(connection_id: str, message: dict):
    media_data = message.get("media", {})
    payload = media_data.get("payload", "")
    audio_bytes = base64.b64decode(payload)
    
    # Add your processing here:
    # - Send to Amazon Transcribe
    # - Forward to SageMaker endpoint
    # - Save to S3
    # - Send to external API
    
    return {"statusCode": 200, "body": "Media processed"}
```

## Monitoring

- **CloudWatch Logs**: Both Lambdas log to CloudWatch
- **DynamoDB**: Track active connections in `twilio-stream-connections` table
- **API Gateway**: View metrics in AWS Console

## Cleanup

```bash
cd infrastructure
cdk destroy
```

## Costs

- **API Gateway WebSocket**: $1.00 per million messages + $0.25 per million connection minutes
- **Lambda**: $0.20 per 1M requests + compute time
- **DynamoDB**: Pay-per-request pricing
- **S3**: Standard storage pricing

For typical usage (few calls/day), costs are minimal (< $1/month).


