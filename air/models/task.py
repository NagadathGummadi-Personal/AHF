"""
Task Models

Models for managing user tasks/requests in the workflow.
A task represents a user's intent and the plan to fulfill it.

Version: 1.0.0
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, Field


class TaskState(str, Enum):
    """Task execution state."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(int, Enum):
    """Task priority levels."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    INTERRUPT = 3  # User interrupt - highest priority


class TaskStep(BaseModel):
    """A single step in a task execution plan."""
    
    step_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    step_name: str = Field(..., description="Name of this step")
    step_type: str = Field(..., description="Type: collect_service, collect_therapist, confirm, etc.")
    
    # Execution state
    state: TaskState = Field(default=TaskState.PENDING)
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    
    # Step data
    input_data: Dict[str, Any] = Field(default_factory=dict)
    output_data: Dict[str, Any] = Field(default_factory=dict)
    
    # Configuration
    required: bool = Field(default=True)
    order: int = Field(default=0, description="Execution order within plan")
    retry_count: int = Field(default=0)
    max_retries: int = Field(default=3)
    
    # Error handling
    error: Optional[str] = Field(default=None)
    fallback_step: Optional[str] = Field(default=None, description="Step to go to on failure")
    
    def mark_started(self) -> None:
        """Mark step as started."""
        self.state = TaskState.IN_PROGRESS
        self.started_at = datetime.utcnow()
    
    def mark_completed(self, output: Optional[Dict[str, Any]] = None) -> None:
        """Mark step as completed."""
        self.state = TaskState.COMPLETED
        self.completed_at = datetime.utcnow()
        if output:
            self.output_data = output
    
    def mark_failed(self, error: str) -> None:
        """Mark step as failed."""
        self.state = TaskState.FAILED
        self.error = error
        self.completed_at = datetime.utcnow()
    
    def is_completed(self) -> bool:
        """Check if step is completed."""
        return self.state == TaskState.COMPLETED
    
    def is_pending(self) -> bool:
        """Check if step is pending."""
        return self.state == TaskState.PENDING


class TaskPlan(BaseModel):
    """Execution plan for a task."""
    
    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    steps: List[TaskStep] = Field(default_factory=list)
    
    # Plan metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Current execution pointer
    current_step_index: int = Field(default=0)
    
    def add_step(
        self,
        step_name: str,
        step_type: str,
        required: bool = True,
        input_data: Optional[Dict[str, Any]] = None,
    ) -> TaskStep:
        """Add a step to the plan."""
        step = TaskStep(
            step_name=step_name,
            step_type=step_type,
            required=required,
            order=len(self.steps),
            input_data=input_data or {},
        )
        self.steps.append(step)
        self.updated_at = datetime.utcnow()
        return step
    
    def get_current_step(self) -> Optional[TaskStep]:
        """Get the current step."""
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None
    
    def advance_to_next_step(self) -> Optional[TaskStep]:
        """Advance to the next pending step."""
        for i in range(self.current_step_index + 1, len(self.steps)):
            if self.steps[i].is_pending():
                self.current_step_index = i
                return self.steps[i]
        return None
    
    def get_step_by_id(self, step_id: str) -> Optional[TaskStep]:
        """Get a step by ID."""
        for step in self.steps:
            if step.step_id == step_id:
                return step
        return None
    
    def get_completed_steps(self) -> List[TaskStep]:
        """Get all completed steps."""
        return [s for s in self.steps if s.is_completed()]
    
    def get_pending_steps(self) -> List[TaskStep]:
        """Get all pending steps."""
        return [s for s in self.steps if s.is_pending()]
    
    def is_complete(self) -> bool:
        """Check if all required steps are complete."""
        return all(
            s.is_completed() for s in self.steps if s.required
        )
    
    def get_progress(self) -> float:
        """Get completion progress (0.0 to 1.0)."""
        if not self.steps:
            return 1.0
        completed = len(self.get_completed_steps())
        return completed / len(self.steps)


class Task(BaseModel):
    """
    A user task/request to be processed by the workflow.
    
    A task represents a complete user intent (e.g., "book a haircut")
    along with the plan to fulfill it and all collected data.
    """
    
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    # Task identity
    intent: str = Field(..., description="User intent: BOOK, CANCEL, RESCHEDULE, FAQ")
    original_input: str = Field(default="", description="Original user input that created this task")
    
    # State
    state: TaskState = Field(default=TaskState.PENDING)
    priority: TaskPriority = Field(default=TaskPriority.NORMAL)
    
    # Execution plan
    plan: Optional[TaskPlan] = Field(default=None)
    
    # Collected data
    collected_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Data collected during task execution"
    )
    
    # Service booking specific
    services: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Services to book"
    )
    therapists: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Selected therapists"
    )
    addons: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Selected add-ons"
    )
    
    # Context
    session_id: str = Field(default="", description="Session this task belongs to")
    workflow_id: str = Field(default="", description="Workflow executing this task")
    current_node: Optional[str] = Field(default=None, description="Current workflow node")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    
    # Error tracking
    error: Optional[str] = Field(default=None)
    retry_count: int = Field(default=0)
    
    # Pause/resume support
    paused_at_step: Optional[str] = Field(default=None)
    pause_reason: Optional[str] = Field(default=None)
    
    def start(self) -> None:
        """Mark task as started."""
        self.state = TaskState.IN_PROGRESS
        self.started_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def complete(self) -> None:
        """Mark task as completed."""
        self.state = TaskState.COMPLETED
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def fail(self, error: str) -> None:
        """Mark task as failed."""
        self.state = TaskState.FAILED
        self.error = error
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def pause(self, step_id: Optional[str] = None, reason: Optional[str] = None) -> None:
        """Pause task execution."""
        self.state = TaskState.PAUSED
        self.paused_at_step = step_id
        self.pause_reason = reason
        self.updated_at = datetime.utcnow()
    
    def resume(self) -> None:
        """Resume task execution."""
        self.state = TaskState.IN_PROGRESS
        self.paused_at_step = None
        self.pause_reason = None
        self.updated_at = datetime.utcnow()
    
    def add_service(
        self,
        service_id: str,
        service_name: str,
        **kwargs,
    ) -> None:
        """Add a service to the task."""
        self.services.append({
            "service_id": service_id,
            "service_name": service_name,
            **kwargs,
        })
        self.updated_at = datetime.utcnow()
    
    def set_data(self, key: str, value: Any) -> None:
        """Set collected data."""
        self.collected_data[key] = value
        self.updated_at = datetime.utcnow()
    
    def get_data(self, key: str, default: Any = None) -> Any:
        """Get collected data."""
        return self.collected_data.get(key, default)
    
    def create_plan(
        self,
        allows_multiple_services: bool = False,
        allows_multiple_therapists: bool = False,
    ) -> TaskPlan:
        """
        Create execution plan based on booking configuration.
        
        Args:
            allows_multiple_services: Whether center allows multiple service booking
            allows_multiple_therapists: Whether center allows multiple therapist selection
        """
        plan = TaskPlan()
        
        num_services = len(self.services) if self.services else 1
        
        if allows_multiple_services and allows_multiple_therapists:
            # Collect service 1 -> therapist 1 -> service 2 -> therapist 2 ...
            for i in range(num_services):
                plan.add_step(
                    step_name=f"Collect Service {i+1} Details",
                    step_type="collect_service",
                    input_data={"service_index": i},
                )
                plan.add_step(
                    step_name=f"Collect Therapist {i+1} Details",
                    step_type="collect_therapist",
                    input_data={"service_index": i},
                )
        elif allows_multiple_services and not allows_multiple_therapists:
            # Collect all services first, then one therapist
            for i in range(num_services):
                plan.add_step(
                    step_name=f"Collect Service {i+1} Details",
                    step_type="collect_service",
                    input_data={"service_index": i},
                )
            plan.add_step(
                step_name="Collect Therapist Details",
                step_type="collect_therapist",
                input_data={"service_index": 0},
            )
        else:
            # Single service, single therapist
            plan.add_step(
                step_name="Collect Service Details",
                step_type="collect_service",
                input_data={"service_index": 0},
            )
            plan.add_step(
                step_name="Collect Therapist Details",
                step_type="collect_therapist",
                input_data={"service_index": 0},
            )
        
        # Add common final steps
        plan.add_step(
            step_name="Check Availability",
            step_type="check_availability",
        )
        plan.add_step(
            step_name="Confirm Booking",
            step_type="confirm_booking",
        )
        
        self.plan = plan
        self.updated_at = datetime.utcnow()
        return plan
    
    def is_booking_intent(self) -> bool:
        """Check if this is a booking task."""
        return self.intent.upper() in ("BOOK", "BOOKING")
    
    def is_cancellation_intent(self) -> bool:
        """Check if this is a cancellation task."""
        return self.intent.upper() in ("CANCEL", "CANCELLATION")
    
    def is_reschedule_intent(self) -> bool:
        """Check if this is a reschedule task."""
        return self.intent.upper() in ("RESCHEDULE", "RESCHEDULING")

