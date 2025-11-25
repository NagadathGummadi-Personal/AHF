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