"""
Workflow State Models

Models for tracking workflow execution state, step progress,
and interrupt handling.

Version: 1.0.0
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, Field


class StepStatus(str, Enum):
    """Status of a workflow step."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


class StepTracker(BaseModel):
    """
    Tracks progress through workflow steps.
    
    Each step can be marked as completed, allowing the workflow
    to resume from where it left off.
    """
    
    # Step tracking
    steps: Dict[str, StepStatus] = Field(default_factory=dict)
    step_data: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    step_order: List[str] = Field(default_factory=list)
    
    # Current position
    current_step: Optional[str] = Field(default=None)
    current_step_index: int = Field(default=0)
    
    # Timestamps
    step_timestamps: Dict[str, datetime] = Field(default_factory=dict)
    
    def register_step(
        self,
        step_id: str,
        initial_status: StepStatus = StepStatus.NOT_STARTED,
    ) -> None:
        """Register a new step."""
        if step_id not in self.steps:
            self.steps[step_id] = initial_status
            self.step_order.append(step_id)
            self.step_data[step_id] = {}
    
    def start_step(self, step_id: str) -> None:
        """Mark a step as started."""
        self.steps[step_id] = StepStatus.IN_PROGRESS
        self.current_step = step_id
        self.step_timestamps[step_id] = datetime.utcnow()
        
        if step_id in self.step_order:
            self.current_step_index = self.step_order.index(step_id)
    
    def complete_step(
        self,
        step_id: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Mark a step as completed."""
        self.steps[step_id] = StepStatus.COMPLETED
        if data:
            self.step_data[step_id] = data
    
    def fail_step(
        self,
        step_id: str,
        error: Optional[str] = None,
    ) -> None:
        """Mark a step as failed."""
        self.steps[step_id] = StepStatus.FAILED
        if error:
            self.step_data[step_id]["error"] = error
    
    def skip_step(self, step_id: str, reason: Optional[str] = None) -> None:
        """Mark a step as skipped."""
        self.steps[step_id] = StepStatus.SKIPPED
        if reason:
            self.step_data[step_id]["skip_reason"] = reason
    
    def is_step_completed(self, step_id: str) -> bool:
        """Check if a step is completed."""
        return self.steps.get(step_id) == StepStatus.COMPLETED
    
    def is_step_pending(self, step_id: str) -> bool:
        """Check if a step is pending (not started or in progress)."""
        status = self.steps.get(step_id)
        return status in (StepStatus.NOT_STARTED, StepStatus.IN_PROGRESS, None)
    
    def get_next_pending_step(self) -> Optional[str]:
        """Get the next pending step."""
        for step_id in self.step_order[self.current_step_index:]:
            if self.is_step_pending(step_id):
                return step_id
        return None
    
    def get_step_data(self, step_id: str) -> Dict[str, Any]:
        """Get data for a step."""
        return self.step_data.get(step_id, {})
    
    def get_progress(self) -> float:
        """Get completion progress (0.0 to 1.0)."""
        if not self.steps:
            return 0.0
        
        completed = sum(
            1 for s in self.steps.values()
            if s in (StepStatus.COMPLETED, StepStatus.SKIPPED)
        )
        return completed / len(self.steps)
    
    def get_completed_steps(self) -> List[str]:
        """Get list of completed step IDs."""
        return [
            step_id for step_id, status in self.steps.items()
            if status == StepStatus.COMPLETED
        ]
    
    def reset(self) -> None:
        """Reset all steps to not started."""
        for step_id in self.steps:
            self.steps[step_id] = StepStatus.NOT_STARTED
        self.current_step = None
        self.current_step_index = 0


class StashedResponse(BaseModel):
    """
    A stashed (partial) response that was interrupted.
    
    Used for interrupt handling - stores the response that was
    being generated when the user interrupted.
    """
    
    stash_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    
    # Content that was being generated
    content: str = Field(default="", description="Partial response content")
    
    # Context at time of interrupt
    node_id: Optional[str] = Field(default=None, description="Node that was generating response")
    step_id: Optional[str] = Field(default=None, description="Step that was in progress")
    
    # Token/generation info
    tokens_generated: int = Field(default=0)
    was_streaming: bool = Field(default=False)
    
    # Timing
    started_at: Optional[datetime] = Field(default=None)
    interrupted_at: datetime = Field(default_factory=datetime.utcnow)
    
    # User interrupt message
    interrupt_message: Optional[str] = Field(default=None)
    
    # Whether to include stashed content in continuation
    include_in_continuation: bool = Field(default=True)
    
    def get_continuation_context(self) -> str:
        """Get context for continuing after interrupt."""
        if not self.include_in_continuation or not self.content:
            return ""
        
        return (
            f"[You were in the middle of saying: \"{self.content}...\" "
            f"when the user interrupted with: \"{self.interrupt_message}\". "
            f"Address their new message appropriately.]"
        )


class WorkflowState(BaseModel):
    """
    Complete workflow execution state.
    
    Tracks all aspects of workflow execution for persistence
    and recovery.
    """
    
    state_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    # Workflow identity
    workflow_id: str = Field(default="")
    session_id: str = Field(default="")
    execution_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    # Current position
    current_node_id: Optional[str] = Field(default=None)
    previous_node_id: Optional[str] = Field(default=None)
    
    # Node visit history
    node_history: List[str] = Field(default_factory=list)
    
    # Step tracking
    step_tracker: StepTracker = Field(default_factory=StepTracker)
    
    # Variables
    variables: Dict[str, Any] = Field(default_factory=dict)
    
    # Task tracking
    current_task_id: Optional[str] = Field(default=None)
    task_queue: List[str] = Field(default_factory=list, description="Queue of task IDs")
    completed_tasks: List[str] = Field(default_factory=list)
    
    # Interrupt handling
    is_interrupted: bool = Field(default=False)
    stashed_response: Optional[StashedResponse] = Field(default=None)
    pending_interrupt: Optional[str] = Field(default=None)
    
    # Error tracking
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    last_error: Optional[str] = Field(default=None)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    
    # Status
    is_active: bool = Field(default=True)
    is_completed: bool = Field(default=False)
    
    def move_to_node(self, node_id: str) -> None:
        """Move to a new node."""
        self.previous_node_id = self.current_node_id
        self.current_node_id = node_id
        self.node_history.append(node_id)
        self.updated_at = datetime.utcnow()
    
    def set_variable(self, key: str, value: Any) -> None:
        """Set a variable."""
        self.variables[key] = value
        self.updated_at = datetime.utcnow()
    
    def get_variable(self, key: str, default: Any = None) -> Any:
        """Get a variable."""
        return self.variables.get(key, default)
    
    def stash_response(
        self,
        content: str,
        interrupt_message: str,
        **kwargs,
    ) -> StashedResponse:
        """Stash current response for interrupt handling."""
        self.stashed_response = StashedResponse(
            content=content,
            interrupt_message=interrupt_message,
            node_id=self.current_node_id,
            **kwargs,
        )
        self.is_interrupted = True
        self.pending_interrupt = interrupt_message
        self.updated_at = datetime.utcnow()
        return self.stashed_response
    
    def clear_interrupt(self) -> Optional[StashedResponse]:
        """Clear interrupt state and return stashed response."""
        stashed = self.stashed_response
        self.stashed_response = None
        self.is_interrupted = False
        self.pending_interrupt = None
        self.updated_at = datetime.utcnow()
        return stashed
    
    def add_error(self, error: str, node_id: Optional[str] = None) -> None:
        """Add an error."""
        self.errors.append({
            "error": error,
            "node_id": node_id or self.current_node_id,
            "timestamp": datetime.utcnow().isoformat(),
        })
        self.last_error = error
        self.updated_at = datetime.utcnow()
    
    def queue_task(self, task_id: str) -> None:
        """Add a task to the queue."""
        if task_id not in self.task_queue:
            self.task_queue.append(task_id)
            self.updated_at = datetime.utcnow()
    
    def dequeue_task(self) -> Optional[str]:
        """Remove and return the next task from the queue."""
        if self.task_queue:
            task_id = self.task_queue.pop(0)
            self.updated_at = datetime.utcnow()
            return task_id
        return None
    
    def complete_task(self, task_id: str) -> None:
        """Mark a task as completed."""
        if task_id in self.task_queue:
            self.task_queue.remove(task_id)
        self.completed_tasks.append(task_id)
        self.updated_at = datetime.utcnow()
    
    def mark_completed(self) -> None:
        """Mark workflow as completed."""
        self.is_active = False
        self.is_completed = True
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def to_checkpoint_data(self) -> Dict[str, Any]:
        """Export state for checkpointing."""
        return self.model_dump(mode="json")
    
    @classmethod
    def from_checkpoint_data(cls, data: Dict[str, Any]) -> "WorkflowState":
        """Restore state from checkpoint data."""
        return cls(**data)

