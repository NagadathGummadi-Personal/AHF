"""
Database Executors for Tools Specification System.

This module provides database-specific executors for various database providers,
following a modular architecture with base class and specific implementations.

Strategy Pattern Implementation:
=================================
All executors extend BaseDbExecutor, allowing runtime selection of the appropriate
execution strategy for each database type via ExecutorFactory.

Available Components:
=====================
- BaseDbExecutor: Base implementation with common patterns
- DynamoDBExecutor: AWS DynamoDB operations

Available Executors:
====================
- DynamoDBExecutor: AWS DynamoDB operations
- PostgreSQLExecutor: PostgreSQL operations (future)
- MySQLExecutor: MySQL operations (future)
- SQLiteExecutor: SQLite operations (future)

Architecture:
=============
BaseDbExecutor (Base implementation)
├── DynamoDBExecutor (AWS DynamoDB)
├── PostgreSQLExecutor (PostgreSQL - to be implemented)
├── MySQLExecutor (MySQL - to be implemented)
└── SQLiteExecutor (SQLite - to be implemented)

Usage:
    # Using unified ExecutorFactory (recommended)
    from core.tools.runtimes.executors import ExecutorFactory
    from core.tools.spec.tool_types import DynamoDbToolSpec
    
    spec = DynamoDbToolSpec(
        id="dynamodb-tool-v1",
        tool_name="user_data",
        description="Get user data from DynamoDB",
        driver="dynamodb",
        region="us-west-2",
        table_name="users",
        parameters=[...]
    )
    
    executor = ExecutorFactory.create_executor(spec)
    result = await executor.execute(args, ctx)
    
    # Or create directly
    from core.tools.runtimes.executors.db_executors import DynamoDBExecutor
    
    executor = DynamoDBExecutor(spec)
    result = await executor.execute(args, ctx)

Extending with Custom Executors:
==================================
To add a new database executor:

1. Implement the executor by inheriting from BaseDbExecutor:

    from core.tools.runtimes.executors.db_executors import BaseDbExecutor
    
    class MongoDBExecutor(BaseDbExecutor):
        def __init__(self, spec: DbToolSpec):
            super().__init__(spec)
            # Your initialization
        
        async def _execute_db_operation(self, args, ctx, timeout):
            # Your database-specific logic
            return {
                'operation': 'find',
                'results': your_data,
                'status': 'success'
            }

2. Register with the unified ExecutorFactory:

    from core.tools.runtimes.executors import ExecutorFactory
    
    ExecutorFactory.register_db_executor('mongodb', MongoDBExecutor)

3. Use it:

    spec = DbToolSpec(driver='mongodb', ...)
    executor = ExecutorFactory.create_executor(spec)
    result = await executor.execute(args, ctx)

Note:
    Executors are stateless - they maintain failure counts and state
    across multiple executions via the context and metrics systems.
"""

from .base_db_executor import BaseDbExecutor
from .dynamodb_executor import DynamoDBExecutor

__all__ = [
    "BaseDbExecutor",
    "DynamoDBExecutor",
]


