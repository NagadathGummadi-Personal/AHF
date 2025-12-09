"""
Cache implementations for Tools and other components.

Provides cache/memory operations with TTL and locking support.
"""

from .noop_cache import NoOpCache
from .cache_factory import CacheFactory

# Aliases for backward compatibility
NoOpMemory = NoOpCache
MemoryFactory = CacheFactory

__all__ = [
    "NoOpCache",
    "CacheFactory",
    # Backward compatibility aliases
    "NoOpMemory",
    "MemoryFactory",
]


