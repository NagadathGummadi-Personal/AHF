"""
Input/Output Type Specifications for Workflow Nodes

Defines the types and formats for data flowing between nodes.
When input/output types don't match, a formatter is required.

Version: 1.0.0
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Type

from pydantic import BaseModel, Field

from ..enum import IOType, IOFormat
from ..defaults import (
    DEFAULT_INPUT_TYPE,
    DEFAULT_OUTPUT_TYPE,
    DEFAULT_INPUT_FORMAT,
    DEFAULT_OUTPUT_FORMAT,
)
from ..constants import (
    ARBITRARY_TYPES_ALLOWED,
    ERROR_INPUT_TYPE_MISMATCH,
    ERROR_FORMATTER_NOT_FOUND,
)


class IOTypeSpec(BaseModel):
    """
    Specification for an input or output type.
    
    Attributes:
        io_type: The data type (TEXT, SPEECH, JSON, etc.)
        format: The format specification (PLAIN, MARKDOWN, JSON_SCHEMA, etc.)
        schema: Optional schema definition for structured types
        description: Human-readable description of the data
        examples: Example values for documentation
    """
    io_type: IOType = Field(default=IOType.TEXT, description="Data type")
    format: IOFormat = Field(default=IOFormat.PLAIN, description="Format specification")
    schema: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Schema definition for structured types (JSON Schema, Pydantic model)"
    )
    pydantic_model: Optional[Type[BaseModel]] = Field(
        default=None,
        description="Pydantic model class for validation (optional)"
    )
    description: str = Field(default="", description="Description of the data")
    examples: list = Field(default_factory=list, description="Example values")
    
    model_config = {ARBITRARY_TYPES_ALLOWED: True}
    
    def is_compatible_with(self, other: IOTypeSpec) -> bool:
        """
        Check if this type is compatible with another type.
        
        Returns True if:
        - Types are exactly the same
        - Either type is ANY
        - Both are text-like types (TEXT, MARKDOWN, HTML)
        """
        if self.io_type == other.io_type:
            return True
        if self.io_type == IOType.ANY or other.io_type == IOType.ANY:
            return True
        
        # Text-like types are compatible with each other
        text_types = {IOType.TEXT, IOType.JSON, IOType.STRUCTURED}
        if self.io_type in text_types and other.io_type in text_types:
            return True
        
        return False


class InputSpec(BaseModel):
    """
    Input specification for a node.
    
    Defines what type of input the node accepts and how to handle
    type mismatches from the previous node.
    
    Attributes:
        type_spec: The expected input type specification
        required: Whether input is required for node execution
        accepts_multiple: Whether node can accept multiple inputs (for merge nodes)
        formatter_ref: Reference to a formatter for type conversion (not implemented yet)
    """
    type_spec: IOTypeSpec = Field(
        default_factory=lambda: IOTypeSpec(io_type=IOType(DEFAULT_INPUT_TYPE), format=IOFormat(DEFAULT_INPUT_FORMAT)),
        description="Expected input type"
    )
    required: bool = Field(default=True, description="Whether input is required")
    accepts_multiple: bool = Field(
        default=False,
        description="Whether node accepts multiple inputs (for merge/parallel nodes)"
    )
    
    # Formatter reference - to be implemented
    # For now, if types don't match and no formatter, raise exception
    formatter_ref: Optional[str] = Field(
        default=None,
        description="Reference to formatter for type conversion (future feature)"
    )
    
    def validate_input(self, source_output: OutputSpec) -> None:
        """
        Validate that the source output is compatible with this input.
        
        Raises:
            ValueError: If types are incompatible and no formatter is available
        """
        if not self.type_spec.is_compatible_with(source_output.type_spec):
            if self.formatter_ref is None:
                raise ValueError(
                    ERROR_INPUT_TYPE_MISMATCH.format(
                        expected=self.type_spec.io_type.value,
                        actual=source_output.type_spec.io_type.value
                    )
                )
            else:
                # Formatter would be used here - not implemented yet
                raise NotImplementedError(
                    ERROR_FORMATTER_NOT_FOUND.format(
                        from_type=source_output.type_spec.io_type.value,
                        to_type=self.type_spec.io_type.value
                    )
                )


class OutputSpec(BaseModel):
    """
    Output specification for a node.
    
    Defines what type of output the node produces.
    
    Attributes:
        type_spec: The output type specification
        optional: Whether the output might be empty/null
        streaming: Whether output is streamed
    """
    type_spec: IOTypeSpec = Field(
        default_factory=lambda: IOTypeSpec(io_type=IOType(DEFAULT_OUTPUT_TYPE), format=IOFormat(DEFAULT_OUTPUT_FORMAT)),
        description="Output type"
    )
    optional: bool = Field(default=False, description="Whether output might be empty")
    streaming: bool = Field(default=False, description="Whether output is streamed")
