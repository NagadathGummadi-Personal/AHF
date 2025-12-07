from enum import Enum

from .constants import (
    JSON,
    TEXT,
    HUMAN,
    LLM,
    AGENT,
    STEP,
    FUNCTION,
    HTTP,
    DB,
    STRING,
    NUMBER,
    INTEGER,
    BOOLEAN,
    ARRAY,
    OBJECT,
    TIMEOUT,
    UNAVAILABLE,
    NETWORK,
    RATE_LIMIT,
    TRANSIENT,
    CIRCUIT_BREAKER_STATE_CLOSED,
    CIRCUIT_BREAKER_STATE_OPEN,
    CIRCUIT_BREAKER_STATE_HALF_OPEN,
    TOON,
    DYNAMODB,
)

class ToolReturnType(str, Enum):
    """Enumeration for tool return formats"""
    JSON = JSON
    TOON = TOON
    TEXT = TEXT

class DatabaseProvider(str, Enum):
    """Enumeration for database providers"""
    DYNAMODB = DYNAMODB

class ToolReturnTarget(str, Enum):
    """Enumeration for tool return routing targets"""
    HUMAN = HUMAN #results sent to human directly
    LLM = LLM #results sent to llm
    AGENT = AGENT #results sent to agent
    STEP = STEP #results are part of workflow step


class ToolType(str, Enum):
    """Enumeration for tool types"""
    FUNCTION = FUNCTION
    HTTP = HTTP
    DB = DB


class ParameterType(str, Enum):
    """Enumeration for parameter types"""
    STRING = STRING
    NUMBER = NUMBER
    INTEGER = INTEGER
    BOOLEAN = BOOLEAN
    ARRAY = ARRAY
    OBJECT = OBJECT

# Enum for retry policy
class RetryableErrorType(str, Enum):
    """Types of errors that are typically retryable."""
    TIMEOUT = TIMEOUT
    UNAVAILABLE = UNAVAILABLE
    NETWORK = NETWORK
    RATE_LIMIT = RATE_LIMIT
    TRANSIENT = TRANSIENT


# Enum for circuit breaker states
class CircuitBreakerState(str, Enum):
    """Circuit breaker states."""
    CLOSED = CIRCUIT_BREAKER_STATE_CLOSED
    OPEN = CIRCUIT_BREAKER_STATE_OPEN
    HALF_OPEN = CIRCUIT_BREAKER_STATE_HALF_OPEN


class SpeechMode(str, Enum):
    """
    Pre-tool speech generation modes.
    
    AUTO: LLM generates speech dynamically based on context
    RANDOM: Randomly select from predefined messages
    CONSTANT: Use a fixed constant message
    """
    AUTO = "auto"
    RANDOM = "random"
    CONSTANT = "constant"


class ExecutionMode(str, Enum):
    """
    Tool execution modes relative to speech.
    
    SEQUENTIAL: Wait for speech to complete, then execute tool
    PARALLEL: Execute speech and tool simultaneously
    """
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"


class VariableAssignmentOperator(str, Enum):
    """
    Operators for dynamic variable assignments from tool results.
    
    SET: Always set the variable to the value
    SET_IF_EXISTS: Only set if the source field exists in result
    SET_IF_TRUTHY: Only set if the source value is truthy
    APPEND: Append value to existing list/string
    INCREMENT: Increment numeric value
    TRANSFORM: Apply a custom function to transform the value
    """
    SET = "set"
    SET_IF_EXISTS = "set_if_exists"
    SET_IF_TRUTHY = "set_if_truthy"
    APPEND = "append"
    INCREMENT = "increment"
    TRANSFORM = "transform"


class SpeechContextScope(str, Enum):
    """
    Defines what context the LLM uses when generating speech in AUTO mode.
    
    FULL_CONTEXT: Use entire conversation history and tool context
    TOOL_ONLY: Use only tool name, description, and parameters
    LAST_MESSAGE: Use only the last user message and tool info
    CUSTOM: Use custom instruction provided in llm_instruction field
    """
    FULL_CONTEXT = "full_context"
    TOOL_ONLY = "tool_only"
    LAST_MESSAGE = "last_message"
    CUSTOM = "custom"


class TransformExecutionMode(str, Enum):
    """
    Execution mode for custom transform functions.
    
    SYNC: Execute transform synchronously, block until complete
    ASYNC: Execute transform asynchronously, don't block tool result
    AWAIT: Execute transform asynchronously but wait for result before returning
    """
    SYNC = "sync"
    ASYNC = "async"
    AWAIT = "await"