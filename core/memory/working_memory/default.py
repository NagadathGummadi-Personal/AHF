"""
Default Working Memory Implementation.

Standard working memory combining conversation history and state tracking.

Version: 1.0.0
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from ..state.models import Checkpoint, MemoryState
from ..conversation_history import DefaultConversationHistory
from ..state_tracker import DefaultStateTracker
from .base import BaseWorkingMemory


class DefaultWorkingMemory(BaseWorkingMemory):
    """
    Default in-memory working memory.
    
    Standard implementation that combines:
    - Conversation history (messages)
    - State tracking (execution state)
    - Variables (context variables)
    - Checkpoints (for recovery)
    
    Usage:
        memory = DefaultWorkingMemory(session_id="session-123")
        
        # Add conversation messages
        memory.add_message("user", "I want to book a haircut")
        memory.add_message("assistant", "I'd be happy to help!")
        
        # Track variables
        memory.set_variable("service_name", "haircut")
        memory.set_variable("current_node", "booking-agent")
        
        # Save checkpoint for recovery
        memory.save_checkpoint("after-greeting")
        
        # Get conversation history for LLM
        messages = memory.get_conversation_history()
        
        # Later: restore from checkpoint
        memory.restore_from_checkpoint("after-greeting")
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
        super().__init__(
            session_id=session_id,
            max_messages=max_messages,
            max_checkpoints=max_checkpoints,
        )
        
        # Conversation history
        self._conversation = DefaultConversationHistory(max_messages=max_messages)
        
        # State tracker
        self._state_tracker = DefaultStateTracker(
            session_id=self._session_id,
            max_checkpoints=max_checkpoints,
        )
        
        # Link state tracker to our data
        self._state_tracker.set_messages_reference(self._conversation._messages)
        self._state_tracker.set_variables_reference(self._variables)
    
    @property
    def conversation(self) -> DefaultConversationHistory:
        """Get conversation memory."""
        return self._conversation
    
    @property
    def state_tracker(self) -> DefaultStateTracker:
        """Get state tracker."""
        return self._state_tracker
    
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
        self._touch()
        return self._conversation.add_message(role, content, metadata)
    
    def get_conversation_history(
        self,
        max_messages: Optional[int] = None,
    ) -> List[Dict[str, str]]:
        """
        Get conversation history for LLM.
        
        Args:
            max_messages: Max messages to include
            
        Returns:
            List of {"role": str, "content": str} dicts
        """
        return self._conversation.to_llm_messages(max_messages)
    
    def save_checkpoint(
        self,
        checkpoint_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Checkpoint:
        """
        Save current state as checkpoint.
        
        Args:
            checkpoint_id: Unique checkpoint identifier
            metadata: Optional metadata
            
        Returns:
            Checkpoint object
        """
        self._touch()
        
        # Include current execution state in checkpoint
        state = {
            "session_id": self._session_id,
            "updated_at": self._updated_at.isoformat(),
        }
        
        return self._state_tracker.save_checkpoint(
            checkpoint_id=checkpoint_id,
            state=state,
            metadata=metadata,
        )
    
    def restore_from_checkpoint(self, checkpoint_id: str) -> bool:
        """
        Restore state from checkpoint.
        
        Args:
            checkpoint_id: Checkpoint ID to restore from
            
        Returns:
            True if restored successfully
        """
        checkpoint = self._state_tracker.get_checkpoint(checkpoint_id)
        if not checkpoint:
            return False
        
        self._touch()
        
        # Restore conversation
        self._conversation.set_raw_messages(checkpoint.messages)
        
        # Restore variables
        self._variables.clear()
        self._variables.update(checkpoint.variables)
        
        # Restore state tracker state
        self._state_tracker.restore_from_checkpoint(checkpoint)
        
        return True
    
    def clear(self) -> None:
        """Clear all working memory."""
        self._conversation.clear_messages()
        self._variables.clear()
        self._state_tracker.clear_state()
        self._state_tracker.clear_checkpoints()
        self._metadata.clear()
        self._touch()
    
    def to_dict(self) -> Dict[str, Any]:
        """Export working memory to dictionary."""
        return {
            "session_id": self._session_id,
            "created_at": self._created_at.isoformat(),
            "updated_at": self._updated_at.isoformat(),
            "conversation": self._conversation.to_dict(),
            "variables": self._variables.copy(),
            "state_tracker": self._state_tracker.to_dict(),
            "metadata": self._metadata.copy(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DefaultWorkingMemory':
        """Create working memory from dictionary."""
        memory = cls(session_id=data["session_id"])
        
        # Restore timestamps
        if "created_at" in data:
            memory._created_at = datetime.fromisoformat(data["created_at"])
        if "updated_at" in data:
            memory._updated_at = datetime.fromisoformat(data["updated_at"])
        
        # Restore conversation
        if "conversation" in data:
            memory._conversation = DefaultConversationHistory.from_dict(data["conversation"])
        
        # Restore variables
        memory._variables = data.get("variables", {}).copy()
        
        # Restore state tracker
        if "state_tracker" in data:
            memory._state_tracker = DefaultStateTracker.from_dict(data["state_tracker"])
        
        # Re-link references
        memory._state_tracker.set_messages_reference(memory._conversation._messages)
        memory._state_tracker.set_variables_reference(memory._variables)
        
        # Restore metadata
        memory._metadata = data.get("metadata", {}).copy()
        
        return memory
    
    def create_memory_state(self) -> MemoryState:
        """Create a MemoryState object from current state."""
        return MemoryState(
            session_id=self._session_id,
            created_at=self._created_at,
            updated_at=self._updated_at,
            messages=self._conversation.get_raw_messages(),
            state=self._state_tracker.get_full_state(),
            variables=self._variables.copy(),
            checkpoints={cp.id: cp for cp in self._state_tracker.list_checkpoints()},
            metadata=self._metadata.copy(),
        )


# Alias for backward compatibility
WorkingMemory = DefaultWorkingMemory
