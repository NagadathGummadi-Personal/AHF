"""
Workflow Constants Module.

This module defines all constants used throughout the workflows subsystem.

Node Types are organized into categories:
- Execution Nodes: LLM, Agent, Tool, Subworkflow
- Control-Flow Nodes: Decision/Router, Switch, Parallel, Loop
- Data & Integration Nodes: VectorStore, HTTP, Database, Transform
- Human Interaction Nodes: HumanInput (HITL), VoiceAgent, Notification
- Utility Nodes: Delay, ErrorHandler, Start, End
"""

# =============================================================================
# NODE TYPE CONSTANTS - EXECUTION NODES
# =============================================================================
NODE_TYPE_LLM = "llm"  # Invoke language model (GPT, Claude, etc.)
NODE_TYPE_AGENT = "agent"  # Intelligent agent with tools and memory
NODE_TYPE_TOOL = "tool"  # External function or API call
NODE_TYPE_SUBWORKFLOW = "subworkflow"  # Nested workflow execution

# =============================================================================
# NODE TYPE CONSTANTS - CONTROL-FLOW NODES
# =============================================================================
NODE_TYPE_DECISION = "decision"  # Router/conditional branching
NODE_TYPE_SWITCH = "switch"  # Match against multiple values (switch/case)
NODE_TYPE_PARALLEL = "parallel"  # Fan-out for concurrent execution
NODE_TYPE_LOOP = "loop"  # Repeat until condition met
NODE_TYPE_JOIN = "join"  # Wait for parallel branches to complete

# =============================================================================
# NODE TYPE CONSTANTS - DATA & INTEGRATION NODES
# =============================================================================
NODE_TYPE_VECTOR_STORE = "vector_store"  # RAG similarity search
NODE_TYPE_HTTP = "http"  # HTTP/REST API calls
NODE_TYPE_DATABASE = "database"  # Database operations
NODE_TYPE_TRANSFORM = "transform"  # Data transformation
NODE_TYPE_WEBHOOK = "webhook"  # Webhook receiver/sender

# =============================================================================
# NODE TYPE CONSTANTS - HUMAN INTERACTION NODES
# =============================================================================
NODE_TYPE_HUMAN_INPUT = "human_input"  # HITL - pause for human input/approval
NODE_TYPE_VOICE_AGENT = "voice_agent"  # Speech-to-text/text-to-speech
NODE_TYPE_NOTIFICATION = "notification"  # Send notifications (email, SMS, push)

# =============================================================================
# NODE TYPE CONSTANTS - UTILITY NODES
# =============================================================================
NODE_TYPE_DELAY = "delay"  # Timer/delay node
NODE_TYPE_START = "start"  # Workflow entry point
NODE_TYPE_END = "end"  # Workflow exit point
NODE_TYPE_ERROR_HANDLER = "error_handler"  # Error handling
NODE_TYPE_CUSTOM = "custom"  # Custom node type

# =============================================================================
# EDGE TYPE CONSTANTS
# =============================================================================
EDGE_TYPE_DEFAULT = "default"
EDGE_TYPE_CONDITIONAL = "conditional"
EDGE_TYPE_FALLBACK = "fallback"
EDGE_TYPE_TIMEOUT = "timeout"
EDGE_TYPE_ERROR = "error"
EDGE_TYPE_LOOP_BACK = "loop_back"
EDGE_TYPE_PARALLEL_JOIN = "parallel_join"
EDGE_TYPE_INTENT = "intent"  # Intent-based routing (LLM classification)
EDGE_TYPE_CUSTOM = "custom"

# =============================================================================
# TRANSITION CONDITION SOURCE TYPES
# =============================================================================
CONDITION_SOURCE_CONTEXT = "context"  # Evaluate from workflow context
CONDITION_SOURCE_NODE_OUTPUT = "node_output"  # Evaluate from node output
CONDITION_SOURCE_TOOL_RESULT = "tool_result"  # Evaluate from tool execution result
CONDITION_SOURCE_LLM_CLASSIFICATION = "llm_classification"  # LLM-based intent/decision
CONDITION_SOURCE_USER_INPUT = "user_input"  # User-provided input
CONDITION_SOURCE_CUSTOM = "custom"  # Custom evaluation function

# =============================================================================
# VARIABLE REQUIREMENT TYPES (for edge transition requirements)
# =============================================================================
VAR_REQUIREMENT_REQUIRED = "required"
VAR_REQUIREMENT_OPTIONAL = "optional"
VAR_REQUIREMENT_CONDITIONAL = "conditional"

# =============================================================================
# INPUT/OUTPUT DATA TYPES
# =============================================================================
DATA_TYPE_STRING = "string"
DATA_TYPE_NUMBER = "number"
DATA_TYPE_INTEGER = "integer"
DATA_TYPE_BOOLEAN = "boolean"
DATA_TYPE_ARRAY = "array"
DATA_TYPE_OBJECT = "object"
DATA_TYPE_ANY = "any"
DATA_TYPE_NULL = "null"

# =============================================================================
# INPUT/OUTPUT DATA FORMATS
# =============================================================================
DATA_FORMAT_TEXT = "text"
DATA_FORMAT_JSON = "json"
DATA_FORMAT_MARKDOWN = "markdown"
DATA_FORMAT_HTML = "html"
DATA_FORMAT_XML = "xml"
DATA_FORMAT_CSV = "csv"
DATA_FORMAT_BINARY = "binary"
DATA_FORMAT_BASE64 = "base64"

# =============================================================================
# INTENT TYPES (for conversational workflows)
# =============================================================================
INTENT_TYPE_BOOK = "book"
INTENT_TYPE_CANCEL = "cancel"
INTENT_TYPE_RESCHEDULE = "reschedule"
INTENT_TYPE_INQUIRY = "inquiry"
INTENT_TYPE_GREETING = "greeting"
INTENT_TYPE_FAREWELL = "farewell"
INTENT_TYPE_CONFIRMATION = "confirmation"
INTENT_TYPE_HANDOVER = "handover"
INTENT_TYPE_UNKNOWN = "unknown"

# =============================================================================
# WORKFLOW STATE CONSTANTS
# =============================================================================
WORKFLOW_STATE_IDLE = "idle"
WORKFLOW_STATE_RUNNING = "running"
WORKFLOW_STATE_PAUSED = "paused"
WORKFLOW_STATE_COMPLETED = "completed"
WORKFLOW_STATE_FAILED = "failed"
WORKFLOW_STATE_CANCELLED = "cancelled"
WORKFLOW_STATE_WAITING = "waiting"  # Waiting for human input or external event

# =============================================================================
# NODE STATE CONSTANTS
# =============================================================================
NODE_STATE_PENDING = "pending"
NODE_STATE_RUNNING = "running"
NODE_STATE_COMPLETED = "completed"
NODE_STATE_FAILED = "failed"
NODE_STATE_SKIPPED = "skipped"
NODE_STATE_WAITING = "waiting"

# =============================================================================
# CONDITION OPERATOR CONSTANTS
# =============================================================================
CONDITION_OP_EQUALS = "equals"
CONDITION_OP_NOT_EQUALS = "not_equals"
CONDITION_OP_CONTAINS = "contains"
CONDITION_OP_NOT_CONTAINS = "not_contains"
CONDITION_OP_GREATER_THAN = "greater_than"
CONDITION_OP_LESS_THAN = "less_than"
CONDITION_OP_GREATER_OR_EQUAL = "greater_or_equal"
CONDITION_OP_LESS_OR_EQUAL = "less_or_equal"
CONDITION_OP_IS_EMPTY = "is_empty"
CONDITION_OP_IS_NOT_EMPTY = "is_not_empty"
CONDITION_OP_MATCHES_REGEX = "matches_regex"
CONDITION_OP_STARTS_WITH = "starts_with"
CONDITION_OP_ENDS_WITH = "ends_with"
CONDITION_OP_IN_LIST = "in_list"
CONDITION_OP_NOT_IN_LIST = "not_in_list"
CONDITION_OP_IS_TRUE = "is_true"
CONDITION_OP_IS_FALSE = "is_false"
CONDITION_OP_CUSTOM = "custom"

# =============================================================================
# ROUTING STRATEGY CONSTANTS
# =============================================================================
ROUTING_STRATEGY_FIRST_MATCH = "first_match"
ROUTING_STRATEGY_ALL_MATCHES = "all_matches"
ROUTING_STRATEGY_WEIGHTED = "weighted"
ROUTING_STRATEGY_ROUND_ROBIN = "round_robin"
ROUTING_STRATEGY_RANDOM = "random"
ROUTING_STRATEGY_LLM_BASED = "llm_based"
ROUTING_STRATEGY_CUSTOM = "custom"

# =============================================================================
# EXECUTION MODE CONSTANTS
# =============================================================================
EXECUTION_MODE_SEQUENTIAL = "sequential"
EXECUTION_MODE_PARALLEL = "parallel"
EXECUTION_MODE_STREAMING = "streaming"

# =============================================================================
# DEFAULT VALUES
# =============================================================================
DEFAULT_MAX_WORKFLOW_ITERATIONS = 100
DEFAULT_MAX_NODE_RETRIES = 3
DEFAULT_NODE_TIMEOUT_SECONDS = 300
DEFAULT_WORKFLOW_TIMEOUT_SECONDS = 3600
DEFAULT_PARALLEL_MAX_CONCURRENCY = 10
DEFAULT_DELAY_SECONDS = 0
DEFAULT_RETRY_DELAY_SECONDS = 1

# =============================================================================
# VARIABLE PREFIX CONSTANTS (for workflow context variables)
# =============================================================================
VAR_PREFIX_INPUT = "$input"
VAR_PREFIX_OUTPUT = "$output"
VAR_PREFIX_NODE = "$node"
VAR_PREFIX_WORKFLOW = "$workflow"
VAR_PREFIX_CONTEXT = "$ctx"
VAR_PREFIX_ENV = "$env"

# =============================================================================
# SPECIAL NODE IDS
# =============================================================================
NODE_ID_START = "__start__"
NODE_ID_END = "__end__"
NODE_ID_ERROR = "__error__"

# =============================================================================
# ERROR CODES
# =============================================================================
ERROR_CODE_WORKFLOW_NOT_FOUND = "WORKFLOW_NOT_FOUND"
ERROR_CODE_NODE_NOT_FOUND = "NODE_NOT_FOUND"
ERROR_CODE_EDGE_NOT_FOUND = "EDGE_NOT_FOUND"
ERROR_CODE_INVALID_WORKFLOW = "INVALID_WORKFLOW"
ERROR_CODE_INVALID_NODE = "INVALID_NODE"
ERROR_CODE_INVALID_EDGE = "INVALID_EDGE"
ERROR_CODE_EXECUTION_FAILED = "EXECUTION_FAILED"
ERROR_CODE_NODE_EXECUTION_FAILED = "NODE_EXECUTION_FAILED"
ERROR_CODE_ROUTING_FAILED = "ROUTING_FAILED"
ERROR_CODE_CONDITION_EVAL_FAILED = "CONDITION_EVAL_FAILED"
ERROR_CODE_TRANSFORM_FAILED = "TRANSFORM_FAILED"
ERROR_CODE_TIMEOUT = "TIMEOUT"
ERROR_CODE_MAX_ITERATIONS = "MAX_ITERATIONS_EXCEEDED"
ERROR_CODE_CYCLE_DETECTED = "CYCLE_DETECTED"
ERROR_CODE_PARALLEL_EXECUTION_FAILED = "PARALLEL_EXECUTION_FAILED"
ERROR_CODE_WEBHOOK_FAILED = "WEBHOOK_FAILED"
ERROR_CODE_SUBWORKFLOW_FAILED = "SUBWORKFLOW_FAILED"

