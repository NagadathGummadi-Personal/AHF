from typing import Callable, Awaitable, Any
from .retry_policy import IRetryPolicy

class NoRetryPolicy(IRetryPolicy):
    """
    No retry policy - fail immediately on first error.
    
    Useful for:
    - Operations that should never retry
    - Development/testing
    - When circuit breaker handles resilience
    
    Usage:
        policy = NoRetryPolicy()
        spec.retry_policy = policy
        
        # First error causes immediate failure
    """
    
    async def execute_with_retry(
        self,
        func: Callable[[], Awaitable[Any]],
        tool_name: str
    ) -> Any:
        """Execute without retry."""
        return await func()
