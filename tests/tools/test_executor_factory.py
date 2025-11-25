"""
Test suite for Unified ExecutorFactory.

This module tests the unified ExecutorFactory that replaces the separate
FunctionExecutorFactory, HttpExecutorFactory, and DbExecutorFactory.

Test Structure:
===============
1. TestExecutorFactoryFunctionExecutors - Function executor creation and registration
2. TestExecutorFactoryHttpExecutors - HTTP executor creation and registration
3. TestExecutorFactoryDbExecutors - Database executor creation and registration
4. TestExecutorFactoryBackwardCompatibility - Deprecated factory delegation
5. TestExecutorFactoryRegistration - Custom executor registration
6. TestExecutorFactoryListMethods - Listing available types/drivers

Pytest Markers:
===============
- unit: Individual factory tests
- integration: Cross-executor integration tests
- asyncio: Async test support (auto-enabled)

Test Coverage:
==============
- Unified create_executor() for all types
- Custom executor registration (function, HTTP, database)
- Listing methods for types and drivers
- Unregistration methods
- Error handling (missing func, invalid types, etc.)
- Backward compatibility with deprecated factories

Usage:
    pytest tests/tools/test_executor_factory.py -v
    pytest tests/tools/test_executor_factory.py::TestExecutorFactoryFunctionExecutors -v
"""

import pytest
import asyncio
from typing import Dict, Any

# Local imports
from core.tools.runtimes.executors import (
    ExecutorFactory,
    FunctionToolExecutor,
    HttpToolExecutor,
    BaseFunctionExecutor,
    BaseHttpExecutor,
    BaseDbExecutor,
)
from core.tools.spec.tool_types import ToolSpec, FunctionToolSpec, HttpToolSpec, DbToolSpec
from core.tools.spec.tool_context import ToolContext
from core.tools.spec.tool_result import ToolResult
from core.tools.enum import ToolType, ToolReturnType, ToolReturnTarget
from core.tools.spec.tool_parameters import NumericParameter, StringParameter


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def function_spec() -> FunctionToolSpec:
    """Create a function tool spec for testing"""
    return FunctionToolSpec(
        id="test-func-001",
        tool_name="test_function",
        description="Test function tool",
        tool_type=ToolType.FUNCTION,
        return_type=ToolReturnType.JSON,
        return_target=ToolReturnTarget.STEP,
        parameters=[
            NumericParameter(name="x", description="First number", required=True),
            NumericParameter(name="y", description="Second number", required=True),
        ]
    )


@pytest.fixture
def http_spec() -> HttpToolSpec:
    """Create an HTTP tool spec for testing"""
    return HttpToolSpec(
        id="test-http-001",
        tool_name="test_http",
        description="Test HTTP tool",
        tool_type=ToolType.HTTP,
        url="https://api.example.com/test",
        method="GET",
        return_type=ToolReturnType.JSON,
        return_target=ToolReturnTarget.STEP,
        parameters=[]
    )


@pytest.fixture
def db_spec() -> DbToolSpec:
    """Create a database tool spec for testing"""
    return DbToolSpec(
        id="test-db-001",
        tool_name="test_dynamodb",
        description="Test DynamoDB tool",
        tool_type=ToolType.DB,
        driver="dynamodb",
        table_name="test-table",
        region="us-east-1",
        return_type=ToolReturnType.JSON,
        return_target=ToolReturnTarget.STEP,
        parameters=[]
    )


@pytest.fixture
def simple_context() -> ToolContext:
    """Create a simple tool context for testing"""
    return ToolContext(
        user_id="test-user",
        session_id="test-session"
    )


async def sample_function(args: Dict[str, Any]) -> Dict[str, Any]:
    """Sample function for testing"""
    return {'result': args['x'] + args['y']}


# ============================================================================
# FUNCTION EXECUTOR TESTS
# ============================================================================

@pytest.mark.unit
class TestExecutorFactoryFunctionExecutors:
    """
    Test suite for creating function executors via unified factory.
    """
    
    def test_create_function_executor(self, function_spec):
        """Test creating a standard function executor"""
        executor = ExecutorFactory.create_executor(function_spec, func=sample_function)
        
        assert isinstance(executor, FunctionToolExecutor)
        assert executor.spec == function_spec
        assert executor.func == sample_function
    
    def test_create_function_executor_with_type(self, function_spec):
        """Test creating function executor with explicit type"""
        executor = ExecutorFactory.create_executor(
            function_spec, 
            func=sample_function,
            executor_type='standard'
        )
        
        assert isinstance(executor, FunctionToolExecutor)
    
    def test_create_function_executor_missing_func(self, function_spec):
        """Test error when func is missing for function executor"""
        with pytest.raises(ValueError, match="Function is required"):
            ExecutorFactory.create_executor(function_spec)
    
    def test_create_function_executor_non_callable_func(self, function_spec):
        """Test error when func is not callable"""
        with pytest.raises(TypeError, match="must be callable"):
            ExecutorFactory.create_executor(function_spec, func="not_a_function")
    
    def test_create_function_executor_invalid_type(self, function_spec):
        """Test error when executor type is invalid"""
        with pytest.raises(ValueError, match="Unknown function executor type"):
            ExecutorFactory.create_executor(
                function_spec,
                func=sample_function,
                executor_type='nonexistent'
            )
    
    @pytest.mark.asyncio
    async def test_function_executor_execution(self, function_spec, simple_context):
        """Test that created function executor works correctly"""
        executor = ExecutorFactory.create_executor(function_spec, func=sample_function)
        
        result = await executor.execute({'x': 10, 'y': 20}, simple_context)
        
        assert result.content['result'] == 30


# ============================================================================
# HTTP EXECUTOR TESTS
# ============================================================================

@pytest.mark.unit
class TestExecutorFactoryHttpExecutors:
    """
    Test suite for creating HTTP executors via unified factory.
    """
    
    def test_create_http_executor(self, http_spec):
        """Test creating a standard HTTP executor"""
        executor = ExecutorFactory.create_executor(http_spec)
        
        assert isinstance(executor, HttpToolExecutor)
        assert executor.spec == http_spec
    
    def test_create_http_executor_with_type(self, http_spec):
        """Test creating HTTP executor with explicit type"""
        executor = ExecutorFactory.create_executor(
            http_spec,
            executor_type='rest'
        )
        
        assert isinstance(executor, HttpToolExecutor)
    
    def test_create_http_executor_invalid_type(self, http_spec):
        """Test error when HTTP executor type is invalid"""
        with pytest.raises(ValueError, match="Unknown HTTP executor type"):
            ExecutorFactory.create_executor(
                http_spec,
                executor_type='nonexistent'
            )


# ============================================================================
# DATABASE EXECUTOR TESTS
# ============================================================================

@pytest.mark.unit
class TestExecutorFactoryDbExecutors:
    """
    Test suite for creating database executors via unified factory.
    """
    
    def test_create_db_executor(self, db_spec):
        """Test creating a database executor"""
        executor = ExecutorFactory.create_executor(db_spec)
        
        assert isinstance(executor, BaseDbExecutor)
        assert executor.spec == db_spec
    
    def test_create_db_executor_invalid_driver(self):
        """Test error when database driver is invalid"""
        spec = DbToolSpec(
            id="test-db-002",
            tool_name="test_unknown_db",
            description="Test unknown DB",
            tool_type=ToolType.DB,
            driver="unknown_database",
            return_type=ToolReturnType.JSON,
            return_target=ToolReturnTarget.STEP,
            parameters=[]
        )
        
        with pytest.raises(ValueError, match="Unknown database driver"):
            ExecutorFactory.create_executor(spec)
    
    def test_create_db_executor_missing_driver(self):
        """Test error when driver is missing and can't be inferred"""
        spec = DbToolSpec(
            id="test-db-003",
            tool_name="test_db",
            description="Test DB",
            tool_type=ToolType.DB,
            return_type=ToolReturnType.JSON,
            return_target=ToolReturnTarget.STEP,
            parameters=[]
        )
        # Remove driver attribute
        delattr(spec, 'driver')
        
        with pytest.raises(ValueError, match="Could not infer driver"):
            ExecutorFactory.create_executor(spec)


# ============================================================================
# REGISTRATION TESTS
# ============================================================================

@pytest.mark.unit
class TestExecutorFactoryRegistration:
    """
    Test suite for custom executor registration.
    """
    
    def test_register_function_executor(self, function_spec):
        """Test registering a custom function executor"""
        
        class CustomFunctionExecutor(BaseFunctionExecutor):
            async def _execute_function(self, args, ctx, timeout):
                return {'custom': True, 'result': args['x'] * args['y']}
        
        # Register
        ExecutorFactory.register_function_executor('custom', CustomFunctionExecutor)
        
        # Use it
        executor = ExecutorFactory.create_executor(
            function_spec,
            func=sample_function,
            executor_type='custom'
        )
        
        assert isinstance(executor, CustomFunctionExecutor)
        
        # Cleanup
        ExecutorFactory.unregister_function_executor('custom')
    
    def test_register_http_executor(self, http_spec):
        """Test registering a custom HTTP executor"""
        
        class CustomHttpExecutor(BaseHttpExecutor):
            async def _execute_http_request(self, args, ctx, timeout):
                return {'custom': True, 'status': 200}
        
        # Register
        ExecutorFactory.register_http_executor('custom_http', CustomHttpExecutor)
        
        # Use it
        executor = ExecutorFactory.create_executor(
            http_spec,
            executor_type='custom_http'
        )
        
        assert isinstance(executor, CustomHttpExecutor)
        
        # Cleanup
        ExecutorFactory.unregister_http_executor('custom_http')
    
    def test_register_db_executor(self):
        """Test registering a custom database executor"""
        
        class CustomDbExecutor(BaseDbExecutor):
            async def _execute_db_operation(self, args, ctx, timeout):
                return {'custom': True, 'operation': 'test'}
        
        # Register
        ExecutorFactory.register_db_executor('custom_db', CustomDbExecutor)
        
        # Create spec with custom driver
        spec = DbToolSpec(
            id="test-custom-db",
            tool_name="test_custom",
            description="Test custom DB",
            tool_type=ToolType.DB,
            driver="custom_db",
            return_type=ToolReturnType.JSON,
            return_target=ToolReturnTarget.STEP,
            parameters=[]
        )
        
        # Use it
        executor = ExecutorFactory.create_executor(spec)
        
        assert isinstance(executor, CustomDbExecutor)
        
        # Cleanup
        ExecutorFactory.unregister_db_executor('custom_db')
    
    def test_register_function_executor_invalid_class(self):
        """Test error when registering invalid function executor class"""
        
        class NotAnExecutor:
            pass
        
        with pytest.raises(TypeError, match="must inherit from BaseFunctionExecutor"):
            ExecutorFactory.register_function_executor('invalid', NotAnExecutor)
    
    def test_register_function_executor_empty_type(self):
        """Test error when registering with empty type"""
        
        class ValidExecutor(BaseFunctionExecutor):
            async def _execute_function(self, args, ctx, timeout):
                return {}
        
        with pytest.raises(ValueError, match="cannot be empty"):
            ExecutorFactory.register_function_executor('', ValidExecutor)
    
    def test_unregister_builtin_function_executor(self):
        """Test error when trying to unregister built-in executor"""
        with pytest.raises(ValueError, match="Cannot unregister built-in"):
            ExecutorFactory.unregister_function_executor('standard')
    
    def test_unregister_nonexistent_function_executor(self):
        """Test error when trying to unregister nonexistent executor"""
        with pytest.raises(ValueError, match="not registered"):
            ExecutorFactory.unregister_function_executor('nonexistent')


# ============================================================================
# LISTING METHODS TESTS
# ============================================================================

@pytest.mark.unit
class TestExecutorFactoryListMethods:
    """
    Test suite for listing available executor types and drivers.
    """
    
    def test_list_function_executor_types(self):
        """Test listing function executor types"""
        types = ExecutorFactory.list_function_executor_types()
        
        assert 'standard' in types
        assert 'default' in types
        assert isinstance(types, list)
    
    def test_list_http_executor_types(self):
        """Test listing HTTP executor types"""
        types = ExecutorFactory.list_http_executor_types()
        
        assert 'standard' in types
        assert 'default' in types
        assert 'rest' in types
        assert isinstance(types, list)
    
    def test_list_db_drivers(self):
        """Test listing database drivers"""
        drivers = ExecutorFactory.list_db_drivers()
        
        assert 'dynamodb' in drivers
        assert isinstance(drivers, list)
    
    def test_list_tool_types(self):
        """Test listing supported tool types"""
        types = ExecutorFactory.list_tool_types()
        
        assert ToolType.FUNCTION in types
        assert ToolType.HTTP in types
        assert ToolType.DB in types
        assert isinstance(types, list)


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

@pytest.mark.integration
class TestExecutorFactoryIntegration:
    """
    Integration tests for ExecutorFactory with different executor types.
    """
    
    @pytest.mark.asyncio
    async def test_create_and_execute_all_types(
        self,
        function_spec,
        http_spec,
        db_spec,
        simple_context
    ):
        """Test creating and executing all executor types"""
        # Function executor
        func_executor = ExecutorFactory.create_executor(function_spec, func=sample_function)
        func_result = await func_executor.execute({'x': 5, 'y': 10}, simple_context)
        assert func_result.content['result'] == 15
        
        # HTTP executor (may fail without network, just test creation)
        http_executor = ExecutorFactory.create_executor(http_spec)
        assert http_executor is not None
        
        # DB executor (just test creation)
        db_executor = ExecutorFactory.create_executor(db_spec)
        assert db_executor is not None
    
    def test_executor_type_detection(self):
        """Test that factory correctly detects executor type from spec"""
        # Function spec -> Function executor
        func_spec = FunctionToolSpec(
            id="func",
            tool_name="func",
            description="test",
            tool_type=ToolType.FUNCTION,
            return_type=ToolReturnType.JSON,
            return_target=ToolReturnTarget.STEP,
            parameters=[]
        )
        func_executor = ExecutorFactory.create_executor(func_spec, func=sample_function)
        assert isinstance(func_executor, FunctionToolExecutor)
        
        # HTTP spec -> HTTP executor
        http_spec = HttpToolSpec(
            id="http",
            tool_name="http",
            description="test",
            tool_type=ToolType.HTTP,
            url="https://api.example.com/test",
            method="GET",
            return_type=ToolReturnType.JSON,
            return_target=ToolReturnTarget.STEP,
            parameters=[]
        )
        http_executor = ExecutorFactory.create_executor(http_spec)
        assert isinstance(http_executor, HttpToolExecutor)
        
        # DB spec -> DB executor
        db_spec = DbToolSpec(
            id="db",
            tool_name="db",
            description="test",
            tool_type=ToolType.DB,
            driver="dynamodb",
            return_type=ToolReturnType.JSON,
            return_target=ToolReturnTarget.STEP,
            parameters=[]
        )
        db_executor = ExecutorFactory.create_executor(db_spec)
        assert isinstance(db_executor, BaseDbExecutor)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

