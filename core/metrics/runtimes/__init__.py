"""
Runtime implementations for Metrics Module.

Storage is now delegated to core.memory.metrics_store for consistent
persistence patterns across the framework.

This module provides:
- MetricsAggregator: Aggregation and comparison utilities
- Factory functions for getting the global metrics store
"""

from .aggregator import MetricsAggregator
from .factory import (
    get_metrics_store,
    shutdown_metrics_store,
    reset_metrics_store,
)

__all__ = [
    "MetricsAggregator",
    "get_metrics_store",
    "shutdown_metrics_store",
    "reset_metrics_store",
]

