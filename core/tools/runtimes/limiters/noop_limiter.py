"""
No-Op Limiter Implementation.

Disables rate limiting for simple execution without throttling.
"""

from contextlib import asynccontextmanager
from typing import AsyncContextManager, Optional

from ...interfaces.tool_interfaces import IToolLimiter


class NoOpLimiter(IToolLimiter):
    """
    No-op implementation of IToolLimiter that doesn't enforce rate limits.
    
    Useful for:
    - Development/testing without rate limiting
    - Internal tools that don't need throttling
    - Trusted environments without rate limit constraints
    - Performance testing without throttling overhead
    
    Usage:
        limiter = NoOpLimiter()
        
        # Acquire is a no-op context manager
        async with limiter.acquire("api.calls", limit=100):
            # No actual rate limiting occurs
            await call_api()
    """
    
    @asynccontextmanager
    async def acquire(self, key: str, limit: Optional[int] = None) -> AsyncContextManager[None]:
        """
        Acquire rate limit (no-op implementation).
        
        Provides a no-op context manager that doesn't enforce rate limits.
        
        Args:
            key: Rate limit key (ignored)
            limit: Rate limit value (ignored)
            
        Yields:
            None
        """
        yield

