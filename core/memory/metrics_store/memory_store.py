"""
In-Memory Metrics Store.

High-performance in-memory storage for metrics.
Optimized for low-latency voice applications.

Features:
- O(1) insert operations
- Pre-computed running aggregates
- LRU eviction for memory management
- No persistence (data lost on restart)

Version: 1.0.0
"""

from typing import Any, Dict, List, Optional

from .base_metrics_store import BaseMetricsStore


class InMemoryMetricsStore(BaseMetricsStore):
    """
    In-memory metrics store with no persistence.
    
    Ideal for:
    - Low-latency applications
    - Development and testing
    - Ephemeral metrics that don't need persistence
    
    Usage:
        store = InMemoryMetricsStore(cache_max_entries=10000)
        
        await store.record(
            entity_id="prompt-123",
            entity_type="prompt",
            metric_type="evaluation",
            scores={"relevance": 0.95}
        )
        
        metrics = await store.get_aggregated("prompt-123")
    """
    
    def __init__(
        self,
        cache_max_entries: int = 10000,
        max_samples_per_entity: int = 1000,
    ):
        """
        Initialize in-memory store.
        
        Args:
            cache_max_entries: Max entities to track
            max_samples_per_entity: Max samples per entity
        """
        super().__init__(
            cache_max_entries=cache_max_entries,
            max_samples_per_entity=max_samples_per_entity,
        )
    
    # No-op persistence methods (in-memory only)
    
    async def _persist_entry(self, entry: Dict[str, Any]) -> None:
        """No persistence for in-memory store."""
        pass
    
    async def _load_entries(self, entity_id: str) -> List[Dict[str, Any]]:
        """No persistence to load from."""
        return []
    
    async def _delete_persisted(
        self,
        entity_id: str,
        older_than_days: Optional[int] = None,
    ) -> None:
        """No persistence to delete from."""
        pass
    
    async def _clear_persisted(self) -> None:
        """No persistence to clear."""
        pass

