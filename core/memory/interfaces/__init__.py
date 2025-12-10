"""
Memory Interfaces.

Exports all memory-related protocols for the framework.

Includes:
- Core memory interfaces (IMemory, IWorkingMemory, IStateTracker, etc.)
- Agent memory interfaces (IAgentMemory, IAgentScratchpad, IAgentChecklist, IAgentObserver)
- Cache interfaces (ICache, IToolMemory)
- Task queue interfaces (ITask, ITaskQueue, ICheckpointer, IInterruptHandler)

Version: 2.1.0
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

# Task queue and checkpoint interfaces
from .task_queue_interfaces import (
    ITask,
    ITaskQueue,
    ICheckpointer,
    IInterruptHandler,
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
    # Task queue and checkpointing
    "ITask",
    "ITaskQueue",
    "ICheckpointer",
    "IInterruptHandler",
]
