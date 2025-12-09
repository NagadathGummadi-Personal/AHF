"""
Cache Factory.

Provides a centralized way to create and register cache implementations by name.
"""

from typing import Dict

from ..interfaces import ICache
from ..constants import NOOP, UNKNOWN_MEMORY_ERROR, COMMA, SPACE
from .noop_cache import NoOpCache


class CacheFactory:
    """
    Factory for creating cache instances.
    
    Built-in Cache Implementations:
        - 'noop': NoOpCache - No caching (for stateless execution)
    
    Usage:
        # Get built-in cache
        cache = CacheFactory.get_cache('noop')
        
        # Register custom cache implementation
        CacheFactory.register('redis', RedisCache())
        cache = CacheFactory.get_cache('redis')
    """
    
    _caches: Dict[str, ICache] = {
        NOOP: NoOpCache(),
    }
    
    @classmethod
    def get_cache(cls, name: str = NOOP) -> ICache:
        """
        Get a cache implementation by name.
        
        Args:
            name: Cache implementation name ('noop', 'redis', etc.)
            
        Returns:
            ICache instance
            
        Raises:
            ValueError: If cache name is not registered
        """
        cache = cls._caches.get(name)
        
        if not cache:
            available = (COMMA + SPACE).join(cls._caches.keys())
            raise ValueError(
                UNKNOWN_MEMORY_ERROR.format(MEMORY_NAME=name, AVAILABLE_MEMORIES=available)
            )
        
        return cache
    
    @classmethod
    def register(cls, name: str, cache: ICache) -> None:
        """
        Register a custom cache implementation.
        
        Args:
            name: Name to register the cache under
            cache: Cache instance implementing ICache
        
        Example:
            class RedisCache(ICache):
                async def get(self, key: str):
                    return await redis_client.get(key)
                # ... implement other methods
            
            CacheFactory.register('redis', RedisCache())
        """
        cls._caches[name] = cache
    
    @classmethod
    def unregister(cls, name: str) -> None:
        """
        Unregister a cache implementation.
        
        Args:
            name: Name of the cache to unregister
        """
        if name == NOOP:
            raise ValueError("Cannot unregister built-in 'noop' cache")
        cls._caches.pop(name, None)
    
    @classmethod
    def list_available(cls) -> list:
        """List all registered cache implementations."""
        return list(cls._caches.keys())


# Backward compatibility aliases
MemoryFactory = CacheFactory


