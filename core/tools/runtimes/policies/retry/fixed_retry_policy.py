from typing import Callable, Awaitable, Any, Optional, List, Type
from .retry_policy import IRetryPolicy
import asyncio
import random

class FixedRetryPolicy(IRetryPolicy):
    """
    Fixed delay retry policy.
    
    Retries with a fixed delay between attempts. Simple and predictable.
    
    Features:
        - Configurable number of attempts
        - Fixed delay between retries
        - Configurable retryable exceptions
        - Optional jitter to avoid thundering herd
    
    Usage:
        policy = FixedRetryPolicy(
            max_attempts=3,
            delay_seconds=2.0,
            jitter=0.5  # ±0.5 seconds random jitter
        )
        
        spec.retry_policy = policy
    
    Example:
        # Attempt 1: Execute immediately
        # Fails
        # Wait 2 seconds
        # Attempt 2: Execute
        # Fails
        # Wait 2 seconds
        # Attempt 3: Execute
        # If fails, raise exception
    """
    
    def __init__(
        self,
        max_attempts: int = 3,
        delay_seconds: float = 1.0,
        jitter: float = 0.0,
        retryable_exceptions: Optional[List[Type[Exception]]] = None
    ):
        """
        Initialize fixed retry policy.
        
        Args:
            max_attempts: Maximum number of attempts (including first)
            delay_seconds: Fixed delay between retries
            jitter: Random jitter to add/subtract from delay (seconds)
            retryable_exceptions: List of exception types to retry
        """
        self.max_attempts = max_attempts
        self.delay_seconds = delay_seconds
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions or [
            TimeoutError,
            ConnectionError,
            asyncio.TimeoutError,
        ]
    
    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """Check if should retry based on exception type and attempt count."""
        if attempt >= self.max_attempts - 1:  # -1 because attempt is 0-based
            return False
        
        return any(isinstance(exception, exc_type) for exc_type in self.retryable_exceptions)
    
    async def execute_with_retry(
        self,
        func: Callable[[], Awaitable[Any]],
        tool_name: str
    ) -> Any:
        """Execute with fixed delay retry."""
        last_exception = None
        
        for attempt in range(self.max_attempts):
            try:
                result = await func()
                return result
            except Exception as e:
                last_exception = e
                
                if not self.should_retry(e, attempt):
                    raise
                
                if attempt < self.max_attempts - 1:
                    # Calculate delay with jitter
                    delay = self.delay_seconds
                    if self.jitter > 0:
                        delay += random.uniform(-self.jitter, self.jitter)
                    delay = max(0, delay)  # Ensure non-negative
                    
                    await asyncio.sleep(delay)
        
        # All retries exhausted
        raise last_exception
