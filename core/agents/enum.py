"""
Enumerations for Agents Subsystem.

This module defines all enumerations used throughout the Agents subsystem including
agent types, states, input/output types, and checklist statuses.

All enum values are imported from constants.py to maintain single source of truth.
"""

from enum import Enum
from .constants import (
    # Agent Types
    AGENT_TYPE_REACT,
    AGENT_TYPE_GOAL_BASED,
    AGENT_TYPE_HIERARCHICAL,
    AGENT_TYPE_SIMPLE,
    # Agent States
    STATE_IDLE,
    STATE_RUNNING,
    STATE_WAITING,
    STATE_COMPLETED,
    STATE_FAILED,
    STATE_CANCELLED,
    # Checklist Statuses
    CHECKLIST_STATUS_PENDING,
    CHECKLIST_STATUS_IN_PROGRESS,
    CHECKLIST_STATUS_COMPLETED,
    CHECKLIST_STATUS_FAILED,
    CHECKLIST_STATUS_SKIPPED,
    # Input Types
    INPUT_TYPE_TEXT,
    INPUT_TYPE_IMAGE,
    INPUT_TYPE_AUDIO,
    INPUT_TYPE_VIDEO,
    INPUT_TYPE_FILE,
    INPUT_TYPE_STRUCTURED,
    INPUT_TYPE_MULTIMODAL,
    # Output Types
    OUTPUT_TYPE_TEXT,
    OUTPUT_TYPE_IMAGE,
    OUTPUT_TYPE_AUDIO,
    OUTPUT_TYPE_VIDEO,
    OUTPUT_TYPE_FILE,
    OUTPUT_TYPE_STRUCTURED,
    OUTPUT_TYPE_STREAM,
    OUTPUT_TYPE_MULTIMODAL,
    # Output Formats
    OUTPUT_FORMAT_TEXT,
    OUTPUT_FORMAT_JSON,
    OUTPUT_FORMAT_MARKDOWN,
    OUTPUT_FORMAT_HTML,
    OUTPUT_FORMAT_XML,
)


class AgentType(str, Enum):
    """
    Built-in agent type identifiers.
    
    For custom agent types, use AgentFactory.register() instead of modifying this enum.
    Custom types can use any string identifier.
    """
    REACT = AGENT_TYPE_REACT
    GOAL_BASED = AGENT_TYPE_GOAL_BASED
    HIERARCHICAL = AGENT_TYPE_HIERARCHICAL
    SIMPLE = AGENT_TYPE_SIMPLE


class AgentState(str, Enum):
    """Agent execution states."""
    IDLE = STATE_IDLE
    RUNNING = STATE_RUNNING
    WAITING = STATE_WAITING
    COMPLETED = STATE_COMPLETED
    FAILED = STATE_FAILED
    CANCELLED = STATE_CANCELLED


class ChecklistStatus(str, Enum):
    """Checklist item statuses."""
    PENDING = CHECKLIST_STATUS_PENDING
    IN_PROGRESS = CHECKLIST_STATUS_IN_PROGRESS
    COMPLETED = CHECKLIST_STATUS_COMPLETED
    FAILED = CHECKLIST_STATUS_FAILED
    SKIPPED = CHECKLIST_STATUS_SKIPPED


class AgentInputType(str, Enum):
    """
    Supported input types for agents.
    
    Defines what types of input an agent can accept and process.
    MULTIMODAL indicates the agent can handle multiple types in a single request.
    """
    TEXT = INPUT_TYPE_TEXT
    IMAGE = INPUT_TYPE_IMAGE
    AUDIO = INPUT_TYPE_AUDIO
    VIDEO = INPUT_TYPE_VIDEO
    FILE = INPUT_TYPE_FILE
    STRUCTURED = INPUT_TYPE_STRUCTURED
    MULTIMODAL = INPUT_TYPE_MULTIMODAL


class AgentOutputType(str, Enum):
    """
    Supported output types for agents.
    
    Defines what types of output an agent can produce.
    MULTIMODAL indicates the agent can produce multiple types in a single response.
    """
    TEXT = OUTPUT_TYPE_TEXT
    IMAGE = OUTPUT_TYPE_IMAGE
    AUDIO = OUTPUT_TYPE_AUDIO
    VIDEO = OUTPUT_TYPE_VIDEO
    FILE = OUTPUT_TYPE_FILE
    STRUCTURED = OUTPUT_TYPE_STRUCTURED
    STREAM = OUTPUT_TYPE_STREAM
    MULTIMODAL = OUTPUT_TYPE_MULTIMODAL


class AgentOutputFormat(str, Enum):
    """
    Output format types for structured outputs.
    
    Defines how text/structured content should be formatted.
    """
    TEXT = OUTPUT_FORMAT_TEXT
    JSON = OUTPUT_FORMAT_JSON
    MARKDOWN = OUTPUT_FORMAT_MARKDOWN
    HTML = OUTPUT_FORMAT_HTML
    XML = OUTPUT_FORMAT_XML


# Helper functions
def get_all_agent_types() -> list[str]:
    """Get list of all agent type identifiers."""
    return [t.value for t in AgentType]


def get_all_agent_states() -> list[str]:
    """Get list of all agent state identifiers."""
    return [s.value for s in AgentState]


def get_all_checklist_statuses() -> list[str]:
    """Get list of all checklist status identifiers."""
    return [s.value for s in ChecklistStatus]


def get_all_input_types() -> list[str]:
    """Get list of all agent input types."""
    return [t.value for t in AgentInputType]


def get_all_output_types() -> list[str]:
    """Get list of all agent output types."""
    return [t.value for t in AgentOutputType]


def get_all_output_formats() -> list[str]:
    """Get list of all agent output formats."""
    return [f.value for f in AgentOutputFormat]

