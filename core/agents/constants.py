"""
Constants for Agents Subsystem.

This module defines all constants used throughout the Agents subsystem including
log messages, configuration keys, defaults, and limits.
"""

# ============================================================================
# ENCODING & FORMAT
# ============================================================================

UTF_8 = "utf-8"
JSON_CONTENT_TYPE = "application/json"

# ============================================================================
# LOG MESSAGES
# ============================================================================

# Agent lifecycle
LOG_AGENT_INITIALIZING = "Initializing agent"
LOG_AGENT_STARTED = "Agent execution started"
LOG_AGENT_COMPLETED = "Agent execution completed"
LOG_AGENT_FAILED = "Agent execution failed"
LOG_AGENT_ITERATION = "Agent iteration"
LOG_AGENT_MAX_ITERATIONS = "Agent reached max iterations"
LOG_AGENT_STREAMING_STARTED = "Agent streaming started"
LOG_AGENT_STREAMING_CHUNK = "Received agent streaming chunk"
LOG_AGENT_STREAMING_COMPLETED = "Agent streaming completed"
LOG_AGENT_STREAMING_FAILED = "Agent streaming failed"

# Tool execution
LOG_TOOL_EXECUTION_STARTED = "Tool execution started"
LOG_TOOL_EXECUTION_COMPLETED = "Tool execution completed"
LOG_TOOL_EXECUTION_FAILED = "Tool execution failed"

# Memory operations
LOG_MEMORY_ADD = "Adding to agent memory"
LOG_MEMORY_GET = "Getting from agent memory"
LOG_MEMORY_CLEAR = "Clearing agent memory"

# Scratchpad operations
LOG_SCRATCHPAD_WRITE = "Writing to scratchpad"
LOG_SCRATCHPAD_READ = "Reading from scratchpad"
LOG_SCRATCHPAD_CLEAR = "Clearing scratchpad"

# Checklist operations
LOG_CHECKLIST_ADD = "Adding item to checklist"
LOG_CHECKLIST_UPDATE = "Updating checklist item status"
LOG_CHECKLIST_COMPLETE = "Checklist complete"

# LLM fallback
LOG_LLM_PRIMARY_FAILED = "Primary LLM failed, switching to backup"
LOG_LLM_BACKUP_SUCCESS = "Backup LLM succeeded"
LOG_LLM_BACKUP_FAILED = "Backup LLM also failed"

# ============================================================================
# ERROR MESSAGES
# ============================================================================

ERROR_NO_LLM = "No LLM configured for agent"
ERROR_NO_TOOLS = "No tools available for agent"
ERROR_MAX_ITERATIONS = "Agent exceeded maximum iterations: {iterations}"
ERROR_INVALID_AGENT_TYPE = "Invalid agent type: {agent_type}"
ERROR_MEMORY_NOT_CONFIGURED = "Memory not configured for this agent"
ERROR_TOOL_NOT_FOUND = "Tool not found: {tool_name}"
ERROR_TOOL_EXECUTION_FAILED = "Tool execution failed: {tool_name}"
ERROR_LLM_FAILED = "LLM request failed: {error}"
ERROR_INVALID_STATE = "Agent in invalid state: {state}"
ERROR_CHECKLIST_ITEM_NOT_FOUND = "Checklist item not found: {item}"
ERROR_AGENT_BUILD_FAILED = "Failed to build agent: {reason}"

# ============================================================================
# CONFIGURATION KEYS
# ============================================================================

CONFIG_LLM = "llm"
CONFIG_BACKUP_LLM = "backup_llm"
CONFIG_TOOLS = "tools"
CONFIG_MEMORY = "memory"
CONFIG_SCRATCHPAD = "scratchpad"
CONFIG_CHECKLIST = "checklist"
CONFIG_PROMPT_REGISTRY = "prompt_registry"
CONFIG_SYSTEM_PROMPT = "system_prompt"
CONFIG_MAX_ITERATIONS = "max_iterations"
CONFIG_AGENT_TYPE = "agent_type"
CONFIG_TIMEOUT = "timeout"

# ============================================================================
# DEFAULT VALUES
# ============================================================================

DEFAULT_MAX_ITERATIONS = 10
DEFAULT_TIMEOUT_SECONDS = 300
DEFAULT_AGENT_TYPE = "react"
DEFAULT_LOCALE = "en-US"
DEFAULT_TIMEZONE = "UTC"

# ============================================================================
# AGENT TYPES
# ============================================================================

AGENT_TYPE_REACT = "react"
AGENT_TYPE_GOAL_BASED = "goal_based"
AGENT_TYPE_HIERARCHICAL = "hierarchical"
AGENT_TYPE_SIMPLE = "simple"

# ============================================================================
# AGENT STATES
# ============================================================================

STATE_IDLE = "idle"
STATE_RUNNING = "running"
STATE_WAITING = "waiting"
STATE_COMPLETED = "completed"
STATE_FAILED = "failed"
STATE_CANCELLED = "cancelled"

# ============================================================================
# CHECKLIST STATUSES
# ============================================================================

CHECKLIST_STATUS_PENDING = "pending"
CHECKLIST_STATUS_IN_PROGRESS = "in_progress"
CHECKLIST_STATUS_COMPLETED = "completed"
CHECKLIST_STATUS_FAILED = "failed"
CHECKLIST_STATUS_SKIPPED = "skipped"

# ============================================================================
# CONTEXT FIELD KEYS
# ============================================================================

CONTEXT_REQUEST_ID = "request_id"
CONTEXT_USER_ID = "user_id"
CONTEXT_SESSION_ID = "session_id"
CONTEXT_TENANT_ID = "tenant_id"
CONTEXT_TRACE_ID = "trace_id"
CONTEXT_LOCALE = "locale"
CONTEXT_TIMEZONE = "timezone"
CONTEXT_METADATA = "metadata"
CONTEXT_CONFIG = "config"

# Context prefixes
PREFIX_REQUEST = "req-"
PREFIX_AGENT = "agent-"
PREFIX_ITERATION = "iter-"

# ============================================================================
# METRIC NAMES
# ============================================================================

METRIC_AGENT_RUNS = "agent.runs"
METRIC_AGENT_ERRORS = "agent.errors"
METRIC_AGENT_LATENCY = "agent.latency"
METRIC_AGENT_ITERATIONS = "agent.iterations"
METRIC_AGENT_TOOL_CALLS = "agent.tool_calls"
METRIC_AGENT_LLM_CALLS = "agent.llm_calls"
METRIC_AGENT_TOKENS_INPUT = "agent.tokens.input"
METRIC_AGENT_TOKENS_OUTPUT = "agent.tokens.output"

# ============================================================================
# SCRATCHPAD CONSTANTS
# ============================================================================

SCRATCHPAD_SEPARATOR = "\n---\n"
SCRATCHPAD_THOUGHT_PREFIX = "Thought: "
SCRATCHPAD_ACTION_PREFIX = "Action: "
SCRATCHPAD_OBSERVATION_PREFIX = "Observation: "

# ============================================================================
# REACT AGENT CONSTANTS
# ============================================================================

REACT_THOUGHT = "thought"
REACT_ACTION = "action"
REACT_ACTION_INPUT = "action_input"
REACT_OBSERVATION = "observation"
REACT_FINAL_ANSWER = "final_answer"

# ============================================================================
# MODEL CONFIG
# ============================================================================

ARBITRARY_TYPES_ALLOWED = "arbitrary_types_allowed"
USE_ENUM_VALUES = "use_enum_values"
JSON_SCHEMA_EXTRA = "json_schema_extra"

# ============================================================================
# INPUT TYPES (What agents can accept)
# ============================================================================

INPUT_TYPE_TEXT = "text"
INPUT_TYPE_IMAGE = "image"
INPUT_TYPE_AUDIO = "audio"
INPUT_TYPE_VIDEO = "video"
INPUT_TYPE_FILE = "file"
INPUT_TYPE_STRUCTURED = "structured"  # JSON/dict input
INPUT_TYPE_MULTIMODAL = "multimodal"

# ============================================================================
# OUTPUT TYPES (What agents can produce)
# ============================================================================

OUTPUT_TYPE_TEXT = "text"
OUTPUT_TYPE_IMAGE = "image"
OUTPUT_TYPE_AUDIO = "audio"
OUTPUT_TYPE_VIDEO = "video"
OUTPUT_TYPE_FILE = "file"
OUTPUT_TYPE_STRUCTURED = "structured"  # JSON/dict output
OUTPUT_TYPE_STREAM = "stream"  # Streaming output
OUTPUT_TYPE_MULTIMODAL = "multimodal"

# ============================================================================
# OUTPUT FORMATS (For structured outputs)
# ============================================================================

OUTPUT_FORMAT_TEXT = "text"
OUTPUT_FORMAT_JSON = "json"
OUTPUT_FORMAT_MARKDOWN = "markdown"
OUTPUT_FORMAT_HTML = "html"
OUTPUT_FORMAT_XML = "xml"

# ============================================================================
# UNKNOWN ERRORS
# ============================================================================

UNKNOWN_AGENT_TYPE_ERROR = "Unknown agent type: {AGENT_TYPE}. Available: {AVAILABLE_TYPES}"
UNKNOWN_MEMORY_ERROR = "Unknown memory implementation: {MEMORY_NAME}. Available: {AVAILABLE_MEMORIES}"
UNKNOWN_SCRATCHPAD_ERROR = "Unknown scratchpad implementation: {SCRATCHPAD_NAME}. Available: {AVAILABLE_SCRATCHPADS}"
UNKNOWN_CHECKLIST_ERROR = "Unknown checklist implementation: {CHECKLIST_NAME}. Available: {AVAILABLE_CHECKLISTS}"
UNSUPPORTED_INPUT_TYPE_ERROR = "Unsupported input type: {INPUT_TYPE}. Supported: {SUPPORTED_TYPES}"
UNSUPPORTED_OUTPUT_TYPE_ERROR = "Unsupported output type: {OUTPUT_TYPE}. Supported: {SUPPORTED_TYPES}"

