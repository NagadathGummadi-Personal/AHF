"""
Tools Specification System (v1.3.0)

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

New in v1.3.0:
- InterruptionConfig: Control whether user input can interrupt tool execution
- PreToolSpeechConfig: Configure agent speech before tool execution
- ExecutionConfig: Control speech/execution timing (sequential or parallel)
- DynamicVariableConfig: Update variables based on tool results
- SpeechMode: Enum for speech generation modes (AUTO, RANDOM, CONSTANT)
- ExecutionMode: Enum for execution modes (SEQUENTIAL, PARALLEL)
- VariableAssignmentOperator: Enum for variable assignment operators
"""

from .enum import (
    ToolType,
    ToolReturnType,
    ToolReturnTarget,
    SpeechMode,
    ExecutionMode,
    VariableAssignmentOperator,
    SpeechContextScope,
    TransformExecutionMode,
)

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
    InterruptionConfig,
    PreToolSpeechConfig,
    ExecutionConfig,
    VariableAssignment,
    DynamicVariableConfig,
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
    AioHttpExecutor,
    ExecutorFactory,
    NoOpExecutor,
    # Session Manager for Fargate/containerized deployments
    HttpSessionManager,
    get_session_manager,
    shutdown_session_manager,
    install_signal_handlers,
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
    # Types & Enums
    "ToolType",
    "ToolReturnType",
    "ToolReturnTarget",
    "SpeechMode",
    "ExecutionMode",
    "VariableAssignmentOperator",
    "SpeechContextScope",
    "TransformExecutionMode",
    "ToolUsage",
    "ToolResult",
    "ToolError",
    "ToolParameter",
    "ToolSpec",
    "FunctionToolSpec",
    "HttpToolSpec",
    "DbToolSpec",
    "ToolContext",
    # Config classes
    "RetryConfig",
    "CircuitBreakerConfig",
    "IdempotencyConfig",
    "InterruptionConfig",
    "PreToolSpeechConfig",
    "ExecutionConfig",
    "VariableAssignment",
    "DynamicVariableConfig",
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
    "AioHttpExecutor",
    "ExecutorFactory",
    "NoOpExecutor",
    # Session Manager (Fargate/containerized deployments)
    "HttpSessionManager",
    "get_session_manager",
    "shutdown_session_manager",
    "install_signal_handlers",
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
