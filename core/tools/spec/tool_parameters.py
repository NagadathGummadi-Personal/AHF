from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# Local imports
from ..enum import ParameterType

class ToolParameter(BaseModel):
    """Base class for tool parameters with common fields"""
    name: str
    description: str
    required: bool = False
    default: Any | None = None
    deprecated: bool = False
    examples: List[Any] = Field(default_factory=list)


class StringParameter(ToolParameter):
    """Parameter for string values with string-specific constraints"""
    param_type: ParameterType = Field(default=ParameterType.STRING)
    enum: List[str] | None = None
    format: Optional[str] = None  # e.g., "email", "uri", "date-time"
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None  # regex for string
    coerce: bool = False  # optional coercion (string->number, etc.)


class NumericParameter(ToolParameter):
    """Parameter for numeric values (number/integer) with numeric constraints"""
    param_type: ParameterType = Field(default=ParameterType.NUMBER)
    min: Optional[float] = None
    max: Optional[float] = None


class IntegerParameter(NumericParameter):
    """Parameter for integer values"""
    param_type: ParameterType = Field(default=ParameterType.INTEGER)


class BooleanParameter(ToolParameter):
    """Parameter for boolean values"""
    param_type: ParameterType = Field(default=ParameterType.BOOLEAN)


class ArrayParameter(ToolParameter):
    """Parameter for array values with array-specific constraints"""
    param_type: ParameterType = Field(default=ParameterType.ARRAY)
    items: Optional[ToolParameter] = None
    min_items: Optional[int] = None
    max_items: Optional[int] = None
    unique_items: bool = False


class ObjectParameter(ToolParameter):
    """Parameter for object values with object-specific constraints"""
    param_type: ParameterType = Field(default=ParameterType.OBJECT)
    properties: Optional[Dict[str, ToolParameter]] = None
    oneOf: Optional[List[ToolParameter]] = None
