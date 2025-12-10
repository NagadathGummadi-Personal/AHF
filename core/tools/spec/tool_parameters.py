"""
Tool Parameter Models with UI Metadata.

This module defines parameter models for tool inputs including
typed parameters (string, number, boolean, array, object).

Each field includes UI metadata for automatic Flutter form generation.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from ..enum import ParameterType
from .ui_metadata import UIPresets, WidgetType, ui


class ToolParameter(BaseModel):
    """
    Base class for tool parameters with common fields.
    
    All tool parameters share these common attributes for metadata
    and documentation purposes.
    """
    name: str = Field(
        json_schema_extra={"ui": UIPresets.text_input(
            display_name="Parameter Name",
            placeholder="user_id",
            help_text="Unique name for this parameter (snake_case recommended)",
            group="basic",
            order=0,
        )}
    )
    description: str = Field(
        json_schema_extra={"ui": UIPresets.multiline_text(
            display_name="Description",
            placeholder="Describe what this parameter is for...",
            help_text="Description of the parameter (shown to LLM and users)",
            group="basic",
            order=1,
        )}
    )
    required: bool = Field(
        default=False,
        json_schema_extra={"ui": ui(
            display_name="Required",
            widget_type=WidgetType.SWITCH,
            help_text="Whether this parameter must be provided",
            group="basic",
            order=2,
        )}
    )
    default: Any | None = Field(
        default=None,
        json_schema_extra={"ui": UIPresets.text_input(
            display_name="Default Value",
            placeholder="null",
            help_text="Default value if parameter is not provided",
            group="basic",
            order=3,
        )}
    )
    deprecated: bool = Field(
        default=False,
        json_schema_extra={"ui": ui(
            display_name="Deprecated",
            widget_type=WidgetType.SWITCH,
            help_text="Mark this parameter as deprecated",
            group="advanced",
            order=10,
        )}
    )
    examples: List[Any] = Field(
        default_factory=list,
        json_schema_extra={"ui": UIPresets.string_list(
            display_name="Examples",
            item_label="Example {index}",
            help_text="Example values for this parameter",
            group="advanced",
            order=11,
        )}
    )


class StringParameter(ToolParameter):
    """
    Parameter for string values with string-specific constraints.
    
    Supports enum values, format validation, length constraints, and patterns.
    """
    param_type: ParameterType = Field(
        default=ParameterType.STRING,
        json_schema_extra={"ui": ui(
            display_name="Type",
            widget_type=WidgetType.HIDDEN,
        )}
    )
    enum: List[str] | None = Field(
        default=None,
        json_schema_extra={"ui": UIPresets.string_list(
            display_name="Allowed Values (Enum)",
            item_label="Value {index}",
            help_text="If set, parameter must be one of these values",
            group="constraints",
            order=4,
        )}
    )
    format: Optional[str] = Field(
        default=None,
        json_schema_extra={"ui": UIPresets.enum_dropdown(
            display_name="Format",
            options=[
                {"value": "", "label": "None"},
                {"value": "email", "label": "Email"},
                {"value": "uri", "label": "URI/URL"},
                {"value": "date", "label": "Date (YYYY-MM-DD)"},
                {"value": "date-time", "label": "DateTime (ISO 8601)"},
                {"value": "time", "label": "Time (HH:MM:SS)"},
                {"value": "uuid", "label": "UUID"},
                {"value": "hostname", "label": "Hostname"},
                {"value": "ipv4", "label": "IPv4 Address"},
                {"value": "ipv6", "label": "IPv6 Address"},
            ],
            help_text="Expected format for validation",
            group="constraints",
            order=5,
        )}
    )
    min_length: Optional[int] = Field(
        default=None,
        ge=0,
        json_schema_extra={"ui": ui(
            display_name="Min Length",
            widget_type=WidgetType.NUMBER,
            min_value=0,
            max_value=10000,
            help_text="Minimum string length",
            group="constraints",
            order=6,
        )}
    )
    max_length: Optional[int] = Field(
        default=None,
        ge=1,
        json_schema_extra={"ui": ui(
            display_name="Max Length",
            widget_type=WidgetType.NUMBER,
            min_value=1,
            max_value=100000,
            help_text="Maximum string length",
            group="constraints",
            order=7,
        )}
    )
    pattern: Optional[str] = Field(
        default=None,
        json_schema_extra={"ui": UIPresets.text_input(
            display_name="Pattern (Regex)",
            placeholder="^[a-z]+$",
            help_text="Regular expression pattern for validation",
            group="constraints",
            order=8,
        )}
    )
    coerce: bool = Field(
        default=False,
        json_schema_extra={"ui": ui(
            display_name="Coerce to String",
            widget_type=WidgetType.SWITCH,
            help_text="Automatically convert other types to string",
            group="advanced",
            order=12,
        )}
    )


class NumericParameter(ToolParameter):
    """
    Parameter for numeric values (number/integer) with numeric constraints.
    
    Supports min/max value validation.
    """
    param_type: ParameterType = Field(
        default=ParameterType.NUMBER,
        json_schema_extra={"ui": ui(
            display_name="Type",
            widget_type=WidgetType.HIDDEN,
        )}
    )
    min: Optional[float] = Field(
        default=None,
        json_schema_extra={"ui": ui(
            display_name="Minimum Value",
            widget_type=WidgetType.NUMBER,
            help_text="Minimum allowed value (inclusive)",
            group="constraints",
            order=4,
        )}
    )
    max: Optional[float] = Field(
        default=None,
        json_schema_extra={"ui": ui(
            display_name="Maximum Value",
            widget_type=WidgetType.NUMBER,
            help_text="Maximum allowed value (inclusive)",
            group="constraints",
            order=5,
        )}
    )


class IntegerParameter(NumericParameter):
    """
    Parameter for integer values.
    
    Inherits min/max from NumericParameter, uses INTEGER type.
    """
    param_type: ParameterType = Field(
        default=ParameterType.INTEGER,
        json_schema_extra={"ui": ui(
            display_name="Type",
            widget_type=WidgetType.HIDDEN,
        )}
    )


class BooleanParameter(ToolParameter):
    """
    Parameter for boolean values.
    
    Simple true/false parameter with no additional constraints.
    """
    param_type: ParameterType = Field(
        default=ParameterType.BOOLEAN,
        json_schema_extra={"ui": ui(
            display_name="Type",
            widget_type=WidgetType.HIDDEN,
        )}
    )


class ArrayParameter(ToolParameter):
    """
    Parameter for array values with array-specific constraints.
    
    Supports item type definition and length constraints.
    """
    param_type: ParameterType = Field(
        default=ParameterType.ARRAY,
        json_schema_extra={"ui": ui(
            display_name="Type",
            widget_type=WidgetType.HIDDEN,
        )}
    )
    items: Optional[ToolParameter] = Field(
        default=None,
        json_schema_extra={"ui": ui(
            display_name="Item Type",
            widget_type=WidgetType.OBJECT_EDITOR,
            help_text="Schema for array items",
            group="constraints",
            order=4,
        )}
    )
    min_items: Optional[int] = Field(
        default=None,
        ge=0,
        json_schema_extra={"ui": ui(
            display_name="Min Items",
            widget_type=WidgetType.NUMBER,
            min_value=0,
            max_value=1000,
            help_text="Minimum number of items",
            group="constraints",
            order=5,
        )}
    )
    max_items: Optional[int] = Field(
        default=None,
        ge=1,
        json_schema_extra={"ui": ui(
            display_name="Max Items",
            widget_type=WidgetType.NUMBER,
            min_value=1,
            max_value=10000,
            help_text="Maximum number of items",
            group="constraints",
            order=6,
        )}
    )
    unique_items: bool = Field(
        default=False,
        json_schema_extra={"ui": ui(
            display_name="Unique Items",
            widget_type=WidgetType.SWITCH,
            help_text="Whether items must be unique",
            group="constraints",
            order=7,
        )}
    )


class ObjectParameter(ToolParameter):
    """
    Parameter for object values with object-specific constraints.
    
    Supports nested property definitions and oneOf schemas.
    """
    param_type: ParameterType = Field(
        default=ParameterType.OBJECT,
        json_schema_extra={"ui": ui(
            display_name="Type",
            widget_type=WidgetType.HIDDEN,
        )}
    )
    properties: Optional[Dict[str, ToolParameter]] = Field(
        default=None,
        json_schema_extra={"ui": ui(
            display_name="Properties",
            widget_type=WidgetType.OBJECT_EDITOR,
            help_text="Nested property definitions",
            group="constraints",
            order=4,
        )}
    )
    oneOf: Optional[List[ToolParameter]] = Field(
        default=None,
        json_schema_extra={"ui": ui(
            display_name="One Of (Union Types)",
            widget_type=WidgetType.ARRAY_EDITOR,
            item_label="Option {index}",
            help_text="Value must match one of these schemas",
            group="constraints",
            order=5,
        )}
    )
