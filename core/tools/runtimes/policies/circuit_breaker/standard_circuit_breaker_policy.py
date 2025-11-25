"""
Standard Circuit Breaker Policy.

Uses pybreaker library with fixed thresholds for failure detection.
"""

from typing import Any, Callable, Dict, Awaitable
from .circuit_breaker import ICircuitBreakerPolicy
from ....enum import CircuitBreakerState
from ....constants import CIRCUIT_BREAKER_OPEN_ERROR


class StandardCircuitBreakerPolicy(ICircuitBreakerPolicy):
    """
    Standard circuit breaker using pybreaker library.
    
    Uses fixed thresholds for failure detection:
    - Failure Threshold: Number of failures before opening circuit
    - Recovery Timeout: Time before attempting to close circuit
    
    Features:
        - Wraps pybreaker library
        - Per-tool circuit breakers
        - Automatic state management
        - Failure counting
    
    Usage:
        policy = StandardCircuitBreakerPolicy(
            failure_threshold=5,    # Open after 5 failures
            recovery_timeout=30     # Try recovery after 30 seconds
        )
        
        spec.circuit_breaker_policy = policy
    
    Example:
        # Circuit starts CLOSED
        result = await policy.execute_with_breaker(my_func, 'tool1')
        
        # After 5 failures, circuit OPENS
        # Subsequent calls fail immediately
        
        # After 30 seconds, circuit goes HALF_OPEN
        # One test call allowed
        
        # If test succeeds, circuit CLOSES
        # If test fails, circuit stays OPEN
    """
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 30):
        """
        Initialize standard circuit breaker policy.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds before attempting recovery
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._breakers: Dict[str, Any] = {}  # tool_name -> CircuitBreaker
    
    def _get_breaker(self, tool_name: str):
        """Get or create circuit breaker for a tool."""
        if tool_name not in self._breakers:
            from utils.circuitBreaker.CircuitBreaker import CircuitBreaker
            self._breakers[tool_name] = CircuitBreaker(
                max_failures=self.failure_threshold,
                reset_timeout=self.recovery_timeout
            )
        return self._breakers[tool_name]
    
    async def execute_with_breaker(
        self,
        func: Callable[[], Awaitable[Any]],
        tool_name: str
    ) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Async function to execute
            tool_name: Tool name for circuit tracking
            
        Returns:
            Function result
            
        Raises:
            Exception: If circuit is open or function fails
        """
        breaker = self._get_breaker(tool_name)
        
        # Check if circuit is open
        if breaker.state.value == CircuitBreakerState.OPEN:
            raise Exception(CIRCUIT_BREAKER_OPEN_ERROR.format(TOOL_NAME=tool_name))
        
        try:
            result = await func()
            breaker.record_success()
            return result
        except Exception as e:
            breaker.record_failure()
            # Check if circuit opened after this failure
            if breaker.state.value == CircuitBreakerState.OPEN:
                raise Exception(CIRCUIT_BREAKER_OPEN_ERROR.format(TOOL_NAME=tool_name)) from e
            raise
    
    def get_state(self, tool_name: str) -> str:
        """Get circuit breaker state."""
        if tool_name not in self._breakers:
            return CircuitBreakerState.CLOSED
        breaker = self._breakers[tool_name]
        # Convert breaker state value to enum (breaker.state.value is a string)
        state_value = breaker.state.value
        # Map string values to enum values
        if state_value == CircuitBreakerState.OPEN:
            return CircuitBreakerState.OPEN
        elif state_value == CircuitBreakerState.CLOSED:
            return CircuitBreakerState.CLOSED
        elif state_value == CircuitBreakerState.HALF_OPEN:
            return CircuitBreakerState.HALF_OPEN
        # Fallback: return as-is if unknown state
        return state_value
    
    def reset(self, tool_name: str):
        """Reset circuit breaker."""
        if tool_name in self._breakers:
            self._breakers[tool_name].close()

