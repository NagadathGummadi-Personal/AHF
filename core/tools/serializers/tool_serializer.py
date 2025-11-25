"""
Tool Serializer - JSON ↔ Tool Object Conversion

This module provides comprehensive serialization and deserialization
functionality for Tool objects, handling all tool types (Function, HTTP, DB)
and their subclasses.

Features:
- Serialize Tool objects to JSON strings or dictionaries
- Deserialize JSON strings or dictionaries to Tool objects
- Automatic detection of tool type and correct class selection
- Proper handling of nested configurations and parameters
- Support for all database tool variants (DynamoDB, PostgreSQL, MySQL, SQLite)

Usage:
    # Tool to JSON
    tool_spec = FunctionToolSpec(...)
    json_str = tool_to_json(tool_spec)
    json_dict = tool_to_dict(tool_spec)
    
    # JSON to Tool
    tool_spec = tool_from_json(json_str)
    tool_spec = tool_from_dict(json_dict)
"""

import json
from typing import Dict, Any, Union, Type

from ..spec.tool_types import (
    ToolSpec,
    FunctionToolSpec,
    HttpToolSpec,
    DbToolSpec,
    DynamoDbToolSpec,
    PostgreSqlToolSpec,
    MySqlToolSpec,
    SqliteToolSpec,
)
from ..enum import ToolType


class ToolSerializationError(Exception):
    """Raised when tool serialization or deserialization fails"""
    pass


# Mapping of tool types and drivers to their corresponding spec classes
TOOL_TYPE_MAP: Dict[ToolType, Type[ToolSpec]] = {
    ToolType.FUNCTION: FunctionToolSpec,
    ToolType.HTTP: HttpToolSpec,
    ToolType.DB: DbToolSpec,
}

DB_DRIVER_MAP: Dict[str, Type[DbToolSpec]] = {
    "dynamodb": DynamoDbToolSpec,
    "postgresql": PostgreSqlToolSpec,
    "mysql": MySqlToolSpec,
    "sqlite": SqliteToolSpec,
}


def tool_to_json(
    tool: ToolSpec,
    *,
    indent: int = 2,
    exclude_none: bool = True,
    exclude_unset: bool = False,
) -> str:
    """
    Serialize a Tool object to a JSON string.
    
    Args:
        tool: Tool specification object to serialize
        indent: Number of spaces for JSON indentation (default: 2)
        exclude_none: Exclude fields with None values (default: True)
        exclude_unset: Exclude fields that weren't explicitly set (default: False)
        
    Returns:
        JSON string representation of the tool
        
    Raises:
        ToolSerializationError: If serialization fails
        
    Example:
        >>> spec = FunctionToolSpec(
        ...     id="my-tool",
        ...     tool_name="my_tool",
        ...     description="My tool",
        ...     parameters=[]
        ... )
        >>> json_str = tool_to_json(spec)
        >>> print(json_str)
        {
          "id": "my-tool",
          "tool_name": "my_tool",
          ...
        }
    """
    try:
        return tool.model_dump_json(
            indent=indent,
            exclude_none=exclude_none,
            exclude_unset=exclude_unset,
            by_alias=True,
        )
    except Exception as e:
        raise ToolSerializationError(f"Failed to serialize tool to JSON: {e}") from e


def tool_to_dict(
    tool: ToolSpec,
    *,
    exclude_none: bool = True,
    exclude_unset: bool = False,
) -> Dict[str, Any]:
    """
    Serialize a Tool object to a dictionary.
    
    Args:
        tool: Tool specification object to serialize
        exclude_none: Exclude fields with None values (default: True)
        exclude_unset: Exclude fields that weren't explicitly set (default: False)
        
    Returns:
        Dictionary representation of the tool
        
    Raises:
        ToolSerializationError: If serialization fails
        
    Example:
        >>> spec = FunctionToolSpec(...)
        >>> tool_dict = tool_to_dict(spec)
        >>> print(tool_dict['tool_name'])
        'my_tool'
    """
    try:
        return tool.model_dump(
            mode='python',
            exclude_none=exclude_none,
            exclude_unset=exclude_unset,
            by_alias=True,
        )
    except Exception as e:
        raise ToolSerializationError(f"Failed to serialize tool to dict: {e}") from e


def tool_from_json(
    json_str: str,
    *,
    strict: bool = False,  # Changed default to False for better compatibility
) -> ToolSpec:
    """
    Deserialize a JSON string to a Tool object.
    
    Automatically detects the correct tool type and instantiates
    the appropriate subclass (FunctionToolSpec, HttpToolSpec, etc.).
    
    Args:
        json_str: JSON string to deserialize
        strict: Whether to validate strictly (default: True)
        
    Returns:
        Tool specification object (correct subclass based on tool_type)
        
    Raises:
        ToolSerializationError: If deserialization fails or tool type is unknown
        
    Example:
        >>> json_str = '''
        ... {
        ...   "id": "my-tool",
        ...   "tool_name": "my_tool",
        ...   "description": "My tool",
        ...   "tool_type": "function",
        ...   "parameters": []
        ... }
        ... '''
        >>> tool = tool_from_json(json_str)
        >>> isinstance(tool, FunctionToolSpec)
        True
    """
    try:
        # First parse the JSON to get the tool_type
        data = json.loads(json_str)
        return tool_from_dict(data, strict=strict)
    except json.JSONDecodeError as e:
        raise ToolSerializationError(f"Invalid JSON: {e}") from e
    except Exception as e:
        raise ToolSerializationError(f"Failed to deserialize tool from JSON: {e}") from e


def tool_from_dict(
    data: Dict[str, Any],
    *,
    strict: bool = False,  # Changed default to False for better compatibility
) -> ToolSpec:
    """
    Deserialize a dictionary to a Tool object.
    
    Automatically detects the correct tool type and instantiates
    the appropriate subclass based on tool_type and driver fields.
    
    Args:
        data: Dictionary containing tool data
        strict: Whether to validate strictly (default: False)
        
    Returns:
        Tool specification object (correct subclass based on tool_type)
        
    Raises:
        ToolSerializationError: If deserialization fails or tool type is unknown
        
    Example:
        >>> data = {
        ...     "id": "my-tool",
        ...     "tool_name": "my_tool",
        ...     "description": "My tool",
        ...     "tool_type": "function",
        ...     "parameters": []
        ... }
        >>> tool = tool_from_dict(data)
        >>> isinstance(tool, FunctionToolSpec)
        True
    """
    try:
        # Extract tool_type
        if 'tool_type' not in data:
            raise ToolSerializationError("Missing 'tool_type' field in data")
        
        tool_type_str = data['tool_type']
        
        # Convert string to ToolType enum
        try:
            if isinstance(tool_type_str, str):
                tool_type = ToolType(tool_type_str.lower())
            elif isinstance(tool_type_str, ToolType):
                tool_type = tool_type_str
            else:
                raise ValueError(f"Invalid tool_type format: {type(tool_type_str)}")
        except ValueError as e:
            raise ToolSerializationError(
                f"Unknown tool_type: {tool_type_str}. "
                f"Valid types: {[t.value for t in ToolType]}"
            ) from e
        
        # For DB tools, check driver to determine specific subclass
        if tool_type == ToolType.DB:
            driver = data.get('driver', 'dynamodb')
            
            if driver in DB_DRIVER_MAP:
                spec_class = DB_DRIVER_MAP[driver]
            else:
                # Fallback to base DbToolSpec for unknown drivers
                spec_class = DbToolSpec
        else:
            # Get the appropriate spec class for non-DB tools
            spec_class = TOOL_TYPE_MAP.get(tool_type, ToolSpec)
        
        # Instantiate and validate using Pydantic
        # Using strict=False by default allows Pydantic to coerce strings to enums
        return spec_class.model_validate(data, strict=strict)
    
    except ToolSerializationError:
        # Re-raise our custom errors
        raise
    except Exception as e:
        raise ToolSerializationError(f"Failed to deserialize tool from dict: {e}") from e


def register_db_driver(driver: str, spec_class: Type[DbToolSpec]) -> None:
    """
    Register a custom database driver and its corresponding spec class.
    
    This allows extending the serializer to support custom database types
    beyond the built-in ones.
    
    Args:
        driver: Driver name (e.g., 'mongodb', 'redis')
        spec_class: ToolSpec subclass for this driver
        
    Example:
        >>> class MongoDbToolSpec(DbToolSpec):
        ...     driver: str = Field(default="mongodb")
        ...     connection_string: str
        ...     database: str
        ...     collection: str
        ...
        >>> register_db_driver("mongodb", MongoDbToolSpec)
        >>> # Now tool_from_json/dict will work with mongodb tools
    """
    DB_DRIVER_MAP[driver] = spec_class


def get_supported_tool_types() -> list[str]:
    """
    Get list of supported tool types.
    
    Returns:
        List of supported tool type strings
        
    Example:
        >>> types = get_supported_tool_types()
        >>> print(types)
        ['function', 'http', 'db']
    """
    return [t.value for t in ToolType]


def get_supported_db_drivers() -> list[str]:
    """
    Get list of supported database drivers.
    
    Returns:
        List of supported database driver strings
        
    Example:
        >>> drivers = get_supported_db_drivers()
        >>> print(drivers)
        ['dynamodb', 'postgresql', 'mysql', 'sqlite']
    """
    return list(DB_DRIVER_MAP.keys())

