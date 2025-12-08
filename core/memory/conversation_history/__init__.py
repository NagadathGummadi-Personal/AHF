"""
Conversation History Module.

Provides base class and implementations for conversation history.
Extend BaseConversationHistory to create custom formats for different workflows.

Version: 1.0.0
"""

from .base import BaseConversationHistory
from .default import DefaultConversationHistory, ConversationHistory

__all__ = [
    "BaseConversationHistory",
    "DefaultConversationHistory",
    "ConversationHistory",  # Alias for backward compatibility
]
