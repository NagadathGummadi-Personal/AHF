"""
Memory Module for AHF Framework.

Provides memory capabilities for LLMs, Agents, and Workflows including:
- Working Memory: Conversation history and active context
- State Tracking: Track and persist execution state for recovery
- Memory Persistence: Save/restore memory across sessions

Architecture:
- Each memory component (working_memory, conversation_history, state_tracker) 
  has a base class that can be extended for custom workflows
- Use MemoryFactory to create and register custom implementations

This module is designed to be used by any component that needs memory:
- Agents use it to maintain conversation context
- LLMs use it to track conversation history
- Workflows use it to maintain state and enable recovery from failures

Usage:
    from core.memory import (
        WorkingMemory,
        MemoryFactory,
        BaseWorkingMemory,
    )
    
    # Create working memory (default implementation)
    memory = WorkingMemory(session_id="session-123")
    
    # Or via factory
    memory = MemoryFactory.create_working_memory(session_id="session-123")
    
    # Add conversation messages
    memory.add_message(role="user", content="Hello")
    memory.add_message(role="assistant", content="Hi there!")
    
    # Get conversation history
    history = memory.get_conversation_history()
    
    # Track state for workflow recovery
    tracker = memory.state_tracker
    memory.save_checkpoint("node-1")
    
    # Recover from checkpoint
    memory.restore_from_checkpoint("node-1")
    
Custom Implementations:
    from core.memory import BaseWorkingMemory, MemoryFactory
    
    class AgentWorkingMemory(BaseWorkingMemory):
        '''Custom working memory for agents.'''
        ...
    
    # Register custom implementation
    MemoryFactory.register_working_memory("agent", AgentWorkingMemory)
    
    # Use via factory
    memory = MemoryFactory.create_working_memory(
        session_id="session-123",
        implementation="agent",
    )

Version: 2.0.0
"""

# Interfaces (Protocols)
from .interfaces import (
    IMemory,
    IWorkingMemory,
    IStateTracker,
    IConversationMemory,
    IMemoryPersistence,
)

# Base Classes (for extension)
from .working_memory import (
    BaseWorkingMemory,
    DefaultWorkingMemory,
    WorkingMemory,
)
from .conversation_history import (
    BaseConversationHistory,
    DefaultConversationHistory,
    ConversationHistory,
)
from .state_tracker import (
    BaseStateTracker,
    DefaultStateTracker,
    InMemoryStateTracker,
)

# State Models
from .state import (
    MemoryState,
    Checkpoint,
    StateSnapshot,
    CheckpointMetadata,
    Message,
)

# Factory
from .factory import (
    MemoryFactory,
    MemoryType,
    create_working_memory,
    create_conversation_history,
    create_state_tracker,
)

__all__ = [
    # Interfaces
    "IMemory",
    "IWorkingMemory",
    "IStateTracker",
    "IConversationMemory",
    "IMemoryPersistence",
    
    # Base Classes
    "BaseWorkingMemory",
    "BaseConversationHistory",
    "BaseStateTracker",
    
    # Default Implementations
    "DefaultWorkingMemory",
    "DefaultConversationHistory",
    "DefaultStateTracker",
    
    # Aliases (backward compatibility)
    "WorkingMemory",
    "ConversationHistory",
    "InMemoryStateTracker",
    
    # State Models
    "MemoryState",
    "Checkpoint",
    "StateSnapshot",
    "CheckpointMetadata",
    "Message",
    
    # Factory
    "MemoryFactory",
    "MemoryType",
    "create_working_memory",
    "create_conversation_history",
    "create_state_tracker",
]
