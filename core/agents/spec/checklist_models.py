"""
Checklist Models.

This module defines the data models for agent checklists and goal tracking.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import uuid
import json
from datetime import datetime

from ..enum import ChecklistStatus


class ChecklistItem(BaseModel):
    """
    A single item in an agent checklist.
    
    Attributes:
        id: Unique item identifier
        description: Task description
        status: Current status
        priority: Priority level (lower = higher priority)
        created_at: Creation timestamp
        updated_at: Last update timestamp
        completed_at: Completion timestamp
        metadata: Additional metadata
        parent_id: Parent item ID for hierarchical checklists
        subtasks: List of subtask IDs
    
    Example:
        item = ChecklistItem(
            description="Research AI topics",
            status=ChecklistStatus.PENDING,
            priority=1
        )
    """
    
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique item identifier"
    )
    description: str = Field(
        description="Task description"
    )
    status: ChecklistStatus = Field(
        default=ChecklistStatus.PENDING,
        description="Current status"
    )
    priority: int = Field(
        default=0,
        ge=0,
        description="Priority level (lower = higher priority)"
    )
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Creation timestamp"
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Last update timestamp"
    )
    completed_at: Optional[str] = Field(
        default=None,
        description="Completion timestamp"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    parent_id: Optional[str] = Field(
        default=None,
        description="Parent item ID for hierarchical checklists"
    )
    subtasks: List[str] = Field(
        default_factory=list,
        description="List of subtask IDs"
    )
    
    def is_pending(self) -> bool:
        """Check if item is pending."""
        return self.status == ChecklistStatus.PENDING
    
    def is_in_progress(self) -> bool:
        """Check if item is in progress."""
        return self.status == ChecklistStatus.IN_PROGRESS
    
    def is_completed(self) -> bool:
        """Check if item is completed."""
        return self.status == ChecklistStatus.COMPLETED
    
    def is_failed(self) -> bool:
        """Check if item is failed."""
        return self.status == ChecklistStatus.FAILED
    
    def is_skipped(self) -> bool:
        """Check if item is skipped."""
        return self.status == ChecklistStatus.SKIPPED
    
    def is_done(self) -> bool:
        """Check if item is done (completed or skipped)."""
        return self.status in (ChecklistStatus.COMPLETED, ChecklistStatus.SKIPPED)
    
    def mark_completed(self) -> None:
        """Mark item as completed."""
        self.status = ChecklistStatus.COMPLETED
        self.completed_at = datetime.utcnow().isoformat()
        self.updated_at = datetime.utcnow().isoformat()
    
    def mark_failed(self) -> None:
        """Mark item as failed."""
        self.status = ChecklistStatus.FAILED
        self.updated_at = datetime.utcnow().isoformat()
    
    def mark_in_progress(self) -> None:
        """Mark item as in progress."""
        self.status = ChecklistStatus.IN_PROGRESS
        self.updated_at = datetime.utcnow().isoformat()
    
    def mark_skipped(self) -> None:
        """Mark item as skipped."""
        self.status = ChecklistStatus.SKIPPED
        self.updated_at = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self.model_dump()


class Checklist(BaseModel):
    """
    A checklist for tracking agent goals and progress.
    
    Attributes:
        id: Unique checklist identifier
        name: Checklist name
        description: Checklist description
        items: List of checklist items
        created_at: Creation timestamp
        updated_at: Last update timestamp
        metadata: Additional metadata
    
    Example:
        checklist = Checklist(
            name="Research Tasks",
            description="Tasks for research project"
        )
        checklist.add_item("Research topic", priority=1)
        checklist.add_item("Write summary", priority=2)
    """
    
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique checklist identifier"
    )
    name: str = Field(
        default="Checklist",
        description="Checklist name"
    )
    description: str = Field(
        default="",
        description="Checklist description"
    )
    items: List[ChecklistItem] = Field(
        default_factory=list,
        description="List of checklist items"
    )
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Creation timestamp"
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Last update timestamp"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    
    def add_item(
        self,
        description: str,
        status: ChecklistStatus = ChecklistStatus.PENDING,
        priority: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
        parent_id: Optional[str] = None
    ) -> str:
        """
        Add an item to the checklist.
        
        Args:
            description: Task description
            status: Initial status
            priority: Priority level
            metadata: Optional metadata
            parent_id: Optional parent item ID
            
        Returns:
            ID of the new item
        """
        item = ChecklistItem(
            description=description,
            status=status,
            priority=priority,
            metadata=metadata or {},
            parent_id=parent_id
        )
        self.items.append(item)
        self.updated_at = datetime.utcnow().isoformat()
        
        # If parent specified, add to parent's subtasks
        if parent_id:
            parent = self.get_item(parent_id)
            if parent:
                parent.subtasks.append(item.id)
        
        return item.id
    
    def get_item(self, item_id: str) -> Optional[ChecklistItem]:
        """Get an item by ID."""
        for item in self.items:
            if item.id == item_id:
                return item
        return None
    
    def get_item_by_description(self, description: str) -> Optional[ChecklistItem]:
        """Get an item by description."""
        for item in self.items:
            if item.description == description:
                return item
        return None
    
    def update_status(self, item_id: str, status: ChecklistStatus) -> None:
        """Update the status of an item."""
        item = self.get_item(item_id)
        if item:
            item.status = status
            item.updated_at = datetime.utcnow().isoformat()
            if status == ChecklistStatus.COMPLETED:
                item.completed_at = datetime.utcnow().isoformat()
            self.updated_at = datetime.utcnow().isoformat()
    
    def remove_item(self, item_id: str) -> bool:
        """Remove an item from the checklist."""
        item = self.get_item(item_id)
        if item:
            self.items.remove(item)
            # Remove from parent's subtasks if applicable
            if item.parent_id:
                parent = self.get_item(item.parent_id)
                if parent and item_id in parent.subtasks:
                    parent.subtasks.remove(item_id)
            self.updated_at = datetime.utcnow().isoformat()
            return True
        return False
    
    def get_pending_items(self) -> List[ChecklistItem]:
        """Get all pending items."""
        return [item for item in self.items if item.is_pending()]
    
    def get_in_progress_items(self) -> List[ChecklistItem]:
        """Get all in-progress items."""
        return [item for item in self.items if item.is_in_progress()]
    
    def get_completed_items(self) -> List[ChecklistItem]:
        """Get all completed items."""
        return [item for item in self.items if item.is_completed()]
    
    def get_failed_items(self) -> List[ChecklistItem]:
        """Get all failed items."""
        return [item for item in self.items if item.is_failed()]
    
    def get_items_by_priority(self) -> List[ChecklistItem]:
        """Get items sorted by priority."""
        return sorted(self.items, key=lambda x: x.priority)
    
    def get_next_pending(self) -> Optional[ChecklistItem]:
        """Get the next pending item by priority."""
        pending = self.get_pending_items()
        if pending:
            return min(pending, key=lambda x: x.priority)
        return None
    
    def is_complete(self) -> bool:
        """Check if all items are done (completed or skipped)."""
        return all(item.is_done() for item in self.items) if self.items else True
    
    def get_progress(self) -> Dict[str, int]:
        """Get progress statistics."""
        return {
            "pending": len([i for i in self.items if i.is_pending()]),
            "in_progress": len([i for i in self.items if i.is_in_progress()]),
            "completed": len([i for i in self.items if i.is_completed()]),
            "failed": len([i for i in self.items if i.is_failed()]),
            "skipped": len([i for i in self.items if i.is_skipped()]),
            "total": len(self.items)
        }
    
    def get_completion_percentage(self) -> float:
        """Get completion percentage."""
        if not self.items:
            return 100.0
        done = len([i for i in self.items if i.is_done()])
        return (done / len(self.items)) * 100.0
    
    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps(self.to_dict(), indent=2)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "items": [item.to_dict() for item in self.items],
            "progress": self.get_progress(),
            "is_complete": self.is_complete(),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Checklist':
        """Create checklist from JSON string."""
        data = json.loads(json_str)
        items = [ChecklistItem(**item) for item in data.get("items", [])]
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", "Checklist"),
            description=data.get("description", ""),
            items=items,
            created_at=data.get("created_at", datetime.utcnow().isoformat()),
            updated_at=data.get("updated_at", datetime.utcnow().isoformat()),
            metadata=data.get("metadata", {})
        )

