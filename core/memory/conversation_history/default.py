"""
Default Conversation History Implementation.

Standard in-memory conversation history for general use.

Version: 1.0.0
"""

from typing import Any, Dict, List, Optional

from ..state.models import Message
from .base import BaseConversationHistory


class DefaultConversationHistory(BaseConversationHistory):
    """
    Default in-memory conversation history.
    
    Standard implementation that works for most use cases.
    Manages messages between user, assistant, system, and tools.
    
    Usage:
        history = DefaultConversationHistory()
        
        # Add messages
        history.add_message("system", "You are a helpful assistant.")
        history.add_message("user", "Hello!")
        history.add_message("assistant", "Hi there!")
        
        # Get messages for LLM
        messages = history.to_llm_messages()
    """
    
    def add_message(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Add a message to history.
        
        Args:
            role: Message role (user, assistant, system, tool)
            content: Message content
            metadata: Optional metadata
            
        Returns:
            Message ID
        """
        message = Message(
            role=role,
            content=content,
            metadata=metadata or {},
        )
        
        self._messages.append(message)
        self._trim_messages()
        
        return message.id
    
    def get_messages(
        self,
        limit: Optional[int] = None,
        roles: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get messages.
        
        Args:
            limit: Max messages to return (from most recent)
            roles: Filter by roles
            
        Returns:
            List of message dicts
        """
        messages = self._messages
        
        if roles:
            messages = [m for m in messages if m.role in roles]
        
        if limit and len(messages) > limit:
            messages = messages[-limit:]
        
        return [m.model_dump() for m in messages]
    
    def get_last_message(self, role: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get the last message, optionally filtered by role."""
        messages = self._messages
        
        if role:
            messages = [m for m in messages if m.role == role]
        
        if messages:
            return messages[-1].model_dump()
        return None
    
    def get_message_count(self) -> int:
        """Get total message count."""
        return len(self._messages)
    
    def clear_messages(self) -> None:
        """Clear all messages."""
        self._messages.clear()
    
    def to_llm_messages(self, max_messages: Optional[int] = None) -> List[Dict[str, str]]:
        """
        Convert to LLM-compatible message format.
        
        Standard format: List of {"role": str, "content": str}
        
        Args:
            max_messages: Max messages to include
            
        Returns:
            List of {"role": str, "content": str} dicts
        """
        messages = self._get_messages_for_llm(max_messages)
        return [m.to_llm_format() for m in messages]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DefaultConversationHistory':
        """Create from dictionary."""
        history = cls(max_messages=data.get("max_messages"))
        for msg_data in data.get("messages", []):
            history._messages.append(Message(**msg_data))
        return history


# Alias for backward compatibility
ConversationHistory = DefaultConversationHistory
