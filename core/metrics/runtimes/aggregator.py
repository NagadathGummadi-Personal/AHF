"""
Metrics Aggregator.

Provides functions for aggregating evaluation results and comparing entities.
Designed for real-time computation with low latency.
"""

from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from ..interfaces import IMetricsAggregator
from ..spec import (
    EvaluationResult,
    AggregatedMetrics,
    ComparisonResult,
    ScoreDistribution,
)
from ..enum import EntityType, AggregationType
from ..constants import (
    DEFAULT_PERCENTILES,
    MIN_SAMPLES_FOR_AGGREGATION,
    COMPARISON_THRESHOLD,
)


class MetricsAggregator(IMetricsAggregator):
    """
    Aggregates evaluation results into summary statistics.
    
    Supports:
    - Average, min, max, percentile computation
    - Entity comparison
    - Ranking multiple entities
    
    Usage:
        aggregator = MetricsAggregator()
        
        # Aggregate results
        metrics = await aggregator.aggregate(results)
        
        # Compare two entities
        comparison = await aggregator.compare(
            results_a, results_b, "relevance"
        )
    """
    
    async def aggregate(
        self,
        results: List[EvaluationResult],
        percentiles: Optional[List[int]] = None,
    ) -> AggregatedMetrics:
        """Aggregate a list of evaluation results."""
        if not results:
            return AggregatedMetrics(
                entity_id="",
                entity_type=EntityType.PROMPT,
            )
        
        percentiles = percentiles or DEFAULT_PERCENTILES
        
        # Get entity info from first result
        entity_id = results[0].entity_id
        entity_type = results[0].entity_type
        version = results[0].version
        
        # Build distributions
        distributions: Dict[str, ScoreDistribution] = defaultdict(ScoreDistribution)
        evaluations_by_type: Dict[str, int] = defaultdict(int)
        
        for result in results:
            for key, value in result.scores.items():
                distributions[key].add_sample(value)
            evaluations_by_type[result.evaluator_type.value] += 1
        
        # Compute aggregates
        avg_scores = {}
        min_scores = {}
        max_scores = {}
        pct_data = {}
        
        for key, dist in distributions.items():
            if dist.count > 0:
                avg_scores[key] = dist.mean
                min_scores[key] = dist.min_value
                max_scores[key] = dist.max_value
                pct_data[key] = {
                    f"p{p}": dist.percentile(p)
                    for p in percentiles
                    if dist.percentile(p) is not None
                }
        
        # Timestamps
        timestamps = [r.timestamp for r in results]
        first_eval = min(timestamps) if timestamps else None
        last_eval = max(timestamps) if timestamps else None
        
        return AggregatedMetrics(
            entity_id=entity_id,
            entity_type=entity_type,
            version=version,
            total_evaluations=len(results),
            evaluations_by_type=dict(evaluations_by_type),
            avg_scores=avg_scores,
            min_scores=min_scores,
            max_scores=max_scores,
            percentiles=pct_data,
            score_distributions={k: v for k, v in distributions.items()},
            first_evaluation=first_eval,
            last_evaluation=last_eval,
        )
    
    async def compare(
        self,
        results_a: List[EvaluationResult],
        results_b: List[EvaluationResult],
        score_key: str,
        method: Optional[AggregationType] = None,
    ) -> ComparisonResult:
        """Compare metrics between two sets of results."""
        method = method or AggregationType.AVERAGE
        
        # Aggregate both
        metrics_a = await self.aggregate(results_a)
        metrics_b = await self.aggregate(results_b)
        
        # Get scores based on method
        if method == AggregationType.AVERAGE:
            score_a = metrics_a.avg_scores.get(score_key, 0.0)
            score_b = metrics_b.avg_scores.get(score_key, 0.0)
        elif method == AggregationType.MEDIAN:
            score_a = metrics_a.get_percentile(score_key, 50)
            score_b = metrics_b.get_percentile(score_key, 50)
        elif method == AggregationType.P95:
            score_a = metrics_a.get_percentile(score_key, 95)
            score_b = metrics_b.get_percentile(score_key, 95)
        else:
            score_a = metrics_a.avg_scores.get(score_key, 0.0)
            score_b = metrics_b.avg_scores.get(score_key, 0.0)
        
        return ComparisonResult.from_scores(
            entity_a_id=metrics_a.entity_id,
            entity_b_id=metrics_b.entity_id,
            score_key=score_key,
            score_a=score_a,
            score_b=score_b,
            count_a=metrics_a.total_evaluations,
            count_b=metrics_b.total_evaluations,
            method=method,
        )
    
    async def rank(
        self,
        entity_results: Dict[str, List[EvaluationResult]],
        score_key: str,
        method: Optional[AggregationType] = None,
    ) -> List[Tuple[str, float]]:
        """Rank multiple entities by a score dimension."""
        method = method or AggregationType.AVERAGE
        
        scores = []
        for entity_id, results in entity_results.items():
            if not results:
                continue
            
            metrics = await self.aggregate(results)
            
            if method == AggregationType.AVERAGE:
                score = metrics.avg_scores.get(score_key, 0.0)
            elif method == AggregationType.MEDIAN:
                score = metrics.get_percentile(score_key, 50)
            elif method == AggregationType.P95:
                score = metrics.get_percentile(score_key, 95)
            else:
                score = metrics.avg_scores.get(score_key, 0.0)
            
            scores.append((entity_id, score))
        
        # Sort descending (higher is better)
        scores.sort(key=lambda x: x[1], reverse=True)
        
        return scores
    
    async def compare_versions(
        self,
        all_results: List[EvaluationResult],
        score_key: str,
        method: Optional[AggregationType] = None,
    ) -> List[Tuple[str, float, int]]:
        """
        Compare different versions of the same entity.
        
        Args:
            all_results: Results across all versions
            score_key: Dimension to compare
            method: Aggregation method
            
        Returns:
            List of (version, score, rank) tuples
        """
        method = method or AggregationType.AVERAGE
        
        # Group by version
        by_version: Dict[str, List[EvaluationResult]] = defaultdict(list)
        for result in all_results:
            version = result.version or "unknown"
            by_version[version].append(result)
        
        # Rank versions
        ranked = await self.rank(by_version, score_key, method)
        
        # Add rank numbers
        result = []
        for rank, (version, score) in enumerate(ranked, 1):
            result.append((version, score, rank))
        
        return result

