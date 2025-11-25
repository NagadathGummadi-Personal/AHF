"""
Circuit Breaker Interface for Tools Specification System.

This module defines the interface for circuit breaker policies that prevent
cascading failures by "opening the circuit" after a threshold of failures.
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Awaitable


class ICircuitBreakerPolicy(ABC):
    """
    Interface for circuit breaker policies.
    
    Circuit breakers prevent cascading failures by stopping requests to a
    failing service after a threshold is reached.
    
    Methods:
        execute_with_breaker: Execute function with circuit breaker protection
        get_state: Get current circuit breaker state
        reset: Reset the circuit breaker
    
    States:
        CLOSED: Normal operation, requests pass through
        OPEN: Circuit is open, requests fail immediately
        HALF_OPEN: Testing if service has recovered
    """
    
    @abstractmethod
    async def execute_with_breaker(
        self,
        func: Callable[[], Awaitable[Any]],
        tool_name: str
    ) -> Any:
        """
        Execute a function with circuit breaker protection.
        
        Args:
            func: Async function to execute
            tool_name: Name of the tool (used for tracking state)
            
        Returns:
            Result from the function
            
        Raises:
            Exception: If circuit is open or function fails
        """
        pass
    
    @abstractmethod
    def get_state(self, tool_name: str) -> str:
        """
        Get current state of circuit breaker for a tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            State string: CircuitBreakerState.CLOSED, CircuitBreakerState.OPEN, or CircuitBreakerState.HALF_OPEN
        """
        pass
    
    @abstractmethod
    def reset(self, tool_name: str):
        """
        Reset the circuit breaker for a tool.
        
        Args:
            tool_name: Name of the tool
        """
        pass

