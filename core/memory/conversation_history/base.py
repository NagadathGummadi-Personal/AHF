"""
Conversation History Base Class.

Defines the abstract base class for conversation history implementations.
Extend this class to create custom conversation history formats for different workflows.

Version: 1.1.0
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from ..state.models import Message
from utils.serialization import SerializableMixin


class BaseConversationHistory(ABC, SerializableMixin):
    """
    Abstract base class for conversation history.
    
    Extend this class to create custom conversation history implementations
    for different workflows (e.g., multi-turn chat, task-based, RAG-enhanced).
    
    Example:
        class ChatConversationHistory(BaseConversationHistory):
            def to_llm_messages(self, max_messages: Optional[int] = None) -> List[Dict[str, str]]:
                # Custom format for chat-based workflows
                messages = self._get_messages_for_llm(max_messages)
                return [{"role": m.role, "content": m.content} for m in messages]
    """
    
    def __init__(self, max_messages: Optional[int] = None):
        """
        Initialize conversation history.
        
        Args:
            max_messages: Max messages to keep (None = unlimited)
        """
        self._messages: List[Message] = []
        self._max_messages = max_messages
    
    @abstractmethod
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
        ...
    
    @abstractmethod
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
        ...
    
    @abstractmethod
    def get_last_message(self, role: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get the last message, optionally filtered by role."""
        ...
    
    @abstractmethod
    def get_message_count(self) -> int:
        """Get total message count."""
        ...
    
    @abstractmethod
    def clear_messages(self) -> None:
        """Clear all messages."""
        ...
    
    @abstractmethod
    def to_llm_messages(self, max_messages: Optional[int] = None) -> List[Dict[str, str]]:
        """
        Convert to LLM-compatible message format.
        
        Override this method to customize the format for different LLM providers
        or workflow requirements.
        
        Args:
            max_messages: Max messages to include
            
        Returns:
            List of {"role": str, "content": str} dicts
        """
        ...
    
    # =========================================================================
    # Helper Methods (Non-abstract - available to all implementations)
    # =========================================================================
    
    def _get_messages_for_llm(self, max_messages: Optional[int] = None) -> List[Message]:
        """
        Get messages prepared for LLM (handles max_messages with system message priority).
        
        Helper method that subclasses can use in their to_llm_messages implementation.
        Always preserves system messages.
        
        Args:
            max_messages: Max messages to include
            
        Returns:
            List of Message objects
        """
        messages = self._messages
        
        if max_messages and len(messages) > max_messages:
            # Always include system messages
            system_msgs = [m for m in messages if m.role == "system"]
            other_msgs = [m for m in messages if m.role != "system"]
            
            # Calculate how many non-system to include
            keep_count = max_messages - len(system_msgs)
            if keep_count > 0:
                other_msgs = other_msgs[-keep_count:]
            else:
                other_msgs = []
            
            messages = system_msgs + other_msgs
        
        return messages
    
    def _trim_messages(self) -> None:
        """
        Trim messages to max_messages limit while preserving system messages.
        
        Helper method that subclasses can call after adding messages.
        """
        if self._max_messages and len(self._messages) > self._max_messages:
            system_msgs = [m for m in self._messages if m.role == "system"]
            other_msgs = [m for m in self._messages if m.role != "system"]
            
            keep_count = self._max_messages - len(system_msgs)
            if keep_count > 0:
                other_msgs = other_msgs[-keep_count:]
            else:
                other_msgs = []
            
            self._messages = system_msgs + other_msgs
    
    def get_raw_messages(self) -> List[Message]:
        """Get raw Message objects."""
        return self._messages.copy()
    
    def set_raw_messages(self, messages: List[Message]) -> None:
        """Set raw Message objects (for restoration)."""
        self._messages = messages.copy()
    
    def to_dict(self) -> Dict[str, Any]:
        """Export to dictionary."""
        return {
            "messages": [m.model_dump() for m in self._messages],
            "max_messages": self._max_messages,
        }
    
    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseConversationHistory':
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
