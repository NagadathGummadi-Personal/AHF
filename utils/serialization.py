"""
Shared Serialization Utilities.

Provides JSON and TOML serialization support for all AHF framework components.
This module centralizes serialization logic to avoid duplication across modules.

Usage:
    from utils.serialization import (
        to_json, from_json,
        to_toml, from_toml,
        save_to_file, load_from_file,
        SerializableMixin,
    )
    
    # Direct serialization
    json_str = to_json({"key": "value"})
    data = from_json(json_str)
    
    # File I/O (auto-detects format from extension)
    save_to_file(data, "config.toml")
    data = load_from_file("config.toml")
    
    # Mixin for classes
    class MyClass(SerializableMixin):
        def to_dict(self) -> Dict[str, Any]:
            return {"field": self.field}
        
        @classmethod
        def from_dict(cls, data: Dict[str, Any]) -> 'MyClass':
            return cls(**data)
    
    obj = MyClass()
    obj.save("output.json")
    obj = MyClass.load("output.json")

Version: 1.0.0
"""

import json
from datetime import datetime, date
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, Union, TypeVar, Type

# Try to import tomllib (Python 3.11+) or tomli for reading
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

# Try to import tomli_w for writing TOML
try:
    import tomli_w
except ImportError:
    tomli_w = None


class SerializationFormat(str, Enum):
    """Supported serialization formats."""
    JSON = "json"
    TOML = "toml"


class SerializationError(Exception):
    """Raised when serialization or deserialization fails."""
    pass


# Type variable for generic class methods
T = TypeVar('T', bound='SerializableMixin')


def _serialize_value(value: Any) -> Any:
    """
    Serialize a value to a JSON/TOML-compatible format.
    
    Handles:
    - datetime/date objects -> ISO format strings
    - Enum values -> underlying value
    - Pydantic models -> dict (via model_dump)
    - Objects with to_dict() method
    - Nested dicts and lists
    
    Args:
        value: Value to serialize
        
    Returns:
        Serialized value
    """
    if value is None:
        return None
    elif isinstance(value, datetime):
        return value.isoformat()
    elif isinstance(value, date):
        return value.isoformat()
    elif isinstance(value, Enum):
        return value.value
    elif isinstance(value, dict):
        return {k: _serialize_value(v) for k, v in value.items()}
    elif isinstance(value, (list, tuple)):
        return [_serialize_value(v) for v in value]
    elif hasattr(value, 'model_dump'):
        # Pydantic model
        return _serialize_value(value.model_dump())
    elif hasattr(value, 'to_dict'):
        # Custom class with to_dict method
        return _serialize_value(value.to_dict())
    elif isinstance(value, (str, int, float, bool)):
        return value
    else:
        # Fallback: convert to string
        return str(value)


def _deserialize_datetime_fields(
    data: Dict[str, Any],
    datetime_keys: Optional[list[str]] = None,
) -> Dict[str, Any]:
    """
    Convert ISO format strings back to datetime objects for specified keys.
    
    Args:
        data: Dictionary with potential datetime strings
        datetime_keys: List of keys to convert (if None, auto-detect common keys)
        
    Returns:
        Dictionary with datetime objects restored
    """
    if datetime_keys is None:
        # Auto-detect common datetime field names
        datetime_keys = [
            'created_at', 'updated_at', 'timestamp', 'datetime',
            'start_time', 'end_time', 'expires_at', 'modified_at',
        ]
    
    result = data.copy()
    for key in datetime_keys:
        if key in result and isinstance(result[key], str):
            try:
                result[key] = datetime.fromisoformat(result[key])
            except (ValueError, TypeError):
                pass  # Not a valid datetime string
    return result


# =============================================================================
# JSON Serialization
# =============================================================================

def to_json(
    data: Dict[str, Any],
    indent: int = 2,
    sort_keys: bool = False,
) -> str:
    """
    Serialize dictionary to JSON string.
    
    Args:
        data: Dictionary to serialize
        indent: Indentation level (default: 2)
        sort_keys: Sort dictionary keys (default: False)
        
    Returns:
        JSON string
        
    Raises:
        SerializationError: If serialization fails
    """
    try:
        serialized = _serialize_value(data)
        return json.dumps(serialized, indent=indent, sort_keys=sort_keys, default=str)
    except Exception as e:
        raise SerializationError(f"Failed to serialize to JSON: {e}") from e


def from_json(
    json_str: str,
    datetime_keys: Optional[list[str]] = None,
) -> Dict[str, Any]:
    """
    Deserialize JSON string to dictionary.
    
    Args:
        json_str: JSON string
        datetime_keys: Keys to convert to datetime (auto-detects if None)
        
    Returns:
        Dictionary
        
    Raises:
        SerializationError: If deserialization fails
    """
    try:
        data = json.loads(json_str)
        if isinstance(data, dict) and datetime_keys is not None:
            data = _deserialize_datetime_fields(data, datetime_keys)
        return data
    except json.JSONDecodeError as e:
        raise SerializationError(f"Invalid JSON: {e}") from e
    except Exception as e:
        raise SerializationError(f"Failed to deserialize from JSON: {e}") from e


# =============================================================================
# TOML Serialization
# =============================================================================

def to_toml(data: Dict[str, Any]) -> str:
    """
    Serialize dictionary to TOML string.
    
    Args:
        data: Dictionary to serialize
        
    Returns:
        TOML string
        
    Raises:
        ImportError: If tomli_w is not installed
        SerializationError: If serialization fails
    """
    if tomli_w is None:
        raise ImportError(
            "TOML writing requires 'tomli-w' package. "
            "Install with: pip install tomli-w"
        )
    
    try:
        serialized = _serialize_value(data)
        return tomli_w.dumps(serialized)
    except Exception as e:
        raise SerializationError(f"Failed to serialize to TOML: {e}") from e


def from_toml(
    toml_str: str,
    datetime_keys: Optional[list[str]] = None,
) -> Dict[str, Any]:
    """
    Deserialize TOML string to dictionary.
    
    Args:
        toml_str: TOML string
        datetime_keys: Keys to convert to datetime (auto-detects if None)
        
    Returns:
        Dictionary
        
    Raises:
        ImportError: If tomllib/tomli is not available
        SerializationError: If deserialization fails
    """
    if tomllib is None:
        raise ImportError(
            "TOML reading requires 'tomli' package (Python < 3.11). "
            "Install with: pip install tomli"
        )
    
    try:
        data = tomllib.loads(toml_str)
        if datetime_keys is not None:
            data = _deserialize_datetime_fields(data, datetime_keys)
        return data
    except Exception as e:
        raise SerializationError(f"Failed to deserialize from TOML: {e}") from e


# =============================================================================
# File I/O
# =============================================================================

def save_to_file(
    data: Dict[str, Any],
    path: Union[str, Path],
    format: Optional[SerializationFormat] = None,
) -> None:
    """
    Save dictionary to file in JSON or TOML format.
    
    Format is auto-detected from file extension if not specified:
    - .toml -> TOML
    - .json (or any other) -> JSON
    
    Args:
        data: Dictionary to save
        path: File path
        format: Serialization format (auto-detected if None)
        
    Raises:
        SerializationError: If serialization fails
        IOError: If file cannot be written
    """
    path = Path(path)
    
    # Auto-detect format from extension
    if format is None:
        if path.suffix.lower() == '.toml':
            format = SerializationFormat.TOML
        else:
            format = SerializationFormat.JSON
    
    if format == SerializationFormat.TOML:
        content = to_toml(data)
    else:
        content = to_json(data)
    
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


def load_from_file(
    path: Union[str, Path],
    format: Optional[SerializationFormat] = None,
    datetime_keys: Optional[list[str]] = None,
) -> Dict[str, Any]:
    """
    Load dictionary from file in JSON or TOML format.
    
    Format is auto-detected from file extension if not specified.
    
    Args:
        path: File path
        format: Serialization format (auto-detected if None)
        datetime_keys: Keys to convert to datetime
        
    Returns:
        Dictionary
        
    Raises:
        SerializationError: If deserialization fails
        FileNotFoundError: If file doesn't exist
    """
    path = Path(path)
    
    # Auto-detect format from extension
    if format is None:
        if path.suffix.lower() == '.toml':
            format = SerializationFormat.TOML
        else:
            format = SerializationFormat.JSON
    
    content = path.read_text(encoding='utf-8')
    
    if format == SerializationFormat.TOML:
        return from_toml(content, datetime_keys)
    else:
        return from_json(content, datetime_keys)


# =============================================================================
# Serializable Mixin
# =============================================================================

class SerializableMixin:
    """
    Mixin class providing JSON and TOML serialization methods.
    
    Classes using this mixin must implement:
    - to_dict() -> Dict[str, Any]
    - from_dict(data: Dict[str, Any]) -> Self
    
    Provides:
    - to_json(indent=2) -> str
    - to_toml() -> str
    - from_json(json_str) -> cls
    - from_toml(toml_str) -> cls
    - save(path, format=None) -> None
    - load(path, format=None) -> cls
    
    Example:
        class Config(SerializableMixin):
            def __init__(self, name: str, value: int):
                self.name = name
                self.value = value
            
            def to_dict(self) -> Dict[str, Any]:
                return {"name": self.name, "value": self.value}
            
            @classmethod
            def from_dict(cls, data: Dict[str, Any]) -> 'Config':
                return cls(name=data["name"], value=data["value"])
        
        config = Config("test", 42)
        config.save("config.json")
        config.save("config.toml")
        
        loaded = Config.load("config.toml")
    """
    
    def to_dict(self) -> Dict[str, Any]:
        """Export to dictionary. Must be implemented by subclass."""
        raise NotImplementedError("Subclass must implement to_dict()")
    
    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        """Create instance from dictionary. Must be implemented by subclass."""
        raise NotImplementedError("Subclass must implement from_dict()")
    
    def to_json(self, indent: int = 2) -> str:
        """
        Export to JSON string.
        
        Args:
            indent: Indentation level
            
        Returns:
            JSON string
        """
        return to_json(self.to_dict(), indent=indent)
    
    def to_toml(self) -> str:
        """
        Export to TOML string.
        
        Returns:
            TOML string
        """
        return to_toml(self.to_dict())
    
    @classmethod
    def from_json(cls: Type[T], json_str: str) -> T:
        """
        Create instance from JSON string.
        
        Args:
            json_str: JSON string
            
        Returns:
            New instance
        """
        data = from_json(json_str)
        return cls.from_dict(data)
    
    @classmethod
    def from_toml(cls: Type[T], toml_str: str) -> T:
        """
        Create instance from TOML string.
        
        Args:
            toml_str: TOML string
            
        Returns:
            New instance
        """
        data = from_toml(toml_str)
        return cls.from_dict(data)
    
    def save(
        self,
        path: Union[str, Path],
        format: Optional[SerializationFormat] = None,
    ) -> None:
        """
        Save to file.
        
        Args:
            path: File path (format detected from extension)
            format: Optional format override
        """
        save_to_file(self.to_dict(), path, format)
    
    @classmethod
    def load(
        cls: Type[T],
        path: Union[str, Path],
        format: Optional[SerializationFormat] = None,
    ) -> T:
        """
        Load from file.
        
        Args:
            path: File path (format detected from extension)
            format: Optional format override
            
        Returns:
            New instance
        """
        data = load_from_file(path, format)
        return cls.from_dict(data)


# =============================================================================
# Utility Functions
# =============================================================================

def is_toml_available() -> bool:
    """Check if TOML reading is available."""
    return tomllib is not None


def is_toml_write_available() -> bool:
    """Check if TOML writing is available."""
    return tomli_w is not None


def get_available_formats() -> list[str]:
    """Get list of available serialization formats."""
    formats = ["json"]
    if is_toml_available() and is_toml_write_available():
        formats.append("toml")
    return formats
