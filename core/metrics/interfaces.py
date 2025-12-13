"""
Interfaces for Metrics Module.

Defines the protocols for metrics aggregation and export.
Storage interface is in core.memory.interfaces.IMetricsStore.

All implementations must be async-first for low-latency voice applications.
"""

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:
    from .spec import EvaluationResult, AggregatedMetrics, MetricSnapshot, ComparisonResult
    from .enum import EntityType, AggregationType

# Note: IMetricsStore is defined in core.memory.interfaces.metrics_store_interfaces
# Import it from core.memory for storage needs.


@runtime_checkable
class IMetricsAggregator(Protocol):
    """
    Interface for Metrics Aggregation.
    
    Computes aggregated statistics from raw evaluation results.
    Supports real-time aggregation for low-latency access.
    
    Example:
        aggregator = MetricsAggregator()
        
        # Compute aggregated metrics
        metrics = await aggregator.aggregate(results)
        
        # Compare two versions
        comparison = await aggregator.compare(
            results_a, results_b, score_key="relevance"
        )
    """
    
    async def aggregate(
        self,
        results: List['EvaluationResult'],
        percentiles: Optional[List[int]] = None,
    ) -> 'AggregatedMetrics':
        """
        Aggregate a list of evaluation results.
        
        Args:
            results: List of evaluation results
            percentiles: Percentiles to compute (default: [50, 90, 95, 99])
            
        Returns:
            AggregatedMetrics with computed statistics
        """
        ...
    
    async def compare(
        self,
        results_a: List['EvaluationResult'],
        results_b: List['EvaluationResult'],
        score_key: str,
        method: Optional['AggregationType'] = None,
    ) -> 'ComparisonResult':
        """
        Compare metrics between two sets of results.
        
        Args:
            results_a: First set of results
            results_b: Second set of results
            score_key: Score dimension to compare
            method: Aggregation method for comparison
            
        Returns:
            ComparisonResult indicating which is better
        """
        ...
    
    async def rank(
        self,
        entity_results: Dict[str, List['EvaluationResult']],
        score_key: str,
        method: Optional['AggregationType'] = None,
    ) -> List[tuple]:
        """
        Rank multiple entities by a score dimension.
        
        Args:
            entity_results: Map of entity_id to results
            score_key: Score dimension to rank by
            method: Aggregation method
            
        Returns:
            List of (entity_id, score) tuples, sorted best to worst
        """
        ...


@runtime_checkable
class IMetricsExporter(Protocol):
    """
    Interface for Metrics Export.
    
    Exports metrics in various formats for analysis and reporting.
    
    Example:
        exporter = JSONMetricsExporter()
        json_data = await exporter.export(metrics)
    """
    
    async def export(
        self,
        metrics: 'AggregatedMetrics',
        format: str = "json",
    ) -> Any:
        """
        Export aggregated metrics.
        
        Args:
            metrics: Metrics to export
            format: Export format ("json", "csv", "dict")
            
        Returns:
            Exported data in requested format
        """
        ...
    
    async def export_comparison(
        self,
        comparison: 'ComparisonResult',
        format: str = "json",
    ) -> Any:
        """
        Export comparison results.
        
        Args:
            comparison: Comparison to export
            format: Export format
            
        Returns:
            Exported data
        """
        ...

