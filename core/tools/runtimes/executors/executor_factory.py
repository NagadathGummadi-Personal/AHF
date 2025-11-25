"""
Executor Factory for Tools Specification System.

Provides a unified, centralized factory for creating all executor types.
This is the single source of truth for executor creation.
"""

from typing import Union, Dict, Type, Optional, Callable, Any, Awaitable

from .base_executor import BaseToolExecutor
from .function_executors import FunctionToolExecutor, BaseFunctionExecutor
from .http_executors import HttpToolExecutor, BaseHttpExecutor
from .db_executors import BaseDbExecutor, DynamoDBExecutor
from ...spec.tool_types import ToolSpec, FunctionToolSpec, HttpToolSpec, DbToolSpec
from ...enum import ToolType


class ExecutorFactory:
    """
    Unified factory for creating executor instances based on tool specifications.
    
    This factory automatically selects the appropriate executor type based on
    the tool specification and provides a consistent API for all executor types.
    
    Architecture:
    =============
    All executors implement IToolExecutor interface (execute method only).
    The factory manages executor creation and custom executor registration.
    
    Executor Types:
    - Function: Executes user-provided async functions
    - HTTP: Makes HTTP requests with full observability
    - Database: Executes database operations (DynamoDB, PostgreSQL, etc.)
    
    Usage:
        # Function executor
        async def my_func(args):
            return {'result': args['x'] + args['y']}
        
        spec = FunctionToolSpec(...)
        executor = ExecutorFactory.create_executor(spec, func=my_func)
        
        # Database executor
        spec = DynamoDbToolSpec(driver="dynamodb", ...)
        executor = ExecutorFactory.create_executor(spec)
        
        # HTTP executor
        spec = HttpToolSpec(...)
        executor = ExecutorFactory.create_executor(spec)
        
        # Register custom function executor
        ExecutorFactory.register_function_executor('cached', MyCachedExecutor)
        
        # Register custom database executor
        ExecutorFactory.register_db_executor('mongodb', MongoDBExecutor)
        
        # Register custom HTTP executor
        ExecutorFactory.register_http_executor('graphql', GraphQLExecutor)
    """
    
    # Registry for function executor variants
    _function_executors: Dict[str, Type[BaseFunctionExecutor]] = {
        'standard': FunctionToolExecutor,
        'default': FunctionToolExecutor,
    }
    
    # Registry for HTTP executor variants
    _http_executors: Dict[str, Type[BaseHttpExecutor]] = {
        'standard': HttpToolExecutor,
        'default': HttpToolExecutor,
        'rest': HttpToolExecutor,
    }
    
    # Registry for database executors by driver
    _db_executors: Dict[str, Type[BaseDbExecutor]] = {
        'dynamodb': DynamoDBExecutor,
        # Future: 'postgresql', 'mysql', 'mongodb', etc.
    }
    
    @classmethod
    def create_executor(
        cls,
        spec: Union[ToolSpec, FunctionToolSpec, HttpToolSpec, DbToolSpec],
        func: Optional[Callable[[Dict[str, Any]], Awaitable[Any]]] = None,
        executor_type: str = 'standard'
    ) -> BaseToolExecutor:
        """
        Create an executor based on the tool specification.
        
        Args:
            spec: Tool specification (FunctionToolSpec, HttpToolSpec, or DbToolSpec)
            func: Function to execute (required for FunctionToolSpec)
            executor_type: Type/variant of executor to create (default: 'standard')
            
        Returns:
            Configured executor instance implementing IToolExecutor
            
        Raises:
            ValueError: If tool type is not supported or func is missing for function tools
            TypeError: If func is not callable (for function tools)
        
        Example:
            # Function executor
            async def my_func(args):
                return {'result': args['x'] + args['y']}
            
            spec = FunctionToolSpec(...)
            executor = ExecutorFactory.create_executor(spec, func=my_func)
            
            # Database executor (automatically selects based on driver)
            spec = DynamoDbToolSpec(driver="dynamodb", ...)
            executor = ExecutorFactory.create_executor(spec)
            
            # HTTP executor
            spec = HttpToolSpec(...)
            executor = ExecutorFactory.create_executor(spec)
            
            # Custom executor variant
            executor = ExecutorFactory.create_executor(spec, executor_type='cached')
        """
        # Determine executor type based on spec class or tool_type
        if isinstance(spec, FunctionToolSpec) or spec.tool_type == ToolType.FUNCTION:
            if func is None:
                raise ValueError("Function is required for FunctionToolSpec")
            if not callable(func):
                raise TypeError(f"Function must be callable, got {type(func)}")
            
            executor_type_lower = executor_type.lower()
            if executor_type_lower not in cls._function_executors:
                raise ValueError(
                    f"Unknown function executor type: '{executor_type}'. "
                    f"Available types: {list(cls._function_executors.keys())}"
                )
            
            executor_class = cls._function_executors[executor_type_lower]
            return executor_class(spec, func)
        
        elif isinstance(spec, HttpToolSpec) or spec.tool_type == ToolType.HTTP:
            executor_type_lower = executor_type.lower()
            if executor_type_lower not in cls._http_executors:
                raise ValueError(
                    f"Unknown HTTP executor type: '{executor_type}'. "
                    f"Available types: {list(cls._http_executors.keys())}"
                )
            
            executor_class = cls._http_executors[executor_type_lower]
            return executor_class(spec)
        
        elif isinstance(spec, DbToolSpec) or spec.tool_type == ToolType.DB:
            # Get driver from spec
            driver = getattr(spec, 'driver', None)
            
            if not driver:
                # Try to infer driver from spec type
                spec_type = type(spec).__name__.lower()
                if 'dynamodb' in spec_type:
                    driver = 'dynamodb'
                elif 'postgres' in spec_type:
                    driver = 'postgresql'
                elif 'mysql' in spec_type:
                    driver = 'mysql'
                else:
                    raise ValueError(
                        f"Could not infer driver from spec type: {type(spec).__name__}. "
                        "Please specify 'driver' attribute in spec."
                    )
            
            driver_lower = driver.lower()
            if driver_lower not in cls._db_executors:
                raise ValueError(
                    f"Unknown database driver: '{driver}'. "
                    f"Available drivers: {list(cls._db_executors.keys())}"
                )
            
            executor_class = cls._db_executors[driver_lower]
            return executor_class(spec)
        
        else:
            raise ValueError(
                f"Unsupported tool type: {spec.tool_type}. "
                f"Supported types: {ToolType.FUNCTION}, {ToolType.HTTP}, {ToolType.DB}"
            )
    
    # Executor registry for backward compatibility
    _executor_map: Dict[ToolType, Type[BaseToolExecutor]] = {
        ToolType.FUNCTION: FunctionToolExecutor,
        ToolType.HTTP: HttpToolExecutor,
    }
    
    # ==================== Registration Methods ====================
    
    @classmethod
    def register_function_executor(
        cls,
        executor_type: str,
        executor_class: Type[BaseFunctionExecutor]
    ) -> None:
        """
        Register a custom function executor type.
        
        Args:
            executor_type: Name for the executor type (e.g., 'cached', 'streaming')
            executor_class: Executor class that inherits from BaseFunctionExecutor
            
        Raises:
            TypeError: If executor_class doesn't inherit from BaseFunctionExecutor
            ValueError: If executor_type is empty
            
        Example:
            ```python
            from core.tools.runtimes.executors import ExecutorFactory
            from core.tools.runtimes.executors.function_executors import BaseFunctionExecutor
            
            class CachedFunctionExecutor(BaseFunctionExecutor):
                def __init__(self, spec, func):
                    super().__init__(spec, func)
                    self.cache = {}
                
                async def _execute_function(self, args, ctx, timeout):
                    cache_key = str(args)
                    if cache_key in self.cache:
                        return self.cache[cache_key]
                    result = await asyncio.wait_for(
                        self.func(args, ctx), 
                        timeout=timeout
                    )
                    self.cache[cache_key] = result
                    return result
            
            ExecutorFactory.register_function_executor('cached', CachedFunctionExecutor)
            
            # Now use it
            executor = ExecutorFactory.create_executor(
                spec, func=my_func, executor_type='cached'
            )
            ```
        """
        if not executor_type:
            raise ValueError("Executor type cannot be empty")
        
        if not issubclass(executor_class, BaseFunctionExecutor):
            raise TypeError(
                f"Executor class must inherit from BaseFunctionExecutor, "
                f"got {executor_class}"
            )
        
        cls._function_executors[executor_type.lower()] = executor_class
    
    @classmethod
    def register_http_executor(
        cls,
        executor_type: str,
        executor_class: Type[BaseHttpExecutor]
    ) -> None:
        """
        Register a custom HTTP executor type.
        
        Args:
            executor_type: Name for the executor type (e.g., 'graphql', 'websocket')
            executor_class: Executor class that inherits from BaseHttpExecutor
            
        Raises:
            TypeError: If executor_class doesn't inherit from BaseHttpExecutor
            ValueError: If executor_type is empty
            
        Example:
            ```python
            from core.tools.runtimes.executors import ExecutorFactory
            from core.tools.runtimes.executors.http_executors import BaseHttpExecutor
            
            class GraphQLExecutor(BaseHttpExecutor):
                async def _execute_http_request(self, args, ctx, timeout):
                    # GraphQL-specific logic
                    query = args.get('query')
                    variables = args.get('variables', {})
                    async with self.session.post(
                        self.spec.base_url,
                        json={'query': query, 'variables': variables}
                    ) as response:
                        return await response.json()
            
            ExecutorFactory.register_http_executor('graphql', GraphQLExecutor)
            
            # Now use it
            executor = ExecutorFactory.create_executor(
                spec, executor_type='graphql'
            )
            ```
        """
        if not executor_type:
            raise ValueError("Executor type cannot be empty")
        
        if not issubclass(executor_class, BaseHttpExecutor):
            raise TypeError(
                f"Executor class must inherit from BaseHttpExecutor, "
                f"got {executor_class}"
            )
        
        cls._http_executors[executor_type.lower()] = executor_class
    
    @classmethod
    def register_db_executor(
        cls,
        driver: str,
        executor_class: Type[BaseDbExecutor]
    ) -> None:
        """
        Register a custom database executor.
        
        Args:
            driver: Database driver name (case-insensitive, e.g., 'mongodb', 'postgresql')
            executor_class: Executor class (not instance) that extends BaseDbExecutor
            
        Raises:
            TypeError: If executor_class doesn't inherit from BaseDbExecutor
            ValueError: If driver is empty
        
        Example:
            ```python
            from core.tools.runtimes.executors import ExecutorFactory
            from core.tools.runtimes.executors.db_executors import BaseDbExecutor
            
            class MongoDBExecutor(BaseDbExecutor):
                def __init__(self, spec):
                    super().__init__(spec)
                
                async def _execute_db_operation(self, args, ctx, timeout):
                    # MongoDB-specific implementation
                    return {
                        'operation': 'find',
                        'documents': [...],
                        'status': 'success'
                    }
            
            # Register the custom executor
            ExecutorFactory.register_db_executor('mongodb', MongoDBExecutor)
            
            # Now it can be used
            spec = DbToolSpec(driver='mongodb', ...)
            executor = ExecutorFactory.create_executor(spec)
            ```
        
        Note:
            Registering a driver name that already exists will override the
            existing executor. This allows replacing built-in executors with
            custom implementations if needed.
        """
        if not driver:
            raise ValueError("Driver name cannot be empty")
        
        if not issubclass(executor_class, BaseDbExecutor):
            raise TypeError(
                f"Executor class must inherit from BaseDbExecutor, "
                f"got {executor_class}"
            )
        
        cls._db_executors[driver.lower()] = executor_class
    
    @classmethod
    def unregister_function_executor(cls, executor_type: str) -> None:
        """
        Unregister a function executor type.
        
        Args:
            executor_type: Name of the executor type to remove
            
        Raises:
            ValueError: If executor_type doesn't exist or is 'standard'/'default'
        """
        executor_type = executor_type.lower()
        
        if executor_type in ('standard', 'default'):
            raise ValueError(
                f"Cannot unregister built-in executor type: '{executor_type}'"
            )
        
        if executor_type not in cls._function_executors:
            raise ValueError(
                f"Executor type '{executor_type}' is not registered"
            )
        
        del cls._function_executors[executor_type]
    
    @classmethod
    def unregister_http_executor(cls, executor_type: str) -> None:
        """Unregister an HTTP executor type."""
        executor_type = executor_type.lower()
        
        if executor_type in ('standard', 'default', 'rest'):
            raise ValueError(
                f"Cannot unregister built-in executor type: '{executor_type}'"
            )
        
        if executor_type not in cls._http_executors:
            raise ValueError(
                f"Executor type '{executor_type}' is not registered"
            )
        
        del cls._http_executors[executor_type]
    
    @classmethod
    def unregister_db_executor(cls, driver: str) -> None:
        """Unregister a database executor."""
        driver = driver.lower()
        
        if driver in ('dynamodb',):
            raise ValueError(
                f"Cannot unregister built-in driver: '{driver}'"
            )
        
        if driver not in cls._db_executors:
            raise ValueError(
                f"Driver '{driver}' is not registered"
            )
        
        del cls._db_executors[driver]
    
    
    @classmethod
    def list_function_executor_types(cls) -> list[str]:
        """
        List all registered function executor types.
        
        Returns:
            List of registered function executor type names
        """
        return list(cls._function_executors.keys())
    
    @classmethod
    def list_http_executor_types(cls) -> list[str]:
        """
        List all registered HTTP executor types.
        
        Returns:
            List of registered HTTP executor type names
        """
        return list(cls._http_executors.keys())
    
    @classmethod
    def list_db_drivers(cls) -> list[str]:
        """
        List all registered database drivers.
        
        Returns:
            List of registered driver names
        """
        return sorted(cls._db_executors.keys())
    
    @classmethod
    def list_tool_types(cls) -> list[ToolType]:
        """
        List all supported tool types.
        
        Returns:
            List of tool types (FUNCTION, HTTP, DB)
        """
        return [ToolType.FUNCTION, ToolType.HTTP, ToolType.DB]


