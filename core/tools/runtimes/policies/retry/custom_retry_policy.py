from typing import Callable, Awaitable, Any, Optional
from .retry_policy import IRetryPolicy
from ....constants import RETRY_FUNC_NOT_CALLABLE_ERROR

class CustomRetryPolicy(IRetryPolicy):
    """
    Custom retry policy using user-provided function.
    
    Allows complete control over retry logic by accepting a custom retry function.
    The function receives the operation, current attempt, and last exception.
    
    Features:
        - Complete flexibility
        - Can access external state
        - Complex business logic
        - Integration with external services
    
    Usage:
        async def my_retry_logic(func, attempt, last_exception):
            if attempt >= 5:
                raise last_exception
            
            if isinstance(last_exception, RateLimitError):
                await asyncio.sleep(60)  # Wait 1 minute for rate limit
            else:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
            
            return await func()
        
        policy = CustomRetryPolicy(my_retry_logic)
        spec.retry_policy = policy
    """
    
    def __init__(
        self,
        retry_func: Callable[[Callable[[], Awaitable[Any]], int, Optional[Exception]], Awaitable[Any]]
    ):
        """
        Initialize with custom retry function.
        
        Args:
            retry_func: Async function that implements retry logic
                       Signature: async def(func, attempt, last_exception) -> result
        
        Raises:
            TypeError: If retry_func is not callable
        """
        if not callable(retry_func):
            raise TypeError(RETRY_FUNC_NOT_CALLABLE_ERROR)
        
        self.retry_func = retry_func
    
    async def execute_with_retry(
        self,
        func: Callable[[], Awaitable[Any]],
        tool_name: str
    ) -> Any:
        """Execute with custom retry logic."""
        attempt = 0
        last_exception = None
        
        while True:
            try:
                if attempt == 0:
                    # First attempt
                    result = await func()
                else:
                    # Retry through custom function
                    result = await self.retry_func(func, attempt, last_exception)
                
                return result
                
            except Exception as e:
                last_exception = e
                attempt += 1
                
                # Let custom function decide if should continue
                # If it raises, we stop retrying
                if attempt >= 10:  # Safety limit
                    raise