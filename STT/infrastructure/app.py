#!/usr/bin/env python3
"""
AWS CDK App for Twilio Real-Time Audio Streaming.

Two stacks available:
1. TwilioStreamStack - Lambda-based (batched transcription at call end)
2. RealtimeSTTStack - Fargate-based (true real-time transcription)

Deploy with:
  cdk deploy RealtimeSTTStack --context elevenlabs_api_key=YOUR_KEY
"""

import aws_cdk as cdk
from stacks.twilio_stream_stack import TwilioStreamStack
from stacks.realtime_stack import RealtimeSTTStack


app = cdk.App()

# Lambda-based stack (original)
TwilioStreamStack(
    app,
    "TwilioStreamStack",
    description="Twilio Audio Streaming with Lambda (batch transcription)",
)

# Fargate-based stack (true real-time)
RealtimeSTTStack(
    app,
    "RealtimeSTTStack",
    description="Twilio Real-Time STT with ECS Fargate",
)

app.synth()

