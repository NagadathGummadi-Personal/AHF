"""
Workflow Module Enumerations

Version: 1.0.0
"""

from enum import Enum

from .constants import (
    # Workflow status
    STATUS_DRAFT,
    STATUS_PUBLISHED,
    STATUS_ARCHIVED,
    STATUS_PENDING_REVIEW,
    STATUS_APPROVED,
    STATUS_REJECTED,
    # Node types
    NODE_TYPE_AGENT,
    NODE_TYPE_TOOL,
    NODE_TYPE_PROMPT,
    NODE_TYPE_CUSTOM,
    NODE_TYPE_START,
    NODE_TYPE_END,
    NODE_TYPE_DECISION,
    NODE_TYPE_PARALLEL,
    NODE_TYPE_MERGE,
    # Edge types
    EDGE_TYPE_DEFAULT,
    EDGE_TYPE_CONDITIONAL,
    EDGE_TYPE_ERROR,
    EDGE_TYPE_TIMEOUT,
    EDGE_TYPE_FALLBACK,
    # IO types
    IO_TYPE_TEXT,
    IO_TYPE_SPEECH,
    IO_TYPE_JSON,
    IO_TYPE_IMAGE,
    IO_TYPE_AUDIO,
    IO_TYPE_VIDEO,
    IO_TYPE_BINARY,
    IO_TYPE_STRUCTURED,
    IO_TYPE_STREAM,
    IO_TYPE_ANY,
    # Formats
    FORMAT_PLAIN,
    FORMAT_MARKDOWN,
    FORMAT_HTML,
    FORMAT_JSON_SCHEMA,
    FORMAT_PYDANTIC,
    # Prompt precedence
    PROMPT_PRECEDENCE_AGENT,
    PROMPT_PRECEDENCE_USER,
    PROMPT_PRECEDENCE_MERGE,
    PROMPT_PRECEDENCE_REPLACE,
    # Prompt merge strategies
    PROMPT_MERGE_APPEND,
    PROMPT_MERGE_PREPEND,
    PROMPT_MERGE_INTERLEAVE,
    # Execution states
    EXEC_STATE_IDLE,
    EXEC_STATE_RUNNING,
    EXEC_STATE_PAUSED,
    EXEC_STATE_COMPLETED,
    EXEC_STATE_FAILED,
    EXEC_STATE_CANCELLED,
    EXEC_STATE_TIMEOUT,
    # Background agent modes
    BG_MODE_MONITOR,
    BG_MODE_ACTIVE,
    BG_MODE_SILENT,
    # Condition operators
    COND_OP_EQUALS,
    COND_OP_NOT_EQUALS,
    COND_OP_GREATER_THAN,
    COND_OP_LESS_THAN,
    COND_OP_GREATER_THAN_OR_EQUALS,
    COND_OP_LESS_THAN_OR_EQUALS,
    COND_OP_CONTAINS,
    COND_OP_NOT_CONTAINS,
    COND_OP_STARTS_WITH,
    COND_OP_ENDS_WITH,
    COND_OP_MATCHES,
    COND_OP_IN,
    COND_OP_NOT_IN,
    COND_OP_IS_NULL,
    COND_OP_IS_NOT_NULL,
    COND_OP_IS_EMPTY,
    COND_OP_IS_NOT_EMPTY,
    COND_OP_CUSTOM,
    # Condition join operators
    COND_JOIN_AND,
    COND_JOIN_OR,
)


class WorkflowStatus(str, Enum):
    """
    Status of a workflow, node, or edge.
    
    Lifecycle: DRAFT -> PENDING_REVIEW -> APPROVED/REJECTED -> PUBLISHED -> ARCHIVED
    """
    DRAFT = STATUS_DRAFT
    PENDING_REVIEW = STATUS_PENDING_REVIEW
    APPROVED = STATUS_APPROVED
    REJECTED = STATUS_REJECTED
    PUBLISHED = STATUS_PUBLISHED
    ARCHIVED = STATUS_ARCHIVED


class NodeType(str, Enum):
    """
    Types of nodes in a workflow.
    
    AGENT: Node that contains an agent (LLM + tools + prompt)
    TOOL: Node that contains only a tool (HTTP, DB, Function)
    PROMPT: Node that contains only a prompt template
    CUSTOM: Custom node with user-defined logic
    START: Entry point of workflow
    END: Exit point of workflow
    DECISION: Branching decision node
    PARALLEL: Parallel execution node
    MERGE: Merge point for parallel branches
    """
    AGENT = NODE_TYPE_AGENT
    TOOL = NODE_TYPE_TOOL
    PROMPT = NODE_TYPE_PROMPT
    CUSTOM = NODE_TYPE_CUSTOM
    START = NODE_TYPE_START
    END = NODE_TYPE_END
    DECISION = NODE_TYPE_DECISION
    PARALLEL = NODE_TYPE_PARALLEL
    MERGE = NODE_TYPE_MERGE


class EdgeType(str, Enum):
    """
    Types of edges connecting nodes.
    
    DEFAULT: Standard connection, always traversed
    CONDITIONAL: Traversed only if condition is met
    ERROR: Traversed on error from source node
    TIMEOUT: Traversed on timeout from source node
    FALLBACK: Fallback path if primary fails
    """
    DEFAULT = EDGE_TYPE_DEFAULT
    CONDITIONAL = EDGE_TYPE_CONDITIONAL
    ERROR = EDGE_TYPE_ERROR
    TIMEOUT = EDGE_TYPE_TIMEOUT
    FALLBACK = EDGE_TYPE_FALLBACK


class IOType(str, Enum):
    """
    Input/Output data types for nodes.
    
    Used to determine if formatters are needed between nodes.
    """
    TEXT = IO_TYPE_TEXT
    SPEECH = IO_TYPE_SPEECH
    JSON = IO_TYPE_JSON
    IMAGE = IO_TYPE_IMAGE
    AUDIO = IO_TYPE_AUDIO
    VIDEO = IO_TYPE_VIDEO
    BINARY = IO_TYPE_BINARY
    STRUCTURED = IO_TYPE_STRUCTURED
    STREAM = IO_TYPE_STREAM
    ANY = IO_TYPE_ANY  # Accepts any type


class IOFormat(str, Enum):
    """
    Format specifications for IO data.
    """
    PLAIN = FORMAT_PLAIN
    MARKDOWN = FORMAT_MARKDOWN
    HTML = FORMAT_HTML
    JSON_SCHEMA = FORMAT_JSON_SCHEMA
    PYDANTIC = FORMAT_PYDANTIC


class PromptPrecedence(str, Enum):
    """
    Determines how to handle agent prompt vs user-provided additional prompt.
    
    AGENT: Agent prompt takes priority, user prompt is supplementary
    USER: User prompt takes priority, agent prompt is supplementary
    MERGE: Both prompts are merged based on merge strategy
    REPLACE: User prompt completely replaces agent prompt
    """
    AGENT = PROMPT_PRECEDENCE_AGENT
    USER = PROMPT_PRECEDENCE_USER
    MERGE = PROMPT_PRECEDENCE_MERGE
    REPLACE = PROMPT_PRECEDENCE_REPLACE


class PromptMergeStrategy(str, Enum):
    """
    Strategy for merging agent and user prompts.
    
    APPEND: User prompt appended after agent prompt
    PREPEND: User prompt prepended before agent prompt
    INTERLEAVE: Custom interleaving based on markers
    """
    APPEND = PROMPT_MERGE_APPEND
    PREPEND = PROMPT_MERGE_PREPEND
    INTERLEAVE = PROMPT_MERGE_INTERLEAVE


class ExecutionState(str, Enum):
    """
    Execution state of a workflow or node.
    """
    IDLE = EXEC_STATE_IDLE
    RUNNING = EXEC_STATE_RUNNING
    PAUSED = EXEC_STATE_PAUSED
    COMPLETED = EXEC_STATE_COMPLETED
    FAILED = EXEC_STATE_FAILED
    CANCELLED = EXEC_STATE_CANCELLED
    TIMEOUT = EXEC_STATE_TIMEOUT


class BackgroundAgentMode(str, Enum):
    """
    Operating mode for background agents.
    
    MONITOR: Passive monitoring, only observes and logs
    ACTIVE: Can take actions (call tools, raise flags)
    SILENT: Runs without user awareness, for internal processing
    """
    MONITOR = BG_MODE_MONITOR
    ACTIVE = BG_MODE_ACTIVE
    SILENT = BG_MODE_SILENT


class ConditionOperator(str, Enum):
    """
    Operators for edge condition evaluation.
    """
    EQUALS = COND_OP_EQUALS
    NOT_EQUALS = COND_OP_NOT_EQUALS
    GREATER_THAN = COND_OP_GREATER_THAN
    LESS_THAN = COND_OP_LESS_THAN
    GREATER_THAN_OR_EQUALS = COND_OP_GREATER_THAN_OR_EQUALS
    LESS_THAN_OR_EQUALS = COND_OP_LESS_THAN_OR_EQUALS
    CONTAINS = COND_OP_CONTAINS
    NOT_CONTAINS = COND_OP_NOT_CONTAINS
    STARTS_WITH = COND_OP_STARTS_WITH
    ENDS_WITH = COND_OP_ENDS_WITH
    MATCHES = COND_OP_MATCHES
    IN = COND_OP_IN
    NOT_IN = COND_OP_NOT_IN
    IS_NULL = COND_OP_IS_NULL
    IS_NOT_NULL = COND_OP_IS_NOT_NULL
    IS_EMPTY = COND_OP_IS_EMPTY
    IS_NOT_EMPTY = COND_OP_IS_NOT_EMPTY
    CUSTOM = COND_OP_CUSTOM


class ConditionJoinOperator(str, Enum):
    """
    Operators for joining multiple conditions.
    """
    AND = COND_JOIN_AND
    OR = COND_JOIN_OR
