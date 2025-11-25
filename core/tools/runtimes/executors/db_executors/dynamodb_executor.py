"""
DynamoDB Executor for Tools Specification System.

This module provides the DynamoDB-specific executor that handles operations
for AWS DynamoDB tables using the DynamoDB strategy pattern.

Classes:
========
- DynamoDBExecutor: Executor for DynamoDB operations

Inheritance:
============
BaseToolExecutor
└── BaseDbExecutor
    └── DynamoDBExecutor (this class)

Supported Operations:
=====================
- put_item: Insert or replace an item
- get_item: Retrieve an item by key
- query: Query items with conditions
- scan: Scan table with optional filters
- update_item: Update item attributes
- delete_item: Delete an item

Usage:
    from core.tools.executors.db_executors import DynamoDBExecutor
    from core.tools.spec.tool_types import DynamoDbToolSpec
    
    spec = DynamoDbToolSpec(
        id="dynamodb-tool-v1",
        tool_name="add_item",
        description="Add item to DynamoDB",
        region="us-west-2",
        table_name="my-table",
        parameters=[
            ObjectParameter(name="item", description="Item to add", required=True)
        ]
    )
    
    executor = DynamoDBExecutor(spec)
    result = await executor.execute({
        'operation': 'put_item',
        'item': {'id': '123', 'name': 'Test', 'price': 99.99}
    }, ctx)

Note:
    - Automatically converts Python floats to Decimal for DynamoDB compatibility
    - Uses boto3 for AWS SDK integration
    - Requires AWS credentials configured (environment variables, config files, or IAM roles)
"""

from typing import Any, Dict

# Local imports
from .base_db_executor import BaseDbExecutor
from ....spec.tool_types import DbToolSpec
from ....spec.tool_context import ToolContext
from ..db_strategies import DbStrategyFactory


class DynamoDBExecutor(BaseDbExecutor):
    """
    DynamoDB-specific executor.
    
    Handles DynamoDB operations by using the DynamoDB strategy pattern.
    Provides seamless integration with AWS DynamoDB tables including
    automatic type conversion and error handling.
    
    Features:
        - Automatic float to Decimal conversion
        - Full DynamoDB operation support (put, get, query, scan, etc.)
        - AWS credential integration
        - Configurable region and table names
        - Error handling with detailed messages
    
    Example Operations:
        # Put item
        result = await executor.execute({
            'operation': 'put_item',
            'item': {'id': '123', 'name': 'John', 'age': 30}
        }, ctx)
        
        # Get item
        result = await executor.execute({
            'operation': 'get_item',
            'key': {'id': '123'}
        }, ctx)
        
        # Query
        result = await executor.execute({
            'operation': 'query',
            'query_params': {
                'KeyConditionExpression': 'id = :id',
                'ExpressionAttributeValues': {':id': '123'}
            }
        }, ctx)
    
    Note:
        Requires boto3 library: pip install boto3
    """
    
    def __init__(self, spec: DbToolSpec):
        """
        Initialize DynamoDB executor.
        
        Args:
            spec: Database tool specification with driver='dynamodb'
        """
        super().__init__(spec)
        # Get the DynamoDB strategy
        self.strategy = DbStrategyFactory.get_strategy('dynamodb')
    
    async def _execute_db_operation(
        self,
        args: Dict[str, Any],
        ctx: ToolContext,
        timeout: float | None
    ) -> Dict[str, Any]:
        """
        Execute DynamoDB operation using the strategy pattern.
        
        Args:
            args: Operation arguments including:
                - operation: 'put_item', 'get_item', 'query', 'scan', etc.
                - table_name: DynamoDB table name (optional, uses spec.table_name)
                - item: Item data for put_item
                - key: Key for get_item/delete_item
                - query_params: Parameters for query operation
                - scan_params: Parameters for scan operation
                - region: AWS region (optional, defaults to spec.region)
            ctx: Tool execution context
            timeout: Optional timeout in seconds
            
        Returns:
            Dictionary containing:
                - operation: The operation that was executed
                - table_name: Table that was operated on
                - status: 'success' or error information
                - Additional operation-specific data (items, response, etc.)
        
        Raises:
            ImportError: If boto3 is not installed
            Exception: DynamoDB-specific errors (permissions, table not found, etc.)
        
        Example Result:
            {
                'operation': 'put_item',
                'table_name': 'users',
                'item': {'id': '123', 'name': 'John'},
                'status': 'success',
                'response': {...}  # boto3 response
            }
        """
        return await self.strategy.execute_operation(args, self.spec, timeout)


