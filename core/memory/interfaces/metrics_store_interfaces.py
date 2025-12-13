"""
Metrics Store Interfaces.

Defines the protocols for metrics storage used by evaluators and the metrics module.
Follows the same patterns as ICheckpointer for consistency.

Version: 1.0.0
"""

from __future__ import annotations
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Protocol,
    runtime_checkable,
)


@runtime_checkable
class IMetricsStore(Protocol):
    """
    Interface for Metrics Storage.
    
    Provides async storage and retrieval of evaluation metrics.
    Implementations should be thread-safe and optimized for high-throughput.
    
    This interface supports both in-memory and persistent (DynamoDB) storage.
    
    Usage:
        store = InMemoryMetricsStore()
        
        # Record a metric
        await store.record(
            entity_id="prompt-123",
            entity_type="prompt",
            metric_type="evaluation",
            scores={"relevance": 0.95, "coherence": 0.88},
            metadata={"evaluator": "llm", "model": "gpt-4"}
        )
        
        # Get metrics for an entity
        metrics = await store.get_metrics("prompt-123")
    """
    
    async def record(
        self,
        entity_id: str,
        entity_type: str,
        metric_type: str,
        scores: Dict[str, float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Record a metric entry.
        
        Args:
            entity_id: ID of the entity being measured
            entity_type: Type of entity (prompt, agent, tool, llm)
            metric_type: Type of metric (evaluation, runtime, custom)
            scores: Score values by dimension
            metadata: Additional context
            
        Returns:
            ID of the stored metric entry
        """
        ...
    
    async def get_metrics(
        self,
        entity_id: str,
        entity_type: Optional[str] = None,
        metric_type: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get metrics for an entity.
        
        Args:
            entity_id: ID of the entity
            entity_type: Optional filter by entity type
            metric_type: Optional filter by metric type
            limit: Maximum number of results
            
        Returns:
            List of metric entries, newest first
        """
        ...
    
    async def get_aggregated(
        self,
        entity_id: str,
        entity_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get aggregated metrics for an entity.
        
        Args:
            entity_id: ID of the entity
            entity_type: Optional filter by entity type
            
        Returns:
            Aggregated metrics with averages, percentiles, etc.
        """
        ...
    
    async def delete_metrics(
        self,
        entity_id: str,
        older_than_days: Optional[int] = None,
    ) -> int:
        """
        Delete metrics for an entity.
        
        Args:
            entity_id: ID of the entity
            older_than_days: Only delete metrics older than N days
            
        Returns:
            Number of deleted entries
        """
        ...
    
    async def list_entities(
        self,
        entity_type: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[str]:
        """
        List all entity IDs with recorded metrics.
        
        Args:
            entity_type: Optional filter by entity type
            limit: Maximum number to return
            
        Returns:
            List of entity IDs
        """
        ...
    
    async def clear(self) -> None:
        """Clear all stored metrics."""
        ...

