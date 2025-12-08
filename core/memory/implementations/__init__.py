"""
Memory Implementations (Backward Compatibility).

This module re-exports from the new modular structure for backward compatibility.
New code should import directly from the specific modules:
    from core.memory.working_memory import WorkingMemory
    from core.memory.conversation_history import ConversationHistory
    from core.memory.state_tracker import InMemoryStateTracker

Version: 2.0.0
"""

# Re-export from new locations for backward compatibility
from ..working_memory import (
    WorkingMemory,
    DefaultWorkingMemory,
    BaseWorkingMemory,
)
from ..conversation_history import (
    ConversationHistory,
    DefaultConversationHistory,
    BaseConversationHistory,
)
from ..state_tracker import (
    InMemoryStateTracker,
    DefaultStateTracker,
    BaseStateTracker,
)

__all__ = [
    # Working Memory
    "WorkingMemory",
    "DefaultWorkingMemory",
    "BaseWorkingMemory",
    # Conversation History
    "ConversationHistory",
    "DefaultConversationHistory",
    "BaseConversationHistory",
    # State Tracker
    "InMemoryStateTracker",
    "DefaultStateTracker",
    "BaseStateTracker",
]
