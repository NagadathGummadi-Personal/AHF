"""
Workflow Module Constants

Defines string constants for the workflow module to maintain consistency
and enable easy refactoring.

Version: 1.0.0
"""

# =============================================================================
# WORKFLOW STATUS VALUES
# =============================================================================

STATUS_DRAFT = "draft"
STATUS_PUBLISHED = "published"
STATUS_ARCHIVED = "archived"
STATUS_PENDING_REVIEW = "pending_review"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"

# =============================================================================
# NODE TYPES
# =============================================================================

NODE_TYPE_AGENT = "agent"
NODE_TYPE_TOOL = "tool"
NODE_TYPE_PROMPT = "prompt"
NODE_TYPE_CUSTOM = "custom"
NODE_TYPE_START = "start"
NODE_TYPE_END = "end"
NODE_TYPE_DECISION = "decision"
NODE_TYPE_PARALLEL = "parallel"
NODE_TYPE_MERGE = "merge"

# =============================================================================
# EDGE TYPES
# =============================================================================

EDGE_TYPE_DEFAULT = "default"
EDGE_TYPE_CONDITIONAL = "conditional"
EDGE_TYPE_ERROR = "error"
EDGE_TYPE_TIMEOUT = "timeout"
EDGE_TYPE_FALLBACK = "fallback"

# =============================================================================
# EDGE CONDITION TYPES
# =============================================================================

EDGE_CONDITION_TYPE_EXPRESSION = "expression"
EDGE_CONDITION_TYPE_DYNAMIC = "dynamic"
EDGE_CONDITION_TYPE_LLM = "llm"
EDGE_CONDITION_TYPE_FUNCTION = "function"

# =============================================================================
# IO TYPES
# =============================================================================

IO_TYPE_TEXT = "text"
IO_TYPE_SPEECH = "speech"
IO_TYPE_JSON = "json"
IO_TYPE_IMAGE = "image"
IO_TYPE_AUDIO = "audio"
IO_TYPE_VIDEO = "video"
IO_TYPE_BINARY = "binary"
IO_TYPE_STRUCTURED = "structured"
IO_TYPE_STREAM = "stream"
IO_TYPE_ANY = "any"

# =============================================================================
# IO FORMATS
# =============================================================================

FORMAT_PLAIN = "plain"
FORMAT_MARKDOWN = "markdown"
FORMAT_HTML = "html"
FORMAT_JSON_SCHEMA = "json_schema"
FORMAT_PYDANTIC = "pydantic"

# =============================================================================
# PROMPT PRECEDENCE
# =============================================================================

PROMPT_PRECEDENCE_AGENT = "agent"
PROMPT_PRECEDENCE_USER = "user"
PROMPT_PRECEDENCE_MERGE = "merge"
PROMPT_PRECEDENCE_REPLACE = "replace"

# =============================================================================
# PROMPT MERGE STRATEGIES
# =============================================================================

PROMPT_MERGE_APPEND = "append"
PROMPT_MERGE_PREPEND = "prepend"
PROMPT_MERGE_INTERLEAVE = "interleave"

# =============================================================================
# EXECUTION STATES
# =============================================================================

EXEC_STATE_IDLE = "idle"
EXEC_STATE_RUNNING = "running"
EXEC_STATE_PAUSED = "paused"
EXEC_STATE_COMPLETED = "completed"
EXEC_STATE_FAILED = "failed"
EXEC_STATE_CANCELLED = "cancelled"
EXEC_STATE_TIMEOUT = "timeout"

# =============================================================================
# BACKGROUND AGENT MODES
# =============================================================================

BG_MODE_MONITOR = "monitor"
BG_MODE_ACTIVE = "active"
BG_MODE_SILENT = "silent"

# =============================================================================
# CONDITION OPERATORS
# =============================================================================

COND_OP_EQUALS = "equals"
COND_OP_NOT_EQUALS = "not_equals"
COND_OP_GREATER_THAN = "greater_than"
COND_OP_LESS_THAN = "less_than"
COND_OP_GREATER_THAN_OR_EQUALS = "greater_than_or_equals"
COND_OP_LESS_THAN_OR_EQUALS = "less_than_or_equals"
COND_OP_CONTAINS = "contains"
COND_OP_NOT_CONTAINS = "not_contains"
COND_OP_STARTS_WITH = "starts_with"
COND_OP_ENDS_WITH = "ends_with"
COND_OP_MATCHES = "matches"
COND_OP_IN = "in"
COND_OP_NOT_IN = "not_in"
COND_OP_IS_NULL = "is_null"
COND_OP_IS_NOT_NULL = "is_not_null"
COND_OP_IS_EMPTY = "is_empty"
COND_OP_IS_NOT_EMPTY = "is_not_empty"
COND_OP_CUSTOM = "custom"

# =============================================================================
# CONDITION JOIN OPERATORS
# =============================================================================

COND_JOIN_AND = "and"
COND_JOIN_OR = "or"

# =============================================================================
# STORAGE DEFAULTS
# =============================================================================

DEFAULT_WORKFLOWS_DIR = ".workflows"
DEFAULT_NODES_DIR = ".nodes"
DEFAULT_EDGES_DIR = ".edges"
FILE_EXT_JSON = ".json"
FILE_EXT_YAML = ".yaml"

# =============================================================================
# MODEL CONFIG KEYS
# =============================================================================

ARBITRARY_TYPES_ALLOWED = "arbitrary_types_allowed"
POPULATE_BY_NAME = "populate_by_name"

# =============================================================================
# ERROR MESSAGES
# =============================================================================

ERROR_VERSION_EXISTS = "Version {version} already exists for {entity_type} '{id}'"
ERROR_IMMUTABLE_VERSION = "Cannot modify published version {version}"
ERROR_INVALID_CONDITION = "Invalid edge condition: {condition}"
ERROR_INPUT_TYPE_MISMATCH = "Input type mismatch: expected {expected}, got {actual}"
ERROR_FORMATTER_NOT_FOUND = "No formatter found for conversion from {source} to {target}"
ERROR_NODE_NOT_FOUND = "Node '{node_id}' not found in workflow"
ERROR_EDGE_NOT_FOUND = "Edge '{edge_id}' not found in workflow"
ERROR_NO_START_NODE = "Workflow must have exactly one start node"
ERROR_MULTIPLE_START_NODES = "Workflow cannot have multiple start nodes"
ERROR_CYCLE_DETECTED = "Cycle detected in workflow at node '{node_id}'"
ERROR_DISCONNECTED_NODES = "Workflow has disconnected nodes: {nodes}"
ERROR_PASS_THROUGH_EXTRACTION_FAILED = "Failed to extract pass-through field '{field}': {error}"
ERROR_LLM_CONDITION_EVALUATION_FAILED = "LLM condition evaluation failed: {error}"

# =============================================================================
# PASS-THROUGH FIELD EXTRACTION STRATEGIES
# =============================================================================

EXTRACT_STRATEGY_CONTEXT = "context"  # Look in workflow context
EXTRACT_STRATEGY_LLM = "llm"  # Use LLM to extract from conversation
EXTRACT_STRATEGY_ASK_USER = "ask_user"  # Ask user for the value

# =============================================================================
# LLM CONDITION EVALUATION MODES
# =============================================================================

LLM_EVAL_MODE_BINARY = "binary"  # Yes/No evaluation
LLM_EVAL_MODE_SCORE = "score"  # Score-based evaluation (0.0-1.0)
LLM_EVAL_MODE_CLASSIFICATION = "classification"  # Classify into categories
