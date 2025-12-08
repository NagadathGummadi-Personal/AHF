"""
Memory Interfaces.

Defines the core protocols for memory components used by LLMs, Agents, and Workflows.

Version: 1.0.0
"""

from __future__ import annotations
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Protocol,
    runtime_checkable,
    TYPE_CHECKING,
)

if TYPE_CHECKING:
    from ..state import Checkpoint, StateSnapshot


@runtime_checkable
class IMemory(Protocol):
    """
    Base Memory Interface.
    
    Provides simple key-value storage with metadata support.
    This is the foundation for all memory types.
    """
    
    async def get(self, key: str) -> Optional[Any]:
        """Get a value by key."""
        ...
    
    async def set(self, key: str, value: Any, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Set a value with optional metadata."""
        ...
    
    async def delete(self, key: str) -> bool:
        """Delete a key. Returns True if deleted."""
        ...
    
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        ...
    
    async def clear(self) -> None:
        """Clear all memory."""
        ...
    
    async def keys(self, prefix: Optional[str] = None) -> List[str]:
        """List all keys, optionally filtered by prefix."""
        ...


@runtime_checkable
class IConversationMemory(Protocol):
    """
    Interface for Conversation History.
    
    Manages conversation messages between user and assistant.
    Used by LLMs and Agents to maintain context.
    """
    
    def add_message(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Add a message to conversation history.
        
        Args:
            role: Message role (user, assistant, system, tool)
            content: Message content
            metadata: Optional metadata (timestamps, tokens, etc.)
            
        Returns:
            Message ID
        """
        ...
    
    def get_messages(
        self,
        limit: Optional[int] = None,
        roles: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get conversation messages.
        
        Args:
            limit: Max messages to return (from most recent)
            roles: Filter by roles
            
        Returns:
            List of message dicts
        """
        ...
    
    def get_last_message(self, role: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get the last message, optionally filtered by role."""
        ...
    
    def get_message_count(self) -> int:
        """Get total message count."""
        ...
    
    def clear_messages(self) -> None:
        """Clear all messages."""
        ...
    
    def to_llm_messages(self, max_messages: Optional[int] = None) -> List[Dict[str, str]]:
        """
        Convert to LLM-compatible message format.
        
        Args:
            max_messages: Max messages to include
            
        Returns:
            List of {"role": str, "content": str} dicts
        """
        ...


@runtime_checkable
class IStateTracker(Protocol):
    """
    Interface for State Tracking.
    
    Tracks execution state and checkpoints for workflows.
    Enables recovery from failures by saving/restoring state.
    """
    
    def save_checkpoint(
        self,
        checkpoint_id: str,
        state: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> 'Checkpoint':
        """
        Save a checkpoint.
        
        Args:
            checkpoint_id: Unique checkpoint identifier
            state: State data to save
            metadata: Optional metadata
            
        Returns:
            Checkpoint object
        """
        ...
    
    def get_checkpoint(self, checkpoint_id: str) -> Optional['Checkpoint']:
        """Get a checkpoint by ID."""
        ...
    
    def get_latest_checkpoint(self) -> Optional['Checkpoint']:
        """Get the most recent checkpoint."""
        ...
    
    def list_checkpoints(self) -> List['Checkpoint']:
        """List all checkpoints ordered by time."""
        ...
    
    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """Delete a checkpoint. Returns True if deleted."""
        ...
    
    def clear_checkpoints(self) -> None:
        """Clear all checkpoints."""
        ...
    
    def get_state(self, key: str) -> Optional[Any]:
        """Get a tracked state value."""
        ...
    
    def set_state(self, key: str, value: Any) -> None:
        """Set a tracked state value."""
        ...
    
    def get_full_state(self) -> Dict[str, Any]:
        """Get all tracked state as a dictionary."""
        ...
    
    def create_snapshot(self) -> 'StateSnapshot':
        """Create a snapshot of current state."""
        ...
    
    def restore_from_snapshot(self, snapshot: 'StateSnapshot') -> None:
        """Restore state from a snapshot."""
        ...


@runtime_checkable
class IWorkingMemory(Protocol):
    """
    Interface for Working Memory.
    
    Combines conversation history and state tracking into a unified
    working memory for agents and workflows.
    
    Working memory includes:
    - Conversation history (messages between user/assistant)
    - State variables (current execution state)
    - Context variables (workflow/agent context)
    - Checkpoints for recovery
    """
    
    @property
    def session_id(self) -> str:
        """Get the session ID."""
        ...
    
    @property
    def conversation(self) -> IConversationMemory:
        """Get conversation memory."""
        ...
    
    @property
    def state_tracker(self) -> IStateTracker:
        """Get state tracker."""
        ...
    
    def add_message(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Add a message (convenience method)."""
        ...
    
    def get_conversation_history(
        self,
        max_messages: Optional[int] = None,
    ) -> List[Dict[str, str]]:
        """Get conversation history for LLM."""
        ...
    
    def set_variable(self, key: str, value: Any) -> None:
        """Set a context variable."""
        ...
    
    def get_variable(self, key: str, default: Any = None) -> Any:
        """Get a context variable."""
        ...
    
    def get_all_variables(self) -> Dict[str, Any]:
        """Get all context variables."""
        ...
    
    def save_checkpoint(
        self,
        checkpoint_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> 'Checkpoint':
        """Save current state as checkpoint."""
        ...
    
    def restore_from_checkpoint(self, checkpoint_id: str) -> bool:
        """Restore state from checkpoint. Returns True if successful."""
        ...
    
    def clear(self) -> None:
        """Clear all working memory."""
        ...
    
    def to_dict(self) -> Dict[str, Any]:
        """Export working memory to dictionary."""
        ...
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'IWorkingMemory':
        """Create working memory from dictionary."""
        ...


@runtime_checkable
class IMemoryPersistence(Protocol):
    """
    Interface for Memory Persistence.
    
    Handles saving/loading memory to/from persistent storage.
    Can be implemented for different backends (file, database, etc.)
    """
    
    async def save(
        self,
        memory_id: str,
        data: Dict[str, Any],
    ) -> bool:
        """
        Save memory data.
        
        Args:
            memory_id: Unique identifier for the memory
            data: Memory data to save
            
        Returns:
            True if saved successfully
        """
        ...
    
    async def load(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """
        Load memory data.
        
        Args:
            memory_id: Unique identifier for the memory
            
        Returns:
            Memory data or None if not found
        """
        ...
    
    async def delete(self, memory_id: str) -> bool:
        """Delete saved memory."""
        ...
    
    async def exists(self, memory_id: str) -> bool:
        """Check if memory exists in storage."""
        ...
    
    async def list_memories(self, prefix: Optional[str] = None) -> List[str]:
        """List all saved memory IDs."""
        ...

