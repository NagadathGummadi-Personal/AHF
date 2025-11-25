from typing import Callable, Awaitable, Any, Optional, List, Type
from .retry_policy import IRetryPolicy
import asyncio
import random

class ExponentialBackoffRetryPolicy(IRetryPolicy):
    """
    Exponential backoff retry policy.
    
    Retries with exponentially increasing delays. Good for handling rate limits
    and giving failing services time to recover.
    
    Features:
        - Exponentially increasing delays
        - Configurable base and max delay
        - Optional jitter
        - Configurable multiplier
    
    Delay Formula:
        delay = min(base_delay * (multiplier ^ attempt), max_delay) ± jitter
    
    Usage:
        policy = ExponentialBackoffRetryPolicy(
            max_attempts=5,
            base_delay=1.0,
            max_delay=30.0,
            multiplier=2.0,
            jitter=0.1
        )
    
    Example:
        # Attempt 1: Execute immediately
        # Fails, wait 1 second
        # Attempt 2: Execute
        # Fails, wait 2 seconds
        # Attempt 3: Execute
        # Fails, wait 4 seconds
        # Attempt 4: Execute
        # Fails, wait 8 seconds
        # Attempt 5: Execute
        # If fails, raise exception
    """
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        multiplier: float = 2.0,
        jitter: float = 0.1,
        retryable_exceptions: Optional[List[Type[Exception]]] = None
    ):
        """
        Initialize exponential backoff retry policy.
        
        Args:
            max_attempts: Maximum number of attempts
            base_delay: Base delay for first retry (seconds)
            max_delay: Maximum delay between retries (seconds)
            multiplier: Exponential multiplier (typically 2.0)
            jitter: Random jitter as percentage (0.0-1.0)
            retryable_exceptions: List of exception types to retry
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.multiplier = multiplier
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions or [
            TimeoutError,
            ConnectionError,
            asyncio.TimeoutError,
        ]
    
    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """Check if should retry."""
        if attempt >= self.max_attempts - 1:
            return False
        
        return any(isinstance(exception, exc_type) for exc_type in self.retryable_exceptions)
    
    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for given attempt with exponential backoff.
        
        Args:
            attempt: Current attempt number (0-based)
            
        Returns:
            Delay in seconds
        """
        # Exponential backoff: base * multiplier^attempt
        delay = self.base_delay * (self.multiplier ** attempt)
        
        # Cap at max delay
        delay = min(delay, self.max_delay)
        
        # Add jitter
        if self.jitter > 0:
            jitter_amount = delay * self.jitter
            delay += random.uniform(-jitter_amount, jitter_amount)
        
        return max(0, delay)
    
    async def execute_with_retry(
        self,
        func: Callable[[], Awaitable[Any]],
        tool_name: str
    ) -> Any:
        """Execute with exponential backoff retry."""
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
                    delay = self.calculate_delay(attempt)
                    await asyncio.sleep(delay)
        
        # All retries exhausted
        raise last_exception
