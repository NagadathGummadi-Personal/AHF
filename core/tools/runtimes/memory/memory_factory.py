"""
Memory Factory for Tools Specification System.

Provides a centralized way to create and register memory implementations by name.
"""

from typing import Dict

from ...interfaces.tool_interfaces import IToolMemory
from .noop_memory import NoOpMemory

from ...constants import (
    NOOP,
    UNKNOWN_MEMORY_ERROR,
    COMMA,
    SPACE
)


class MemoryFactory:
    """
    Factory for creating memory/cache instances.
    
    Built-in Memory Implementations:
        - 'noop': NoOpMemory - No memory/caching (for stateless execution)
    
    Usage:
        # Get built-in memory
        memory = MemoryFactory.get_memory('noop')
        
        # Register custom memory implementation
        MemoryFactory.register('redis', RedisMemory())
        memory = MemoryFactory.get_memory('redis')
    """
    
    _memories: Dict[str, IToolMemory] = {
        NOOP: NoOpMemory(),
    }
    
    @classmethod
    def get_memory(cls, name: str = NOOP) -> IToolMemory:
        """
        Get a memory implementation by name.
        
        Args:
            name: Memory implementation name ('noop', 'redis', etc.)
            
        Returns:
            IToolMemory instance
            
        Raises:
            ValueError: If memory name is not registered
        """
        memory = cls._memories.get(name)
        
        if not memory:
            available = (COMMA + SPACE).join(cls._memories.keys())
            raise ValueError(
                UNKNOWN_MEMORY_ERROR.format(MEMORY_NAME=name, AVAILABLE_MEMORIES=available)
            )
        
        return memory
    
    @classmethod
    def register(cls, name: str, memory: IToolMemory):
        """
        Register a custom memory implementation.
        
        Args:
            name: Name to register the memory under
            memory: Memory instance implementing IToolMemory
        
        Example:
            class RedisMemory(IToolMemory):
                async def get(self, key: str):
                    return await redis_client.get(key)
                # ... implement other methods
            
            MemoryFactory.register('redis', RedisMemory())
        """
        cls._memories[name] = memory

