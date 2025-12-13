"""
Metrics Data Models.

Defines the core data structures for storing and aggregating evaluation metrics.
Optimized for low-latency access and efficient aggregation.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
import math

from pydantic import BaseModel, Field

from ..constants import (
    DEFAULT_PERCENTILES,
    MAX_SAMPLES_PER_METRIC,
    MIN_SAMPLES_FOR_AGGREGATION,
    COMPARISON_THRESHOLD,
)
from ..enum import MetricType, EvaluatorType, EntityType, AggregationType


class ScoreDistribution(BaseModel):
    """
    Distribution of scores for a single dimension.
    
    Maintains samples for percentile computation and running statistics.
    """
    
    samples: List[float] = Field(default_factory=list, description="Score samples")
    count: int = Field(default=0, description="Total count of samples")
    sum: float = Field(default=0.0, description="Sum for average computation")
    min_value: Optional[float] = Field(default=None, description="Minimum observed value")
    max_value: Optional[float] = Field(default=None, description="Maximum observed value")
    
    def add_sample(self, value: float) -> None:
        """Add a sample to the distribution."""
        self.samples.append(value)
        self.count += 1
        self.sum += value
        
        if self.min_value is None or value < self.min_value:
            self.min_value = value
        if self.max_value is None or value > self.max_value:
            self.max_value = value
        
        # Trim samples if over limit (keep most recent)
        if len(self.samples) > MAX_SAMPLES_PER_METRIC:
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
    
    @property
    def median(self) -> Optional[float]:
        """Compute median (p50)."""
        return self.percentile(50)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with computed stats."""
        return {
            "count": self.count,
            "mean": self.mean,
            "min": self.min_value,
            "max": self.max_value,
            "median": self.median,
            "p90": self.percentile(90),
            "p95": self.percentile(95),
            "p99": self.percentile(99),
        }


class EvaluationResult(BaseModel):
    """
    A single evaluation result.
    
    Captures the output of an evaluator (LLM, human, or rule-based)
    for a specific entity at a specific time.
    
    Example:
        result = EvaluationResult(
            entity_id="prompt-abc123",
            entity_type=EntityType.PROMPT,
            evaluator_type=EvaluatorType.LLM,
            scores={"relevance": 0.95, "coherence": 0.88},
            metadata={"model": "gpt-4", "prompt_version": "1.0.0"}
        )
    """
    
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique result ID"
    )
    entity_id: str = Field(description="ID of the entity being evaluated")
    entity_type: EntityType = Field(
        default=EntityType.PROMPT,
        description="Type of entity"
    )
    version: Optional[str] = Field(
        default=None,
        description="Version of the entity (for version comparison)"
    )
    evaluator_type: EvaluatorType = Field(
        default=EvaluatorType.LLM,
        description="Type of evaluator"
    )
    evaluator_id: Optional[str] = Field(
        default=None,
        description="ID of the specific evaluator (e.g., human user ID)"
    )
    metric_type: MetricType = Field(
        default=MetricType.LLM_EVAL,
        description="Type of metric"
    )
    scores: Dict[str, float] = Field(
        default_factory=dict,
        description="Score values by dimension"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context"
    )
    input_data: Optional[str] = Field(
        default=None,
        description="The input that was evaluated"
    )
    output_data: Optional[str] = Field(
        default=None,
        description="The output that was evaluated"
    )
    expected_output: Optional[str] = Field(
        default=None,
        description="Expected output for comparison"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the evaluation occurred"
    )
    
    def get_score(self, key: str, default: float = 0.0) -> float:
        """Get a specific score value."""
        return self.scores.get(key, default)
    
    def set_score(self, key: str, value: float) -> None:
        """Set a score value."""
        self.scores[key] = value


class MetricEntry(BaseModel):
    """
    A metric entry for a specific entity and score dimension.
    
    Tracks running statistics and samples for a single score key.
    """
    
    entity_id: str = Field(description="Entity ID")
    entity_type: EntityType = Field(description="Entity type")
    score_key: str = Field(description="Score dimension key")
    distribution: ScoreDistribution = Field(
        default_factory=ScoreDistribution,
        description="Score distribution"
    )
    last_updated: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update time"
    )
    
    def add_value(self, value: float) -> None:
        """Add a value to this metric."""
        self.distribution.add_sample(value)
        self.last_updated = datetime.utcnow()


class AggregatedMetrics(BaseModel):
    """
    Aggregated metrics for an entity.
    
    Combines all evaluation results into summary statistics
    for each score dimension.
    
    Example:
        metrics = AggregatedMetrics(
            entity_id="prompt-123",
            entity_type=EntityType.PROMPT,
            total_evaluations=100,
            avg_scores={"relevance": 0.92, "coherence": 0.88},
            percentiles={"relevance": {"p50": 0.92, "p95": 0.98}}
        )
    """
    
    entity_id: str = Field(description="Entity ID")
    entity_type: EntityType = Field(
        default=EntityType.PROMPT,
        description="Entity type"
    )
    version: Optional[str] = Field(
        default=None,
        description="Entity version"
    )
    total_evaluations: int = Field(
        default=0,
        description="Total number of evaluations"
    )
    evaluations_by_type: Dict[str, int] = Field(
        default_factory=dict,
        description="Count by evaluator type"
    )
    avg_scores: Dict[str, float] = Field(
        default_factory=dict,
        description="Average scores by dimension"
    )
    min_scores: Dict[str, float] = Field(
        default_factory=dict,
        description="Minimum scores by dimension"
    )
    max_scores: Dict[str, float] = Field(
        default_factory=dict,
        description="Maximum scores by dimension"
    )
    percentiles: Dict[str, Dict[str, float]] = Field(
        default_factory=dict,
        description="Percentiles by dimension {dim: {p50: x, p95: y}}"
    )
    score_distributions: Dict[str, ScoreDistribution] = Field(
        default_factory=dict,
        description="Full distributions by dimension"
    )
    comparison_rank: Optional[int] = Field(
        default=None,
        description="Rank among versions (1 = best)"
    )
    first_evaluation: Optional[datetime] = Field(
        default=None,
        description="First evaluation timestamp"
    )
    last_evaluation: Optional[datetime] = Field(
        default=None,
        description="Last evaluation timestamp"
    )
    
    def get_avg_score(self, key: str, default: float = 0.0) -> float:
        """Get average score for a dimension."""
        return self.avg_scores.get(key, default)
    
    def get_percentile(self, key: str, percentile: int, default: float = 0.0) -> float:
        """Get percentile for a dimension."""
        dim_percentiles = self.percentiles.get(key, {})
        return dim_percentiles.get(f"p{percentile}", default)
    
    def is_better_than(
        self,
        other: 'AggregatedMetrics',
        score_key: str,
        method: AggregationType = AggregationType.AVERAGE,
    ) -> bool:
        """
        Compare if this entity's metrics are better than another.
        
        Args:
            other: Other metrics to compare
            score_key: Dimension to compare
            method: How to aggregate for comparison
            
        Returns:
            True if this is better (higher score)
        """
        if method == AggregationType.AVERAGE:
            self_score = self.avg_scores.get(score_key, 0.0)
            other_score = other.avg_scores.get(score_key, 0.0)
        elif method == AggregationType.MEDIAN:
            self_score = self.get_percentile(score_key, 50)
            other_score = other.get_percentile(score_key, 50)
        elif method == AggregationType.P95:
            self_score = self.get_percentile(score_key, 95)
            other_score = other.get_percentile(score_key, 95)
        else:
            self_score = self.avg_scores.get(score_key, 0.0)
            other_score = other.avg_scores.get(score_key, 0.0)
        
        # Account for threshold
        diff = self_score - other_score
        return diff > (other_score * COMPARISON_THRESHOLD)


class MetricSnapshot(BaseModel):
    """
    Point-in-time snapshot of all metrics for an entity.
    
    Used for exporting and comparing metrics across time.
    """
    
    entity_id: str = Field(description="Entity ID")
    entity_type: EntityType = Field(description="Entity type")
    version: Optional[str] = Field(default=None, description="Entity version")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Snapshot time"
    )
    aggregated: AggregatedMetrics = Field(description="Aggregated metrics")
    recent_results: List[EvaluationResult] = Field(
        default_factory=list,
        description="Recent raw results"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional snapshot metadata"
    )


class ComparisonResult(BaseModel):
    """
    Result of comparing two entities' metrics.
    
    Provides detailed breakdown of which is better by each dimension.
    """
    
    entity_a_id: str = Field(description="First entity ID")
    entity_b_id: str = Field(description="Second entity ID")
    score_key: str = Field(description="Dimension compared")
    method: AggregationType = Field(
        default=AggregationType.AVERAGE,
        description="Comparison method"
    )
    entity_a_score: float = Field(description="Entity A's score")
    entity_b_score: float = Field(description="Entity B's score")
    difference: float = Field(description="Score difference (A - B)")
    difference_pct: float = Field(description="Percentage difference")
    winner: Optional[str] = Field(
        default=None,
        description="ID of the better entity (None if equal)"
    )
    is_significant: bool = Field(
        default=False,
        description="Whether difference exceeds threshold"
    )
    entity_a_sample_count: int = Field(default=0, description="Samples for A")
    entity_b_sample_count: int = Field(default=0, description="Samples for B")
    sufficient_data: bool = Field(
        default=True,
        description="Whether both have enough samples"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Comparison time"
    )
    
    @classmethod
    def from_scores(
        cls,
        entity_a_id: str,
        entity_b_id: str,
        score_key: str,
        score_a: float,
        score_b: float,
        count_a: int,
        count_b: int,
        method: AggregationType = AggregationType.AVERAGE,
    ) -> 'ComparisonResult':
        """Create a comparison result from scores."""
        difference = score_a - score_b
        diff_pct = (difference / score_b * 100) if score_b != 0 else 0.0
        is_significant = abs(diff_pct) > (COMPARISON_THRESHOLD * 100)
        sufficient = count_a >= MIN_SAMPLES_FOR_AGGREGATION and count_b >= MIN_SAMPLES_FOR_AGGREGATION
        
        winner = None
        if is_significant and sufficient:
            winner = entity_a_id if difference > 0 else entity_b_id
        
        return cls(
            entity_a_id=entity_a_id,
            entity_b_id=entity_b_id,
            score_key=score_key,
            method=method,
            entity_a_score=score_a,
            entity_b_score=score_b,
            difference=difference,
            difference_pct=diff_pct,
            winner=winner,
            is_significant=is_significant,
            entity_a_sample_count=count_a,
            entity_b_sample_count=count_b,
            sufficient_data=sufficient,
        )

