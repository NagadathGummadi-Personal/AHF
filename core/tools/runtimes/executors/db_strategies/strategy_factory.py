"""
Database Strategy Factory.

This module provides the factory class for creating and managing database
operation strategies. It supports both built-in strategies and custom strategy
registration.

Factory:
========
- DbStrategyFactory: Creates and manages database strategy instances

Built-in Strategies:
====================
- dynamodb: AWS DynamoDB operations
- postgresql/postgres: PostgreSQL operations
- mysql: MySQL operations
- sqlite: SQLite operations

Usage:
    from core.tools.executors.db_strategies import DbStrategyFactory
    
    # Get built-in strategy
    strategy = DbStrategyFactory.get_strategy('dynamodb')
    result = await strategy.execute_operation(args, spec, timeout)
    
    # Register custom strategy
    from my_module import MongoDBStrategy
    DbStrategyFactory.register_strategy('mongodb', MongoDBStrategy())
    
    # Use custom strategy
    strategy = DbStrategyFactory.get_strategy('mongodb')

Note:
    Strategy instances are shared (singleton pattern) for efficiency.
    Each strategy should be stateless to support concurrent operations.
"""

from typing import Dict
from .strategy_interface import IDbOperationStrategy
from .dynamodb_strategy import DynamoDBStrategy


class DbStrategyFactory:
    """
    Factory for creating database operation strategies.
    
    This factory class manages strategy instances and provides methods to
    retrieve strategies by driver name. It supports both built-in strategies
    and custom strategy registration.
    
    Built-in Strategies:
        - dynamodb: AWS DynamoDB operations
        - postgresql/postgres: PostgreSQL operations (to be implemented)
        - mysql: MySQL operations (to be implemented)
        - sqlite: SQLite operations (to be implemented)
    
    Class Methods:
        get_strategy: Retrieve strategy by driver name
        register_strategy: Register a custom strategy
    
    Example:
        # Get built-in strategy
        strategy = DbStrategyFactory.get_strategy('dynamodb')
        
        # Register custom strategy
        class MongoDBStrategy(IDbOperationStrategy):
            async def execute_operation(self, args, spec, timeout):
                # MongoDB implementation
                pass
        
        DbStrategyFactory.register_strategy('mongodb', MongoDBStrategy())
        
        # Use registered strategy
        strategy = DbStrategyFactory.get_strategy('mongodb')
    
    Note:
        Strategy instances are shared (singleton pattern) for efficiency.
        Each strategy should be stateless to support concurrent operations.
    """
    
    _strategies: Dict[str, IDbOperationStrategy] = {
        'dynamodb': DynamoDBStrategy(),
        # Future strategies can be added here as they're implemented:
        # 'postgresql': PostgreSQLStrategy(),
        # 'postgres': PostgreSQLStrategy(),
        # 'mysql': MySQLStrategy(),
        # 'sqlite': SQLiteStrategy(),
    }
    
    @classmethod
    def get_strategy(cls, driver: str) -> IDbOperationStrategy:
        """
        Get the appropriate database strategy for the given driver.
        
        Args:
            driver: Database driver name (e.g., 'dynamodb', 'postgresql', etc.)
                   Case-insensitive.
            
        Returns:
            IDbOperationStrategy: Database operation strategy instance
            
        Raises:
            ValueError: If driver is not supported. Error message includes
                       list of supported drivers.
        
        Example:
            strategy = DbStrategyFactory.get_strategy('DynamoDB')
            result = await strategy.execute_operation(args, spec, timeout)
        """
        driver_lower = driver.lower()
        strategy = cls._strategies.get(driver_lower)
        
        if not strategy:
            raise ValueError(
                f"Unsupported database driver: {driver}. "
                f"Supported drivers: {', '.join(sorted(cls._strategies.keys()))}"
            )
        
        return strategy
    
    @classmethod
    def register_strategy(cls, driver: str, strategy: IDbOperationStrategy):
        """
        Register a custom database strategy.
        
        Allows registration of custom database strategies at runtime. This is
        useful for adding support for additional databases without modifying
        the core codebase.
        
        Args:
            driver: Database driver name (case-insensitive). This will be the
                   identifier used to retrieve the strategy via get_strategy().
            strategy: Strategy implementation instance that implements the
                     IDbOperationStrategy interface.
        
        Example:
            class MongoDBStrategy(IDbOperationStrategy):
                async def execute_operation(self, args, spec, timeout):
                    import motor.motor_asyncio
                    client = motor.motor_asyncio.AsyncIOMotorClient(spec.connection_string)
                    # MongoDB implementation
                    return {'operation': 'find', 'status': 'success'}
            
            # Register the custom strategy
            DbStrategyFactory.register_strategy('mongodb', MongoDBStrategy())
            
            # Now it can be used
            strategy = DbStrategyFactory.get_strategy('mongodb')
            result = await strategy.execute_operation(args, spec, timeout)
        
        Note:
            Registering a driver name that already exists will override the
            existing strategy. This allows replacing built-in strategies with
            custom implementations if needed.
        """
        cls._strategies[driver.lower()] = strategy

