#!/usr/bin/env python3
"""
Local development runner with ngrok integration.
Starts the STT server and creates an ngrok tunnel for Twilio testing.

Usage:
    python run_local.py                    # Start server only (port 8000)
    python run_local.py --ngrok            # Start server + ngrok tunnel
    python run_local.py --port 8080        # Use custom port
    python run_local.py --provider deepgram # Set default provider
"""

import os
import sys
import subprocess
import asyncio
import argparse
import signal
from pathlib import Path
from typing import Optional

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✓ Loaded environment from {env_path}")
except ImportError:
    pass


def check_api_keys():
    """Check if required API keys are configured."""
    providers = {
        "elevenlabs": "ELEVENLABS_API_KEY",
        "assemblyai": "ASSEMBLYAI_API_KEY",
        "deepgram": "DEEPGRAM_API_KEY",
    }
    
    print("\n📋 API Key Status:")
    print("-" * 40)
    
    available = []
    for provider, env_var in providers.items():
        key = os.getenv(env_var, "")
        if key:
            masked = key[:8] + "..." + key[-4:] if len(key) > 12 else "***"
            print(f"  ✓ {provider:12s} : {masked}")
            available.append(provider)
        else:
            print(f"  ✗ {provider:12s} : NOT SET ({env_var})")
    
    print("-" * 40)
    return available


def start_ngrok(port: int, ngrok_path: str = "ngrok") -> Optional[subprocess.Popen]:
    """Start ngrok tunnel."""
    try:
        # Try to find ngrok
        ngrok_exe = Path(__file__).parent.parent / "ngrok.exe"
        if ngrok_exe.exists():
            ngrok_path = str(ngrok_exe)
        
        print(f"\n🚀 Starting ngrok tunnel on port {port}...")
        
        # Start ngrok
        process = subprocess.Popen(
            [ngrok_path, "http", str(port), "--log=stdout"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait a bit for ngrok to start
        import time
        time.sleep(2)
        
        # Get the public URL from ngrok API
        try:
            import urllib.request
            import json
            
            with urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels") as response:
                data = json.loads(response.read())
                tunnels = data.get("tunnels", [])
                
                for tunnel in tunnels:
                    if tunnel.get("proto") == "https":
                        public_url = tunnel.get("public_url")
                        print(f"\n✓ ngrok tunnel established!")
                        print(f"  Public URL: {public_url}")
                        return process, public_url
        except Exception as e:
            print(f"  ⚠ Could not get ngrok URL from API: {e}")
            print(f"  Check http://127.0.0.1:4040 for the public URL")
            return process, None
            
    except FileNotFoundError:
        print(f"  ✗ ngrok not found at: {ngrok_path}")
        print(f"    Download from: https://ngrok.com/download")
        return None, None
    except Exception as e:
        print(f"  ✗ Failed to start ngrok: {e}")
        return None, None


def print_twilio_instructions(host: str, default_provider: str, available_providers: list):
    """Print instructions for configuring Twilio."""
    print("\n" + "=" * 60)
    print("📞 TWILIO CONFIGURATION")
    print("=" * 60)
    
    print(f"\n1. Go to: https://console.twilio.com/")
    print(f"2. Navigate to: Phone Numbers → Active Numbers")
    print(f"3. Select your phone number")
    print(f"4. Under 'Voice Configuration', set 'A Call Comes In' to:")
    
    print("\n" + "=" * 60)
    print("🔬 COMPARISON MODE (RECOMMENDED)")
    print("=" * 60)
    print(f"\n   POST {host}/twiml/compare")
    print(f"\n   This sends your audio to ALL providers simultaneously!")
    print(f"   You'll see a real-time side-by-side latency comparison.")
    
    print("\n" + "-" * 60)
    print("📡 SINGLE PROVIDER MODE")
    print("-" * 60)
    for provider in available_providers:
        print(f"   POST {host}/twiml/{provider}")
    
    print("\n" + "=" * 60)
    print("🎤 HOW IT WORKS")
    print("=" * 60)
    print(f"""
In COMPARISON MODE (/twiml/compare):

1. Call your Twilio number
2. Speak normally
3. Watch the console - you'll see output like:

   [  1234ms] DEEPGRA  | PARTIAL | "Hello" | Latency: 134ms
   [  1256ms] ELEVENL  | PARTIAL | "Hello" | Latency: 156ms
   [  1312ms] ASSEMBL  | PARTIAL | "Hello" | Latency: 212ms
   ...
   [  2500ms] DEEPGRA  | FINAL   | "Hello world" | Latency: 200ms
   [  2650ms] ELEVENL  | FINAL   | "Hello world" | Latency: 350ms

4. At the end, you'll see a summary table:

   Provider     | Partials | Avg     | Finals | Avg     | 1st Partial
   -------------|----------|---------|--------|---------|------------
   deepgram     |       15 |  140ms  |      3 |  200ms  |     1234ms
   elevenlabs   |       12 |  180ms  |      3 |  350ms  |     1256ms
   assemblyai   |       10 |  250ms  |      3 |  420ms  |     1312ms

   🏆 WINNER: DEEPGRAM (150ms faster than elevenlabs)
""")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Run STT server locally with optional ngrok tunnel")
    parser.add_argument("--port", type=int, default=8000, help="Port to run server on (default: 8000)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--ngrok", action="store_true", help="Start ngrok tunnel")
    parser.add_argument("--provider", type=str, default="elevenlabs", 
                        choices=["elevenlabs", "assemblyai", "deepgram"],
                        help="Default STT provider (default: elevenlabs)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    args = parser.parse_args()
    
    # Set default provider
    os.environ["STT_PROVIDER"] = args.provider
    
    # Check API keys
    available = check_api_keys()
    
    if not available:
        print("\n❌ No API keys configured! Set at least one of:")
        print("   - ELEVENLABS_API_KEY")
        print("   - ASSEMBLYAI_API_KEY")
        print("   - DEEPGRAM_API_KEY")
        print("\nYou can create a .env file in the project root with these variables.")
        sys.exit(1)
    
    ngrok_process = None
    public_url = None
    
    if args.ngrok:
        result = start_ngrok(args.port)
        if result:
            ngrok_process, public_url = result
    
    # Determine the host URL
    if public_url:
        host = public_url
    else:
        host = f"http://localhost:{args.port}"
    
    # Print instructions
    print_twilio_instructions(host, args.provider, available)
    
    # Start the FastAPI server
    print(f"\n🚀 Starting STT server on {args.host}:{args.port}...")
    print(f"   Default provider: {args.provider}")
    print(f"   Press Ctrl+C to stop\n")
    
    try:
        import uvicorn
        uvicorn.run(
            "app:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down...")
    finally:
        if ngrok_process:
            print("   Stopping ngrok...")
            ngrok_process.terminate()
            ngrok_process.wait()
        print("   Done!")


if __name__ == "__main__":
    main()

