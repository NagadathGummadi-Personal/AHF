"""
Metrics Module for AHF Framework.

Provides a centralized, reusable metrics system for tracking and aggregating
evaluation results across prompts, agents, tools, and LLMs.

This module provides high-level evaluation and comparison functionality,
while actual storage is delegated to core.memory.metrics_store for
consistent persistence patterns (in-memory and DynamoDB).

Features:
=========
- Async-first design for low-latency voice applications
- Storage via core.memory (in-memory or DynamoDB with local fallback)
- Real-time aggregation with percentiles
- Support for LLM and human evaluations
- Version comparison and ranking

Usage:
======
    from core.metrics import (
        EvaluationResult,
        MetricsAggregator,
        get_metrics_store,
    )
    
    # Get the metrics store (from core.memory)
    store = await get_metrics_store()
    
    # Record an evaluation
    await store.record(
        entity_id="prompt-123",
        entity_type="prompt",
        metric_type="evaluation",
        scores={"relevance": 0.95, "coherence": 0.88},
    )
    
    # Get aggregated metrics
    metrics = await store.get_aggregated("prompt-123")
    print(f"Average relevance: {metrics['avg_scores']['relevance']}")

Version: 1.1.0 - Now uses core.memory for storage
"""

from .constants import (
    # Metric types
    METRIC_TYPE_LLM_EVAL,
    METRIC_TYPE_HUMAN_EVAL,
    METRIC_TYPE_RUNTIME,
    # Score keys
    SCORE_RELEVANCE,
    SCORE_COHERENCE,
    SCORE_HELPFULNESS,
    SCORE_SAFETY,
    SCORE_ACCURACY,
    # Entity types
    ENTITY_TYPE_PROMPT,
    ENTITY_TYPE_AGENT,
    ENTITY_TYPE_TOOL,
    ENTITY_TYPE_LLM,
    # Defaults
    DEFAULT_PERCENTILES,
    MAX_SAMPLES_PER_METRIC,
)

from .enum import (
    MetricType,
    EvaluatorType,
    EntityType,
    AggregationType,
)

from .interfaces import (
    IMetricsAggregator,
    IMetricsExporter,
)

from .spec import (
    EvaluationResult,
    MetricEntry,
    AggregatedMetrics,
    MetricSnapshot,
    ComparisonResult,
)

from .runtimes import (
    MetricsAggregator,
    get_metrics_store,
    shutdown_metrics_store,
    reset_metrics_store,
)

# Re-export IMetricsStore from core.memory for convenience
from core.memory import IMetricsStore, InMemoryMetricsStore, DynamoDBMetricsStore

__all__ = [
    # Constants
    "METRIC_TYPE_LLM_EVAL",
    "METRIC_TYPE_HUMAN_EVAL",
    "METRIC_TYPE_RUNTIME",
    "SCORE_RELEVANCE",
    "SCORE_COHERENCE",
    "SCORE_HELPFULNESS",
    "SCORE_SAFETY",
    "SCORE_ACCURACY",
    "ENTITY_TYPE_PROMPT",
    "ENTITY_TYPE_AGENT",
    "ENTITY_TYPE_TOOL",
    "ENTITY_TYPE_LLM",
    "DEFAULT_PERCENTILES",
    "MAX_SAMPLES_PER_METRIC",
    # Enums
    "MetricType",
    "EvaluatorType",
    "EntityType",
    "AggregationType",
    # Interfaces
    "IMetricsStore",
    "IMetricsAggregator",
    "IMetricsExporter",
    # Models
    "EvaluationResult",
    "MetricEntry",
    "AggregatedMetrics",
    "MetricSnapshot",
    "ComparisonResult",
    # Storage (from core.memory)
    "InMemoryMetricsStore",
    "DynamoDBMetricsStore",
    # Runtimes
    "MetricsAggregator",
    "get_metrics_store",
    "shutdown_metrics_store",
    "reset_metrics_store",
]

