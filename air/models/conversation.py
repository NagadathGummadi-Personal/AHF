"""
Conversation Models

Models for managing conversation history and LLM message formatting.

Version: 1.0.0
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, Field


class ConversationRole(str, Enum):
    """Message role in conversation."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    TOOL_RESULT = "tool_result"


class ConversationMessage(BaseModel):
    """
    A single message in the conversation history.
    
    Stores complete message information including metadata
    for conversation tracking and analysis.
    """
    
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    role: ConversationRole
    content: str
    
    # Timestamps
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Tool-specific fields
    tool_name: Optional[str] = Field(default=None, description="Name of tool if role is tool")
    tool_call_id: Optional[str] = Field(default=None, description="Tool call ID for correlation")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Token tracking
    tokens: Optional[int] = Field(default=None, description="Token count for this message")
    
    # Node tracking
    node_id: Optional[str] = Field(default=None, description="Node that generated this message")
    
    def to_llm_format(self) -> Dict[str, str]:
        """Convert to LLM-compatible format."""
        result = {
            "role": self.role.value if self.role != ConversationRole.TOOL_RESULT else "tool",
            "content": self.content,
        }
        
        if self.tool_call_id:
            result["tool_call_id"] = self.tool_call_id
        
        if self.tool_name:
            result["name"] = self.tool_name
        
        return result
    
    @classmethod
    def user(cls, content: str, **kwargs) -> "ConversationMessage":
        """Create a user message."""
        return cls(role=ConversationRole.USER, content=content, **kwargs)
    
    @classmethod
    def assistant(cls, content: str, **kwargs) -> "ConversationMessage":
        """Create an assistant message."""
        return cls(role=ConversationRole.ASSISTANT, content=content, **kwargs)
    
    @classmethod
    def system(cls, content: str, **kwargs) -> "ConversationMessage":
        """Create a system message."""
        return cls(role=ConversationRole.SYSTEM, content=content, **kwargs)
    
    @classmethod
    def tool(
        cls,
        tool_name: str,
        content: str,
        tool_call_id: Optional[str] = None,
        **kwargs,
    ) -> "ConversationMessage":
        """Create a tool message."""
        return cls(
            role=ConversationRole.TOOL,
            content=content,
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            **kwargs,
        )
    
    @classmethod
    def tool_result(
        cls,
        tool_name: str,
        content: str,
        tool_call_id: Optional[str] = None,
        **kwargs,
    ) -> "ConversationMessage":
        """Create a tool result message."""
        return cls(
            role=ConversationRole.TOOL_RESULT,
            content=content,
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            **kwargs,
        )


class LLMMessagePayload(BaseModel):
    """
    Complete message payload for LLM inference.
    
    Combines all context needed for a single LLM call.
    """
    
    # System prompt
    system_prompt: str = Field(..., description="System prompt for the agent")
    
    # Conversation history
    conversation_history: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Previous conversation messages in LLM format"
    )
    
    # Current user input
    user_input: str = Field(..., description="Current user message")
    
    # Task context
    current_task_status: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Current task state and progress"
    )
    
    # Tools available
    tools: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Available tools in LLM function format"
    )
    
    # Retrieved context
    kb_chunks_retrieved: List[str] = Field(
        default_factory=list,
        description="Knowledge base chunks retrieved via RAG"
    )
    
    # Additional context
    customer_instructions: Optional[str] = Field(
        default=None,
        description="Additional customer-provided instructions"
    )
    
    def to_messages(self) -> List[Dict[str, str]]:
        """Convert to LLM messages format."""
        messages = []
        
        # Add system prompt with all context
        system_content = self._build_system_content()
        messages.append({"role": "system", "content": system_content})
        
        # Add conversation history
        messages.extend(self.conversation_history)
        
        # Add current user input
        messages.append({"role": "user", "content": self.user_input})
        
        return messages
    
    def _build_system_content(self) -> str:
        """Build complete system prompt with all context."""
        parts = [self.system_prompt]
        
        # Add customer instructions
        if self.customer_instructions:
            parts.append(f"\n\n<Customer Instructions>\n{self.customer_instructions}\n</Customer Instructions>")
        
        # Add task status
        if self.current_task_status:
            import json
            status_str = json.dumps(self.current_task_status, indent=2)
            parts.append(f"\n\n<Current Task Status>\n{status_str}\n</Current Task Status>")
        
        # Add KB context
        if self.kb_chunks_retrieved:
            kb_content = "\n---\n".join(self.kb_chunks_retrieved)
            parts.append(f"\n\n<Knowledge Base Context>\n{kb_content}\n</Knowledge Base Context>")
        
        return "".join(parts)

