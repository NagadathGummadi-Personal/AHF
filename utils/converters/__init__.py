"""
Converters for LLM output transformations.

This module provides utilities for converting between different output formats:
- JSON schema generation from Pydantic models
- Response parsing and validation (complete and partial)
- Streaming JSON parsing
- JSON to TOON conversion (text-oriented object notation)
"""

from .json_schema_converter import (
    pydantic_to_openai_schema,
    json_object_schema,
    validate_json_response,
    validate_json_dict,
    parse_structured_response,
    parse_streaming_json,
    is_valid_json,
    extract_json_from_text,
    get_partial_json_fields,
)
from .partial_json_parser import (
    parse_partial_json,
    parse_json_markdown,
    is_complete_json,
    get_partial_json_progress,
    get_partial_json_dict,
)

__all__ = [
    # Schema conversion
    "pydantic_to_openai_schema",
    "json_object_schema",
    # Complete JSON parsing
    "validate_json_response",
    "validate_json_dict",
    "parse_structured_response",
    "extract_json_from_text",
    # Streaming/partial JSON parsing
    "parse_streaming_json",
    "parse_partial_json",
    "parse_json_markdown",
    "is_valid_json",
    "is_complete_json",
    "get_partial_json_progress",
    "get_partial_json_fields",
    "get_partial_json_dict",
]

