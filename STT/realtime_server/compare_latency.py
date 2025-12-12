#!/usr/bin/env python3
"""
Latency Comparison Tool for STT Providers.

This script collects and analyzes latency metrics from transcription events.
Run this alongside the main server to get aggregated latency statistics.

Usage:
    python compare_latency.py --help
    python compare_latency.py analyze     # Analyze collected metrics
    python compare_latency.py clear       # Clear collected metrics
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Optional
from statistics import mean, median, stdev


@dataclass
class LatencyMetric:
    """Single latency measurement."""
    provider: str
    event_type: str  # "partial" or "final"
    wall_clock_ms: int
    audio_ms: int
    latency_ms: int
    text: str
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class ProviderStats:
    """Aggregated stats for a provider."""
    provider: str
    total_events: int
    partial_count: int
    final_count: int
    
    # Partial latency stats
    partial_latency_min: float = 0
    partial_latency_max: float = 0
    partial_latency_mean: float = 0
    partial_latency_median: float = 0
    partial_latency_stdev: float = 0
    
    # Final latency stats
    final_latency_min: float = 0
    final_latency_max: float = 0
    final_latency_mean: float = 0
    final_latency_median: float = 0
    final_latency_stdev: float = 0


class LatencyCollector:
    """Collects and analyzes latency metrics."""
    
    def __init__(self, data_file: str = "latency_data.json"):
        self.data_file = Path(__file__).parent / data_file
        self.metrics: List[LatencyMetric] = []
        self._load()
    
    def _load(self):
        """Load existing metrics from file."""
        if self.data_file.exists():
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    self.metrics = [LatencyMetric(**m) for m in data]
            except Exception as e:
                print(f"Warning: Could not load metrics: {e}")
                self.metrics = []
    
    def _save(self):
        """Save metrics to file."""
        with open(self.data_file, 'w') as f:
            json.dump([asdict(m) for m in self.metrics], f, indent=2)
    
    def add_metric(self, metric: LatencyMetric):
        """Add a new metric."""
        self.metrics.append(metric)
        self._save()
    
    def clear(self):
        """Clear all metrics."""
        self.metrics = []
        if self.data_file.exists():
            self.data_file.unlink()
        print("✓ Cleared all latency metrics")
    
    def get_provider_stats(self, provider: str) -> Optional[ProviderStats]:
        """Calculate stats for a single provider."""
        provider_metrics = [m for m in self.metrics if m.provider == provider]
        if not provider_metrics:
            return None
        
        partial_latencies = [m.latency_ms for m in provider_metrics if m.event_type == "partial"]
        final_latencies = [m.latency_ms for m in provider_metrics if m.event_type == "final"]
        
        stats = ProviderStats(
            provider=provider,
            total_events=len(provider_metrics),
            partial_count=len(partial_latencies),
            final_count=len(final_latencies),
        )
        
        if partial_latencies:
            stats.partial_latency_min = min(partial_latencies)
            stats.partial_latency_max = max(partial_latencies)
            stats.partial_latency_mean = mean(partial_latencies)
            stats.partial_latency_median = median(partial_latencies)
            if len(partial_latencies) > 1:
                stats.partial_latency_stdev = stdev(partial_latencies)
        
        if final_latencies:
            stats.final_latency_min = min(final_latencies)
            stats.final_latency_max = max(final_latencies)
            stats.final_latency_mean = mean(final_latencies)
            stats.final_latency_median = median(final_latencies)
            if len(final_latencies) > 1:
                stats.final_latency_stdev = stdev(final_latencies)
        
        return stats
    
    def analyze(self) -> Dict[str, ProviderStats]:
        """Analyze all metrics by provider."""
        providers = set(m.provider for m in self.metrics)
        return {p: self.get_provider_stats(p) for p in providers if self.get_provider_stats(p)}
    
    def print_report(self):
        """Print a formatted latency comparison report."""
        if not self.metrics:
            print("\n❌ No latency metrics collected yet.")
            print("   Run the server and make some test calls first.")
            return
        
        stats = self.analyze()
        
        print("\n" + "=" * 70)
        print("📊 STT LATENCY COMPARISON REPORT")
        print("=" * 70)
        print(f"   Total measurements: {len(self.metrics)}")
        print(f"   Providers tested: {', '.join(stats.keys())}")
        print(f"   Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Sort providers by mean final latency
        sorted_providers = sorted(
            stats.values(),
            key=lambda s: s.final_latency_mean if s.final_latency_mean else float('inf')
        )
        
        print("\n" + "-" * 70)
        print("FINAL TRANSCRIPTION LATENCY (lower is better)")
        print("-" * 70)
        print(f"{'Provider':<15} {'Count':>6} {'Min':>8} {'Max':>8} {'Mean':>8} {'Median':>8} {'StdDev':>8}")
        print("-" * 70)
        
        for s in sorted_providers:
            if s.final_count > 0:
                print(f"{s.provider:<15} {s.final_count:>6} {s.final_latency_min:>7.0f}ms {s.final_latency_max:>7.0f}ms {s.final_latency_mean:>7.0f}ms {s.final_latency_median:>7.0f}ms {s.final_latency_stdev:>7.0f}ms")
        
        print("\n" + "-" * 70)
        print("PARTIAL/INTERIM TRANSCRIPTION LATENCY")
        print("-" * 70)
        print(f"{'Provider':<15} {'Count':>6} {'Min':>8} {'Max':>8} {'Mean':>8} {'Median':>8} {'StdDev':>8}")
        print("-" * 70)
        
        for s in sorted_providers:
            if s.partial_count > 0:
                print(f"{s.provider:<15} {s.partial_count:>6} {s.partial_latency_min:>7.0f}ms {s.partial_latency_max:>7.0f}ms {s.partial_latency_mean:>7.0f}ms {s.partial_latency_median:>7.0f}ms {s.partial_latency_stdev:>7.0f}ms")
        
        print("\n" + "=" * 70)
        
        # Winner
        if len(sorted_providers) > 1 and sorted_providers[0].final_count > 0:
            winner = sorted_providers[0]
            runner_up = sorted_providers[1] if len(sorted_providers) > 1 and sorted_providers[1].final_count > 0 else None
            
            print(f"\n🏆 WINNER: {winner.provider.upper()}")
            print(f"   Average final latency: {winner.final_latency_mean:.0f}ms")
            
            if runner_up and runner_up.final_latency_mean > 0:
                improvement = ((runner_up.final_latency_mean - winner.final_latency_mean) / runner_up.final_latency_mean) * 100
                print(f"   {improvement:.1f}% faster than {runner_up.provider}")
        
        print("\n")


def main():
    parser = argparse.ArgumentParser(description="STT Latency Comparison Tool")
    parser.add_argument("command", choices=["analyze", "clear", "status"], 
                        help="Command to run")
    args = parser.parse_args()
    
    collector = LatencyCollector()
    
    if args.command == "analyze":
        collector.print_report()
    elif args.command == "clear":
        collector.clear()
    elif args.command == "status":
        print(f"\n📊 Latency Collector Status")
        print(f"   Data file: {collector.data_file}")
        print(f"   Total metrics: {len(collector.metrics)}")
        
        providers = set(m.provider for m in collector.metrics)
        for provider in providers:
            count = len([m for m in collector.metrics if m.provider == provider])
            print(f"   - {provider}: {count} measurements")


if __name__ == "__main__":
    main()

