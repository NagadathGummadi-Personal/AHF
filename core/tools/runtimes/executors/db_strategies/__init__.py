"""
Database Operation Strategies for Generic DB Tool Execution.

This module provides strategy pattern implementations for different database
backends, making the DbToolExecutor fully generic and extensible. New database
backends can be added by implementing the IDbOperationStrategy interface.

Architecture:
=============
The module follows the Strategy pattern to allow runtime selection of database
operation implementations based on the driver type (e.g., 'dynamodb', 'postgresql').

Components:
===========
- IDbOperationStrategy: Abstract base class for all database strategies
- DynamoDBStrategy: AWS DynamoDB operations implementation
- DbStrategyFactory: Factory for creating and managing strategies

Available Strategies:
=====================
- DynamoDBStrategy: AWS DynamoDB operations with automatic type conversion
- PostgreSQLStrategy: PostgreSQL async operations (to be implemented)
- MySQLStrategy: MySQL async operations (to be implemented)
- SQLiteStrategy: SQLite async operations (to be implemented)

Usage:
    from core.tools.executors.db_strategies import DbStrategyFactory
    
    # Get strategy for a specific database
    strategy = DbStrategyFactory.get_strategy('dynamodb')
    
    # Execute database operation
    result = await strategy.execute_operation(
        args={'operation': 'put_item', 'item': {...}},
        spec=db_tool_spec,
        timeout=30.0
    )

Extending with Custom Strategies:
==================================
To add support for a new database backend:

1. Create a new strategy class implementing IDbOperationStrategy:

    from core.tools.executors.db_strategies import IDbOperationStrategy
    
    class MongoDBStrategy(IDbOperationStrategy):
        async def execute_operation(self, args, spec, timeout):
            # MongoDB implementation
            import motor.motor_asyncio
            client = motor.motor_asyncio.AsyncIOMotorClient(spec.connection_string)
            db = client[spec.database]
            
            operation = args.get('operation')
            if operation == 'find':
                collection = db[args['collection']]
                results = await collection.find(args.get('query', {})).to_list()
                return {
                    'operation': 'find',
                    'results': results,
                    'count': len(results),
                    'status': 'success'
                }

2. Register the strategy with the factory:

    from core.tools.executors.db_strategies import DbStrategyFactory
    
    DbStrategyFactory.register_strategy('mongodb', MongoDBStrategy())

3. Use it like any built-in strategy:

    strategy = DbStrategyFactory.get_strategy('mongodb')
    result = await strategy.execute_operation(args, spec, timeout)

Note:
    Each strategy is responsible for:
    - Establishing database connections
    - Executing operations with proper error handling
    - Converting types as needed for the specific database
    - Returning standardized result dictionaries
"""

from .strategy_interface import IDbOperationStrategy
from .dynamodb_strategy import DynamoDBStrategy
from .strategy_factory import DbStrategyFactory

__all__ = [
    "IDbOperationStrategy",
    "DynamoDBStrategy",
    "DbStrategyFactory",
]

