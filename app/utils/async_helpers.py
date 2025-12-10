"""
Async Helpers

Utilities for async operations.

Version: 1.0.0
"""

import asyncio
from functools import wraps
from typing import Any, Awaitable, Callable, List, Optional, TypeVar

T = TypeVar("T")


async def run_with_timeout(
    coro: Awaitable[T],
    timeout_ms: int,
    default: Optional[T] = None,
) -> T:
    """
    Run a coroutine with timeout.
    
    Args:
        coro: Coroutine to run
        timeout_ms: Timeout in milliseconds
        default: Default value if timeout
        
    Returns:
        Result or default
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout_ms / 1000)
    except asyncio.TimeoutError:
        if default is not None:
            return default
        raise


async def gather_with_cancel(
    *coros: Awaitable[Any],
    return_exceptions: bool = False,
) -> List[Any]:
    """
    Gather coroutines with proper cancellation on failure.
    
    If any coroutine fails, others are cancelled.
    """
    tasks = [asyncio.create_task(coro) for coro in coros]
    
    try:
        return await asyncio.gather(*tasks, return_exceptions=return_exceptions)
    except Exception:
        # Cancel remaining tasks
        for task in tasks:
            if not task.done():
                task.cancel()
        raise


def async_retry(
    max_retries: int = 3,
    delay_ms: int = 1000,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
):
    """
    Decorator for async retry with exponential backoff.
    
    Args:
        max_retries: Maximum retry attempts
        delay_ms: Initial delay between retries
        backoff: Backoff multiplier
        exceptions: Exception types to catch
    """
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None
            current_delay = delay_ms
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        await asyncio.sleep(current_delay / 1000)
                        current_delay *= backoff
            
            raise last_exception
        
        return wrapper
    return decorator


def create_background_task(
    coro: Awaitable[Any],
    name: Optional[str] = None,
    on_done: Optional[Callable[[asyncio.Task], None]] = None,
) -> asyncio.Task:
    """
    Create a background task that doesn't block.
    
    Args:
        coro: Coroutine to run
        name: Optional task name
        on_done: Callback when task completes
        
    Returns:
        Created task
    """
    task = asyncio.create_task(coro, name=name)
    
    if on_done:
        task.add_done_callback(on_done)
    
    return task


class AsyncLazyValue:
    """
    Lazy-initialized async value.
    
    Computes value on first access and caches it.
    """
    
    def __init__(self, factory: Callable[[], Awaitable[T]]):
        self._factory = factory
        self._value: Optional[T] = None
        self._initialized = False
        self._lock = asyncio.Lock()
    
    async def get(self) -> T:
        """Get the value, computing if needed."""
        if self._initialized:
            return self._value
        
        async with self._lock:
            if not self._initialized:
                self._value = await self._factory()
                self._initialized = True
            
            return self._value
    
    def is_initialized(self) -> bool:
        """Check if value is initialized."""
        return self._initialized
    
    def reset(self) -> None:
        """Reset to uninitialized state."""
        self._initialized = False
        self._value = None

