"""
Executors for Tools Specification System.

This module provides executor implementations organized by type, following
a modular architecture with separate folders for each executor category.

Architecture Overview:
======================
All executors implement IToolExecutor interface (execute method only).
The unified ExecutorFactory provides a consistent API for creating all executor types.

Folder Structure:
=================
- base_executor.py: BaseToolExecutor base class with utility methods
- executor_factory.py: Unified ExecutorFactory for creating all executor types
- noop_executor.py: NoOpExecutor placeholder
- db_executors/: Database-specific executors
- function_executors/: Function-based tool executors
- http_executors/: HTTP-based tool executors
- db_strategies/: Database operation strategies (Strategy pattern)

Executor Hierarchy:
===================
BaseToolExecutor (utility methods)
├── BaseFunctionExecutor (implements execute, defines _execute_function)
│   └── FunctionToolExecutor (implements _execute_function)
├── BaseHttpExecutor (implements execute, defines _execute_http_request)
│   └── HttpToolExecutor (implements _execute_http_request)
└── BaseDbExecutor (implements execute, defines _execute_db_operation)
    └── DynamoDBExecutor (implements _execute_db_operation)

Available Components:
=====================
Core:
- IToolExecutor: Base executor protocol - only defines execute()
- BaseToolExecutor: Base class with utility methods (idempotency, usage, etc.)
- ExecutorFactory: Unified factory for creating all executor types
- NoOpExecutor: Placeholder executor for testing

Executor Types:
- FunctionToolExecutor: Executes user-provided async functions
- HttpToolExecutor: Makes HTTP requests with observability
- DynamoDBExecutor: AWS DynamoDB database operations

Base Classes (for extending):
- BaseFunctionExecutor: Base for function executors
- BaseHttpExecutor: Base for HTTP executors
- BaseDbExecutor: Base for database executors

Usage Examples:
===============

Using ExecutorFactory (Recommended):
====================================
    from core.tools.runtimes.executors import ExecutorFactory
    
    # Function executor
    async def my_func(args):
        return {'result': args['x'] + args['y']}
    
    executor = ExecutorFactory.create_executor(spec, func=my_func)
    result = await executor.execute(args, ctx)
    
    # HTTP executor
    executor = ExecutorFactory.create_executor(http_spec)
    result = await executor.execute(args, ctx)
    
    # Database executor
    executor = ExecutorFactory.create_executor(db_spec)
    result = await executor.execute(args, ctx)

Custom Executors:
=================
    from core.tools.runtimes.executors import ExecutorFactory
    from core.tools.runtimes.executors.function_executors import BaseFunctionExecutor
    
    class CachedFunctionExecutor(BaseFunctionExecutor):
        async def _execute_function(self, args, ctx, timeout):
            # Your cached implementation
            pass
    
    # Register custom executor
    ExecutorFactory.register_function_executor('cached', CachedFunctionExecutor)
    
    # Use it
    executor = ExecutorFactory.create_executor(spec, func=my_func, executor_type='cached')

"""

# Core components
from ...interfaces.tool_interfaces import IToolExecutor
from .base_executor import BaseToolExecutor
from .executor_factory import ExecutorFactory
from .noop_executor import NoOpExecutor

# Re-export commonly used executors for convenience
from .db_executors import (
    BaseDbExecutor,
    DynamoDBExecutor,
)
from .function_executors import (
    BaseFunctionExecutor,
    FunctionToolExecutor,
)
from .http_executors import (
    BaseHttpExecutor,
    HttpToolExecutor,
)

__all__ = [
    # Core
    "IToolExecutor",
    "BaseToolExecutor",
    "ExecutorFactory",
    "NoOpExecutor",
    # Database executors
    "BaseDbExecutor",
    "DynamoDBExecutor",
    # Function executors
    "BaseFunctionExecutor",
    "FunctionToolExecutor",
    # HTTP executors
    "BaseHttpExecutor",
    "HttpToolExecutor",
]

