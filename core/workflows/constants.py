"""
Workflow Module Constants

Version: 1.0.0
"""

# =============================================================================
# WORKFLOW CONSTANTS
# =============================================================================

# Type identifiers
WORKFLOW = "workflow"
NODE = "node"
EDGE = "edge"

# Workflow status
STATUS_DRAFT = "draft"
STATUS_PUBLISHED = "published"
STATUS_ARCHIVED = "archived"
STATUS_PENDING_REVIEW = "pending_review"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"

# Node types
NODE_TYPE_AGENT = "agent"
NODE_TYPE_TOOL = "tool"
NODE_TYPE_PROMPT = "prompt"
NODE_TYPE_CUSTOM = "custom"
NODE_TYPE_START = "start"
NODE_TYPE_END = "end"
NODE_TYPE_DECISION = "decision"
NODE_TYPE_PARALLEL = "parallel"
NODE_TYPE_MERGE = "merge"

# Edge types
EDGE_TYPE_DEFAULT = "default"
EDGE_TYPE_CONDITIONAL = "conditional"
EDGE_TYPE_ERROR = "error"
EDGE_TYPE_TIMEOUT = "timeout"
EDGE_TYPE_FALLBACK = "fallback"

# =============================================================================
# INPUT/OUTPUT TYPE CONSTANTS
# =============================================================================

# Input/Output types
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

# Format identifiers
FORMAT_PLAIN = "plain"
FORMAT_MARKDOWN = "markdown"
FORMAT_HTML = "html"
FORMAT_JSON_SCHEMA = "json_schema"
FORMAT_PYDANTIC = "pydantic"

# =============================================================================
# PROMPT CONFIGURATION CONSTANTS
# =============================================================================

# Prompt precedence levels
PROMPT_PRECEDENCE_AGENT = "agent"  # Agent prompt takes priority
PROMPT_PRECEDENCE_USER = "user"  # User additional prompt takes priority
PROMPT_PRECEDENCE_MERGE = "merge"  # Merge both prompts
PROMPT_PRECEDENCE_REPLACE = "replace"  # User prompt replaces agent prompt

# Prompt merge strategies
PROMPT_MERGE_APPEND = "append"  # Append user prompt after agent prompt
PROMPT_MERGE_PREPEND = "prepend"  # Prepend user prompt before agent prompt
PROMPT_MERGE_INTERLEAVE = "interleave"  # Custom interleaving based on markers

# =============================================================================
# EXECUTION CONSTANTS
# =============================================================================

# Execution states
EXEC_STATE_IDLE = "idle"
EXEC_STATE_RUNNING = "running"
EXEC_STATE_PAUSED = "paused"
EXEC_STATE_COMPLETED = "completed"
EXEC_STATE_FAILED = "failed"
EXEC_STATE_CANCELLED = "cancelled"
EXEC_STATE_TIMEOUT = "timeout"

# Background agent modes
BG_MODE_MONITOR = "monitor"  # Passive monitoring
BG_MODE_ACTIVE = "active"  # Can take actions
BG_MODE_SILENT = "silent"  # Run without user awareness

# =============================================================================
# STORAGE CONSTANTS
# =============================================================================

# File extensions
FILE_EXT_JSON = ".json"
FILE_EXT_YAML = ".yaml"
FILE_EXT_YML = ".yml"

# Default directories
DEFAULT_WORKFLOWS_DIR = ".workflows"
DEFAULT_NODES_DIR = ".workflows/nodes"
DEFAULT_EDGES_DIR = ".workflows/edges"

# =============================================================================
# CONDITION CONSTANTS
# =============================================================================

# Condition operators
COND_OP_EQUALS = "equals"
COND_OP_NOT_EQUALS = "not_equals"
COND_OP_GREATER_THAN = "greater_than"
COND_OP_LESS_THAN = "less_than"
COND_OP_GREATER_THAN_OR_EQUALS = "gte"
COND_OP_LESS_THAN_OR_EQUALS = "lte"
COND_OP_CONTAINS = "contains"
COND_OP_NOT_CONTAINS = "not_contains"
COND_OP_STARTS_WITH = "starts_with"
COND_OP_ENDS_WITH = "ends_with"
COND_OP_MATCHES = "matches"  # Regex match
COND_OP_IN = "in"
COND_OP_NOT_IN = "not_in"
COND_OP_IS_NULL = "is_null"
COND_OP_IS_NOT_NULL = "is_not_null"
COND_OP_IS_EMPTY = "is_empty"
COND_OP_IS_NOT_EMPTY = "is_not_empty"
COND_OP_CUSTOM = "custom"  # Custom function evaluation

# Condition join operators
COND_JOIN_AND = "and"
COND_JOIN_OR = "or"

# =============================================================================
# ERROR MESSAGES
# =============================================================================

ERROR_NODE_NOT_FOUND = "Node not found: {node_id}"
ERROR_EDGE_NOT_FOUND = "Edge not found: {edge_id}"
ERROR_WORKFLOW_NOT_FOUND = "Workflow not found: {workflow_id}"
ERROR_INVALID_NODE_TYPE = "Invalid node type: {node_type}"
ERROR_INVALID_EDGE_TYPE = "Invalid edge type: {edge_type}"
ERROR_INPUT_TYPE_MISMATCH = "Input type mismatch: expected {expected}, got {actual}. No formatter configured."
ERROR_OUTPUT_TYPE_MISMATCH = "Output type mismatch: expected {expected}, got {actual}. No formatter configured."
ERROR_FORMATTER_NOT_FOUND = "No formatter found for conversion: {from_type} -> {to_type}"
ERROR_CYCLE_DETECTED = "Cycle detected in workflow"
ERROR_NO_START_NODE = "Workflow has no start node"
ERROR_MULTIPLE_START_NODES = "Workflow has multiple start nodes"
ERROR_DISCONNECTED_NODES = "Workflow has disconnected nodes: {nodes}"
ERROR_INVALID_CONDITION = "Invalid edge condition: {condition}"
ERROR_VERSION_EXISTS = "Version {version} already exists for {entity_type}: {id}"
ERROR_IMMUTABLE_VERSION = "Cannot modify immutable version: {version}"

# =============================================================================
# PYDANTIC CONFIG KEYS
# =============================================================================

ARBITRARY_TYPES_ALLOWED = "arbitrary_types_allowed"
POPULATE_BY_NAME = "populate_by_name"
VALIDATE_ASSIGNMENT = "validate_assignment"
