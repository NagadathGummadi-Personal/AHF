"""
Workflow Configuration Models

Additional configuration models for workflow components.

Version: 1.0.0
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field

from ..defaults import DEFAULT_VARIABLE_ASSIGNMENT_ENABLED, DEFAULT_ON_ERROR_BEHAVIOR


class NodeVariableAssignment(BaseModel):
    """
    Configuration for assigning node output values to workflow variables.
    
    Similar to tool variable assignments but for workflow nodes.
    
    Attributes:
        target_variable: Name of the workflow variable to update
        source_field: Dot-notation path to the value in node output (e.g., "result.data.id")
        operator: Assignment operator (set, set_if_exists, set_if_truthy, append, increment, transform)
        default_value: Value to use if source field doesn't exist
        transform_expr: Python expression to transform the value (uses 'value' variable)
        transform_func: Optional callable for complex transformations
    """
    target_variable: str = Field(..., description="Name of the workflow variable to update")
    source_field: str = Field(..., description="Dot-notation path to value in node output")
    operator: str = Field(
        default="set",
        description="Assignment operator: set, set_if_exists, set_if_truthy, append, increment, transform"
    )
    default_value: Optional[Any] = Field(
        default=None,
        description="Default value if source field doesn't exist"
    )
    transform_expr: Optional[str] = Field(
        default=None,
        description="Python expression to transform value (e.g., 'str(value).upper()')"
    )
    transform_func: Optional[Callable[[Any], Any]] = Field(
        default=None,
        description="Callable for complex transformations"
    )
    
    model_config = {"arbitrary_types_allowed": True}


class NodeDynamicVariableConfig(BaseModel):
    """
    Configuration for dynamic variable assignments from node results.
    
    Attributes:
        enabled: Whether dynamic variable assignment is enabled
        assignments: List of variable assignment configurations
        on_error: Behavior on assignment error (log, raise, ignore)
    """
    enabled: bool = Field(
        default=DEFAULT_VARIABLE_ASSIGNMENT_ENABLED,
        description="Whether dynamic variable assignment is enabled"
    )
    assignments: List[NodeVariableAssignment] = Field(
        default_factory=list,
        description="List of variable assignment configurations"
    )
    on_error: str = Field(
        default=DEFAULT_ON_ERROR_BEHAVIOR,
        description="Behavior on assignment error: log, raise, or ignore"
    )
