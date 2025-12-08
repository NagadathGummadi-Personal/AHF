"""
Memory State Models.

Pydantic models for memory state, checkpoints, and snapshots.

Version: 1.0.0
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import uuid


class Message(BaseModel):
    """A conversation message."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    role: str = Field(..., description="Message role (user, assistant, system, tool)")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def to_llm_format(self) -> Dict[str, str]:
        """Convert to LLM-compatible format."""
        return {"role": self.role, "content": self.content}


class CheckpointMetadata(BaseModel):
    """Metadata for a checkpoint."""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    component_type: Optional[str] = Field(default=None, description="Type of component (workflow, node, agent)")
    component_id: Optional[str] = Field(default=None, description="ID of the component")
    description: Optional[str] = Field(default=None, description="Checkpoint description")
    tags: List[str] = Field(default_factory=list)
    custom: Dict[str, Any] = Field(default_factory=dict)


class Checkpoint(BaseModel):
    """
    A checkpoint capturing state at a point in time.
    
    Used for workflow recovery and state persistence.
    """
    id: str = Field(..., description="Unique checkpoint identifier")
    state: Dict[str, Any] = Field(default_factory=dict, description="State data")
    metadata: CheckpointMetadata = Field(default_factory=CheckpointMetadata)
    
    # Conversation state at checkpoint
    messages: List[Message] = Field(default_factory=list, description="Messages at checkpoint")
    message_count: int = Field(default=0, description="Number of messages")
    
    # Variables at checkpoint
    variables: Dict[str, Any] = Field(default_factory=dict, description="Variables at checkpoint")
    
    def age_seconds(self) -> float:
        """Get age of checkpoint in seconds."""
        delta = datetime.utcnow() - self.metadata.created_at
        return delta.total_seconds()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self.model_dump(mode='json')
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Checkpoint':
        """Create from dictionary."""
        return cls(**data)


class StateSnapshot(BaseModel):
    """
    A complete snapshot of memory state.
    
    Includes all state, messages, variables, and metadata.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = Field(..., description="Session identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # State data
    state: Dict[str, Any] = Field(default_factory=dict)
    variables: Dict[str, Any] = Field(default_factory=dict)
    
    # Conversation
    messages: List[Message] = Field(default_factory=list)
    
    # Checkpoints
    checkpoints: List[Checkpoint] = Field(default_factory=list)
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self.model_dump(mode='json')
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StateSnapshot':
        """Create from dictionary."""
        return cls(**data)


class MemoryState(BaseModel):
    """
    Complete memory state for serialization.
    
    Contains everything needed to save/restore working memory.
    """
    session_id: str = Field(..., description="Session identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Conversation history
    messages: List[Message] = Field(default_factory=list)
    
    # State tracking
    state: Dict[str, Any] = Field(default_factory=dict)
    variables: Dict[str, Any] = Field(default_factory=dict)
    
    # Checkpoints
    checkpoints: Dict[str, Checkpoint] = Field(default_factory=dict)
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def add_message(self, message: Message) -> None:
        """Add a message."""
        self.messages.append(message)
        self.updated_at = datetime.utcnow()
    
    def get_llm_messages(self, max_messages: Optional[int] = None) -> List[Dict[str, str]]:
        """Get messages in LLM format."""
        messages = self.messages
        if max_messages and len(messages) > max_messages:
            messages = messages[-max_messages:]
        return [m.to_llm_format() for m in messages]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self.model_dump(mode='json')
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryState':
        """Create from dictionary."""
        return cls(**data)

