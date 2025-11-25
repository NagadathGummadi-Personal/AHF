"""
Specifications for LLM Subsystem.

This module exports all specification types including metadata,
results, and context objects.
"""

from .llm_schema import ModelMetadata, create_model_metadata
from .llm_result import (
    LLMResponse,
    LLMStreamChunk,
    LLMUsage,
    LLMError,
    LLMImageResponse,
    LLMImageChunk,
    LLMAudioResponse,
    LLMAudioChunk,
    LLMVideoResponse,
    LLMVideoChunk,
    create_response,
    create_chunk,
)
from .llm_context import (
    LLMContext,
    create_context,
)
from .llm_output_config import (
    OutputConfig,
    OutputFormat,
    ResponseMode,
    ParseResult,
)

__all__ = [
    # Types
    "ModelMetadata",
    "create_model_metadata",
    # Results - Text
    "LLMResponse",
    "LLMStreamChunk",
    "LLMUsage",
    "LLMError",
    # Results - Media
    "LLMImageResponse",
    "LLMImageChunk",
    "LLMAudioResponse",
    "LLMAudioChunk",
    "LLMVideoResponse",
    "LLMVideoChunk",
    # Helpers
    "create_response",
    "create_chunk",
    # Context
    "LLMContext",
    "create_context",
    # Output Configuration
    "OutputConfig",
    "OutputFormat",
    "ResponseMode",
    "ParseResult",
]

