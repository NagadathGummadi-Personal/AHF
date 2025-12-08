"""
State Tracker Base Class.

Defines the abstract base class for state tracking implementations.
Extend this class to create custom state tracking for different workflows.

Version: 1.1.0
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from collections import OrderedDict

from utils.serialization import SerializableMixin

if TYPE_CHECKING:
    from ..state.models import Checkpoint, StateSnapshot, Message


class BaseStateTracker(ABC, SerializableMixin):
    """
    Abstract base class for state tracking.
    
    Tracks execution state and saves checkpoints for recovery.
    Extend this class to create custom state tracking implementations
    (e.g., persistent storage, distributed state, versioned state).
    
    Example:
        class PersistentStateTracker(BaseStateTracker):
            def save_checkpoint(self, checkpoint_id, state, metadata=None):
                checkpoint = self._create_checkpoint(checkpoint_id, state, metadata)
                # Custom: persist to database
                self._db.save(checkpoint)
                return checkpoint
    """
    
    def __init__(
        self,
        session_id: str,
        max_checkpoints: int = 50,
    ):
        """
        Initialize state tracker.
        
        Args:
            session_id: Session identifier
            max_checkpoints: Max checkpoints to keep
        """
        self.session_id = session_id
        self._max_checkpoints = max_checkpoints
        
        # Current state
        self._state: Dict[str, Any] = {}
        
        # Checkpoints (ordered by time)
        self._checkpoints: OrderedDict[str, 'Checkpoint'] = OrderedDict()
        
        # External references for checkpoint creation
        self._messages: List['Message'] = []
        self._variables: Dict[str, Any] = {}
    
    def set_messages_reference(self, messages: List['Message']) -> None:
        """Set reference to conversation messages for checkpoints."""
        self._messages = messages
    
    def set_variables_reference(self, variables: Dict[str, Any]) -> None:
        """Set reference to variables for checkpoints."""
        self._variables = variables
    
    # =========================================================================
    # Abstract Methods - Must be implemented
    # =========================================================================
    
    @abstractmethod
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
    
    @abstractmethod
    def get_checkpoint(self, checkpoint_id: str) -> Optional['Checkpoint']:
        """Get a checkpoint by ID."""
        ...
    
    @abstractmethod
    def get_latest_checkpoint(self) -> Optional['Checkpoint']:
        """Get the most recent checkpoint."""
        ...
    
    @abstractmethod
    def list_checkpoints(self) -> List['Checkpoint']:
        """List all checkpoints ordered by time."""
        ...
    
    @abstractmethod
    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """Delete a checkpoint. Returns True if deleted."""
        ...
    
    @abstractmethod
    def clear_checkpoints(self) -> None:
        """Clear all checkpoints."""
        ...
    
    @abstractmethod
    def create_snapshot(self) -> 'StateSnapshot':
        """Create a snapshot of current state."""
        ...
    
    @abstractmethod
    def restore_from_snapshot(self, snapshot: 'StateSnapshot') -> None:
        """Restore state from a snapshot."""
        ...
    
    @abstractmethod
    def restore_from_checkpoint(self, checkpoint: 'Checkpoint') -> None:
        """Restore state from a checkpoint."""
        ...
    
    # =========================================================================
    # State Methods - Default implementations
    # =========================================================================
    
    def get_state(self, key: str) -> Optional[Any]:
        """Get a tracked state value."""
        return self._state.get(key)
    
    def set_state(self, key: str, value: Any) -> None:
        """Set a tracked state value."""
        self._state[key] = value
    
    def delete_state(self, key: str) -> bool:
        """Delete a state value."""
        if key in self._state:
            del self._state[key]
            return True
        return False
    
    def get_full_state(self) -> Dict[str, Any]:
        """Get all tracked state as a dictionary."""
        return self._state.copy()
    
    def clear_state(self) -> None:
        """Clear all state."""
        self._state.clear()
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def _trim_checkpoints(self) -> None:
        """Trim old checkpoints if over limit."""
        while len(self._checkpoints) > self._max_checkpoints:
            oldest_key = next(iter(self._checkpoints))
            del self._checkpoints[oldest_key]
    
    def to_dict(self) -> Dict[str, Any]:
        """Export to dictionary."""
        return {
            "session_id": self.session_id,
            "state": self._state.copy(),
            "checkpoints": {k: v.to_dict() for k, v in self._checkpoints.items()},
            "max_checkpoints": self._max_checkpoints,
        }
    
    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseStateTracker':
        """Create from dictionary."""
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
