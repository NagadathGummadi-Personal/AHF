"""
LLM Output Configuration.

This module defines the output configuration for LLM responses,
including response format, retry behavior, and parsing modes.
"""

from enum import Enum
from typing import Any, Dict, Optional, Type, Union
from pydantic import BaseModel, Field


class ResponseMode(str, Enum):
    """Response handling mode for structured outputs."""
    
    # Wait for complete, validated response; fail if can't parse after retries
    STRICT = "strict"
    
    # Return text content immediately if parsing fails (no retries)
    IMMEDIATE = "immediate"
    
    # Try to parse, return None for structured_output if fails (no retries)
    BEST_EFFORT = "best_effort"


class OutputFormat(str, Enum):
    """Output format types."""
    
    TEXT = "text"  # Plain text output
    JSON = "json"  # Raw JSON dict output
    PYDANTIC = "pydantic"  # Pydantic model validated output


class OutputConfig(BaseModel):
    """
    Configuration for LLM output handling.
    
    Controls how the LLM response should be formatted, parsed, and validated.
    Supports retry logic for structured outputs.
    
    Attributes:
        response_format: The expected response format
            - None: Plain text output
            - Dict: Raw JSON schema (OpenAI format)
            - Type[BaseModel]: Pydantic model for validation
        max_retries: Maximum retries if structured output parsing fails
        response_mode: How to handle parsing failures
        strict_schema: Whether to enforce strict schema validation
        
    Example:
        # Simple text output
        config = OutputConfig()
        
        # JSON output with retries
        config = OutputConfig(
            response_format={"type": "json_object"},
            max_retries=2
        )
        
        # Pydantic model with strict validation
        config = OutputConfig(
            response_format=MovieRecommendation,
            max_retries=3,
            response_mode=ResponseMode.STRICT
        )
        
        # Best effort - return what we can
        config = OutputConfig(
            response_format=MovieRecommendation,
            response_mode=ResponseMode.BEST_EFFORT
        )
    """
    
    response_format: Optional[Union[Dict[str, Any], Type[BaseModel]]] = Field(
        default=None,
        description="Response format: None for text, dict for JSON schema, or Pydantic model class"
    )
    
    max_retries: int = Field(
        default=0,
        ge=0,
        le=5,
        description="Max retries if structured output parsing fails (0 = no retries)"
    )
    
    response_mode: ResponseMode = Field(
        default=ResponseMode.BEST_EFFORT,
        description="How to handle parsing failures"
    )
    
    strict_schema: bool = Field(
        default=True,
        description="Whether to enforce strict schema validation"
    )
    
    model_config = {"arbitrary_types_allowed": True}
    
    @property
    def output_format_type(self) -> OutputFormat:
        """Get the output format type."""
        if self.response_format is None:
            return OutputFormat.TEXT
        elif isinstance(self.response_format, dict):
            return OutputFormat.JSON
        elif isinstance(self.response_format, type) and issubclass(self.response_format, BaseModel):
            return OutputFormat.PYDANTIC
        return OutputFormat.TEXT
    
    @property
    def expects_structured_output(self) -> bool:
        """Check if structured output is expected."""
        return self.response_format is not None
    
    @property
    def should_retry_on_parse_failure(self) -> bool:
        """Check if should retry on parse failure."""
        return (
            self.max_retries > 0 and 
            self.response_mode == ResponseMode.STRICT and
            self.expects_structured_output
        )
    
    @property
    def should_fail_on_parse_error(self) -> bool:
        """Check if should raise error on parse failure."""
        return self.response_mode == ResponseMode.STRICT
    
    def get_schema_name(self) -> Optional[str]:
        """Get the schema name for Pydantic models."""
        if self.output_format_type == OutputFormat.PYDANTIC:
            return self.response_format.__name__
        elif self.output_format_type == OutputFormat.JSON:
            # Try to extract from OpenAI format
            if "json_schema" in self.response_format:
                return self.response_format["json_schema"].get("name", "json_schema")
        return None


class ParseResult(BaseModel):
    """
    Result of parsing a structured response.
    
    Contains both the parsed result and metadata about the parsing process.
    
    Attributes:
        success: Whether parsing succeeded
        parsed_output: The parsed and validated output (Pydantic model or dict)
        raw_content: Original response content
        error: Error message if parsing failed
        attempts: Number of parsing attempts made
    """
    
    success: bool = Field(description="Whether parsing succeeded")
    parsed_output: Optional[Any] = Field(default=None, description="Parsed output")
    raw_content: str = Field(default="", description="Original response content")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    attempts: int = Field(default=1, ge=1, description="Number of attempts made")
    
    model_config = {"arbitrary_types_allowed": True}

