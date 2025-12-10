"""
Voice Agent Memory Module

Custom memory implementations for the voice agent workflow.
All implementations extend base classes from core.memory.

Components:
- VoiceAgentTaskQueue: Task queue for user requests (extends BaseTaskQueue)
- VoiceAgentCheckpointer: DynamoDB checkpointer with TTL (from core.memory)
- VoiceAgentSession: Unified session memory (uses core.memory.WorkingMemory)
"""

from .task_queue import VoiceAgentTaskQueue
from .checkpointer import (
    VoiceAgentCheckpointer,
    DynamoDBCheckpointer,
    create_voice_agent_checkpointer,
    DEFAULT_TTL_DAYS,
    MAX_TTL_DAYS,
)
from .session import VoiceAgentSession, create_session

__all__ = [
    "VoiceAgentTaskQueue",
    "VoiceAgentCheckpointer",
    "DynamoDBCheckpointer",
    "create_voice_agent_checkpointer",
    "DEFAULT_TTL_DAYS",
    "MAX_TTL_DAYS",
    "VoiceAgentSession",
    "create_session",
]
