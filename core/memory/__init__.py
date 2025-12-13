"""
Memory Module for AHF Framework.

Provides comprehensive memory capabilities for LLMs, Agents, Tools, and Workflows:

Core Memory:
- Working Memory: Conversation history and active context
- State Tracking: Track and persist execution state for recovery
- Memory Persistence: Save/restore memory across sessions

Agent Memory:
- IAgentMemory: Key-value storage interface for agent context
- DictMemory: Simple in-memory dictionary implementation
- NoOpAgentMemory: No-op implementation for stateless agents
- Scratchpad: Temporary workspace for agent reasoning traces
- Checklist: Goal/task tracking for goal-based agents
- Observers: Execution observation and lifecycle hooks

Cache:
- ICache: Cache interface with TTL and locking support
- NoOpCache: No-op implementation for stateless execution

Architecture:
- Each memory component has a base class that can be extended for custom workflows
- Use MemoryFactory to create and register custom implementations

This module is designed to be used by any component that needs memory:
- Agents use it to maintain conversation context and reasoning traces
- LLMs use it to track conversation history
- Tools use it for caching and idempotency
- Workflows use it to maintain state and enable recovery from failures

Usage:
    from core.memory import (
        # Core memory
        WorkingMemory,
        MemoryFactory,
        BaseWorkingMemory,
        
        # Agent memory
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
        
        # Cache (for tools)
        NoOpCache,
        CacheFactory,
        
        # Interfaces
        IAgentMemory,
        IAgentScratchpad,
        IAgentChecklist,
        IAgentObserver,
        ICache,
    )

Version: 3.0.0
"""

# ============================================================================
# Interfaces (Protocols)
# ============================================================================
from .interfaces import (
    # Core memory interfaces
    IMemory,
    IWorkingMemory,
    IStateTracker,
    IConversationMemory,
    IMemoryPersistence,
    # Agent memory interfaces
    IAgentMemory,
    IAgentScratchpad,
    IAgentChecklist,
    IAgentObserver,
    # Cache interfaces
    ICache,
    IToolMemory,  # Alias for backward compatibility
    # Task queue and checkpointing interfaces
    ITask,
    ITaskQueue,
    ICheckpointer,
    IInterruptHandler,
    # Metrics store interfaces
    IMetricsStore,
)

# ============================================================================
# Core Memory (Working Memory, Conversation, State Tracking)
# ============================================================================
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

# ============================================================================
# State Models
# ============================================================================
from .state import (
    MemoryState,
    Checkpoint,
    StateSnapshot,
    CheckpointMetadata,
    Message,
)

# ============================================================================
# Core Memory Factory
# ============================================================================
from .factory import (
    MemoryFactory,
    MemoryType,
    create_working_memory,
    create_conversation_history,
    create_state_tracker,
)

# ============================================================================
# Constants
# ============================================================================
from .constants import (
    SCRATCHPAD_SEPARATOR,
    REACT_THOUGHT,
    REACT_ACTION,
    REACT_OBSERVATION,
    CHECKLIST_STATUS_PENDING,
    CHECKLIST_STATUS_IN_PROGRESS,
    CHECKLIST_STATUS_COMPLETED,
    CHECKLIST_STATUS_FAILED,
    CHECKLIST_STATUS_SKIPPED,
)

# ============================================================================
# Task Queue and Checkpointing Base Classes
# ============================================================================
from .task_queue import (
    BaseTaskQueue,
    BaseCheckpointer,
    DynamoDBCheckpointer,
    create_dynamodb_checkpointer,
    create_table_if_not_exists,
    DEFAULT_TTL_DAYS,
    MAX_TTL_DAYS,
)

# ============================================================================
# Agent Memory Components
# ============================================================================
from .agent import (
    # Memory
    DictMemory,
    NoOpAgentMemory,
    AgentMemoryFactory,
    # Scratchpad
    BasicScratchpad,
    StructuredScratchpad,
    ScratchpadFactory,
    # Checklist
    BasicChecklist,
    ChecklistFactory,
    # Observers
    NoOpObserver,
    LoggingObserver,
    ObserverFactory,
)

# ============================================================================
# Cache Components (for Tools)
# ============================================================================
from .cache import (
    NoOpCache,
    CacheFactory,
    # Backward compatibility aliases
    NoOpMemory,
    MemoryFactory as ToolMemoryFactory,  # Renamed to avoid conflict with core MemoryFactory
)

# ============================================================================
# Metrics Store (for Evaluators and Metrics)
# ============================================================================
from .metrics_store import (
    BaseMetricsStore,
    InMemoryMetricsStore,
    DynamoDBMetricsStore,
    create_metrics_store,
)

__all__ = [
    # =========================================================================
    # Interfaces
    # =========================================================================
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
    # Metrics store
    "IMetricsStore",
    
    # =========================================================================
    # Core Memory Base Classes
    # =========================================================================
    "BaseWorkingMemory",
    "BaseConversationHistory",
    "BaseStateTracker",
    
    # =========================================================================
    # Core Memory Default Implementations
    # =========================================================================
    "DefaultWorkingMemory",
    "DefaultConversationHistory",
    "DefaultStateTracker",
    
    # =========================================================================
    # Core Memory Aliases (backward compatibility)
    # =========================================================================
    "WorkingMemory",
    "ConversationHistory",
    "InMemoryStateTracker",
    
    # =========================================================================
    # State Models
    # =========================================================================
    "MemoryState",
    "Checkpoint",
    "StateSnapshot",
    "CheckpointMetadata",
    "Message",
    
    # =========================================================================
    # Core Memory Factory
    # =========================================================================
    "MemoryFactory",
    "MemoryType",
    "create_working_memory",
    "create_conversation_history",
    "create_state_tracker",
    
    # =========================================================================
    # Constants
    # =========================================================================
    "SCRATCHPAD_SEPARATOR",
    "REACT_THOUGHT",
    "REACT_ACTION",
    "REACT_OBSERVATION",
    "CHECKLIST_STATUS_PENDING",
    "CHECKLIST_STATUS_IN_PROGRESS",
    "CHECKLIST_STATUS_COMPLETED",
    "CHECKLIST_STATUS_FAILED",
    "CHECKLIST_STATUS_SKIPPED",
    
    # =========================================================================
    # Agent Memory Components
    # =========================================================================
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
    
    # =========================================================================
    # Cache Components
    # =========================================================================
    "NoOpCache",
    "CacheFactory",
    # Backward compatibility
    "NoOpMemory",
    "ToolMemoryFactory",
    
    # =========================================================================
    # Task Queue and Checkpointing Base Classes
    # =========================================================================
    "BaseTaskQueue",
    "BaseCheckpointer",
    # DynamoDB Checkpointer
    "DynamoDBCheckpointer",
    "create_dynamodb_checkpointer",
    "create_table_if_not_exists",
    "DEFAULT_TTL_DAYS",
    "MAX_TTL_DAYS",
    # =========================================================================
    # Metrics Store
    # =========================================================================
    "BaseMetricsStore",
    "InMemoryMetricsStore",
    "DynamoDBMetricsStore",
    "create_metrics_store",
]
