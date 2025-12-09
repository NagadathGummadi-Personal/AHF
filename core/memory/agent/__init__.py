"""
Agent Memory Components.

Provides memory-related implementations specifically for agents:
- Memory: Key-value storage (DictMemory, NoOpAgentMemory)
- Scratchpad: Reasoning workspace (BasicScratchpad, StructuredScratchpad)
- Checklist: Goal/task tracking (BasicChecklist)
- Observers: Execution observation (NoOpObserver, LoggingObserver)

Usage:
    from core.memory.agent import (
        DictMemory,
        NoOpAgentMemory,
        AgentMemoryFactory,
        BasicScratchpad,
        StructuredScratchpad,
        ScratchpadFactory,
        BasicChecklist,
        ChecklistFactory,
        NoOpObserver,
        LoggingObserver,
        ObserverFactory,
    )

Version: 1.0.0
"""

# Memory implementations
from .memory import (
    DictMemory,
    NoOpAgentMemory,
    AgentMemoryFactory,
)

# Scratchpad implementations
from .scratchpad import (
    BasicScratchpad,
    StructuredScratchpad,
    ScratchpadFactory,
)

# Checklist implementations
from .checklist import (
    BasicChecklist,
    ChecklistFactory,
)

# Observer implementations
from .observers import (
    NoOpObserver,
    LoggingObserver,
    ObserverFactory,
)

__all__ = [
    # Memory
    "DictMemory",
    "NoOpAgentMemory",
    "AgentMemoryFactory",
    # Scratchpad
    "BasicScratchpad",
    "StructuredScratchpad",
    "ScratchpadFactory",
    # Checklist
    "BasicChecklist",
    "ChecklistFactory",
    # Observers
    "NoOpObserver",
    "LoggingObserver",
    "ObserverFactory",
]


