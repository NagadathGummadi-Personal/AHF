"""
UI Metadata for Schema-Driven Form Generation.

This module defines UI configuration classes that enhance Pydantic models
with metadata for automatic Flutter form generation.

UI metadata is embedded in Pydantic fields via json_schema_extra={"ui": {...}}
and is exported to JSON Schema for consumption by the Dart code generator.
"""

from typing import Any, Dict, List, Optional, Union
from enum import Enum


class WidgetType(str, Enum):
    """Widget types for form field rendering."""
    TEXT = "text"
    TEXTAREA = "textarea"
    NUMBER = "number"
    INTEGER = "integer"
    SLIDER = "slider"
    CHECKBOX = "checkbox"
    SWITCH = "switch"
    DROPDOWN = "dropdown"
    RADIO = "radio"
    CODE_EDITOR = "code_editor"
    ARRAY_EDITOR = "array_editor"
    OBJECT_EDITOR = "object_editor"
    KEY_VALUE_EDITOR = "key_value_editor"
    DATE_PICKER = "date_picker"
    TIME_PICKER = "time_picker"
    DATETIME_PICKER = "datetime_picker"
    COLOR_PICKER = "color_picker"
    FILE_PICKER = "file_picker"
    HIDDEN = "hidden"


class UIFieldConfig:
    """
    UI configuration for a Pydantic field.
    
    This class defines how a field should be rendered in the Flutter UI.
    Use the to_dict() method to get the configuration for json_schema_extra.
    
    Attributes:
        display_name: Human-readable label for the field
        widget_type: Type of widget to render (text, dropdown, slider, etc.)
        visible: Whether the field is visible (default True)
        visible_when: Condition expression for conditional visibility
                      e.g., "enabled == true", "mode == 'auto'"
        group: Group name for organizing fields into sections
        order: Display order within group (lower = first)
        help_text: Tooltip/helper text for the field
        placeholder: Placeholder text for input fields
        
        # Numeric field constraints
        min_value: Minimum value for numeric fields
        max_value: Maximum value for numeric fields
        step: Step increment for sliders/number inputs
        
        # Selection fields
        options: List of options for dropdown/radio (list of dicts with 'value' and 'label')
        
        # Array fields
        item_label: Label format for array items (e.g., "Item {index}")
        min_items: Minimum number of items
        max_items: Maximum number of items
        
        # Code editor
        language: Programming language for syntax highlighting
        
        # Role-based access (future-ready)
        required_roles: List of roles that can see/edit this field
                        Empty list = visible to everyone
        editable_roles: List of roles that can edit this field
                        Empty list = editable by everyone
        
        # Validation
        validation_message: Custom validation error message
        
    Example:
        class RetryConfig(BaseModel):
            enabled: bool = Field(
                default=False,
                json_schema_extra={
                    "ui": UIFieldConfig(
                        display_name="Enable Retries",
                        widget_type=WidgetType.SWITCH,
                        help_text="Automatically retry on transient failures",
                        group="retry",
                        order=0,
                    ).to_dict()
                }
            )
            max_attempts: int = Field(
                default=3,
                json_schema_extra={
                    "ui": UIFieldConfig(
                        display_name="Max Retry Attempts",
                        widget_type=WidgetType.SLIDER,
                        visible_when="enabled == true",
                        min_value=1,
                        max_value=10,
                        step=1,
                        group="retry",
                        order=1,
                    ).to_dict()
                }
            )
    """
    
    def __init__(
        self,
        display_name: str = "",
        widget_type: Union[WidgetType, str] = WidgetType.TEXT,
        visible: bool = True,
        visible_when: Optional[str] = None,
        group: Optional[str] = None,
        order: int = 0,
        help_text: Optional[str] = None,
        placeholder: Optional[str] = None,
        # Numeric
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        step: Optional[float] = None,
        # Selection
        options: Optional[List[Dict[str, Any]]] = None,
        # Array
        item_label: Optional[str] = None,
        min_items: Optional[int] = None,
        max_items: Optional[int] = None,
        # Code editor
        language: Optional[str] = None,
        # Role-based access (future-ready)
        required_roles: Optional[List[str]] = None,
        editable_roles: Optional[List[str]] = None,
        # Validation
        validation_message: Optional[str] = None,
        # Additional properties
        **extra: Any,
    ):
        self.display_name = display_name
        self.widget_type = widget_type.value if isinstance(widget_type, WidgetType) else widget_type
        self.visible = visible
        self.visible_when = visible_when
        self.group = group
        self.order = order
        self.help_text = help_text
        self.placeholder = placeholder
        self.min_value = min_value
        self.max_value = max_value
        self.step = step
        self.options = options
        self.item_label = item_label
        self.min_items = min_items
        self.max_items = max_items
        self.language = language
        self.required_roles = required_roles or []
        self.editable_roles = editable_roles or []
        self.validation_message = validation_message
        self.extra = extra
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for json_schema_extra."""
        result = {}
        
        # Always include these
        if self.display_name:
            result["display_name"] = self.display_name
        result["widget_type"] = self.widget_type
        
        # Only include non-default values
        if not self.visible:
            result["visible"] = self.visible
        if self.visible_when:
            result["visible_when"] = self.visible_when
        if self.group:
            result["group"] = self.group
        if self.order != 0:
            result["order"] = self.order
        if self.help_text:
            result["help_text"] = self.help_text
        if self.placeholder:
            result["placeholder"] = self.placeholder
        if self.min_value is not None:
            result["min_value"] = self.min_value
        if self.max_value is not None:
            result["max_value"] = self.max_value
        if self.step is not None:
            result["step"] = self.step
        if self.options:
            result["options"] = self.options
        if self.item_label:
            result["item_label"] = self.item_label
        if self.min_items is not None:
            result["min_items"] = self.min_items
        if self.max_items is not None:
            result["max_items"] = self.max_items
        if self.language:
            result["language"] = self.language
        if self.required_roles:
            result["required_roles"] = self.required_roles
        if self.editable_roles:
            result["editable_roles"] = self.editable_roles
        if self.validation_message:
            result["validation_message"] = self.validation_message
        
        # Include any extra properties
        result.update(self.extra)
        
        return result


def ui(
    display_name: str = "",
    widget_type: Union[WidgetType, str] = WidgetType.TEXT,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Shorthand function to create UI metadata dict.
    
    Example:
        class MyModel(BaseModel):
            name: str = Field(
                json_schema_extra={"ui": ui("Display Name", WidgetType.TEXT)}
            )
    """
    return UIFieldConfig(display_name=display_name, widget_type=widget_type, **kwargs).to_dict()


# Pre-configured UI configs for common patterns
class UIPresets:
    """Pre-configured UI metadata for common field patterns."""
    
    @staticmethod
    def enabled_switch(
        display_name: str = "Enabled",
        help_text: Optional[str] = None,
        group: Optional[str] = None,
        order: int = 0,
    ) -> Dict[str, Any]:
        """Switch for enabling/disabling a feature."""
        return UIFieldConfig(
            display_name=display_name,
            widget_type=WidgetType.SWITCH,
            help_text=help_text,
            group=group,
            order=order,
        ).to_dict()
    
    @staticmethod
    def count_slider(
        display_name: str,
        min_value: int = 1,
        max_value: int = 10,
        visible_when: Optional[str] = None,
        help_text: Optional[str] = None,
        group: Optional[str] = None,
        order: int = 0,
    ) -> Dict[str, Any]:
        """Slider for count/quantity fields."""
        return UIFieldConfig(
            display_name=display_name,
            widget_type=WidgetType.SLIDER,
            min_value=min_value,
            max_value=max_value,
            step=1,
            visible_when=visible_when,
            help_text=help_text,
            group=group,
            order=order,
        ).to_dict()
    
    @staticmethod
    def duration_seconds(
        display_name: str,
        min_value: float = 0.1,
        max_value: float = 300,
        visible_when: Optional[str] = None,
        help_text: Optional[str] = None,
        group: Optional[str] = None,
        order: int = 0,
    ) -> Dict[str, Any]:
        """Number input for duration in seconds."""
        return UIFieldConfig(
            display_name=display_name,
            widget_type=WidgetType.NUMBER,
            min_value=min_value,
            max_value=max_value,
            step=0.1,
            visible_when=visible_when,
            help_text=help_text,
            placeholder="seconds",
            group=group,
            order=order,
        ).to_dict()
    
    @staticmethod
    def enum_dropdown(
        display_name: str,
        options: List[Dict[str, str]],
        visible_when: Optional[str] = None,
        help_text: Optional[str] = None,
        group: Optional[str] = None,
        order: int = 0,
    ) -> Dict[str, Any]:
        """Dropdown for enum selection."""
        return UIFieldConfig(
            display_name=display_name,
            widget_type=WidgetType.DROPDOWN,
            options=options,
            visible_when=visible_when,
            help_text=help_text,
            group=group,
            order=order,
        ).to_dict()
    
    @staticmethod
    def text_input(
        display_name: str,
        placeholder: Optional[str] = None,
        visible_when: Optional[str] = None,
        help_text: Optional[str] = None,
        group: Optional[str] = None,
        order: int = 0,
    ) -> Dict[str, Any]:
        """Standard text input."""
        return UIFieldConfig(
            display_name=display_name,
            widget_type=WidgetType.TEXT,
            placeholder=placeholder,
            visible_when=visible_when,
            help_text=help_text,
            group=group,
            order=order,
        ).to_dict()
    
    @staticmethod
    def multiline_text(
        display_name: str,
        placeholder: Optional[str] = None,
        visible_when: Optional[str] = None,
        help_text: Optional[str] = None,
        group: Optional[str] = None,
        order: int = 0,
    ) -> Dict[str, Any]:
        """Multiline textarea."""
        return UIFieldConfig(
            display_name=display_name,
            widget_type=WidgetType.TEXTAREA,
            placeholder=placeholder,
            visible_when=visible_when,
            help_text=help_text,
            group=group,
            order=order,
        ).to_dict()
    
    @staticmethod
    def code_editor(
        display_name: str,
        language: str = "python",
        visible_when: Optional[str] = None,
        help_text: Optional[str] = None,
        group: Optional[str] = None,
        order: int = 0,
    ) -> Dict[str, Any]:
        """Code editor with syntax highlighting."""
        return UIFieldConfig(
            display_name=display_name,
            widget_type=WidgetType.CODE_EDITOR,
            language=language,
            visible_when=visible_when,
            help_text=help_text,
            group=group,
            order=order,
        ).to_dict()
    
    @staticmethod
    def string_list(
        display_name: str,
        item_label: str = "Item {index}",
        visible_when: Optional[str] = None,
        help_text: Optional[str] = None,
        group: Optional[str] = None,
        order: int = 0,
    ) -> Dict[str, Any]:
        """Array editor for list of strings."""
        return UIFieldConfig(
            display_name=display_name,
            widget_type=WidgetType.ARRAY_EDITOR,
            item_label=item_label,
            visible_when=visible_when,
            help_text=help_text,
            group=group,
            order=order,
        ).to_dict()
    
    @staticmethod
    def key_value_pairs(
        display_name: str,
        visible_when: Optional[str] = None,
        help_text: Optional[str] = None,
        group: Optional[str] = None,
        order: int = 0,
    ) -> Dict[str, Any]:
        """Key-value pair editor."""
        return UIFieldConfig(
            display_name=display_name,
            widget_type=WidgetType.KEY_VALUE_EDITOR,
            visible_when=visible_when,
            help_text=help_text,
            group=group,
            order=order,
        ).to_dict()


