"""
Enumerations for LLM Subsystem.

This module defines all enumerations used throughout the LLM subsystem including
providers, model families, media types, roles, and capabilities.

All enum values are imported from constants.py to maintain single source of truth.
"""

from enum import Enum
from .constants import (
    # Providers
    PROVIDER_AZURE,
    PROVIDER_OPENAI,
    # Model Families
    MODEL_FAMILY_GPT_4,
    MODEL_FAMILY_GPT_4_1_MINI,
    MODEL_FAMILY_AZURE_GPT_4,
    MODEL_FAMILY_AZURE_GPT_4_1_MINI,
    # Media Types
    MEDIA_TYPE_TEXT,
    MEDIA_TYPE_IMAGE,
    MEDIA_TYPE_AUDIO,
    MEDIA_TYPE_VIDEO,
    MEDIA_TYPE_MULTIMODAL,
    # Output Format Types (for TEXT media)
    OUTPUT_FORMAT_TEXT,
    OUTPUT_FORMAT_JSON,
    OUTPUT_FORMAT_TOON,
    # Roles
    ROLE_SYSTEM,
    ROLE_USER,
    ROLE_ASSISTANT,
    ROLE_FUNCTION,
    ROLE_TOOL,
    # Capabilities
    CAPABILITY_STREAMING,
    CAPABILITY_FUNCTION_CALLING,
    CAPABILITY_VISION,
    CAPABILITY_JSON_MODE,
    CAPABILITY_TOOL_USE,
    CAPABILITY_MULTI_TURN,
    CAPABILITY_CONTEXT_CACHING,
    CAPABILITY_PARALLEL_FUNCTION_CALLING,
    # LLM Types
    LLM_TYPE_CHAT,
    LLM_TYPE_COMPLETION,
    LLM_TYPE_INSTRUCTION,
    LLM_TYPE_EMBEDDING,
    LLM_TYPE_CODE,
    # Stream Events
    STREAM_EVENT_START,
    STREAM_EVENT_CONTENT,
    STREAM_EVENT_FUNCTION_CALL,
    STREAM_EVENT_TOOL_USE,
    STREAM_EVENT_END,
    STREAM_EVENT_ERROR,
    STREAM_EVENT_METADATA,
    # Finish Reasons
    FINISH_REASON_STOP,
    FINISH_REASON_LENGTH,
    FINISH_REASON_CONTENT_FILTER,
    FINISH_REASON_FUNCTION_CALL,
    FINISH_REASON_ERROR,
    FINISH_REASON_TIMEOUT,
    # Model Display Names
    DISPLAY_NAME_GPT_4,
    DISPLAY_NAME_GPT_4_1_MINI,
    DISPLAY_NAME_AZURE_GPT_4,
    DISPLAY_NAME_AZURE_GPT_4_1_MINI,
)


class LLMProvider(str, Enum):
    """LLM Provider identifiers."""
    AZURE = PROVIDER_AZURE
    OPENAI = PROVIDER_OPENAI


class ModelFamily(str, Enum):
    """Model family groupings."""
    GPT_4 = MODEL_FAMILY_GPT_4
    GPT_4_1_MINI = MODEL_FAMILY_GPT_4_1_MINI
    AZURE_GPT_4 = MODEL_FAMILY_AZURE_GPT_4
    AZURE_GPT_4_1_MINI = MODEL_FAMILY_AZURE_GPT_4_1_MINI


class ModelDisplayName(str, Enum):
    """Model display names."""
    GPT_4 = DISPLAY_NAME_GPT_4
    GPT_4_1_MINI = DISPLAY_NAME_GPT_4_1_MINI
    AZURE_GPT_4 = DISPLAY_NAME_AZURE_GPT_4
    AZURE_GPT_4_1_MINI = DISPLAY_NAME_AZURE_GPT_4_1_MINI


class InputMediaType(str, Enum):
    """
    Supported input media types.
    
    Note: MULTIMODAL indicates the model can handle multiple types in a single
    request. The exact combination is specified in ModelMetadata.supported_input_types.
    """
    TEXT = MEDIA_TYPE_TEXT
    IMAGE = MEDIA_TYPE_IMAGE
    AUDIO = MEDIA_TYPE_AUDIO
    VIDEO = MEDIA_TYPE_VIDEO
    MULTIMODAL = MEDIA_TYPE_MULTIMODAL


class OutputMediaType(str, Enum):
    """Supported output media types."""
    TEXT = MEDIA_TYPE_TEXT
    AUDIO = MEDIA_TYPE_AUDIO
    IMAGE = MEDIA_TYPE_IMAGE
    VIDEO = MEDIA_TYPE_VIDEO
    MULTIMODAL = MEDIA_TYPE_MULTIMODAL


class OutputFormatType(str, Enum):
    """
    Output format types for TEXT media.
    
    This enum defines how text content should be formatted:
    - TEXT: Plain text output
    - JSON: Structured JSON output (with optional schema validation)
    - TOON: Toon/cartoon format output
    """
    TEXT = OUTPUT_FORMAT_TEXT
    JSON = OUTPUT_FORMAT_JSON
    TOON = OUTPUT_FORMAT_TOON


class MessageRole(str, Enum):
    """Message role identifiers for conversation context."""
    SYSTEM = ROLE_SYSTEM
    USER = ROLE_USER
    ASSISTANT = ROLE_ASSISTANT
    FUNCTION = ROLE_FUNCTION
    TOOL = ROLE_TOOL


class LLMCapability(str, Enum):
    """LLM capability flags."""
    STREAMING = CAPABILITY_STREAMING
    FUNCTION_CALLING = CAPABILITY_FUNCTION_CALLING
    VISION = CAPABILITY_VISION
    JSON_MODE = CAPABILITY_JSON_MODE
    TOOL_USE = CAPABILITY_TOOL_USE
    MULTI_TURN = CAPABILITY_MULTI_TURN
    PARALLEL_FUNCTION_CALLING = CAPABILITY_PARALLEL_FUNCTION_CALLING
    CONTEXT_CACHING = CAPABILITY_CONTEXT_CACHING


class LLMType(str, Enum):
    """LLM type classification."""
    CHAT = LLM_TYPE_CHAT
    COMPLETION = LLM_TYPE_COMPLETION
    INSTRUCTION = LLM_TYPE_INSTRUCTION
    EMBEDDING = LLM_TYPE_EMBEDDING
    CODE = LLM_TYPE_CODE


class StreamEventType(str, Enum):
    """Stream event types for streaming responses."""
    START = STREAM_EVENT_START
    CONTENT = STREAM_EVENT_CONTENT
    FUNCTION_CALL = STREAM_EVENT_FUNCTION_CALL
    TOOL_USE = STREAM_EVENT_TOOL_USE
    END = STREAM_EVENT_END
    ERROR = STREAM_EVENT_ERROR
    METADATA = STREAM_EVENT_METADATA


class FinishReason(str, Enum):
    """Reasons why LLM generation stopped."""
    STOP = FINISH_REASON_STOP
    LENGTH = FINISH_REASON_LENGTH
    CONTENT_FILTER = FINISH_REASON_CONTENT_FILTER
    FUNCTION_CALL = FINISH_REASON_FUNCTION_CALL
    ERROR = FINISH_REASON_ERROR
    TIMEOUT = FINISH_REASON_TIMEOUT


# Helper function to get all values
def get_all_providers() -> list[str]:
    """Get list of all provider identifiers."""
    return [p.value for p in LLMProvider]


def get_all_model_families() -> list[str]:
    """Get list of all model family identifiers."""
    return [f.value for f in ModelFamily]


def get_all_input_types() -> list[str]:
    """Get list of all input media types."""
    return [t.value for t in InputMediaType]


def get_all_output_types() -> list[str]:
    """Get list of all output media types."""
    return [t.value for t in OutputMediaType]


def get_all_output_formats() -> list[str]:
    """Get list of all output format types for TEXT media."""
    return [f.value for f in OutputFormatType]

