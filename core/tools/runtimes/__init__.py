"""
Runtimes for Tools Specification System.

This module provides runtime components for tool execution including executors,
validators, policies, idempotency, and usage calculators.

Folder Structure:
=================
- executors/: Executor implementations organized by type
  - db_executors/: Database-specific executors
  - function_executors/: Function-based executors  
  - http_executors/: HTTP-based executors
  - db_strategies/: Database operation strategies
- policies/: Retry and circuit breaker policies
- idempotency/: Idempotency key generators
- validators/: Parameter validators
- security/: Security and authorization implementations
- emitters/: Event emission implementations
- memory/: Memory and caching implementations
- metrics/: Metrics collection implementations
- tracers/: Distributed tracing implementations
- limiters/: Rate limiting implementations
- usage_calculators/: Usage tracking and cost calculation

Core Components:
================
- IToolExecutor: Base executor interface (from tool_interfaces)
- BaseToolExecutor: Base implementation with common patterns
- ExecutorFactory: Factory for creating executors
- Various executor implementations (Function, HTTP, DB)

Usage:
    from core.tools.runtimes import FunctionToolExecutor, BaseToolExecutor
    from core.tools.runtimes.executors.db_executors import DynamoDBExecutor
    
    # Function executor
    executor = FunctionToolExecutor(spec, my_function)
    
    # Database executor
    db_executor = DynamoDBExecutor(spec)
    
    # Use factory
    executor = ExecutorFactory.create_executor(spec, my_function)

Extending:
==========
All executors follow SOLID principles and can be extended by inheriting
from base classes or implementing interfaces.
"""

# Re-export from executors module
from .executors import (
    IToolExecutor,
    BaseToolExecutor,
    ExecutorFactory,
    NoOpExecutor,
    FunctionToolExecutor,
    HttpToolExecutor,
    BaseDbExecutor,
    DynamoDBExecutor,
)

# Re-export from validators module
from .validators import NoOpValidator, BasicValidator, ValidatorFactory

# Re-export from security module
from .security import NoOpSecurity, BasicSecurity, SecurityFactory

# Re-export from policies module
from .policies import NoOpPolicy, PolicyFactory

# Re-export from emitters module
from .emitters import NoOpEmitter, EmitterFactory

# Re-export from memory module
from .memory import NoOpMemory, MemoryFactory

# Re-export from metrics module
from .metrics import NoOpMetrics, MetricsFactory

# Re-export from tracers module
from .tracers import NoOpTracer, TracerFactory

# Re-export from limiters module
from .limiters import NoOpLimiter, LimiterFactory

__all__ = [
    # Core
    "IToolExecutor",
    "BaseToolExecutor",
    "ExecutorFactory",
    "NoOpExecutor",
    # Executors
    "FunctionToolExecutor",
    "HttpToolExecutor",
    # Database executors
    "BaseDbExecutor",
    "DynamoDBExecutor",
    # Validators
    "NoOpValidator",
    "BasicValidator",
    "ValidatorFactory",
    # Security
    "NoOpSecurity",
    "BasicSecurity",
    "SecurityFactory",
    # Policy
    "NoOpPolicy",
    "PolicyFactory",
    # Emitter
    "NoOpEmitter",
    "EmitterFactory",
    # Memory
    "NoOpMemory",
    "MemoryFactory",
    # Metrics
    "NoOpMetrics",
    "MetricsFactory",
    # Tracer
    "NoOpTracer",
    "TracerFactory",
    # Limiter
    "NoOpLimiter",
    "LimiterFactory",
]


