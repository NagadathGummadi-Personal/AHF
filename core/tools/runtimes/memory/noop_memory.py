"""
No-Op Memory Implementation.

Disables memory/caching operations for stateless execution.
"""

from contextlib import asynccontextmanager
from typing import Any, AsyncContextManager, Optional

from ...interfaces.tool_interfaces import IToolMemory


class NoOpMemory(IToolMemory):
    """
    No-op implementation of IToolMemory that doesn't store or retrieve data.
    
    Useful for:
    - Stateless executions without caching
    - Testing without memory infrastructure
    - Development environments
    - Tools that don't need memory/caching
    
    Usage:
        memory = NoOpMemory()
        
        # All operations are no-ops
        await memory.set("key", "value")  # Doesn't store
        value = await memory.get("key")  # Returns None
        exists = await memory.set_if_absent("key", "value")  # Returns False
        await memory.delete("key")  # No-op
        
        # Lock is no-op context manager
        async with memory.lock("resource"):
            # No actual locking
            pass
    """
    
    async def get(self, key: str) -> Any:
        """
        Get value from memory (no-op implementation).
        
        Args:
            key: Memory key (ignored)
            
        Returns:
            None (always)
        """
        return None
    
    async def set(self, key: str, value: Any, ttl_s: Optional[int] = None) -> None:
        """
        Set value in memory (no-op implementation).
        
        Args:
            key: Memory key (ignored)
            value: Value to store (ignored)
            ttl_s: Time-to-live in seconds (ignored)
        """
        pass
    
    async def set_if_absent(self, key: str, value: Any, ttl_s: Optional[int] = None) -> bool:
        """
        Set value if absent (no-op implementation).
        
        Args:
            key: Memory key (ignored)
            value: Value to store (ignored)
            ttl_s: Time-to-live in seconds (ignored)
            
        Returns:
            False (always, indicating key was not set)
        """
        return False
    
    async def delete(self, key: str) -> None:
        """
        Delete value from memory (no-op implementation).
        
        Args:
            key: Memory key to delete (ignored)
        """
        pass
    
    @asynccontextmanager
    async def lock(self, key: str, ttl_s: int = 10) -> AsyncContextManager[None]:
        """
        Acquire lock (no-op implementation).
        
        Provides a no-op context manager that doesn't actually lock.
        
        Args:
            key: Lock key (ignored)
            ttl_s: Lock time-to-live in seconds (ignored)
            
        Yields:
            None
        """
        yield

