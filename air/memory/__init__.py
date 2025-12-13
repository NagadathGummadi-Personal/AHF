"""
Voice Agent Memory Module

Custom memory implementations for the voice agent workflow.
All implementations extend base classes from core.memory.

Components:
- VoiceAgentTaskQueue: Task queue for user requests (extends BaseTaskQueue)
- VoiceAgentSession: Unified session memory (uses core.memory.WorkingMemory)
"""

from .task_queue import VoiceAgentTaskQueue
from .session import VoiceAgentSession, create_session

__all__ = [
    "VoiceAgentTaskQueue",
    "VoiceAgentSession",
    "create_session",
]
