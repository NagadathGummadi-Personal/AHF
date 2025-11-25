"""
DynamoDB Operation Strategy.

This module provides the strategy implementation for AWS DynamoDB operations.
Handles DynamoDB-specific operations with automatic type conversion and proper
AWS SDK integration.

Strategy:
=========
- DynamoDBStrategy: Implements IDbOperationStrategy for DynamoDB

Supported Operations:
=====================
- put_item: Insert or replace an item
- get_item: Retrieve an item by key
- query: Query items with conditions
- scan: Scan table with optional filters
- update_item: Update item attributes
- delete_item: Delete an item

Features:
=========
- Automatic float to Decimal conversion for DynamoDB compatibility
- Support for LocalStack endpoint (for testing)
- Configurable timeout and connection settings
- Proper error handling

Dependencies:
=============
Requires boto3 library: pip install boto3

Usage:
    from core.tools.executors.db_strategies import DynamoDBStrategy
    
    strategy = DynamoDBStrategy()
    result = await strategy.execute_operation(
        args={'operation': 'put_item', 'item': {'id': '123', 'name': 'John'}},
        spec=dynamodb_spec,
        timeout=30.0
    )

Note:
    AWS credentials should be configured via environment variables,
    AWS config files, or IAM roles when running on AWS infrastructure.
"""

import asyncio
from typing import Any, Dict, Optional
from .strategy_interface import IDbOperationStrategy
from core.tools.enum import DatabaseProvider
from core.tools.constants import (
    DEFAULT_REGION,
    ENDPOINT_URL,
    REGION,
)

class DynamoDBStrategy(IDbOperationStrategy):
    """
    Strategy for AWS DynamoDB operations.
    
    Handles DynamoDB-specific operations including put_item, get_item, query, and scan.
    Automatically converts Python float types to Decimal for DynamoDB compatibility.
    
    Supported Operations:
        - put_item: Insert or replace an item
        - get_item: Retrieve an item by key
        - query: Query items with conditions
        - scan: Scan table with optional filters
        - update_item: Update attributes (future)
        - delete_item: Delete an item (future)
    
    Type Conversion:
        Python floats are automatically converted to Decimal types as required
        by DynamoDB's number type system.
    
    Configuration:
        Uses spec attributes:
        - table_name: DynamoDB table name (required)
        - region: AWS region (default: 'us-west-2')
        - endpoint_url: Custom endpoint for LocalStack/testing (optional)
    
    Example:
        strategy = DynamoDBStrategy()
        
        # Put item
        result = await strategy.execute_operation({
            'operation': 'put_item',
            'item': {'id': '123', 'name': 'John', 'price': 99.99}
        }, spec, timeout=30)
        
        # Get item
        result = await strategy.execute_operation({
            'operation': 'get_item',
            'key': {'id': '123'}
        }, spec, timeout=30)
        
        # Query
        result = await strategy.execute_operation({
            'operation': 'query',
            'query_params': {
                'KeyConditionExpression': 'id = :id',
                'ExpressionAttributeValues': {':id': '123'}
            }
        }, spec, timeout=30)
    """
    
    @staticmethod
    def _convert_floats_to_decimal(obj: Any) -> Any:
        """
        Recursively convert floats to Decimal for DynamoDB compatibility.
        
        DynamoDB requires numeric values with decimal points to be Decimal type,
        not Python float. This method recursively converts all floats in nested
        data structures.
        
        Args:
            obj: Object to convert (can be dict, list, float, or other types)
            
        Returns:
            Object with all floats converted to Decimal
        
        Example:
            >>> item = {'price': 99.99, 'discount': 0.15}
            >>> converted = DynamoDBStrategy._convert_floats_to_decimal(item)
            >>> # {'price': Decimal('99.99'), 'discount': Decimal('0.15')}
        """
        from decimal import Decimal
        
        if isinstance(obj, float):
            return Decimal(str(obj))
        elif isinstance(obj, dict):
            return {k: DynamoDBStrategy._convert_floats_to_decimal(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [DynamoDBStrategy._convert_floats_to_decimal(item) for item in obj]
        return obj
    
    async def execute_operation(
        self,
        args: Dict[str, Any],
        spec: Any,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Execute DynamoDB operation.
        
        Args:
            args: Operation arguments:
                - operation: 'put_item', 'get_item', 'query', 'scan'
                - item: Item data for put_item
                - key: Key for get_item
                - query_params: Parameters for query
                - scan_params: Parameters for scan
            spec: DynamoDbToolSpec with table_name, region, endpoint_url
            timeout: Optional timeout in seconds
            
        Returns:
            Dictionary with operation results:
                - operation: Operation type
                - table_name: Table name
                - status: 'success'
                - Additional operation-specific data
        
        Raises:
            ImportError: If boto3 is not installed
            ValueError: If operation is not supported
            Exception: AWS/boto3 errors
        """
        try:
            import boto3
            from botocore.config import Config
            
            # Configure boto3 client with timeout
            config_dict = {}
            if timeout:
                config_dict['connect_timeout'] = timeout
                config_dict['read_timeout'] = timeout
            
            config = Config(**config_dict) if config_dict else None
            
            def _do_dynamodb_operation():
                # Get configuration from spec (NOT from args!)
                table_name = spec.table_name
                region = getattr(spec, REGION, DEFAULT_REGION)
                endpoint_url = getattr(spec, ENDPOINT_URL, None)
                
                # Create DynamoDB resource
                if endpoint_url:
                    # Use custom endpoint (for testing with LocalStack)
                    dynamodb = boto3.resource(
                        DatabaseProvider.DYNAMODB,
                        region_name=region,
                        endpoint_url=endpoint_url,
                        config=config
                    )
                else:
                    dynamodb = boto3.resource('dynamodb', region_name=region, config=config)
                
                table = dynamodb.Table(table_name)
                
                # Determine operation type
                operation = args.get('operation', 'put_item')
                
                if operation == 'put_item':
                    item = args.get('item', {})
                    # Convert floats to Decimal for DynamoDB compatibility
                    item_converted = DynamoDBStrategy._convert_floats_to_decimal(item)
                    response = table.put_item(Item=item_converted)
                    return {
                        'operation': 'put_item',
                        'table_name': table_name,
                        'item': item,
                        'response': response,
                        'status': 'success'
                    }
                    
                elif operation == 'get_item':
                    key = args.get('key', {})
                    response = table.get_item(Key=key)
                    return {
                        'operation': 'get_item',
                        'table_name': table_name,
                        'key': key,
                        'item': response.get('Item'),
                        'status': 'success'
                    }
                    
                elif operation == 'query':
                    query_params = args.get('query_params', {})
                    response = table.query(**query_params)
                    return {
                        'operation': 'query',
                        'table_name': table_name,
                        'items': response.get('Items', []),
                        'count': response.get('Count', 0),
                        'status': 'success'
                    }
                    
                elif operation == 'scan':
                    scan_params = args.get('scan_params', {})
                    response = table.scan(**scan_params)
                    return {
                        'operation': 'scan',
                        'table_name': table_name,
                        'items': response.get('Items', []),
                        'count': response.get('Count', 0),
                        'status': 'success'
                    }
                    
                else:
                    raise ValueError(f"Unsupported DynamoDB operation: {operation}")
            
            # Run in thread to avoid blocking event loop
            result = await asyncio.to_thread(_do_dynamodb_operation)
            return result
            
        except ImportError as e:
            raise ImportError(
                "boto3 is required for DynamoDB operations. "
                "Install with: pip install boto3"
            ) from e

