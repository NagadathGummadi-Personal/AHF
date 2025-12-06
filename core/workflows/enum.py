"""
Workflow Enumerations Module.

This module defines all enumerations used throughout the workflows subsystem.

Node Types are organized into categories:
- Execution Nodes: LLM, Agent, Tool, Subworkflow
- Control-Flow Nodes: Decision/Router, Switch, Parallel, Loop, Join
- Data & Integration Nodes: VectorStore, HTTP, Database, Transform, Webhook
- Human Interaction Nodes: HumanInput (HITL), VoiceAgent, Notification
- Utility Nodes: Delay, ErrorHandler, Start, End
"""

from enum import Enum

from .constants import (
    # Node Types - Execution
    NODE_TYPE_LLM,
    NODE_TYPE_AGENT,
    NODE_TYPE_TOOL,
    NODE_TYPE_SUBWORKFLOW,
    # Node Types - Control Flow
    NODE_TYPE_DECISION,
    NODE_TYPE_SWITCH,
    NODE_TYPE_PARALLEL,
    NODE_TYPE_LOOP,
    NODE_TYPE_JOIN,
    # Node Types - Data & Integration
    NODE_TYPE_VECTOR_STORE,
    NODE_TYPE_HTTP,
    NODE_TYPE_DATABASE,
    NODE_TYPE_TRANSFORM,
    NODE_TYPE_WEBHOOK,
    # Node Types - Human Interaction
    NODE_TYPE_HUMAN_INPUT,
    NODE_TYPE_VOICE_AGENT,
    NODE_TYPE_NOTIFICATION,
    # Node Types - Utility
    NODE_TYPE_DELAY,
    NODE_TYPE_START,
    NODE_TYPE_END,
    NODE_TYPE_ERROR_HANDLER,
    NODE_TYPE_CUSTOM,
    # Edge Types
    EDGE_TYPE_DEFAULT,
    EDGE_TYPE_CONDITIONAL,
    EDGE_TYPE_FALLBACK,
    EDGE_TYPE_TIMEOUT,
    EDGE_TYPE_ERROR,
    EDGE_TYPE_LOOP_BACK,
    EDGE_TYPE_PARALLEL_JOIN,
    EDGE_TYPE_INTENT,
    EDGE_TYPE_CUSTOM,
    # Condition Source Types
    CONDITION_SOURCE_CONTEXT,
    CONDITION_SOURCE_NODE_OUTPUT,
    CONDITION_SOURCE_TOOL_RESULT,
    CONDITION_SOURCE_LLM_CLASSIFICATION,
    CONDITION_SOURCE_USER_INPUT,
    CONDITION_SOURCE_CUSTOM,
    # Variable Requirements
    VAR_REQUIREMENT_REQUIRED,
    VAR_REQUIREMENT_OPTIONAL,
    VAR_REQUIREMENT_CONDITIONAL,
    # Data Types
    DATA_TYPE_STRING,
    DATA_TYPE_NUMBER,
    DATA_TYPE_INTEGER,
    DATA_TYPE_BOOLEAN,
    DATA_TYPE_ARRAY,
    DATA_TYPE_OBJECT,
    DATA_TYPE_ANY,
    DATA_TYPE_NULL,
    # Data Formats
    DATA_FORMAT_TEXT,
    DATA_FORMAT_JSON,
    DATA_FORMAT_MARKDOWN,
    DATA_FORMAT_HTML,
    DATA_FORMAT_XML,
    DATA_FORMAT_CSV,
    DATA_FORMAT_BINARY,
    DATA_FORMAT_BASE64,
    # Intent Types
    INTENT_TYPE_BOOK,
    INTENT_TYPE_CANCEL,
    INTENT_TYPE_RESCHEDULE,
    INTENT_TYPE_INQUIRY,
    INTENT_TYPE_GREETING,
    INTENT_TYPE_FAREWELL,
    INTENT_TYPE_CONFIRMATION,
    INTENT_TYPE_HANDOVER,
    INTENT_TYPE_UNKNOWN,
    # Workflow States
    WORKFLOW_STATE_IDLE,
    WORKFLOW_STATE_RUNNING,
    WORKFLOW_STATE_PAUSED,
    WORKFLOW_STATE_COMPLETED,
    WORKFLOW_STATE_FAILED,
    WORKFLOW_STATE_CANCELLED,
    WORKFLOW_STATE_WAITING,
    # Node States
    NODE_STATE_PENDING,
    NODE_STATE_RUNNING,
    NODE_STATE_COMPLETED,
    NODE_STATE_FAILED,
    NODE_STATE_SKIPPED,
    NODE_STATE_WAITING,
    # Condition Operators
    CONDITION_OP_EQUALS,
    CONDITION_OP_NOT_EQUALS,
    CONDITION_OP_CONTAINS,
    CONDITION_OP_NOT_CONTAINS,
    CONDITION_OP_GREATER_THAN,
    CONDITION_OP_LESS_THAN,
    CONDITION_OP_GREATER_OR_EQUAL,
    CONDITION_OP_LESS_OR_EQUAL,
    CONDITION_OP_IS_EMPTY,
    CONDITION_OP_IS_NOT_EMPTY,
    CONDITION_OP_MATCHES_REGEX,
    CONDITION_OP_STARTS_WITH,
    CONDITION_OP_ENDS_WITH,
    CONDITION_OP_IN_LIST,
    CONDITION_OP_NOT_IN_LIST,
    CONDITION_OP_IS_TRUE,
    CONDITION_OP_IS_FALSE,
    CONDITION_OP_CUSTOM,
    # Routing Strategies
    ROUTING_STRATEGY_FIRST_MATCH,
    ROUTING_STRATEGY_ALL_MATCHES,
    ROUTING_STRATEGY_WEIGHTED,
    ROUTING_STRATEGY_ROUND_ROBIN,
    ROUTING_STRATEGY_RANDOM,
    ROUTING_STRATEGY_LLM_BASED,
    ROUTING_STRATEGY_CUSTOM,
    # Execution Modes
    EXECUTION_MODE_SEQUENTIAL,
    EXECUTION_MODE_PARALLEL,
    EXECUTION_MODE_STREAMING,
)


class NodeType(str, Enum):
    """
    Types of nodes available in workflows.
    
    Categories:
    - Execution: LLM, AGENT, TOOL, SUBWORKFLOW
    - Control-Flow: DECISION, SWITCH, PARALLEL, LOOP, JOIN
    - Data & Integration: VECTOR_STORE, HTTP, DATABASE, TRANSFORM, WEBHOOK
    - Human Interaction: HUMAN_INPUT, VOICE_AGENT, NOTIFICATION
    - Utility: DELAY, START, END, ERROR_HANDLER
    """
    
    # Execution Nodes
    LLM = NODE_TYPE_LLM  # Invoke language model directly
    AGENT = NODE_TYPE_AGENT  # Intelligent agent with tools/memory
    TOOL = NODE_TYPE_TOOL  # External function/API call
    SUBWORKFLOW = NODE_TYPE_SUBWORKFLOW  # Nested workflow
    
    # Control-Flow Nodes
    DECISION = NODE_TYPE_DECISION  # Router/conditional branching
    SWITCH = NODE_TYPE_SWITCH  # Switch/case matching
    PARALLEL = NODE_TYPE_PARALLEL  # Fan-out concurrent execution
    LOOP = NODE_TYPE_LOOP  # Repeat until condition
    JOIN = NODE_TYPE_JOIN  # Wait for parallel branches
    
    # Data & Integration Nodes
    VECTOR_STORE = NODE_TYPE_VECTOR_STORE  # RAG similarity search
    HTTP = NODE_TYPE_HTTP  # HTTP/REST API calls
    DATABASE = NODE_TYPE_DATABASE  # Database operations
    TRANSFORM = NODE_TYPE_TRANSFORM  # Data transformation
    WEBHOOK = NODE_TYPE_WEBHOOK  # Webhook receiver/sender
    
    # Human Interaction Nodes
    HUMAN_INPUT = NODE_TYPE_HUMAN_INPUT  # HITL pause for human
    VOICE_AGENT = NODE_TYPE_VOICE_AGENT  # Speech processing
    NOTIFICATION = NODE_TYPE_NOTIFICATION  # Send notifications
    
    # Utility Nodes
    DELAY = NODE_TYPE_DELAY  # Timer/delay
    START = NODE_TYPE_START  # Workflow entry
    END = NODE_TYPE_END  # Workflow exit
    ERROR_HANDLER = NODE_TYPE_ERROR_HANDLER  # Error handling
    CUSTOM = NODE_TYPE_CUSTOM  # Custom node type


class EdgeType(str, Enum):
    """Types of edges connecting nodes in workflows."""
    
    DEFAULT = EDGE_TYPE_DEFAULT  # Standard edge
    CONDITIONAL = EDGE_TYPE_CONDITIONAL  # Condition-based routing
    FALLBACK = EDGE_TYPE_FALLBACK  # Default when no conditions match
    TIMEOUT = EDGE_TYPE_TIMEOUT  # Taken on timeout
    ERROR = EDGE_TYPE_ERROR  # Taken on error
    LOOP_BACK = EDGE_TYPE_LOOP_BACK  # Loop iteration edge
    PARALLEL_JOIN = EDGE_TYPE_PARALLEL_JOIN  # Join parallel branches
    INTENT = EDGE_TYPE_INTENT  # Intent-based routing (LLM classification)
    CUSTOM = EDGE_TYPE_CUSTOM  # Custom edge type


class ConditionSourceType(str, Enum):
    """Source types for edge condition evaluation."""
    
    CONTEXT = CONDITION_SOURCE_CONTEXT  # From workflow context
    NODE_OUTPUT = CONDITION_SOURCE_NODE_OUTPUT  # From node output
    TOOL_RESULT = CONDITION_SOURCE_TOOL_RESULT  # From tool result
    LLM_CLASSIFICATION = CONDITION_SOURCE_LLM_CLASSIFICATION  # LLM intent/decision
    USER_INPUT = CONDITION_SOURCE_USER_INPUT  # User input
    CUSTOM = CONDITION_SOURCE_CUSTOM  # Custom evaluation


class VariableRequirement(str, Enum):
    """Requirement level for transition variables."""
    
    REQUIRED = VAR_REQUIREMENT_REQUIRED  # Must be present to transition
    OPTIONAL = VAR_REQUIREMENT_OPTIONAL  # Nice to have
    CONDITIONAL = VAR_REQUIREMENT_CONDITIONAL  # Required if condition met


class DataType(str, Enum):
    """Data types for input/output specifications."""
    
    STRING = DATA_TYPE_STRING
    NUMBER = DATA_TYPE_NUMBER
    INTEGER = DATA_TYPE_INTEGER
    BOOLEAN = DATA_TYPE_BOOLEAN
    ARRAY = DATA_TYPE_ARRAY
    OBJECT = DATA_TYPE_OBJECT
    ANY = DATA_TYPE_ANY
    NULL = DATA_TYPE_NULL


class DataFormat(str, Enum):
    """Data formats for input/output specifications."""
    
    TEXT = DATA_FORMAT_TEXT
    JSON = DATA_FORMAT_JSON
    MARKDOWN = DATA_FORMAT_MARKDOWN
    HTML = DATA_FORMAT_HTML
    XML = DATA_FORMAT_XML
    CSV = DATA_FORMAT_CSV
    BINARY = DATA_FORMAT_BINARY
    BASE64 = DATA_FORMAT_BASE64


class IntentType(str, Enum):
    """Intent types for conversational workflows."""
    
    BOOK = INTENT_TYPE_BOOK
    CANCEL = INTENT_TYPE_CANCEL
    RESCHEDULE = INTENT_TYPE_RESCHEDULE
    INQUIRY = INTENT_TYPE_INQUIRY
    GREETING = INTENT_TYPE_GREETING
    FAREWELL = INTENT_TYPE_FAREWELL
    CONFIRMATION = INTENT_TYPE_CONFIRMATION
    HANDOVER = INTENT_TYPE_HANDOVER
    UNKNOWN = INTENT_TYPE_UNKNOWN


class WorkflowState(str, Enum):
    """Possible states of a workflow execution."""
    
    IDLE = WORKFLOW_STATE_IDLE
    RUNNING = WORKFLOW_STATE_RUNNING
    PAUSED = WORKFLOW_STATE_PAUSED
    COMPLETED = WORKFLOW_STATE_COMPLETED
    FAILED = WORKFLOW_STATE_FAILED
    CANCELLED = WORKFLOW_STATE_CANCELLED
    WAITING = WORKFLOW_STATE_WAITING


class NodeState(str, Enum):
    """Possible states of a node during execution."""
    
    PENDING = NODE_STATE_PENDING
    RUNNING = NODE_STATE_RUNNING
    COMPLETED = NODE_STATE_COMPLETED
    FAILED = NODE_STATE_FAILED
    SKIPPED = NODE_STATE_SKIPPED
    WAITING = NODE_STATE_WAITING


class ConditionOperator(str, Enum):
    """Operators for edge conditions."""
    
    EQUALS = CONDITION_OP_EQUALS
    NOT_EQUALS = CONDITION_OP_NOT_EQUALS
    CONTAINS = CONDITION_OP_CONTAINS
    NOT_CONTAINS = CONDITION_OP_NOT_CONTAINS
    GREATER_THAN = CONDITION_OP_GREATER_THAN
    LESS_THAN = CONDITION_OP_LESS_THAN
    GREATER_OR_EQUAL = CONDITION_OP_GREATER_OR_EQUAL
    LESS_OR_EQUAL = CONDITION_OP_LESS_OR_EQUAL
    IS_EMPTY = CONDITION_OP_IS_EMPTY
    IS_NOT_EMPTY = CONDITION_OP_IS_NOT_EMPTY
    MATCHES_REGEX = CONDITION_OP_MATCHES_REGEX
    STARTS_WITH = CONDITION_OP_STARTS_WITH
    ENDS_WITH = CONDITION_OP_ENDS_WITH
    IN_LIST = CONDITION_OP_IN_LIST
    NOT_IN_LIST = CONDITION_OP_NOT_IN_LIST
    IS_TRUE = CONDITION_OP_IS_TRUE
    IS_FALSE = CONDITION_OP_IS_FALSE
    CUSTOM = CONDITION_OP_CUSTOM


class RoutingStrategy(str, Enum):
    """Strategies for routing between nodes."""
    
    FIRST_MATCH = ROUTING_STRATEGY_FIRST_MATCH
    ALL_MATCHES = ROUTING_STRATEGY_ALL_MATCHES
    WEIGHTED = ROUTING_STRATEGY_WEIGHTED
    ROUND_ROBIN = ROUTING_STRATEGY_ROUND_ROBIN
    RANDOM = ROUTING_STRATEGY_RANDOM
    LLM_BASED = ROUTING_STRATEGY_LLM_BASED
    CUSTOM = ROUTING_STRATEGY_CUSTOM


class ExecutionMode(str, Enum):
    """Modes of workflow execution."""
    
    SEQUENTIAL = EXECUTION_MODE_SEQUENTIAL
    PARALLEL = EXECUTION_MODE_PARALLEL
    STREAMING = EXECUTION_MODE_STREAMING


class DataTransformType(str, Enum):
    """Types of data transformations between nodes."""
    
    PASS_THROUGH = "pass_through"
    MAP = "map"
    FILTER = "filter"
    REDUCE = "reduce"
    MERGE = "merge"
    SPLIT = "split"
    EXTRACT = "extract"
    FORMAT = "format"
    TEMPLATE = "template"
    JMESPATH = "jmespath"
    JSONPATH = "jsonpath"
    PYTHON = "python"
    CUSTOM = "custom"


class TriggerType(str, Enum):
    """Types of workflow triggers."""
    
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    WEBHOOK = "webhook"
    EVENT = "event"
    API = "api"
    MESSAGE = "message"
    FILE = "file"
    CUSTOM = "custom"


class RetryStrategy(str, Enum):
    """Strategies for retrying failed nodes."""
    
    NONE = "none"
    FIXED = "fixed"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    CUSTOM = "custom"

