"""
Constants for Prompt Registry Subsystem.
"""

# ============================================================================
# STORAGE
# ============================================================================

DEFAULT_STORAGE_PATH = ".prompts"
STORAGE_FORMAT_JSON = "json"
STORAGE_FORMAT_YAML = "yaml"
DEFAULT_STORAGE_FORMAT = STORAGE_FORMAT_JSON

# File extensions
JSON_EXTENSION = ".json"
YAML_EXTENSION = ".yaml"
YML_EXTENSION = ".yml"

# ============================================================================
# VERSIONING
# ============================================================================

DEFAULT_VERSION = "1.0.0"
LATEST_VERSION = "latest"
VERSION_SEPARATOR = "."

# ============================================================================
# ENVIRONMENTS
# ============================================================================

ENV_PROD = "prod"
ENV_STAGING = "staging"
ENV_DEV = "dev"
ENV_TEST = "test"
DEFAULT_ENVIRONMENT = ENV_PROD

# Environment priority (higher = preferred)
ENV_PRIORITY = {
    ENV_PROD: 100,
    ENV_STAGING: 50,
    ENV_DEV: 20,
    ENV_TEST: 10,
}

# ============================================================================
# PROMPT TYPES
# ============================================================================

PROMPT_TYPE_SYSTEM = "system"
PROMPT_TYPE_USER = "user"

# ============================================================================
# PROMPT STRUCTURE
# ============================================================================

FIELD_LABEL = "label"
FIELD_CONTENT = "content"
FIELD_VERSION = "version"
FIELD_MODEL = "model"
FIELD_MODEL_TARGET = "model_target"
FIELD_TAGS = "tags"
FIELD_METRICS = "metrics"
FIELD_METADATA = "metadata"
FIELD_VERSIONS = "versions"
FIELD_CREATED_AT = "created_at"
FIELD_UPDATED_AT = "updated_at"
FIELD_STATUS = "status"
FIELD_CATEGORY = "category"
FIELD_ENVIRONMENT = "environment"
FIELD_PROMPT_TYPE = "prompt_type"
FIELD_DYNAMIC_VARIABLES = "dynamic_variables"
FIELD_RESPONSE_FORMAT = "response_format"
FIELD_LLM_EVAL_SCORE = "llm_eval_score"
FIELD_HUMAN_EVAL_SCORE = "human_eval_score"

# Default model target
DEFAULT_MODEL = "default"

# ============================================================================
# METRIC NAMES
# ============================================================================

METRIC_ACCURACY = "accuracy"
METRIC_RELEVANCE = "relevance"
METRIC_FLUENCY = "fluency"
METRIC_CONSISTENCY = "consistency"
METRIC_LATENCY_MS = "latency_ms"
METRIC_TOKEN_COUNT = "token_count"
METRIC_USAGE_COUNT = "usage_count"
METRIC_SUCCESS_RATE = "success_rate"
METRIC_COST = "cost"
METRIC_AVG_LATENCY_MS = "avg_latency_ms"
METRIC_AVG_TOKEN_COUNT = "avg_token_count"
METRIC_AVG_COST = "avg_cost"
METRIC_PROMPT_TOKENS = "prompt_tokens"
METRIC_COMPLETION_TOKENS = "completion_tokens"
METRIC_TOTAL_TOKENS = "total_tokens"

# ============================================================================
# EVAL SCORE RANGES
# ============================================================================

MIN_EVAL_SCORE = 0.0
MAX_EVAL_SCORE = 1.0
DEFAULT_EVAL_SCORE = None

# ============================================================================
# STATUS VALUES
# ============================================================================

STATUS_DRAFT = "draft"
STATUS_ACTIVE = "active"
STATUS_DEPRECATED = "deprecated"
STATUS_ARCHIVED = "archived"

# ============================================================================
# CATEGORY VALUES
# ============================================================================

CATEGORY_SYSTEM = "system"
CATEGORY_USER = "user"
CATEGORY_ASSISTANT = "assistant"
CATEGORY_FUNCTION = "function"
CATEGORY_TOOL = "tool"
CATEGORY_TEMPLATE = "template"
CATEGORY_EXAMPLE = "example"

# ============================================================================
# DYNAMIC VARIABLE PATTERNS
# ============================================================================

# Pattern for extracting {variable_name} from templates
VARIABLE_PATTERN = r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}'

# ============================================================================
# CONDITIONAL PATTERNS
# ============================================================================

# Pattern for conditional blocks: {# if condition #}, {# elif condition #}, etc.
CONDITIONAL_PATTERN = r'\{#\s*(if|elif|else|endif)(?:\s+(.+?))?\s*#\}'

# Conditional keywords
CONDITIONAL_IF = "if"
CONDITIONAL_ELIF = "elif"
CONDITIONAL_ELSE = "else"
CONDITIONAL_ENDIF = "endif"

# Conditional operators
CONDITIONAL_OPERATORS = ['==', '!=', '>=', '<=', '>', '<', 'and', 'or', 'not', 'in', 'not in']

# ============================================================================
# AGENT PROMPT LABELS
# ============================================================================

# Built-in agent prompt labels
PROMPT_LABEL_REACT_AGENT = "agent.react.system"
PROMPT_LABEL_GOAL_BASED_PLANNING = "agent.goal_based.planning"
PROMPT_LABEL_GOAL_BASED_EXECUTION = "agent.goal_based.execution"
PROMPT_LABEL_GOAL_BASED_FINAL = "agent.goal_based.final"
PROMPT_LABEL_HIERARCHICAL_MANAGER = "agent.hierarchical.manager"

# ============================================================================
# ERROR MESSAGES
# ============================================================================

ERROR_PROMPT_NOT_FOUND = "Prompt not found: {label}"
ERROR_VERSION_NOT_FOUND = "Version not found: {label}@{version}"
ERROR_INVALID_LABEL = "Invalid prompt label: {label}"
ERROR_INVALID_VERSION = "Invalid version format: {version}"
ERROR_STORAGE_ERROR = "Storage error: {error}"
ERROR_DUPLICATE_PROMPT = "Prompt already exists: {label}"
ERROR_IMMUTABLE_PROMPT = "Cannot modify existing prompt version: {label}@{version}. Create a new version instead."
ERROR_MISSING_VARIABLES = "Missing required dynamic variables: {variables}"
ERROR_NO_FALLBACK_FOUND = "No prompt found for {label} in any environment"

# ============================================================================
# LOG MESSAGES
# ============================================================================

LOG_PROMPT_SAVED = "Prompt saved: {label}@{version}"
LOG_PROMPT_LOADED = "Prompt loaded: {label}@{version}"
LOG_PROMPT_DELETED = "Prompt deleted: {label}"
LOG_METRICS_UPDATED = "Metrics updated: {prompt_id}"
LOG_VERSION_CREATED = "New version created: {label}@{version}"
LOG_USAGE_RECORDED = "Usage recorded for prompt: {prompt_id}"
LOG_FALLBACK_USED = "Fallback used for {label}: {from_env} -> {to_env}"

# ============================================================================
# ENCODING
# ============================================================================

UTF_8 = "utf-8"

