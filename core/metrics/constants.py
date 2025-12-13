"""
Constants for Metrics Module.

Defines metric types, score keys, entity types, and configuration defaults.
"""

# =============================================================================
# METRIC TYPES
# =============================================================================

METRIC_TYPE_LLM_EVAL = "llm_eval"
METRIC_TYPE_HUMAN_EVAL = "human_eval"
METRIC_TYPE_RUNTIME = "runtime"
METRIC_TYPE_CUSTOM = "custom"

# =============================================================================
# EVALUATOR TYPES
# =============================================================================

EVALUATOR_LLM = "llm"
EVALUATOR_HUMAN = "human"
EVALUATOR_RULE = "rule"
EVALUATOR_SEMANTIC = "semantic"

# =============================================================================
# SCORE KEYS (Standard evaluation dimensions)
# =============================================================================

# LLM Evaluation Scores
SCORE_RELEVANCE = "relevance"
SCORE_COHERENCE = "coherence"
SCORE_HELPFULNESS = "helpfulness"
SCORE_SAFETY = "safety"
SCORE_ACCURACY = "accuracy"
SCORE_FLUENCY = "fluency"
SCORE_GROUNDEDNESS = "groundedness"

# Runtime Scores
SCORE_LATENCY_MS = "latency_ms"
SCORE_TOKEN_COUNT = "token_count"
SCORE_PROMPT_TOKENS = "prompt_tokens"
SCORE_COMPLETION_TOKENS = "completion_tokens"
SCORE_COST_USD = "cost_usd"
SCORE_SUCCESS_RATE = "success_rate"

# Human Evaluation Scores
SCORE_HUMAN_RATING = "human_rating"
SCORE_HUMAN_PREFERENCE = "human_preference"

# All standard score keys
STANDARD_LLM_SCORES = [
    SCORE_RELEVANCE,
    SCORE_COHERENCE,
    SCORE_HELPFULNESS,
    SCORE_SAFETY,
    SCORE_ACCURACY,
    SCORE_FLUENCY,
    SCORE_GROUNDEDNESS,
]

STANDARD_RUNTIME_SCORES = [
    SCORE_LATENCY_MS,
    SCORE_TOKEN_COUNT,
    SCORE_PROMPT_TOKENS,
    SCORE_COMPLETION_TOKENS,
    SCORE_COST_USD,
    SCORE_SUCCESS_RATE,
]

# =============================================================================
# ENTITY TYPES (What is being evaluated)
# =============================================================================

ENTITY_TYPE_PROMPT = "prompt"
ENTITY_TYPE_AGENT = "agent"
ENTITY_TYPE_TOOL = "tool"
ENTITY_TYPE_LLM = "llm"
ENTITY_TYPE_WORKFLOW = "workflow"
ENTITY_TYPE_NODE = "node"

# =============================================================================
# AGGREGATION
# =============================================================================

# Default percentiles to compute
DEFAULT_PERCENTILES = [50, 90, 95, 99]

# Maximum samples to keep per metric for percentile computation
MAX_SAMPLES_PER_METRIC = 1000

# Minimum samples required for meaningful aggregation
MIN_SAMPLES_FOR_AGGREGATION = 5

# =============================================================================
# SCORE RANGES
# =============================================================================

MIN_SCORE = 0.0
MAX_SCORE = 1.0
DEFAULT_SCORE = None

# Human rating scale (1-5 stars typically)
MIN_HUMAN_RATING = 1
MAX_HUMAN_RATING = 5

# =============================================================================
# STORAGE
# =============================================================================

DEFAULT_METRICS_TTL_DAYS = 30
MAX_METRICS_TTL_DAYS = 365

# DynamoDB table name
DEFAULT_METRICS_TABLE = "ahf_metrics"

# =============================================================================
# COMPARISON
# =============================================================================

# Ranking methods
RANK_BY_AVG = "average"
RANK_BY_MEDIAN = "median"
RANK_BY_P95 = "p95"

DEFAULT_RANK_METHOD = RANK_BY_AVG

# Comparison result codes
COMPARISON_BETTER = "better"
COMPARISON_WORSE = "worse"
COMPARISON_EQUAL = "equal"
COMPARISON_INSUFFICIENT_DATA = "insufficient_data"

# Minimum difference threshold for comparison (percentage)
COMPARISON_THRESHOLD = 0.05  # 5%

# =============================================================================
# LOG MESSAGES
# =============================================================================

LOG_METRIC_RECORDED = "Metric recorded: {entity_type}/{entity_id}"
LOG_AGGREGATION_COMPUTED = "Aggregation computed for {entity_id}"
LOG_COMPARISON_RESULT = "Comparison {entity_a} vs {entity_b}: {result}"

