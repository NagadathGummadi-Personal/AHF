"""
Basic Checklist Implementation.

Provides a checklist implementation using the Checklist model.
"""

from typing import Any, Dict, List, Optional
import json

from ...interfaces.agent_interfaces import IAgentChecklist
from ...spec.checklist_models import Checklist, ChecklistItem
from ...enum import ChecklistStatus


class BasicChecklist(IAgentChecklist):
    """
    Basic checklist implementation using the Checklist model.
    
    Wraps the Checklist pydantic model to implement IAgentChecklist.
    
    Usage:
        checklist = BasicChecklist()
        
        item_id = checklist.add_item("Research topic", priority=1)
        checklist.update_status(item_id, "in_progress")
        
        pending = checklist.get_pending_items()
        if checklist.is_complete():
            print("All done!")
        
        json_state = checklist.to_json()
    """
    
    def __init__(self, name: str = "Agent Checklist", description: str = ""):
        """
        Initialize checklist.
        
        Args:
            name: Checklist name
            description: Checklist description
        """
        self._checklist = Checklist(name=name, description=description)
    
    def add_item(
        self,
        item: str,
        status: str = "pending",
        priority: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add an item to the checklist.
        
        Args:
            item: Description of the task
            status: Initial status
            priority: Priority level (lower = higher priority)
            metadata: Optional metadata
            
        Returns:
            Unique ID for the checklist item
        """
        checklist_status = ChecklistStatus(status) if isinstance(status, str) else status
        return self._checklist.add_item(
            description=item,
            status=checklist_status,
            priority=priority,
            metadata=metadata
        )
    
    def update_status(self, item_id: str, status: str) -> None:
        """
        Update the status of a checklist item.
        
        Args:
            item_id: ID of the item to update
            status: New status
        """
        checklist_status = ChecklistStatus(status) if isinstance(status, str) else status
        self._checklist.update_status(item_id, checklist_status)
    
    def get_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a checklist item by ID.
        
        Args:
            item_id: ID of the item
            
        Returns:
            Item dict or None if not found
        """
        item = self._checklist.get_item(item_id)
        return item.to_dict() if item else None
    
    def get_pending_items(self) -> List[Dict[str, Any]]:
        """Get all pending items."""
        return [item.to_dict() for item in self._checklist.get_pending_items()]
    
    def get_in_progress_items(self) -> List[Dict[str, Any]]:
        """Get all in-progress items."""
        return [item.to_dict() for item in self._checklist.get_in_progress_items()]
    
    def get_completed_items(self) -> List[Dict[str, Any]]:
        """Get all completed items."""
        return [item.to_dict() for item in self._checklist.get_completed_items()]
    
    def is_complete(self) -> bool:
        """Check if all items are completed."""
        return self._checklist.is_complete()
    
    def get_progress(self) -> Dict[str, int]:
        """Get progress statistics."""
        return self._checklist.get_progress()
    
    def to_json(self) -> str:
        """Serialize the checklist to JSON."""
        return self._checklist.to_json()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self._checklist.to_dict()
    
    @classmethod
    def from_json(cls, json_str: str) -> 'BasicChecklist':
        """Create checklist from JSON string."""
        checklist = Checklist.from_json(json_str)
        instance = cls.__new__(cls)
        instance._checklist = checklist
        return instance

