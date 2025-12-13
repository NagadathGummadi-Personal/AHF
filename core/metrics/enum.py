"""
Enumerations for Metrics Module.
"""

from enum import Enum
from .constants import (
    METRIC_TYPE_LLM_EVAL,
    METRIC_TYPE_HUMAN_EVAL,
    METRIC_TYPE_RUNTIME,
    METRIC_TYPE_CUSTOM,
    EVALUATOR_LLM,
    EVALUATOR_HUMAN,
    EVALUATOR_RULE,
    EVALUATOR_SEMANTIC,
    ENTITY_TYPE_PROMPT,
    ENTITY_TYPE_AGENT,
    ENTITY_TYPE_TOOL,
    ENTITY_TYPE_LLM,
    ENTITY_TYPE_WORKFLOW,
    ENTITY_TYPE_NODE,
    RANK_BY_AVG,
    RANK_BY_MEDIAN,
    RANK_BY_P95,
)


class MetricType(str, Enum):
    """Type of metric being recorded."""
    LLM_EVAL = METRIC_TYPE_LLM_EVAL
    HUMAN_EVAL = METRIC_TYPE_HUMAN_EVAL
    RUNTIME = METRIC_TYPE_RUNTIME
    CUSTOM = METRIC_TYPE_CUSTOM


class EvaluatorType(str, Enum):
    """Type of evaluator that produced the metric."""
    LLM = EVALUATOR_LLM
    HUMAN = EVALUATOR_HUMAN
    RULE = EVALUATOR_RULE
    SEMANTIC = EVALUATOR_SEMANTIC


class EntityType(str, Enum):
    """Type of entity being evaluated."""
    PROMPT = ENTITY_TYPE_PROMPT
    AGENT = ENTITY_TYPE_AGENT
    TOOL = ENTITY_TYPE_TOOL
    LLM = ENTITY_TYPE_LLM
    WORKFLOW = ENTITY_TYPE_WORKFLOW
    NODE = ENTITY_TYPE_NODE


class AggregationType(str, Enum):
    """How to aggregate scores for ranking."""
    AVERAGE = RANK_BY_AVG
    MEDIAN = RANK_BY_MEDIAN
    P95 = RANK_BY_P95


class ComparisonResult(str, Enum):
    """Result of comparing two entities."""
    BETTER = "better"
    WORSE = "worse"
    EQUAL = "equal"
    INSUFFICIENT_DATA = "insufficient_data"

