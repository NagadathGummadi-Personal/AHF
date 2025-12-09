"""
Cache Interfaces.

Defines the protocols for cache/memory operations with TTL and locking support.
Used by tools and other components that need temporary storage with expiration.

Version: 1.0.0
"""

from __future__ import annotations
from typing import Any, AsyncContextManager, Optional, Protocol, runtime_checkable
from contextlib import asynccontextmanager


@runtime_checkable
class ICache(Protocol):
    """
    Interface for cache operations with TTL and locking support.
    
    Provides temporary storage with time-to-live and distributed locking
    capabilities. Used by tools for caching results and ensuring idempotency.
    
    Built-in implementations:
    - NoOpCache: No-op implementation for stateless execution
    
    Future implementations:
    - RedisCache: Redis-based distributed cache
    - MemCache: In-memory cache with TTL
    
    Example:
        class RedisCache(ICache):
            async def get(self, key: str) -> Any:
                return await self.redis.get(key)
            
            async def set(self, key: str, value: Any, ttl_s: Optional[int] = None) -> None:
                await self.redis.set(key, value, ex=ttl_s)
            
            @asynccontextmanager
            async def lock(self, key: str, ttl_s: int = 10):
                lock = await self.redis.lock(f"lock:{key}", timeout=ttl_s)
                try:
                    yield
                finally:
                    await lock.release()
    """
    
    async def get(self, key: str) -> Any:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        ...
    
    async def set(self, key: str, value: Any, ttl_s: Optional[int] = None) -> None:
        """
        Set value in cache with optional TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_s: Time-to-live in seconds (None = no expiration)
        """
        ...
    
    async def set_if_absent(self, key: str, value: Any, ttl_s: Optional[int] = None) -> bool:
        """
        Set value only if key doesn't exist (atomic operation).
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_s: Time-to-live in seconds
            
        Returns:
            True if value was set, False if key already exists
        """
        ...
    
    async def delete(self, key: str) -> None:
        """
        Delete value from cache.
        
        Args:
            key: Cache key to delete
        """
        ...
    
    @asynccontextmanager
    async def lock(self, key: str, ttl_s: int = 10) -> AsyncContextManager[None]:
        """
        Acquire a distributed lock.
        
        Args:
            key: Lock key
            ttl_s: Lock time-to-live in seconds
            
        Yields:
            None (context manager)
            
        Example:
            async with cache.lock("resource-id"):
                # Critical section
                pass
        """
        yield


# Alias for backward compatibility with tools
IToolMemory = ICache


