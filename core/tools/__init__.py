"""
Tools Specification System (v1.2.0)

This module provides a modular, asynchronous tool execution system with SOLID separation,
strict validation, security, idempotency, tracing, metrics, and circuit breaker-aware retries.

Core components:
- ToolType: Enumeration for tool types (Function, Http, DB)
- ToolReturnType: Enumeration for return formats (JSON, Text)
- ToolReturnTarget: Enumeration for return routing (Human, LLM, Agent, Step)
- ToolParameter: Schema definition for tool parameters
- ToolSpec: Main tool specification with metadata and configuration
- ToolContext: Execution context with tracing, auth, and dependencies
- ToolResult: Standardized result format with usage metrics
- ToolError: Exception class for tool errors
- Protocol interfaces for pluggable components (validators, security, policies, etc.)
- Base executor classes for common tool types
- Example implementations and usage patterns
"""

from .enum import ToolType, ToolReturnType, ToolReturnTarget

# Core spec models (re-export from subpackage)
from .spec import (
    ToolContext,
    ToolUsage,
    ToolResult,
    ToolError,
    ToolParameter,
    ToolSpec,
    FunctionToolSpec,
    HttpToolSpec,
    DbToolSpec,
    RetryConfig,
    CircuitBreakerConfig,
    IdempotencyConfig,
)

# Interfaces (re-export from subpackage)
from .interfaces import (
    IToolExecutor,
    IToolValidator,
    IToolSecurity,
    IToolPolicy,
    IToolEmitter,
    IToolMemory,
    IToolMetrics,
    IToolTracer,
    IToolLimiter,
)

# Implementations / executors / validators
from .runtimes.validators import BasicValidator, NoOpValidator
from .runtimes.executors import (
    BaseToolExecutor,
    FunctionToolExecutor,
    HttpToolExecutor,
    ExecutorFactory,
    NoOpExecutor,
)
from .runtimes.security import NoOpSecurity, BasicSecurity
from .runtimes.policies import NoOpPolicy
from .runtimes.emitters import NoOpEmitter
from .runtimes.memory import NoOpMemory
from .runtimes.metrics import NoOpMetrics
from .runtimes.tracers import NoOpTracer
from .runtimes.limiters import NoOpLimiter

# Serialization utilities
from .serializers import (
    tool_to_json,
    tool_to_dict,
    tool_from_json,
    tool_from_dict,
    ToolSerializationError,
)

__all__ = [
    # Types
    "ToolType",
    "ToolReturnType",
    "ToolReturnTarget",
    "ToolUsage",
    "ToolResult",
    "ToolError",
    "ToolParameter",
    "ToolSpec",
    "FunctionToolSpec",
    "HttpToolSpec",
    "DbToolSpec",
    "ToolContext",
    "RetryConfig",
    "CircuitBreakerConfig",
    "IdempotencyConfig",
    # Interfaces
    "IToolExecutor",
    "IToolValidator",
    "IToolSecurity",
    "IToolPolicy",
    "IToolEmitter",
    "IToolMemory",
    "IToolMetrics",
    "IToolTracer",
    "IToolLimiter",
    # Implementations
    "BasicValidator",
    "NoOpValidator",
    "BaseToolExecutor",
    "FunctionToolExecutor",
    "HttpToolExecutor",
    "ExecutorFactory",
    "NoOpExecutor",
    "NoOpSecurity",
    "BasicSecurity",
    "NoOpPolicy",
    "NoOpEmitter",
    "NoOpMemory",
    "NoOpMetrics",
    "NoOpTracer",
    "NoOpLimiter",
    # Serialization
    "tool_to_json",
    "tool_to_dict",
    "tool_from_json",
    "tool_from_dict",
    "ToolSerializationError",
]
