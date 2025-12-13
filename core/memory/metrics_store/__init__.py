"""
Metrics Store implementations.

Provides storage backends for evaluation metrics:
- InMemoryMetricsStore: Fast in-memory storage (low-latency, non-persistent)
- DynamoDBMetricsStore: Persistent storage with DynamoDB and local fallback

Usage:
    from core.memory import (
        InMemoryMetricsStore,
        DynamoDBMetricsStore,
        create_metrics_store,
    )
    
    # In-memory for low-latency
    store = InMemoryMetricsStore()
    
    # DynamoDB for persistence
    store = DynamoDBMetricsStore(table_name="ahf_metrics")
    
    # Factory function
    store = create_metrics_store(store_type="dynamodb")

Version: 1.0.0
"""

from .base_metrics_store import BaseMetricsStore
from .memory_store import InMemoryMetricsStore
from .dynamo_store import DynamoDBMetricsStore, create_metrics_store

__all__ = [
    "BaseMetricsStore",
    "InMemoryMetricsStore",
    "DynamoDBMetricsStore",
    "create_metrics_store",
]

