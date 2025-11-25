"""
Tool Implementations for Testing.

This module provides concrete implementations of three different tool types
to demonstrate and test the tool execution system. Each tool showcases different
capabilities and integration patterns.

Tool Implementations:
=====================
1. Division Function Tool
   - Type: Function-based tool
   - Purpose: Performs division with comprehensive error handling
   - Features: Division by zero detection, type coercion, ToolError usage
   
2. HTTP API Tool
   - Type: HTTP-based tool
   - Purpose: Interacts with REST API endpoints
   - Endpoint: https://kdahhpfkwb.execute-api.us-west-2.amazonaws.com/api/items
   - Methods: GET (list items), POST (create item)
   
3. DynamoDB Tool
   - Type: Database tool
   - Purpose: Add items to DynamoDB table
   - Table: api-test-items
   - Strategy: DynamoDB with automatic float→Decimal conversion

Usage:
    from tests.tools.tool_implementations import (
        division_function,
        create_division_tool_spec,
        create_http_api_tool_spec,
        create_dynamodb_tool_spec
    )
    
    # Create and execute division tool
    spec = create_division_tool_spec()
    executor = FunctionToolExecutor(spec, division_function)
    result = await executor.execute({'numerator': 10, 'denominator': 2}, ctx)
    
    # Create and execute HTTP tool
    spec = create_http_api_tool_spec()
    executor = HttpToolExecutor(spec)
    result = await executor.execute({'method': 'GET'}, ctx)
    
    # Create and execute DynamoDB tool
    spec = create_dynamodb_tool_spec()
    executor = DbToolExecutor(spec)
    result = await executor.execute({
        'operation': 'put_item',
        'table_name': 'api-test-items',
        'item': {'id': '123', 'name': 'Test', 'price': 99.99}
    }, ctx)

Note:
    These implementations are designed for testing and demonstration purposes.
    Production implementations should include additional error handling,
    logging, and business logic as appropriate.
"""

from typing import Any, Dict
from core.tools.spec.tool_types import FunctionToolSpec, HttpToolSpec, DbToolSpec
from core.tools.spec.tool_parameters import NumericParameter
from core.tools.spec.tool_result import ToolError
from core.tools.enum import ToolType, ToolReturnType, ToolReturnTarget
from core.tools.constants import ERROR_MATH


# ============================================================================
# 1. DIVISION FUNCTION TOOL
# ============================================================================

async def division_function(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Perform division of two numbers
    
    Args:
        args: Dictionary containing 'numerator' and 'denominator'
        
    Returns:
        Dictionary with 'result' key containing the division result
        
    Raises:
        ToolError: If denominator is zero
    """
    numerator = args.get('numerator', 0)
    denominator = args.get('denominator', 1)
    
    # Convert to float if they're strings
    try:
        numerator = float(numerator)
        denominator = float(denominator)
    except (ValueError, TypeError):
        raise ToolError(
            f"Invalid numeric values: numerator={numerator}, denominator={denominator}",
            retryable=False,
            code=ERROR_MATH
        )
    
    # Check for division by zero
    if denominator == 0:
        raise ToolError(
            "Division by zero is not allowed",
            retryable=False,
            code=ERROR_MATH
        )
    
    result = numerator / denominator
    
    return {
        'numerator': numerator,
        'denominator': denominator,
        'result': result,
        'operation': 'division'
    }


def create_division_tool_spec() -> FunctionToolSpec:
    """Create the tool specification for division function"""
    return FunctionToolSpec(
        id="tool-division-v1",
        version="1.0.0",
        tool_name="division",
        description="Divides two numbers and returns the result. Handles division by zero gracefully.",
        tool_type=ToolType.FUNCTION,
        parameters=[
            NumericParameter(
                name="numerator",
                description="The number to be divided (dividend)",
                required=True,
                examples=[10, 100.5, -50]
            ),
            NumericParameter(
                name="denominator",
                description="The number to divide by (divisor). Cannot be zero.",
                required=True,
                examples=[2, 5.5, -10]
            )
        ],
        return_type=ToolReturnType.JSON,
        return_target=ToolReturnTarget.STEP,
        timeout_s=5,
        examples=[
            {
                "input": {"numerator": 10, "denominator": 2},
                "output": {"result": 5.0}
            },
            {
                "input": {"numerator": 100, "denominator": 4},
                "output": {"result": 25.0}
            }
        ]
    )


# ============================================================================
# 2. HTTP API TOOL
# ============================================================================

def create_http_api_tool_spec() -> HttpToolSpec:
    """Create the tool specification for HTTP API interactions"""
    return HttpToolSpec(
        id="tool-http-api-v1",
        version="1.0.0",
        tool_name="api_items",
        description="Interact with the Items API - supports GET (list items) and POST (create item)",
        tool_type=ToolType.HTTP,
        url="https://kdahhpfkwb.execute-api.us-west-2.amazonaws.com/api/items",
        method="GET",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        parameters=[],
        return_type=ToolReturnType.JSON,
        return_target=ToolReturnTarget.STEP,
        timeout_s=30,
        examples=[
            {
                "description": "Get all items",
                "input": {"method": "GET"},
                "output": {"status_code": 200, "response": []}
            },
            {
                "description": "Create a new item",
                "input": {
                    "method": "POST",
                    "body": {"name": "Test Item", "price": 99.99}
                },
                "output": {"status_code": 201}
            }
        ]
    )


# ============================================================================
# 3. DYNAMODB TOOL
# ============================================================================

def create_dynamodb_tool_spec():
    """
    Create the tool specification for DynamoDB operations.
    
    Returns:
        DynamoDbToolSpec: Provider-specific specification for DynamoDB
        
    Note:
        Configuration (region, table_name) is at spec level, not in parameters.
        Parameters are for actual operation arguments like 'item', 'key', etc.
    """
    from core.tools.spec.tool_types import DynamoDbToolSpec
    from core.tools.spec.tool_parameters import StringParameter, ObjectParameter
    
    return DynamoDbToolSpec(
        id="tool-dynamodb-items-v1",
        version="1.0.0",
        tool_name="dynamodb_add_item",
        description="Add items to the api-test-items DynamoDB table",
        # Provider-specific configuration (NOT parameters)
        region="us-west-2",
        table_name="api-test-items",
        # Parameters for actual operation
        parameters=[
            StringParameter(
                name="operation",
                description="DynamoDB operation to perform",
                required=False,
                default="put_item",
                enum=["put_item", "get_item", "query", "scan", "update_item", "delete_item"]
            ),
            ObjectParameter(
                name="item",
                description="Item data for put_item operation",
                required=False
            ),
            ObjectParameter(
                name="key",
                description="Key for get_item/update_item/delete_item operations",
                required=False
            ),
            ObjectParameter(
                name="query_params",
                description="Parameters for query operation",
                required=False
            ),
            ObjectParameter(
                name="scan_params",
                description="Parameters for scan operation",
                required=False
            ),
            ObjectParameter(
                name="update_expression",
                description="Update expression for update_item operation",
                required=False
            )
        ],
        return_type=ToolReturnType.JSON,
        return_target=ToolReturnTarget.STEP,
        timeout_s=30,
        examples=[
            {
                "description": "Add an item to DynamoDB",
                "input": {
                    "operation": "put_item",
                    "item": {
                        "id": "item-001",
                        "name": "Test Item",
                        "price": 99.99,
                        "created_at": "2024-01-01T00:00:00Z"
                    }
                },
                "output": {
                    "operation": "put_item",
                    "table_name": "api-test-items",
                    "status": "success"
                }
            },
            {
                "description": "Get an item from DynamoDB",
                "input": {
                    "operation": "get_item",
                    "key": {"id": "item-001"}
                },
                "output": {
                    "operation": "get_item",
                    "item": {"id": "item-001", "name": "Test Item"},
                    "status": "success"
                }
            }
        ]
    )

