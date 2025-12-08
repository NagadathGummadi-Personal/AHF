"""
Default State Tracker Implementation.

Standard in-memory state tracking for general use.

Version: 1.0.0
"""

from typing import Any, Dict, List, Optional

from ..state.models import Checkpoint, CheckpointMetadata, StateSnapshot
from .base import BaseStateTracker


class DefaultStateTracker(BaseStateTracker):
    """
    Default in-memory state tracker.
    
    Standard implementation that works for most use cases.
    Tracks execution state and saves checkpoints for recovery.
    
    Usage:
        tracker = DefaultStateTracker(session_id="session-123")
        
        # Track state
        tracker.set_state("current_node", "booking-agent")
        tracker.set_state("user_intent", "booking")
        
        # Save checkpoint
        checkpoint = tracker.save_checkpoint(
            "after-greeting",
            {"node": "greeting", "status": "completed"}
        )
        
        # Later: recover from checkpoint
        checkpoint = tracker.get_latest_checkpoint()
        if checkpoint:
            tracker.restore_from_checkpoint(checkpoint)
    """
    
    def save_checkpoint(
        self,
        checkpoint_id: str,
        state: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Checkpoint:
        """
        Save a checkpoint.
        
        Args:
            checkpoint_id: Unique checkpoint identifier
            state: State data to save
            metadata: Optional metadata
            
        Returns:
            Checkpoint object
        """
        checkpoint_metadata = CheckpointMetadata(
            **(metadata or {})
        )
        
        checkpoint = Checkpoint(
            id=checkpoint_id,
            state={**self._state, **state},
            metadata=checkpoint_metadata,
            messages=self._messages.copy(),
            message_count=len(self._messages),
            variables=self._variables.copy(),
        )
        
        # Remove old checkpoint with same ID if exists
        if checkpoint_id in self._checkpoints:
            del self._checkpoints[checkpoint_id]
        
        self._checkpoints[checkpoint_id] = checkpoint
        self._trim_checkpoints()
        
        return checkpoint
    
    def get_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """Get a checkpoint by ID."""
        return self._checkpoints.get(checkpoint_id)
    
    def get_latest_checkpoint(self) -> Optional[Checkpoint]:
        """Get the most recent checkpoint."""
        if not self._checkpoints:
            return None
        
        # Last item in OrderedDict is most recent
        return list(self._checkpoints.values())[-1]
    
    def list_checkpoints(self) -> List[Checkpoint]:
        """List all checkpoints ordered by time."""
        return list(self._checkpoints.values())
    
    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """Delete a checkpoint. Returns True if deleted."""
        if checkpoint_id in self._checkpoints:
            del self._checkpoints[checkpoint_id]
            return True
        return False
    
    def clear_checkpoints(self) -> None:
        """Clear all checkpoints."""
        self._checkpoints.clear()
    
    def create_snapshot(self) -> StateSnapshot:
        """Create a snapshot of current state."""
        return StateSnapshot(
            session_id=self.session_id,
            state=self._state.copy(),
            variables=self._variables.copy(),
            messages=self._messages.copy(),
            checkpoints=list(self._checkpoints.values()),
        )
    
    def restore_from_snapshot(self, snapshot: StateSnapshot) -> None:
        """Restore state from a snapshot."""
        self._state = snapshot.state.copy()
        self._variables.clear()
        self._variables.update(snapshot.variables)
        self._messages.clear()
        self._messages.extend(snapshot.messages)
        
        self._checkpoints.clear()
        for cp in snapshot.checkpoints:
            self._checkpoints[cp.id] = cp
    
    def restore_from_checkpoint(self, checkpoint: Checkpoint) -> None:
        """Restore state from a checkpoint."""
        self._state = checkpoint.state.copy()
        self._variables.clear()
        self._variables.update(checkpoint.variables)
        self._messages.clear()
        self._messages.extend(checkpoint.messages)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DefaultStateTracker':
        """Create from dictionary."""
        tracker = cls(
            session_id=data["session_id"],
            max_checkpoints=data.get("max_checkpoints", 50),
        )
        tracker._state = data.get("state", {})
        
        for cp_id, cp_data in data.get("checkpoints", {}).items():
            tracker._checkpoints[cp_id] = Checkpoint.from_dict(cp_data)
        
        return tracker


# Alias for backward compatibility
InMemoryStateTracker = DefaultStateTracker
