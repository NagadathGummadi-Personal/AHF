"""
Memory Interfaces.

Defines the core protocols for memory components.
"""

from .memory_interfaces import (
    IMemory,
    IWorkingMemory,
    IStateTracker,
    IConversationMemory,
    IMemoryPersistence,
)

__all__ = [
    "IMemory",
    "IWorkingMemory",
    "IStateTracker",
    "IConversationMemory",
    "IMemoryPersistence",
]

