"""
Memory Factory for Agents.

Provides factory methods for creating memory implementations.
"""

from typing import Dict, Type

from ...interfaces.agent_interfaces import IAgentMemory
from .noop_memory import NoOpAgentMemory
from .dict_memory import DictMemory
from ...constants import UNKNOWN_MEMORY_ERROR


class AgentMemoryFactory:
    """
    Factory for creating agent memory implementations.
    
    Supports registration of custom memory implementations.
    
    Usage:
        # Get built-in memory
        memory = AgentMemoryFactory.get_memory('dict')
        
        # Register custom memory
        AgentMemoryFactory.register('redis', RedisMemory)
        memory = AgentMemoryFactory.get_memory('redis')
    """
    
    _memory_map: Dict[str, Type[IAgentMemory]] = {
        'noop': NoOpAgentMemory,
        'dict': DictMemory,
        'default': DictMemory,
    }
    
    @classmethod
    def get_memory(cls, name: str) -> IAgentMemory:
        """
        Get a memory implementation by name.
        
        Args:
            name: Memory implementation name
            
        Returns:
            Memory instance
            
        Raises:
            ValueError: If name is not registered
        """
        name_lower = name.lower()
        memory_class = cls._memory_map.get(name_lower)
        
        if not memory_class:
            raise ValueError(
                UNKNOWN_MEMORY_ERROR.format(
                    MEMORY_NAME=name,
                    AVAILABLE_MEMORIES=list(cls._memory_map.keys())
                )
            )
        
        return memory_class()
    
    @classmethod
    def register(cls, name: str, memory_class: Type[IAgentMemory]) -> None:
        """
        Register a custom memory implementation.
        
        Args:
            name: Name for the memory implementation
            memory_class: Class implementing IAgentMemory
        """
        cls._memory_map[name.lower()] = memory_class
    
    @classmethod
    def unregister(cls, name: str) -> None:
        """
        Unregister a memory implementation.
        
        Args:
            name: Name of the memory to unregister
        """
        name_lower = name.lower()
        if name_lower in ('noop', 'dict', 'default'):
            raise ValueError(f"Cannot unregister built-in memory: {name}")
        cls._memory_map.pop(name_lower, None)
    
    @classmethod
    def list_available(cls) -> list:
        """List all registered memory implementations."""
        return list(cls._memory_map.keys())

