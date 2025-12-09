"""
Memory Interfaces.

Exports all memory-related protocols for the framework.

Includes:
- Core memory interfaces (IMemory, IWorkingMemory, IStateTracker, etc.)
- Agent memory interfaces (IAgentMemory, IAgentScratchpad, IAgentChecklist, IAgentObserver)
- Cache interfaces (ICache, IToolMemory)

Version: 2.0.0
"""

# Core memory interfaces
from .memory_interfaces import (
    IMemory,
    IWorkingMemory,
    IStateTracker,
    IConversationMemory,
    IMemoryPersistence,
)

# Agent memory interfaces
from .agent_memory_interfaces import (
    IAgentMemory,
    IAgentScratchpad,
    IAgentChecklist,
    IAgentObserver,
)

# Cache interfaces
from .cache_interfaces import (
    ICache,
    IToolMemory,  # Alias for backward compatibility
)

__all__ = [
    # Core memory
    "IMemory",
    "IWorkingMemory",
    "IStateTracker",
    "IConversationMemory",
    "IMemoryPersistence",
    # Agent memory
    "IAgentMemory",
    "IAgentScratchpad",
    "IAgentChecklist",
    "IAgentObserver",
    # Cache
    "ICache",
    "IToolMemory",
]
