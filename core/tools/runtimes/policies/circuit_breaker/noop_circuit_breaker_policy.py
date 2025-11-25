"""
No-Op Circuit Breaker Policy.

Disables circuit breaking for development/testing or gradual rollouts.
"""

from typing import Any, Callable, Awaitable
from .circuit_breaker import ICircuitBreakerPolicy
from ....enum import CircuitBreakerState


class NoOpCircuitBreakerPolicy(ICircuitBreakerPolicy):
    """
    No-op circuit breaker that doesn't actually break circuits.
    
    Useful for:
    - Development/testing
    - Disabling circuit breaking for specific tools
    - Gradually rolling out circuit breakers
    
    Usage:
        policy = NoOpCircuitBreakerPolicy()
        spec.circuit_breaker_policy = policy
        
        # All requests pass through, no circuit breaking
    """
    
    async def execute_with_breaker(
        self,
        func: Callable[[], Awaitable[Any]],
        tool_name: str
    ) -> Any:
        """Execute without circuit breaking."""
        return await func()
    
    def get_state(self, tool_name: str) -> str:
        """Always returns 'closed'."""
        return CircuitBreakerState.CLOSED
    
    def reset(self, tool_name: str):
        """No-op reset."""
        pass

