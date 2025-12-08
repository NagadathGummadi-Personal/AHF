"""
Interrupt State Models.

Tracks the state of interrupted operations and stashed responses.

Version: 1.0.0
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class InterruptReason(str, Enum):
    """Reason for interrupt."""
    USER_INTERRUPT = "user_interrupt"
    SYSTEM_INTERRUPT = "system_interrupt"
    TIMEOUT = "timeout"
    ERROR = "error"
    PRIORITY_MESSAGE = "priority_message"
    VOICE_ACTIVITY = "voice_activity"


class StashedResponse(BaseModel):
    """
    Represents a stashed partial response.
    
    When an operation is interrupted, the partial response is stashed
    for potential use in continuation.
    
    Attributes:
        content: The partial response content
        component_type: Type of component that was interrupted
        component_id: ID of the interrupted component
        interrupt_reason: Why the interrupt occurred
        stashed_at: When the response was stashed
        conversation_context: Conversation context at time of interrupt
        metadata: Additional metadata
    """
    content: str = Field(..., description="Partial response content")
    component_type: str = Field(..., description="Type of component (llm, agent, node, workflow)")
    component_id: str = Field(..., description="ID of the interrupted component")
    interrupt_reason: InterruptReason = Field(
        default=InterruptReason.USER_INTERRUPT,
        description="Why the interrupt occurred"
    )
    stashed_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the response was stashed"
    )
    
    # Context at time of interrupt
    last_user_message: Optional[str] = Field(
        default=None,
        description="Last user message before interrupt"
    )
    conversation_messages: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Conversation history at time of interrupt"
    )
    
    # Execution state
    execution_progress: Optional[float] = Field(
        default=None,
        ge=0,
        le=1,
        description="Progress through execution (0-1)"
    )
    tokens_generated: int = Field(
        default=0,
        ge=0,
        description="Tokens generated before interrupt"
    )
    
    # Tool state (if interrupted during tool call)
    pending_tool_call: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Tool call that was pending when interrupted"
    )
    tool_results: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Tool results collected before interrupt"
    )
    
    # Metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    
    def age_ms(self) -> float:
        """Get age of stashed response in milliseconds."""
        delta = datetime.utcnow() - self.stashed_at
        return delta.total_seconds() * 1000
    
    def is_expired(self, max_age_ms: int = 60000) -> bool:
        """Check if stashed response has expired."""
        return self.age_ms() > max_age_ms
    
    def get_truncated_content(self, max_length: int = 500) -> str:
        """Get truncated content for logging."""
        if len(self.content) <= max_length:
            return self.content
        return self.content[:max_length - 3] + "..."


class InterruptState(BaseModel):
    """
    Current interrupt state for a component.
    
    Tracks whether an interrupt has occurred and manages stashed responses.
    
    Attributes:
        is_interrupted: Whether an interrupt signal has been received
        interrupt_time: When the interrupt occurred
        interrupt_reason: Reason for the interrupt
        stashed_response: The stashed partial response (if any)
        waiting_for_followup: Whether we're waiting for a follow-up message
        followup_deadline: Deadline for receiving follow-up message
    """
    is_interrupted: bool = Field(
        default=False,
        description="Whether an interrupt signal has been received"
    )
    interrupt_time: Optional[datetime] = Field(
        default=None,
        description="When the interrupt occurred"
    )
    interrupt_reason: Optional[InterruptReason] = Field(
        default=None,
        description="Reason for the interrupt"
    )
    
    stashed_response: Optional[StashedResponse] = Field(
        default=None,
        description="The stashed partial response"
    )
    
    waiting_for_followup: bool = Field(
        default=False,
        description="Whether waiting for follow-up message"
    )
    followup_deadline: Optional[datetime] = Field(
        default=None,
        description="Deadline for receiving follow-up"
    )
    followup_received: bool = Field(
        default=False,
        description="Whether follow-up message was received"
    )
    followup_message: Optional[str] = Field(
        default=None,
        description="The follow-up message (if received)"
    )
    
    # Continuation tracking
    continuation_generated: bool = Field(
        default=False,
        description="Whether continuation response was generated"
    )
    continuation_content: Optional[str] = Field(
        default=None,
        description="The continuation response content"
    )
    
    def reset(self):
        """Reset interrupt state."""
        self.is_interrupted = False
        self.interrupt_time = None
        self.interrupt_reason = None
        self.stashed_response = None
        self.waiting_for_followup = False
        self.followup_deadline = None
        self.followup_received = False
        self.followup_message = None
        self.continuation_generated = False
        self.continuation_content = None
    
    def set_interrupted(
        self,
        reason: InterruptReason = InterruptReason.USER_INTERRUPT,
        stashed: Optional[StashedResponse] = None,
    ):
        """Set interrupt state."""
        self.is_interrupted = True
        self.interrupt_time = datetime.utcnow()
        self.interrupt_reason = reason
        self.stashed_response = stashed
    
    def start_waiting_for_followup(self, timeout_ms: int):
        """Start waiting for follow-up message."""
        from datetime import timedelta
        self.waiting_for_followup = True
        self.followup_deadline = datetime.utcnow() + timedelta(milliseconds=timeout_ms)
    
    def receive_followup(self, message: str):
        """Record receipt of follow-up message."""
        self.waiting_for_followup = False
        self.followup_received = True
        self.followup_message = message
    
    def is_followup_deadline_passed(self) -> bool:
        """Check if follow-up deadline has passed."""
        if not self.followup_deadline:
            return True
        return datetime.utcnow() > self.followup_deadline
    
    def has_stashed_response(self) -> bool:
        """Check if there's a stashed response."""
        return self.stashed_response is not None
    
    def should_combine_with_followup(self) -> bool:
        """Check if we should combine stashed response with follow-up."""
        return (
            self.has_stashed_response() and
            self.followup_received and
            self.followup_message is not None
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self.model_dump(
            exclude_none=True,
            mode='json'
        )
