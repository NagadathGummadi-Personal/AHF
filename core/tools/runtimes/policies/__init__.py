"""
Execution Policies for Tools Specification System.

This module provides pluggable strategies for circuit breakers and retry logic,
allowing different policy implementations for different tool types and use cases.

Policy Types:
=============
1. Circuit Breaker Policies - Prevent cascading failures
2. Retry Policies - Handle transient failures with retry logic

Architecture:
=============
Similar to idempotency module, provides:
- Abstract base interfaces
- Multiple built-in implementations  
- Factory pattern for creation
- Easy extensibility

Usage:
    from core.tools.executors.policies import (
        StandardCircuitBreakerPolicy,
        ExponentialBackoffRetryPolicy
    )
    
    # Configure at tool spec creation
    spec.circuit_breaker_policy = StandardCircuitBreakerPolicy()
    spec.retry_policy = ExponentialBackoffRetryPolicy()
"""

from .circuit_breaker import (
    ICircuitBreakerPolicy,
    StandardCircuitBreakerPolicy,
    AdaptiveCircuitBreakerPolicy,
    NoOpCircuitBreakerPolicy,
    CircuitBreakerPolicyFactory,
)

from .retry import (
    IRetryPolicy,
    NoRetryPolicy,
    FixedRetryPolicy,
    ExponentialBackoffRetryPolicy,
    CustomRetryPolicy,
    RetryPolicyFactory,
)

from .noop_policy import NoOpPolicy
from .policy_factory import PolicyFactory

__all__ = [
    # Circuit Breaker
    "ICircuitBreakerPolicy",
    "StandardCircuitBreakerPolicy",
    "AdaptiveCircuitBreakerPolicy",
    "NoOpCircuitBreakerPolicy",
    "CircuitBreakerPolicyFactory",
    # Retry
    "IRetryPolicy",
    "NoRetryPolicy",
    "FixedRetryPolicy",
    "ExponentialBackoffRetryPolicy",
    "CustomRetryPolicy",
    "RetryPolicyFactory",
    # General Policy
    "NoOpPolicy",
    "PolicyFactory",
]

