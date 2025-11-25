import asyncio
from abc import ABC, abstractmethod
from typing import Any, Callable, Awaitable

class IRetryPolicy(ABC):
    """
    Interface for retry policies.
    
    Retry policies handle transient failures by retrying operations with
    configurable delays and backoff strategies.
    
    Methods:
        execute_with_retry: Execute function with retry logic
        should_retry: Determine if an error should trigger retry
    """
    
    @abstractmethod
    async def execute_with_retry(
        self,
        func: Callable[[], Awaitable[Any]],
        tool_name: str
    ) -> Any:
        """
        Execute a function with retry logic.
        
        Args:
            func: Async function to execute
            tool_name: Name of the tool (for logging/metrics)
            
        Returns:
            Result from the function
            
        Raises:
            Exception: If all retries exhausted or non-retryable error
        """
        pass
    
    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """
        Determine if an error should trigger a retry.
        
        Args:
            exception: The exception that occurred
            attempt: Current attempt number (0-based)
            
        Returns:
            True if should retry, False otherwise
        """
        # Default: retry on common transient errors
        retryable_types = (
            TimeoutError,
            ConnectionError,
            asyncio.TimeoutError,
        )
        return isinstance(exception, retryable_types)








