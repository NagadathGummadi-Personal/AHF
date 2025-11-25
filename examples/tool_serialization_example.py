"""
Tool Serialization Example

This example demonstrates how to convert between JSON and Tool objects
using the new serialization functionality.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from core.tools import (
    FunctionToolSpec,
    HttpToolSpec,
    tool_to_json,
    tool_from_json,
    tool_to_dict,
    tool_from_dict,
)
from core.tools.spec.tool_types import DynamoDbToolSpec
from core.tools.spec.tool_parameters import StringParameter, NumericParameter
from core.tools.enum import ToolType, ToolReturnType, ToolReturnTarget


def example_1_function_tool():
    """Example 1: Serialize and deserialize a Function Tool"""
    print("\n=== Example 1: Function Tool ===\n")
    
    # Create a function tool
    tool = FunctionToolSpec(
        id="calculator-v1",
        tool_name="calculator",
        description="Perform mathematical calculations",
        parameters=[
            NumericParameter(name="x", description="First number", required=True),
            NumericParameter(name="y", description="Second number", required=True),
            StringParameter(name="operation", description="Operation (+, -, *, /)", required=True),
        ],
        return_type=ToolReturnType.JSON,
        return_target=ToolReturnTarget.STEP,
    )
    
    # Convert to JSON
    json_str = tool_to_json(tool, indent=2)
    print("Tool as JSON:")
    print(json_str)
    
    # Convert back to Tool object
    restored_tool = tool_from_json(json_str)
    print(f"\nRestored tool: {restored_tool.tool_name}")
    print(f"Tool type: {restored_tool.tool_type}")
    print(f"Parameters count: {len(restored_tool.parameters)}")


def example_2_http_tool():
    """Example 2: Serialize and deserialize an HTTP Tool"""
    print("\n\n=== Example 2: HTTP Tool ===\n")
    
    # Create an HTTP tool
    tool = HttpToolSpec(
        id="api-client-v1",
        tool_name="fetch_user",
        description="Fetch user data from API",
        url="https://api.example.com/users/{user_id}",
        method="GET",
        headers={"Authorization": "Bearer {token}"},
        parameters=[
            StringParameter(name="user_id", description="User ID", required=True),
            StringParameter(name="token", description="Auth token", required=True),
        ],
    )
    
    # Convert to dictionary
    tool_dict = tool_to_dict(tool)
    print("Tool as dictionary:")
    for key, value in tool_dict.items():
        if key != "parameters":  # Skip parameters for brevity
            print(f"  {key}: {value}")
    
    # Convert back to Tool object
    restored_tool = tool_from_dict(tool_dict)
    print(f"\nRestored tool: {restored_tool.tool_name}")
    print(f"URL: {restored_tool.url}")
    print(f"Method: {restored_tool.method}")


def example_3_database_tool():
    """Example 3: Serialize and deserialize a Database Tool"""
    print("\n\n=== Example 3: Database Tool ===\n")
    
    # Create a DynamoDB tool
    tool = DynamoDbToolSpec(
        id="user-orders-v1",
        tool_name="get_user_orders",
        description="Get user orders from DynamoDB",
        region="us-west-2",
        table_name="user-orders",
        parameters=[
            StringParameter(name="user_id", description="User ID", required=True),
            StringParameter(name="status", description="Order status filter", required=False),
        ],
    )
    
    # Convert to JSON
    json_str = tool_to_json(tool)
    print("Tool as JSON (compact):")
    print(json_str[:200] + "...")  # Show first 200 chars
    
    # Convert back to Tool object
    restored_tool = tool_from_json(json_str)
    print(f"\nRestored tool: {restored_tool.tool_name}")
    print(f"Driver: {restored_tool.driver}")
    print(f"Region: {restored_tool.region}")
    print(f"Table: {restored_tool.table_name}")


def example_4_round_trip():
    """Example 4: Complete round-trip conversion"""
    print("\n\n=== Example 4: Round-trip Conversion ===\n")
    
    # Start with a tool
    original = FunctionToolSpec(
        id="test-tool",
        tool_name="my_tool",
        description="Test tool for round-trip",
        parameters=[
            StringParameter(name="input", description="Input value", required=True),
        ],
    )
    
    print(f"Original tool ID: {original.id}")
    
    # Convert to JSON
    json_str = tool_to_json(original)
    print(f"Serialized to JSON ({len(json_str)} characters)")
    
    # Convert back to Tool
    restored = tool_from_json(json_str)
    print(f"Restored tool ID: {restored.id}")
    
    # Verify they match
    assert original.id == restored.id
    assert original.tool_name == restored.tool_name
    assert original.description == restored.description
    print("\n[OK] Round-trip successful! All fields match.")


def example_5_from_external_json():
    """Example 5: Create tool from external JSON (e.g., from API or file)"""
    print("\n\n=== Example 5: Create Tool from External JSON ===\n")
    
    # Simulating JSON received from an external source
    external_json = '''
    {
        "id": "external-tool-001",
        "tool_name": "process_data",
        "description": "Process data from external system",
        "tool_type": "function",
        "parameters": [
            {
                "name": "data",
                "type": "string",
                "description": "Data to process",
                "required": true
            }
        ],
        "return_type": "json",
        "return_target": "step"
    }
    '''
    
    # Create tool from JSON
    tool = tool_from_json(external_json)
    
    print(f"Created tool from external JSON:")
    print(f"  ID: {tool.id}")
    print(f"  Name: {tool.tool_name}")
    print(f"  Type: {tool.tool_type}")
    print(f"  Parameters: {len(tool.parameters)}")
    print(f"  Tool class: {tool.__class__.__name__}")


def main():
    """Run all examples"""
    print("="  * 60)
    print("Tool Serialization Examples")
    print("=" * 60)
    
    example_1_function_tool()
    example_2_http_tool()
    example_3_database_tool()
    example_4_round_trip()
    example_5_from_external_json()
    
    print("\n" + "=" * 60)
    print("All examples completed successfully!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()

