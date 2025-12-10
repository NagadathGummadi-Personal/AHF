#!/usr/bin/env python3
"""
Export Pydantic Models to JSON Schema with UI Metadata.

This script exports all tool-related Pydantic models to JSON Schema format,
including UI metadata for automatic Flutter form generation.

Usage:
    python scripts/export_schemas.py

Output:
    frontend/lib/generated/tool_schemas.json
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Type

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pydantic import BaseModel

# Import all tool-related models
from core.tools.spec import (
    # Config models
    RetryConfig,
    CircuitBreakerConfig,
    IdempotencyConfig,
    InterruptionConfig,
    PreToolSpeechConfig,
    ExecutionConfig,
    VariableAssignment,
    DynamicVariableConfig,
    # Parameter models
    ToolParameter,
    StringParameter,
    NumericParameter,
    IntegerParameter,
    BooleanParameter,
    ArrayParameter,
    ObjectParameter,
    # Tool types
    ToolSpec,
    FunctionToolSpec,
    HttpToolSpec,
    DbToolSpec,
    DynamoDbToolSpec,
    PostgreSqlToolSpec,
    MySqlToolSpec,
    SqliteToolSpec,
)

# Import enums
from core.tools.enum import (
    ToolType,
    ToolReturnType,
    ToolReturnTarget,
    ParameterType,
    SpeechMode,
    ExecutionMode,
    VariableAssignmentOperator,
    SpeechContextScope,
    TransformExecutionMode,
    CircuitBreakerState,
    RetryableErrorType,
)


# Models to export (order matters for dependencies)
CONFIG_MODELS: List[Type[BaseModel]] = [
    RetryConfig,
    CircuitBreakerConfig,
    IdempotencyConfig,
    InterruptionConfig,
    PreToolSpeechConfig,
    ExecutionConfig,
    VariableAssignment,
    DynamicVariableConfig,
]

PARAMETER_MODELS: List[Type[BaseModel]] = [
    ToolParameter,
    StringParameter,
    NumericParameter,
    IntegerParameter,
    BooleanParameter,
    ArrayParameter,
    ObjectParameter,
]

TOOL_MODELS: List[Type[BaseModel]] = [
    ToolSpec,
    FunctionToolSpec,
    HttpToolSpec,
    DbToolSpec,
    DynamoDbToolSpec,
    PostgreSqlToolSpec,
    MySqlToolSpec,
    SqliteToolSpec,
]

# Enums to export with labels
ENUMS = {
    "ToolType": {
        "values": [e.value for e in ToolType],
        "labels": {
            "function": "Function (Python)",
            "http": "HTTP (REST API)",
            "db": "Database (SQL/NoSQL)",
        }
    },
    "ToolReturnType": {
        "values": [e.value for e in ToolReturnType],
        "labels": {
            "json": "JSON",
            "text": "Text",
            "toon": "TOON",
        }
    },
    "ToolReturnTarget": {
        "values": [e.value for e in ToolReturnTarget],
        "labels": {
            "human": "Human (direct to user)",
            "llm": "LLM (continue conversation)",
            "agent": "Agent (for agent processing)",
            "step": "Step (workflow step output)",
        }
    },
    "ParameterType": {
        "values": [e.value for e in ParameterType],
        "labels": {
            "string": "String",
            "number": "Number",
            "integer": "Integer",
            "boolean": "Boolean",
            "array": "Array",
            "object": "Object",
        }
    },
    "SpeechMode": {
        "values": [e.value for e in SpeechMode],
        "labels": {
            "auto": "Auto (LLM generates)",
            "random": "Random (from list)",
            "constant": "Constant (fixed message)",
        }
    },
    "ExecutionMode": {
        "values": [e.value for e in ExecutionMode],
        "labels": {
            "sequential": "Sequential (speech then execute)",
            "parallel": "Parallel (speech and execute together)",
        }
    },
    "VariableAssignmentOperator": {
        "values": [e.value for e in VariableAssignmentOperator],
        "labels": {
            "set": "Set (always)",
            "set_if_exists": "Set if Exists",
            "set_if_truthy": "Set if Truthy",
            "append": "Append to List",
            "increment": "Increment Number",
            "transform": "Transform with Function",
        }
    },
    "SpeechContextScope": {
        "values": [e.value for e in SpeechContextScope],
        "labels": {
            "full_context": "Full Context",
            "tool_only": "Tool Only",
            "last_message": "Last Message",
            "custom": "Custom Instruction",
        }
    },
    "TransformExecutionMode": {
        "values": [e.value for e in TransformExecutionMode],
        "labels": {
            "sync": "Sync (block)",
            "async": "Async (fire-and-forget)",
            "await": "Await (async but wait)",
        }
    },
    "CircuitBreakerState": {
        "values": [e.value for e in CircuitBreakerState],
        "labels": {
            "closed": "Closed (normal)",
            "open": "Open (failing fast)",
            "half_open": "Half Open (testing)",
        }
    },
}


def extract_ui_metadata(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract and organize UI metadata from a JSON schema.
    
    Walks through all properties and extracts the 'ui' field
    from json_schema_extra.
    """
    if "properties" not in schema:
        return schema
    
    # Process each property
    for prop_name, prop_schema in schema.get("properties", {}).items():
        # Handle nested objects
        if prop_schema.get("type") == "object" and "properties" in prop_schema:
            extract_ui_metadata(prop_schema)
        
        # Handle arrays
        if prop_schema.get("type") == "array" and "items" in prop_schema:
            items = prop_schema["items"]
            if isinstance(items, dict) and "properties" in items:
                extract_ui_metadata(items)
    
    return schema


def get_model_schema(model: Type[BaseModel]) -> Dict[str, Any]:
    """
    Get JSON schema for a Pydantic model with UI metadata.
    """
    schema = model.model_json_schema(mode='serialization')
    
    # Extract UI metadata from schema
    schema = extract_ui_metadata(schema)
    
    # Add model name
    schema["_model_name"] = model.__name__
    
    # Add model docstring as description if not present
    if not schema.get("description") and model.__doc__:
        schema["description"] = model.__doc__.strip()
    
    return schema


def export_schemas(output_path: Path) -> None:
    """
    Export all schemas to a single JSON file.
    """
    output = {
        "version": "1.0.0",
        "generated": True,
        "enums": ENUMS,
        "schemas": {
            "configs": {},
            "parameters": {},
            "tools": {},
        },
        "definitions": {},
    }
    
    # Export config models
    for model in CONFIG_MODELS:
        schema = get_model_schema(model)
        output["schemas"]["configs"][model.__name__] = schema
        print(f"  Exported: {model.__name__}")
    
    # Export parameter models
    for model in PARAMETER_MODELS:
        schema = get_model_schema(model)
        output["schemas"]["parameters"][model.__name__] = schema
        print(f"  Exported: {model.__name__}")
    
    # Export tool models
    for model in TOOL_MODELS:
        schema = get_model_schema(model)
        output["schemas"]["tools"][model.__name__] = schema
        print(f"  Exported: {model.__name__}")
    
    # Collect shared definitions ($defs)
    all_defs = {}
    for category in output["schemas"].values():
        for schema in category.values():
            if "$defs" in schema:
                all_defs.update(schema["$defs"])
                del schema["$defs"]
    
    output["definitions"] = all_defs
    
    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\nExported schemas to: {output_path}")
    print(f"  Configs: {len(CONFIG_MODELS)}")
    print(f"  Parameters: {len(PARAMETER_MODELS)}")
    print(f"  Tools: {len(TOOL_MODELS)}")
    print(f"  Enums: {len(ENUMS)}")


def main():
    """Main entry point."""
    output_dir = PROJECT_ROOT / "frontend" / "lib" / "generated"
    output_file = output_dir / "tool_schemas.json"
    
    print("Exporting Pydantic schemas with UI metadata...")
    print("-" * 50)
    
    export_schemas(output_file)
    
    print("-" * 50)
    print("Done!")


if __name__ == "__main__":
    main()


