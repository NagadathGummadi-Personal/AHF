"""
Limiter Factory for Tools Specification System.

Provides a centralized way to create and register rate limiter implementations by name.
"""

from typing import Dict

from ...interfaces.tool_interfaces import IToolLimiter
from .noop_limiter import NoOpLimiter

from ...constants import (
    NOOP,
    UNKNOWN_LIMITER_ERROR,
    COMMA,
    SPACE
)


class LimiterFactory:
    """
    Factory for creating rate limiter instances.
    
    Built-in Limiter Implementations:
        - 'noop': NoOpLimiter - No rate limiting (for testing/development)
    
    Usage:
        # Get built-in limiter
        limiter = LimiterFactory.get_limiter('noop')
        
        # Register custom limiter implementation
        LimiterFactory.register('redis', RedisLimiter())
        limiter = LimiterFactory.get_limiter('redis')
    """
    
    _limiters: Dict[str, IToolLimiter] = {
        NOOP: NoOpLimiter(),
    }
    
    @classmethod
    def get_limiter(cls, name: str = NOOP) -> IToolLimiter:
        """
        Get a limiter implementation by name.
        
        Args:
            name: Limiter implementation name ('noop', 'redis', etc.)
            
        Returns:
            IToolLimiter instance
            
        Raises:
            ValueError: If limiter name is not registered
        """
        limiter = cls._limiters.get(name)
        
        if not limiter:
            available = (COMMA + SPACE).join(cls._limiters.keys())
            raise ValueError(
                UNKNOWN_LIMITER_ERROR.format(LIMITER_NAME=name, AVAILABLE_LIMITERS=available)
            )
        
        return limiter
    
    @classmethod
    def register(cls, name: str, limiter: IToolLimiter):
        """
        Register a custom limiter implementation.
        
        Args:
            name: Name to register the limiter under
            limiter: Limiter instance implementing IToolLimiter
        
        Example:
            class RedisLimiter(IToolLimiter):
                @asynccontextmanager
                async def acquire(self, key: str, limit=None):
                    # Redis-based rate limiting logic
                    yield
            
            LimiterFactory.register('redis', RedisLimiter())
        """
        cls._limiters[name] = limiter

