"""
Base Metrics Store Implementation.

Provides common functionality for metrics stores including:
- In-memory caching for fast reads
- Aggregation computation
- Score distribution tracking

Version: 1.0.0
"""

import math
import threading
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..interfaces import IMetricsStore


# Default percentiles to compute
DEFAULT_PERCENTILES = [50, 90, 95, 99]

# Maximum samples to keep per dimension for percentile computation
MAX_SAMPLES_PER_DIMENSION = 1000


class ScoreDistribution:
    """Tracks score distribution for a single dimension."""
    
    def __init__(self, max_samples: int = MAX_SAMPLES_PER_DIMENSION):
        self.samples: List[float] = []
        self.count: int = 0
        self.sum: float = 0.0
        self.min_value: Optional[float] = None
        self.max_value: Optional[float] = None
        self._max_samples = max_samples
    
    def add_sample(self, value: float) -> None:
        """Add a sample to the distribution."""
        self.samples.append(value)
        self.count += 1
        self.sum += value
        
        if self.min_value is None or value < self.min_value:
            self.min_value = value
        if self.max_value is None or value > self.max_value:
            self.max_value = value
        
        # Trim if over limit (keep most recent)
        if len(self.samples) > self._max_samples:
            removed = self.samples.pop(0)
            self.sum -= removed
    
    @property
    def mean(self) -> float:
        """Compute the mean of samples."""
        if self.count == 0:
            return 0.0
        return self.sum / self.count
    
    def percentile(self, p: int) -> Optional[float]:
        """Compute a percentile from samples."""
        if not self.samples:
            return None
        sorted_samples = sorted(self.samples)
        rank = math.ceil((p / 100) * len(sorted_samples))
        rank = max(1, min(rank, len(sorted_samples)))
        return sorted_samples[rank - 1]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with computed stats."""
        return {
            "count": self.count,
            "mean": self.mean,
            "min": self.min_value,
            "max": self.max_value,
            "p50": self.percentile(50),
            "p90": self.percentile(90),
            "p95": self.percentile(95),
            "p99": self.percentile(99),
        }


class BaseMetricsStore(ABC, IMetricsStore):
    """
    Base implementation for metrics stores.
    
    Provides:
    - In-memory caching for fast reads
    - Score distribution tracking
    - Aggregation computation
    
    Subclasses implement persistence methods.
    """
    
    def __init__(
        self,
        cache_max_entries: int = 10000,
        max_samples_per_entity: int = 1000,
    ):
        """
        Initialize the metrics store.
        
        Args:
            cache_max_entries: Max entries in memory cache
            max_samples_per_entity: Max samples to keep per entity
        """
        self._cache_max = cache_max_entries
        self._max_samples = max_samples_per_entity
        
        # In-memory storage: entity_id -> list of metric entries
        self._entries: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        
        # Score distributions: entity_id -> {score_key -> ScoreDistribution}
        self._distributions: Dict[str, Dict[str, ScoreDistribution]] = defaultdict(
            lambda: defaultdict(ScoreDistribution)
        )
        
        # Entity metadata
        self._entity_types: Dict[str, str] = {}
        
        # LRU tracking
        self._access_order: List[str] = []
        
        # Thread safety
        self._lock = threading.Lock()
    
    async def record(
        self,
        entity_id: str,
        entity_type: str,
        metric_type: str,
        scores: Dict[str, float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Record a metric entry."""
        entry_id = str(uuid.uuid4())
        
        entry = {
            "id": entry_id,
            "entity_id": entity_id,
            "entity_type": entity_type,
            "metric_type": metric_type,
            "scores": scores,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        with self._lock:
            # Update access order (LRU)
            if entity_id in self._access_order:
                self._access_order.remove(entity_id)
            self._access_order.append(entity_id)
            
            # Evict oldest if over limit
            while len(self._access_order) > self._cache_max:
                oldest = self._access_order.pop(0)
                self._entries.pop(oldest, None)
                self._distributions.pop(oldest, None)
                self._entity_types.pop(oldest, None)
            
            # Store entry
            self._entries[entity_id].append(entry)
            self._entity_types[entity_id] = entity_type
            
            # Trim if over limit
            if len(self._entries[entity_id]) > self._max_samples:
                self._entries[entity_id] = self._entries[entity_id][-self._max_samples:]
            
            # Update distributions
            for key, value in scores.items():
                self._distributions[entity_id][key].add_sample(value)
        
        # Persist if implemented
        await self._persist_entry(entry)
        
        return entry_id
    
    async def get_metrics(
        self,
        entity_id: str,
        entity_type: Optional[str] = None,
        metric_type: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get metrics for an entity."""
        # Try cache first
        with self._lock:
            entries = list(self._entries.get(entity_id, []))
        
        # Load from persistence if not in cache
        if not entries:
            entries = await self._load_entries(entity_id)
            if entries:
                with self._lock:
                    self._entries[entity_id] = entries
        
        # Filter
        if entity_type:
            entries = [e for e in entries if e.get("entity_type") == entity_type]
        if metric_type:
            entries = [e for e in entries if e.get("metric_type") == metric_type]
        
        # Sort by timestamp descending
        entries = sorted(entries, key=lambda e: e.get("timestamp", ""), reverse=True)
        
        if limit:
            entries = entries[:limit]
        
        return entries
    
    async def get_aggregated(
        self,
        entity_id: str,
        entity_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get aggregated metrics for an entity."""
        entries = await self.get_metrics(entity_id, entity_type)
        
        if not entries:
            return {
                "entity_id": entity_id,
                "entity_type": entity_type,
                "total_entries": 0,
                "avg_scores": {},
                "percentiles": {},
            }
        
        # Get or compute distributions
        with self._lock:
            distributions = self._distributions.get(entity_id, {})
        
        if not distributions:
            # Rebuild from entries
            distributions = defaultdict(ScoreDistribution)
            for entry in entries:
                for key, value in entry.get("scores", {}).items():
                    distributions[key].add_sample(value)
        
        avg_scores = {}
        min_scores = {}
        max_scores = {}
        percentiles = {}
        
        for key, dist in distributions.items():
            if dist.count > 0:
                avg_scores[key] = dist.mean
                min_scores[key] = dist.min_value
                max_scores[key] = dist.max_value
                percentiles[key] = {
                    f"p{p}": dist.percentile(p)
                    for p in DEFAULT_PERCENTILES
                    if dist.percentile(p) is not None
                }
        
        # Count by metric type
        by_type: Dict[str, int] = defaultdict(int)
        for entry in entries:
            by_type[entry.get("metric_type", "unknown")] += 1
        
        # Timestamps
        timestamps = [e.get("timestamp") for e in entries if e.get("timestamp")]
        
        return {
            "entity_id": entity_id,
            "entity_type": entity_type or self._entity_types.get(entity_id, "unknown"),
            "total_entries": len(entries),
            "entries_by_type": dict(by_type),
            "avg_scores": avg_scores,
            "min_scores": min_scores,
            "max_scores": max_scores,
            "percentiles": percentiles,
            "first_entry": min(timestamps) if timestamps else None,
            "last_entry": max(timestamps) if timestamps else None,
        }
    
    async def delete_metrics(
        self,
        entity_id: str,
        older_than_days: Optional[int] = None,
    ) -> int:
        """Delete metrics for an entity."""
        deleted = 0
        
        with self._lock:
            if entity_id not in self._entries:
                return 0
            
            original_count = len(self._entries[entity_id])
            
            if older_than_days is not None:
                from datetime import timedelta
                cutoff = (datetime.utcnow() - timedelta(days=older_than_days)).isoformat()
                
                self._entries[entity_id] = [
                    e for e in self._entries[entity_id]
                    if e.get("timestamp", "") >= cutoff
                ]
                deleted = original_count - len(self._entries[entity_id])
                
                # Rebuild distributions
                if deleted > 0:
                    self._rebuild_distributions(entity_id)
            else:
                # Delete all
                self._entries.pop(entity_id, None)
                self._distributions.pop(entity_id, None)
                self._entity_types.pop(entity_id, None)
                if entity_id in self._access_order:
                    self._access_order.remove(entity_id)
                deleted = original_count
        
        # Delete from persistence
        await self._delete_persisted(entity_id, older_than_days)
        
        return deleted
    
    async def list_entities(
        self,
        entity_type: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[str]:
        """List all entity IDs with recorded metrics."""
        with self._lock:
            entities = list(self._entries.keys())
            
            if entity_type:
                entities = [
                    e for e in entities
                    if self._entity_types.get(e) == entity_type
                ]
            
            if limit:
                entities = entities[:limit]
        
        return entities
    
    async def clear(self) -> None:
        """Clear all stored metrics."""
        with self._lock:
            self._entries.clear()
            self._distributions.clear()
            self._entity_types.clear()
            self._access_order.clear()
        
        await self._clear_persisted()
    
    def _rebuild_distributions(self, entity_id: str) -> None:
        """Rebuild distributions from entries (must hold lock)."""
        entries = self._entries.get(entity_id, [])
        
        new_distributions = defaultdict(ScoreDistribution)
        for entry in entries:
            for key, value in entry.get("scores", {}).items():
                new_distributions[key].add_sample(value)
        
        self._distributions[entity_id] = new_distributions
    
    # Abstract methods for persistence (subclasses implement)
    
    @abstractmethod
    async def _persist_entry(self, entry: Dict[str, Any]) -> None:
        """Persist a single entry (for DynamoDB, etc.)."""
        ...
    
    @abstractmethod
    async def _load_entries(self, entity_id: str) -> List[Dict[str, Any]]:
        """Load entries from persistence."""
        ...
    
    @abstractmethod
    async def _delete_persisted(
        self,
        entity_id: str,
        older_than_days: Optional[int] = None,
    ) -> None:
        """Delete from persistence."""
        ...
    
    @abstractmethod
    async def _clear_persisted(self) -> None:
        """Clear all persisted data."""
        ...

