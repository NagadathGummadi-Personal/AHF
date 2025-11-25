"""
Circuit Breaker Policies for Tools Specification System.

This module provides pluggable circuit breaker strategies that prevent cascading
failures by "opening the circuit" after a threshold of failures.

Strategy Pattern Implementation:
=================================
All policies implement ICircuitBreakerPolicy, allowing runtime selection of
the appropriate circuit breaking strategy for each tool.

Available Strategies:
=====================
- StandardCircuitBreakerPolicy: Uses pybreaker with fixed thresholds
- AdaptiveCircuitBreakerPolicy: Adjusts thresholds based on error rates
- NoOpCircuitBreakerPolicy: Disables circuit breaking (for development/testing)

Usage:
    from core.tools.executors.policies import StandardCircuitBreakerPolicy
    
    # Configure at tool spec creation
    spec.circuit_breaker_policy = StandardCircuitBreakerPolicy(
        failure_threshold=5,
        recovery_timeout=30
    )
    
    # Or use factory
    from core.tools.executors.policies import CircuitBreakerPolicyFactory
    policy = CircuitBreakerPolicyFactory.get_policy('standard')
    spec.circuit_breaker_policy = policy

Extending:
==========
Create custom policy by implementing ICircuitBreakerPolicy:

    class RateLimitCircuitBreaker(ICircuitBreakerPolicy):
        async def execute_with_breaker(self, func, tool_name, *args, **kwargs):
            # Your logic
            pass

Note:
    Circuit breakers are stateful - they maintain failure counts and state
    across multiple executions of the same tool.
"""

from .circuit_breaker import ICircuitBreakerPolicy
from .standard_circuit_breaker_policy import StandardCircuitBreakerPolicy
from .adaptive_circuit_breaker_policy import AdaptiveCircuitBreakerPolicy
from .noop_circuit_breaker_policy import NoOpCircuitBreakerPolicy
from .circuit_breaker_policy_factory import CircuitBreakerPolicyFactory

__all__ = [
    "ICircuitBreakerPolicy",
    "StandardCircuitBreakerPolicy",
    "AdaptiveCircuitBreakerPolicy",
    "NoOpCircuitBreakerPolicy",
    "CircuitBreakerPolicyFactory",
]

