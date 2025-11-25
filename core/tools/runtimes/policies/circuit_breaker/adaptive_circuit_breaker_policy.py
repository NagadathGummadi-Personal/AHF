"""
Adaptive Circuit Breaker Policy.

Adjusts thresholds based on error rates and service health.
"""

import time
from typing import Any, Callable, Dict, Awaitable
from .circuit_breaker import ICircuitBreakerPolicy
from ....enum import CircuitBreakerState
from ....constants import (
    CIRCUIT_BREAKER_OPEN_ERROR,
    FAILURES,
    SUCCESSES,
    RECENT_RESULTS,
    IS_OPEN,
    OPENED_AT,
    CURRENT_THRESHOLD
)



class AdaptiveCircuitBreakerPolicy(ICircuitBreakerPolicy):
    """
    Adaptive circuit breaker that adjusts thresholds based on error rates.
    
    Unlike standard circuit breakers with fixed thresholds, this implementation
    adapts based on:
    - Recent error rate
    - Response time patterns
    - Success/failure ratio
    
    Features:
        - Dynamic threshold adjustment
        - Error rate monitoring
        - Gradual recovery
        - Configurable sensitivity
    
    Usage:
        policy = AdaptiveCircuitBreakerPolicy(
            base_threshold=5,
            max_threshold=20,
            error_rate_threshold=0.5,  # 50% error rate
            window_size=100             # Last 100 requests
        )
    
    Example:
        # Threshold starts at 5
        # If error rate < 50%, threshold increases to 20
        # If error rate > 50%, threshold decreases to 5
        # Adapts based on service behavior
    """
    
    def __init__(
        self,
        base_threshold: int = 5,
        max_threshold: int = 20,
        error_rate_threshold: float = 0.5,
        window_size: int = 100
    ):
        """
        Initialize adaptive circuit breaker.
        
        Args:
            base_threshold: Minimum failure threshold
            max_threshold: Maximum failure threshold
            error_rate_threshold: Error rate that triggers adjustment
            window_size: Number of recent requests to consider
        """
        self.base_threshold = base_threshold
        self.max_threshold = max_threshold
        self.error_rate_threshold = error_rate_threshold
        self.window_size = window_size
        self._states: Dict[str, Dict[str, Any]] = {}
    
    def _get_state(self, tool_name: str) -> Dict[str, Any]:
        """Get or create state for a tool."""
        if tool_name not in self._states:
            self._states[tool_name] = {
                FAILURES: 0,
                SUCCESSES: 0,
                RECENT_RESULTS: [],  # Boolean list of recent results
                IS_OPEN: False,
                OPENED_AT: None,
                CURRENT_THRESHOLD: self.base_threshold
            }
        return self._states[tool_name]
    
    def _calculate_error_rate(self, state: Dict[str, Any]) -> float:
        """Calculate current error rate."""
        recent = state[RECENT_RESULTS]
        if not recent:
            return 0.0
        errors = sum(1 for r in recent if not r)
        return errors / len(recent)
    
    def _adjust_threshold(self, state: Dict[str, Any]):
        """Adjust threshold based on error rate."""
        error_rate = self._calculate_error_rate(state)
        
        if error_rate < self.error_rate_threshold / 2:
            # Service is healthy, increase threshold
            state[CURRENT_THRESHOLD] = min(
                state[CURRENT_THRESHOLD] + 1,
                self.max_threshold
            )
        elif error_rate > self.error_rate_threshold:
            # Service is unhealthy, decrease threshold
            state[CURRENT_THRESHOLD] = max(
                state[CURRENT_THRESHOLD] - 1,
                self.base_threshold
            )
    
    async def execute_with_breaker(
        self,
        func: Callable[[], Awaitable[Any]],
        tool_name: str
    ) -> Any:
        """Execute with adaptive circuit breaker."""
        state = self._get_state(tool_name)
        
        # Check if circuit is open
        if state[IS_OPEN]:
            # Check if recovery timeout has passed
            if time.time() - state[OPENED_AT] > 30:  # Recovery timeout
                state[IS_OPEN] = False
                state[FAILURES] = 0
            else:
                raise Exception(CIRCUIT_BREAKER_OPEN_ERROR.format(TOOL_NAME=tool_name))
        
        try:
            result = await func()
            
            # Record success
            state[SUCCESSES] += 1
            state[FAILURES] = 0
            state[RECENT_RESULTS].append(True)
            
            # Trim window
            if len(state[RECENT_RESULTS]) > self.window_size:
                state[RECENT_RESULTS].pop(0)
            
            # Adjust threshold
            self._adjust_threshold(state)
            
            return result
            
        except Exception:
            # Record failure
            state[FAILURES] += 1
            state[RECENT_RESULTS].append(False)
            
            # Trim window
            if len(state[RECENT_RESULTS]) > self.window_size:
                state[RECENT_RESULTS].pop(0)
            
            # Check if threshold exceeded
            if state[FAILURES] >= state[CURRENT_THRESHOLD]:
                state[IS_OPEN] = True
                state[OPENED_AT] = time.time()
            
            # Adjust threshold
            self._adjust_threshold(state)
            
            raise
    
    def get_state(self, tool_name: str) -> str:
        """Get circuit state."""
        state = self._get_state(tool_name)
        return CircuitBreakerState.OPEN if state[IS_OPEN] else CircuitBreakerState.CLOSED
    
    def reset(self, tool_name: str):
        """Reset circuit breaker."""
        if tool_name in self._states:
            self._states[tool_name] = {
                FAILURES: 0,
                SUCCESSES: 0,
                RECENT_RESULTS: [],
                IS_OPEN: False,
                OPENED_AT: None,
                CURRENT_THRESHOLD: self.base_threshold
            }

