"""
Working Memory Base Class.

Defines the abstract base class for working memory implementations.
Extend this class to create custom working memory for different workflows.

Version: 1.1.0
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING
import uuid

from utils.serialization import SerializableMixin

if TYPE_CHECKING:
    from ..state.models import Checkpoint, MemoryState
    from ..conversation_history.base import BaseConversationHistory
    from ..state_tracker.base import BaseStateTracker


class BaseWorkingMemory(ABC, SerializableMixin):
    """
    Abstract base class for working memory.
    
    Working memory combines:
    - Conversation history (messages)
    - State tracking (execution state)
    - Variables (context variables)
    - Checkpoints (for recovery)
    
    Extend this class to create custom working memory implementations
    for different workflows (e.g., multi-agent, hierarchical, distributed).
    
    Example:
        class AgentWorkingMemory(BaseWorkingMemory):
            def __init__(self, agent_id: str, **kwargs):
                super().__init__(**kwargs)
                self._agent_id = agent_id
                
            def get_conversation_history(self, max_messages=None):
                # Custom: include agent context in history
                history = super().get_conversation_history(max_messages)
                return self._inject_agent_context(history)
    """
    
    def __init__(
        self,
        session_id: Optional[str] = None,
        max_messages: Optional[int] = None,
        max_checkpoints: int = 50,
    ):
        """
        Initialize working memory.
        
        Args:
            session_id: Session identifier (auto-generated if not provided)
            max_messages: Max conversation messages to keep
            max_checkpoints: Max checkpoints to keep
        """
        self._session_id = session_id or str(uuid.uuid4())[:8]
        self._created_at = datetime.utcnow()
        self._updated_at = datetime.utcnow()
        
        # Max settings for subclasses
        self._max_messages = max_messages
        self._max_checkpoints = max_checkpoints
        
        # Variables
        self._variables: Dict[str, Any] = {}
        
        # Metadata
        self._metadata: Dict[str, Any] = {}
    
    @property
    def session_id(self) -> str:
        """Get the session ID."""
        return self._session_id
    
    @property
    @abstractmethod
    def conversation(self) -> 'BaseConversationHistory':
        """Get conversation memory."""
        ...
    
    @property
    @abstractmethod
    def state_tracker(self) -> 'BaseStateTracker':
        """Get state tracker."""
        ...
    
    @property
    def created_at(self) -> datetime:
        """Get creation time."""
        return self._created_at
    
    @property
    def updated_at(self) -> datetime:
        """Get last update time."""
        return self._updated_at
    
    def _touch(self):
        """Update the updated_at timestamp."""
        self._updated_at = datetime.utcnow()
    
    # =========================================================================
    # Abstract Conversation Methods
    # =========================================================================
    
    @abstractmethod
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
            metadata: Optional metadata
            
        Returns:
            Message ID
        """
        ...
    
    @abstractmethod
    def get_conversation_history(
        self,
        max_messages: Optional[int] = None,
    ) -> List[Dict[str, str]]:
        """
        Get conversation history for LLM.
        
        Override to customize the format or inject additional context.
        
        Args:
            max_messages: Max messages to include
            
        Returns:
            List of {"role": str, "content": str} dicts
        """
        ...
    
    # =========================================================================
    # Convenience Message Methods
    # =========================================================================
    
    def add_system_message(self, content: str) -> str:
        """Add a system message."""
        return self.add_message("system", content)
    
    def add_user_message(self, content: str) -> str:
        """Add a user message."""
        return self.add_message("user", content)
    
    def add_assistant_message(self, content: str) -> str:
        """Add an assistant message."""
        return self.add_message("assistant", content)
    
    def get_last_user_message(self) -> Optional[str]:
        """Get the last user message content."""
        msg = self.conversation.get_last_message(role="user")
        return msg["content"] if msg else None
    
    def get_last_assistant_message(self) -> Optional[str]:
        """Get the last assistant message content."""
        msg = self.conversation.get_last_message(role="assistant")
        return msg["content"] if msg else None
    
    def clear_conversation(self) -> None:
        """Clear conversation history."""
        self._touch()
        self.conversation.clear_messages()
    
    # =========================================================================
    # Variable Methods
    # =========================================================================
    
    def set_variable(self, key: str, value: Any) -> None:
        """Set a context variable."""
        self._touch()
        self._variables[key] = value
    
    def get_variable(self, key: str, default: Any = None) -> Any:
        """Get a context variable."""
        return self._variables.get(key, default)
    
    def delete_variable(self, key: str) -> bool:
        """Delete a variable. Returns True if deleted."""
        if key in self._variables:
            del self._variables[key]
            self._touch()
            return True
        return False
    
    def get_all_variables(self) -> Dict[str, Any]:
        """Get all context variables."""
        return self._variables.copy()
    
    def update_variables(self, variables: Dict[str, Any]) -> None:
        """Update multiple variables at once."""
        self._touch()
        self._variables.update(variables)
    
    def clear_variables(self) -> None:
        """Clear all variables."""
        self._touch()
        self._variables.clear()
    
    # =========================================================================
    # State Tracking Methods (Delegate to state_tracker)
    # =========================================================================
    
    def set_state(self, key: str, value: Any) -> None:
        """Set a tracked state value."""
        self._touch()
        self.state_tracker.set_state(key, value)
    
    def get_state(self, key: str) -> Optional[Any]:
        """Get a tracked state value."""
        return self.state_tracker.get_state(key)
    
    def get_full_state(self) -> Dict[str, Any]:
        """Get all tracked state."""
        return self.state_tracker.get_full_state()
    
    # =========================================================================
    # Abstract Checkpoint Methods
    # =========================================================================
    
    @abstractmethod
    def save_checkpoint(
        self,
        checkpoint_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> 'Checkpoint':
        """
        Save current state as checkpoint.
        
        Args:
            checkpoint_id: Unique checkpoint identifier
            metadata: Optional metadata
            
        Returns:
            Checkpoint object
        """
        ...
    
    @abstractmethod
    def restore_from_checkpoint(self, checkpoint_id: str) -> bool:
        """
        Restore state from checkpoint.
        
        Args:
            checkpoint_id: Checkpoint ID to restore from
            
        Returns:
            True if restored successfully
        """
        ...
    
    def get_checkpoint(self, checkpoint_id: str) -> Optional['Checkpoint']:
        """Get a checkpoint by ID."""
        return self.state_tracker.get_checkpoint(checkpoint_id)
    
    def get_latest_checkpoint(self) -> Optional['Checkpoint']:
        """Get the most recent checkpoint."""
        return self.state_tracker.get_latest_checkpoint()
    
    def list_checkpoints(self) -> List['Checkpoint']:
        """List all checkpoints."""
        return self.state_tracker.list_checkpoints()
    
    # =========================================================================
    # Metadata Methods
    # =========================================================================
    
    def set_metadata(self, key: str, value: Any) -> None:
        """Set metadata value."""
        self._metadata[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata value."""
        return self._metadata.get(key, default)
    
    # =========================================================================
    # Abstract Serialization Methods
    # =========================================================================
    
    @abstractmethod
    def clear(self) -> None:
        """Clear all working memory."""
        ...
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Export working memory to dictionary."""
        ...
    
    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseWorkingMemory':
        """Create working memory from dictionary."""
        ...
    
    @abstractmethod
    def create_memory_state(self) -> 'MemoryState':
        """Create a MemoryState object from current state."""
        ...
    
    # =========================================================================
    # Serialization Methods (JSON/TOML) - from SerializableMixin
    # =========================================================================
    # Inherited from SerializableMixin:
    # - to_json(indent=2) -> str
    # - to_toml() -> str
    # - from_json(json_str) -> cls
    # - from_toml(toml_str) -> cls
    # - save(path, format=None) -> None
    # - load(path, format=None) -> cls
