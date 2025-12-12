"""
Multi-Provider STT Adapter.
Sends the same audio stream to multiple STT providers simultaneously
for real-time latency comparison.
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Callable
from statistics import mean, median

from .base import STTAdapter, STTConfig, TranscriptResult, ms_since


@dataclass
class LatencyStats:
    """Latency statistics for a provider."""
    provider: str
    partial_latencies: List[int] = field(default_factory=list)
    final_latencies: List[int] = field(default_factory=list)
    first_partial_ms: Optional[int] = None
    first_final_ms: Optional[int] = None
    
    def add_partial(self, latency_ms: int, wall_clock_ms: int):
        self.partial_latencies.append(latency_ms)
        if self.first_partial_ms is None:
            self.first_partial_ms = wall_clock_ms
    
    def add_final(self, latency_ms: int, wall_clock_ms: int):
        self.final_latencies.append(latency_ms)
        if self.first_final_ms is None:
            self.first_final_ms = wall_clock_ms
    
    def summary(self) -> Dict:
        return {
            "provider": self.provider,
            "partial_count": len(self.partial_latencies),
            "final_count": len(self.final_latencies),
            "partial_avg_ms": int(mean(self.partial_latencies)) if self.partial_latencies else 0,
            "partial_median_ms": int(median(self.partial_latencies)) if self.partial_latencies else 0,
            "final_avg_ms": int(mean(self.final_latencies)) if self.final_latencies else 0,
            "final_median_ms": int(median(self.final_latencies)) if self.final_latencies else 0,
            "first_partial_ms": self.first_partial_ms,
            "first_final_ms": self.first_final_ms,
        }


class MultiProviderAdapter(STTAdapter):
    """
    Adapter that sends audio to multiple STT providers simultaneously.
    Collects and compares results in real-time.
    """
    
    def __init__(self, adapters: List[STTAdapter]):
        """
        Initialize with a list of STT adapters.
        
        Args:
            adapters: List of configured STT adapters to use in parallel.
        """
        # Use a dummy config for base class
        super().__init__(STTConfig())
        self.adapters = adapters
        self.stats: Dict[str, LatencyStats] = {}
        
        # Initialize stats for each provider
        for adapter in adapters:
            self.stats[adapter.provider_name] = LatencyStats(provider=adapter.provider_name)
        
        # Tracking
        self.audio_state = {"chunks": 0, "audio_ms": 0}
        self.last_transcripts: Dict[str, str] = {}
    
    @property
    def provider_name(self) -> str:
        return "multi_provider"
    
    def _create_transcript_handler(self, provider_name: str) -> Callable[[TranscriptResult], None]:
        """Create a transcript handler for a specific provider."""
        def handler(result: TranscriptResult):
            audio_sent_ms = self.audio_state.get("audio_ms", 0)
            latency = result.received_at_ms - audio_sent_ms
            
            stats = self.stats[provider_name]
            
            if result.is_final:
                stats.add_final(latency, result.received_at_ms)
                self._print_comparison("FINAL", provider_name, result.text, latency, result.received_at_ms)
                self.last_transcripts[provider_name] = ""
            else:
                stats.add_partial(latency, result.received_at_ms)
                # Show incremental text
                last = self.last_transcripts.get(provider_name, "")
                new_text = result.text[len(last):].strip() if result.text.startswith(last) else result.text
                self.last_transcripts[provider_name] = result.text
                self._print_comparison("PARTIAL", provider_name, new_text, latency, result.received_at_ms)
            
            # Call the original callback if set
            if self.on_transcript:
                # Add provider info to the result
                result.raw_response["_provider"] = provider_name
                result.raw_response["_latency_ms"] = latency
                self.on_transcript(result)
        
        return handler
    
    def _print_comparison(self, event_type: str, provider: str, text: str, latency: int, wall_clock_ms: int):
        """Print a comparison line with color coding for the provider."""
        # ANSI color codes for different providers
        colors = {
            "elevenlabs": "\033[95m",  # Magenta
            "assemblyai": "\033[94m",  # Blue
            "deepgram": "\033[92m",    # Green
        }
        reset = "\033[0m"
        
        color = colors.get(provider, "")
        provider_short = provider[:8].upper().ljust(8)
        
        if text:
            print(f"[{wall_clock_ms:6d}ms] {color}{provider_short}{reset} | {event_type:7s} | \"{text}\" | Latency: {latency}ms")
    
    async def connect(self, context: Optional[dict] = None) -> bool:
        """Connect all adapters in parallel."""
        self.session_start = time.time()
        
        print(f"\n{'='*70}")
        print(f"MULTI-PROVIDER COMPARISON MODE")
        print(f"{'='*70}")
        print(f"Connecting to {len(self.adapters)} providers simultaneously...")
        
        # Set up transcript handlers for each adapter
        for adapter in self.adapters:
            adapter.set_callbacks(
                on_transcript=self._create_transcript_handler(adapter.provider_name),
                on_error=lambda e, p=adapter.provider_name: print(f"[ERROR] {p}: {e}")
            )
        
        # Connect all adapters in parallel
        connect_tasks = [adapter.connect(context) for adapter in self.adapters]
        results = await asyncio.gather(*connect_tasks, return_exceptions=True)
        
        # Check results
        connected = []
        failed = []
        for adapter, result in zip(self.adapters, results):
            if isinstance(result, Exception):
                failed.append((adapter.provider_name, str(result)))
            elif result:
                connected.append(adapter.provider_name)
            else:
                failed.append((adapter.provider_name, "Connection failed"))
        
        print(f"\n{'─'*70}")
        print(f"Connected: {', '.join(connected) if connected else 'None'}")
        if failed:
            print(f"Failed: {', '.join([f'{p} ({e})' for p, e in failed])}")
        print(f"{'─'*70}")
        print(f"\n📊 Comparison started. Speak now!\n")
        print(f"{'─'*70}")
        print(f"{'Time':>8} | {'Provider':8} | {'Type':7} | Text | Latency")
        print(f"{'─'*70}")
        
        self.is_connected = len(connected) > 0
        
        if self.is_connected and self.on_connected:
            self.on_connected()
        
        return self.is_connected
    
    async def send_audio(self, audio_data: str) -> None:
        """Send audio to all connected adapters in parallel."""
        if not self.is_connected:
            return
        
        self.audio_state["chunks"] += 1
        self.audio_state["audio_ms"] = self.audio_state["chunks"] * 20
        
        # Send to all adapters in parallel
        send_tasks = []
        for adapter in self.adapters:
            if adapter.is_connected:
                send_tasks.append(adapter.send_audio(audio_data))
        
        if send_tasks:
            await asyncio.gather(*send_tasks, return_exceptions=True)
    
    async def start_receiving(self) -> None:
        """Start receiving from all adapters."""
        receive_tasks = []
        for adapter in self.adapters:
            if adapter.is_connected:
                receive_tasks.append(adapter.start_receiving())
        
        if receive_tasks:
            await asyncio.gather(*receive_tasks, return_exceptions=True)
    
    async def close(self) -> None:
        """Close all adapters and print summary."""
        # Close all adapters
        close_tasks = [adapter.close() for adapter in self.adapters]
        await asyncio.gather(*close_tasks, return_exceptions=True)
        
        self.is_connected = False
        
        # Print summary
        self._print_summary()
        
        if self.on_disconnected:
            self.on_disconnected()
    
    def _print_summary(self):
        """Print a latency comparison summary."""
        total_ms = ms_since(self.session_start)
        audio_ms = self.audio_state.get("audio_ms", 0)
        
        print(f"\n{'='*70}")
        print(f"📊 LATENCY COMPARISON SUMMARY")
        print(f"{'='*70}")
        print(f"Session duration: {total_ms}ms | Audio processed: {audio_ms}ms")
        print(f"{'─'*70}")
        
        # Collect all stats
        summaries = []
        for provider, stats in self.stats.items():
            s = stats.summary()
            if s["partial_count"] > 0 or s["final_count"] > 0:
                summaries.append(s)
        
        if not summaries:
            print("No transcriptions received from any provider.")
            return
        
        # Sort by final average latency (lower is better)
        summaries.sort(key=lambda x: x["final_avg_ms"] if x["final_avg_ms"] > 0 else float('inf'))
        
        # Print table header
        print(f"\n{'Provider':<12} | {'Partials':>8} | {'Avg':>7} | {'Finals':>6} | {'Avg':>7} | {'1st Partial':>11} | {'1st Final':>9}")
        print(f"{'─'*12}-+-{'─'*8}-+-{'─'*7}-+-{'─'*6}-+-{'─'*7}-+-{'─'*11}-+-{'─'*9}")
        
        for s in summaries:
            first_p = f"{s['first_partial_ms']}ms" if s['first_partial_ms'] else "N/A"
            first_f = f"{s['first_final_ms']}ms" if s['first_final_ms'] else "N/A"
            
            print(f"{s['provider']:<12} | {s['partial_count']:>8} | {s['partial_avg_ms']:>6}ms | {s['final_count']:>6} | {s['final_avg_ms']:>6}ms | {first_p:>11} | {first_f:>9}")
        
        print(f"{'─'*70}")
        
        # Winner announcement
        if len(summaries) > 1:
            # Find winner by average final latency
            valid = [s for s in summaries if s["final_avg_ms"] > 0]
            if valid:
                winner = valid[0]
                print(f"\n🏆 WINNER: {winner['provider'].upper()}")
                print(f"   Average final latency: {winner['final_avg_ms']}ms")
                
                if len(valid) > 1:
                    runner_up = valid[1]
                    diff = runner_up['final_avg_ms'] - winner['final_avg_ms']
                    pct = (diff / runner_up['final_avg_ms']) * 100 if runner_up['final_avg_ms'] > 0 else 0
                    print(f"   {diff}ms ({pct:.1f}%) faster than {runner_up['provider']}")
            
            # First response winner
            first_partials = [(s['provider'], s['first_partial_ms']) for s in summaries if s['first_partial_ms']]
            if first_partials:
                first_partials.sort(key=lambda x: x[1])
                fastest = first_partials[0]
                print(f"\n⚡ FASTEST FIRST RESPONSE: {fastest[0].upper()} ({fastest[1]}ms)")
        
        print(f"\n{'='*70}\n")

