"""
Database Operation Strategy Interface.

This module defines the abstract base class for all database operation strategies.
Each database provider (DynamoDB, PostgreSQL, MySQL, etc.) implements this interface
to provide database-specific operation handling.

Interface:
==========
- IDbOperationStrategy: Abstract base class for all database strategies

Architecture:
=============
The Strategy pattern allows runtime selection of database operations based on
the driver type. This makes the system extensible - new database providers can
be added without modifying existing code.

Usage:
    from core.tools.executors.db_strategies import IDbOperationStrategy
    
    class CustomDbStrategy(IDbOperationStrategy):
        async def execute_operation(self, args, spec, timeout):
            # Your database-specific implementation
            return {
                'operation': 'custom_query',
                'status': 'success',
                'result': data
            }

Note:
    Strategies should be stateless to support concurrent operations.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class IDbOperationStrategy(ABC):
    """
    Interface for database operation strategies.
    
    This abstract base class defines the contract that all database operation
    strategies must implement. Each concrete strategy handles operations for
    a specific database backend (e.g., DynamoDB, PostgreSQL, MySQL).
    
    Methods:
        execute_operation: Execute a database operation asynchronously
    
    Implementing Classes:
        DynamoDBStrategy: AWS DynamoDB operations
        PostgreSQLStrategy: PostgreSQL operations
        MySQLStrategy: MySQL operations
        SQLiteStrategy: SQLite operations
    
    Example Implementation:
        class MongoDBStrategy(IDbOperationStrategy):
            async def execute_operation(self, args, spec, timeout):
                # Connect to MongoDB
                client = await motor.motor_asyncio.AsyncIOMotorClient(...)
                db = client[spec.database]
                
                # Execute operation
                operation = args.get('operation')
                if operation == 'find':
                    results = await db[args['collection']].find(args.get('query', {}))
                    return {
                        'operation': 'find',
                        'results': list(results),
                        'status': 'success'
                    }
    """
    
    @abstractmethod
    async def execute_operation(
        self,
        args: Dict[str, Any],
        spec: Any,  # DbToolSpec
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Execute the database operation asynchronously.
        
        Args:
            args: Operation arguments containing:
                - operation: Type of operation (e.g., 'put_item', 'query', 'select')
                - Additional operation-specific parameters
            spec: Database tool specification (DbToolSpec) containing:
                - connection_string or connection parameters
                - database name
                - driver type
            timeout: Optional timeout in seconds for the operation
            
        Returns:
            Dictionary containing operation results with keys:
                - operation: The operation that was executed
                - status: 'success' or error information
                - Additional result-specific data
                
        Raises:
            ImportError: If required database library is not installed
            Exception: Database-specific errors from the underlying driver
        
        Example Return:
            {
                'operation': 'query',
                'status': 'success',
                'rows': [...],
                'row_count': 10
            }
        """
        pass

