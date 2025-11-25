"""
Test suite for Tool Executors.

This module contains comprehensive tests for all tool executor types, covering:
- Function-based tools with custom logic
- HTTP-based tools for API interactions
- Database tools with strategy pattern support
- Full tool context integration (metrics, tracing, caching, etc.)
- Error handling and edge cases
- Idempotency and caching behavior
- Security and validation

Test Structure:
===============
1. TestDivisionTool - Function tool tests (8 tests)
2. TestHttpTool - HTTP API tool tests (6 tests)
3. TestDynamoDBTool - DynamoDB tool tests (5 tests)
4. TestToolIntegration - Integration tests (2 tests)

Pytest Markers:
===============
- unit: Individual tool tests
- integration: Cross-tool integration tests
- asyncio: Async test support (auto-enabled)

Test Coverage:
==============
- Success scenarios with full context
- Error handling (division by zero, validation failures, auth failures)
- Minimal context scenarios (without optional services)
- Idempotency and result caching
- Metrics collection and tracing
- Rate limiting and security checks
- Parallel execution

Usage:
    pytest tests/tools/test_tool_executors.py -v
    pytest tests/tools/test_tool_executors.py::TestDivisionTool -v
"""

import pytest
import asyncio
from typing import Dict, Any
import uuid

# Local imports
from core.tools.runtimes.executors import (
    ExecutorFactory,
    FunctionToolExecutor,
    HttpToolExecutor,
)
from core.tools.spec.tool_context import ToolContext
from core.tools.spec.tool_result import ToolError
from tests.tools.mocks import (
    MockMemory,
    MockMetrics,
    MockTracer,
    MockLimiter,
    MockValidator,
    MockSecurity
)
from tests.tools.tool_implementations import (
    division_function,
    create_division_tool_spec,
    create_http_api_tool_spec,
    create_dynamodb_tool_spec
)


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def base_context() -> ToolContext:
    """Create a base tool context with all services"""
    return ToolContext(
        tenant_id="tenant-test-001",
        user_id="user-test-001",
        session_id=f"session-{uuid.uuid4()}",
        trace_id=f"trace-{uuid.uuid4()}",
        locale="en-US",
        timezone="America/Los_Angeles",
        memory=MockMemory(),
        metrics=MockMetrics(),
        tracer=MockTracer(),
        limiter=MockLimiter(),
        validator=MockValidator(),
        security=MockSecurity()
    )


@pytest.fixture
def minimal_context() -> ToolContext:
    """Create a minimal tool context without optional services"""
    return ToolContext(
        user_id="user-minimal-001",
        session_id=f"session-{uuid.uuid4()}"
    )


# ============================================================================
# DIVISION TOOL TESTS
# ============================================================================

@pytest.mark.unit
class TestDivisionTool:
    """
    Test suite for division function tool.
    
    Tests the FunctionToolExecutor with a division function that handles:
    - Standard division operations
    - Division by zero errors
    - Float and negative number support
    - Error handling and ToolResult formatting
    """
    
    @pytest.mark.asyncio
    async def test_successful_division(self, base_context):
        """Test successful division operation with full context integration."""
        spec = create_division_tool_spec()
        executor = FunctionToolExecutor(spec, division_function)
        
        args = {
            'numerator': 100,
            'denominator': 5
        }
        
        result = await executor.execute(args, base_context)
        
        # Verify result
        assert result.content['result'] == 20.0
        assert result.content['numerator'] == 100
        assert result.content['denominator'] == 5
        assert result.content['operation'] == 'division'
        
        # Verify usage metrics
        assert result.usage is not None
        assert result.usage['input_bytes'] > 0
        assert result.usage['output_bytes'] > 0
        
        # Verify metrics were recorded
        metrics: MockMetrics = base_context.metrics
        assert len(metrics.increments) > 0
        assert len(metrics.timings) > 0
        
        # Verify tracer spans were created
        tracer: MockTracer = base_context.tracer
        assert len(tracer.spans) > 0
        assert any('division.execute' in span['name'] for span in tracer.spans)
        
        # Verify limiter was used
        limiter: MockLimiter = base_context.limiter
        assert len(limiter.acquisitions) > 0
        
        # Verify validator was called
        validator: MockValidator = base_context.validator
        assert len(validator.validations) == 1
        
        # Verify security checks
        security: MockSecurity = base_context.security
        assert len(security.authorizations) == 1
        assert len(security.egress_checks) == 1
    
    @pytest.mark.asyncio
    async def test_division_by_zero(self, base_context):
        """Test division by zero error handling"""
        spec = create_division_tool_spec()
        executor = FunctionToolExecutor(spec, division_function)
        
        args = {
            'numerator': 10,
            'denominator': 0
        }
        
        result = await executor.execute(args, base_context)
        
        # Should return error result, not raise exception
        assert 'error' in result.content
        assert len(result.warnings) > 0
        assert 'Division by zero' in str(result.content['error'])
    
    @pytest.mark.asyncio
    async def test_division_with_floats(self, base_context):
        """Test division with floating point numbers"""
        spec = create_division_tool_spec()
        executor = FunctionToolExecutor(spec, division_function)
        
        args = {
            'numerator': 22.5,
            'denominator': 4.5
        }
        
        result = await executor.execute(args, base_context)
        
        assert result.content['result'] == 5.0
    
    @pytest.mark.asyncio
    async def test_division_with_negative_numbers(self, base_context):
        """Test division with negative numbers"""
        spec = create_division_tool_spec()
        executor = FunctionToolExecutor(spec, division_function)
        
        args = {
            'numerator': -100,
            'denominator': 4
        }
        
        result = await executor.execute(args, base_context)
        
        assert result.content['result'] == -25.0
    
    @pytest.mark.asyncio
    async def test_division_minimal_context(self, minimal_context):
        """Test division with minimal context (no optional services)"""
        spec = create_division_tool_spec()
        executor = FunctionToolExecutor(spec, division_function)
        
        args = {
            'numerator': 50,
            'denominator': 2
        }
        
        result = await executor.execute(args, minimal_context)
        
        # Should still work without optional services
        assert result.content['result'] == 25.0
        assert result.usage is not None
    
    @pytest.mark.asyncio
    async def test_division_idempotency(self, base_context):
        """Test idempotency - same inputs should use cached result"""
        spec = create_division_tool_spec()
        spec.idempotency.enabled = True
        spec.idempotency.persist_result = True
        spec.idempotency.ttl_s = 300
        
        executor = FunctionToolExecutor(spec, division_function)
        
        args = {
            'numerator': 100,
            'denominator': 4
        }
        
        # First execution
        result1 = await executor.execute(args, base_context)
        assert result1.content['result'] == 25.0
        
        # Second execution with same args - should use cache
        result2 = await executor.execute(args, base_context)
        assert result2.content['result'] == 25.0
        
        # Verify cache was used
        memory: MockMemory = base_context.memory
        assert len(memory.storage) > 0  # Should have cached result
    
    @pytest.mark.asyncio
    async def test_division_validation_failure(self):
        """Test behavior when validation fails"""
        ctx = ToolContext(
            user_id="user-test-001",
            session_id="session-test-001",
            validator=MockValidator(should_fail=True, failure_msg="Invalid parameters"),
            metrics=MockMetrics()
        )
        
        spec = create_division_tool_spec()
        executor = FunctionToolExecutor(spec, division_function)
        
        args = {
            'numerator': 10,
            'denominator': 2
        }
        
        result = await executor.execute(args, ctx)
        
        # Should return error result
        assert 'error' in result.content
        assert 'Invalid parameters' in str(result.content['error'])
    
    @pytest.mark.asyncio
    async def test_division_authorization_failure(self):
        """Test behavior when authorization fails"""
        ctx = ToolContext(
            user_id="unauthorized-user",
            session_id="session-test-001",
            security=MockSecurity(should_fail_auth=True, auth_failure_msg="User not authorized"),
            validator=MockValidator(),
            metrics=MockMetrics()
        )
        
        spec = create_division_tool_spec()
        executor = FunctionToolExecutor(spec, division_function)
        
        args = {
            'numerator': 10,
            'denominator': 2
        }
        
        result = await executor.execute(args, ctx)
        
        # Should return error result
        assert 'error' in result.content
        assert 'not authorized' in str(result.content['error']).lower()


# ============================================================================
# HTTP TOOL TESTS
# ============================================================================

@pytest.mark.unit
class TestHttpTool:
    """
    Test suite for HTTP API tool.
    
    Tests the HttpToolExecutor with real API endpoints:
    - GET requests to list items
    - POST requests to create items
    - Custom headers and query parameters
    - HTTP-specific error handling
    - Idempotency for HTTP operations
    """
    
    @pytest.mark.asyncio
    async def test_http_get_items(self, base_context):
        """Test HTTP GET request to list items"""
        spec = create_http_api_tool_spec()
        executor = HttpToolExecutor(spec)
        
        args = {
            'method': 'GET'
        }
        
        result = await executor.execute(args, base_context)
        
        # Verify result structure
        assert 'status_code' in result.content
        assert 'response' in result.content
        assert result.content['status_code'] == 200
        
        # Verify metrics
        metrics: MockMetrics = base_context.metrics
        assert metrics.get_incr_count('tool.executions', {'tool': 'api_items', 'status': 'success'}) > 0
        
        # Verify tracer
        tracer: MockTracer = base_context.tracer
        assert any('api_items.http' in span['name'] for span in tracer.spans)
    
    @pytest.mark.asyncio
    async def test_http_post_create_item(self, base_context):
        """Test HTTP POST request to create item"""
        spec = create_http_api_tool_spec()
        executor = HttpToolExecutor(spec)
        
        args = {
            'method': 'POST',
            'body': {
                'name': 'Test Item',
                'price': 99.99
            }
        }
        
        result = await executor.execute(args, base_context)
        
        # Verify result
        assert 'status_code' in result.content
        assert result.content['status_code'] in [200, 201]
        
        # Verify usage metrics
        assert result.usage is not None
        assert result.usage['input_bytes'] > 0
    
    @pytest.mark.asyncio
    async def test_http_with_custom_headers(self, base_context):
        """Test HTTP request with custom headers"""
        spec = create_http_api_tool_spec()
        executor = HttpToolExecutor(spec)
        
        args = {
            'method': 'GET',
            'headers': {
                'X-Custom-Header': 'test-value'
            }
        }
        
        result = await executor.execute(args, base_context)
        
        # Should complete successfully
        assert 'status_code' in result.content
    
    @pytest.mark.asyncio
    async def test_http_with_query_params(self, base_context):
        """Test HTTP request with query parameters"""
        spec = create_http_api_tool_spec()
        executor = HttpToolExecutor(spec)
        
        args = {
            'method': 'GET',
            'query_params': {
                'limit': '10',
                'offset': '0'
            }
        }
        
        result = await executor.execute(args, base_context)
        
        # Should complete successfully
        assert 'status_code' in result.content
    
    @pytest.mark.asyncio
    async def test_http_idempotency(self, base_context):
        """Test HTTP request idempotency"""
        spec = create_http_api_tool_spec()
        spec.idempotency.enabled = True
        spec.idempotency.persist_result = True
        spec.idempotency.key_fields = ['method', 'body']
        
        executor = HttpToolExecutor(spec)
        
        args = {
            'method': 'POST',
            'body': {
                'name': 'Idempotent Item',
                'price': 49.99
            }
        }
        
        # First call
        result1 = await executor.execute(args, base_context)
        
        # Second call with same args
        result2 = await executor.execute(args, base_context)
        
        # Both should succeed
        assert 'status_code' in result1.content
        assert 'status_code' in result2.content
    
    @pytest.mark.asyncio
    async def test_http_minimal_context(self, minimal_context):
        """Test HTTP tool with minimal context"""
        spec = create_http_api_tool_spec()
        executor = HttpToolExecutor(spec)
        
        args = {
            'method': 'GET'
        }
        
        result = await executor.execute(args, minimal_context)
        
        # Should work without optional services
        assert 'status_code' in result.content


# ============================================================================
# DYNAMODB TOOL TESTS
# ============================================================================

@pytest.mark.unit
class TestDynamoDBTool:
    """
    Test suite for DynamoDB tool.
    
    Tests the DbToolExecutor with DynamoDB strategy:
    - Put item operations to api-test-items table
    - Automatic float to Decimal conversion
    - Full context usage (metrics, tracer, limiter, etc.)
    - Idempotency for database operations
    - Multiple item insertion
    """
    
    @pytest.mark.asyncio
    async def test_dynamodb_put_item_success(self, base_context):
        """Test successful DynamoDB put_item operation"""
        spec = create_dynamodb_tool_spec()
        executor = ExecutorFactory.create_executor(spec)
        
        args = {
            'operation': 'put_item',
            'item': {
                'id': f'item-{uuid.uuid4()}',
                'name': 'Test Item',
                'price': 99.99,
                'category': 'Electronics'
            }
        }
        
        result = await executor.execute(args, base_context)
        
        # Verify result
        assert result.content['status'] == 'success'
        assert result.content['operation'] == 'put_item'
        assert result.content['table_name'] == 'api-test-items'  # Should still be in result
        
        # Verify metrics
        metrics: MockMetrics = base_context.metrics
        assert metrics.get_incr_count('tool.executions', {'tool': 'dynamodb_add_item', 'status': 'success'}) > 0
        
        # Verify tracer
        tracer: MockTracer = base_context.tracer
        assert any('dynamodb_add_item.db' in span['name'] for span in tracer.spans)
        
        # Verify usage
        assert result.usage is not None
    
    @pytest.mark.asyncio
    async def test_dynamodb_put_item_with_all_context(self, base_context):
        """Test DynamoDB with full context including all services"""
        spec = create_dynamodb_tool_spec()
        executor = ExecutorFactory.create_executor(spec)
        
        item_data = {
            'id': f'item-{uuid.uuid4()}',
            'name': 'Premium Item',
            'price': 199.99,
            'description': 'High quality product',
            'stock': 50
        }
        
        args = {
            'operation': 'put_item',
            'item': item_data
        }
        
        result = await executor.execute(args, base_context)
        
        # Verify all services were used
        validator: MockValidator = base_context.validator
        assert len(validator.validations) == 1
        
        security: MockSecurity = base_context.security
        assert len(security.authorizations) == 1
        assert len(security.egress_checks) == 1
        
        limiter: MockLimiter = base_context.limiter
        assert len(limiter.acquisitions) > 0
        
        tracer: MockTracer = base_context.tracer
        assert len(tracer.spans) > 0
        
        metrics: MockMetrics = base_context.metrics
        assert len(metrics.timings) > 0
        assert len(metrics.increments) > 0
    
    @pytest.mark.asyncio
    async def test_dynamodb_idempotency(self, base_context):
        """Test DynamoDB operation idempotency"""
        spec = create_dynamodb_tool_spec()
        spec.idempotency.enabled = True
        spec.idempotency.persist_result = True
        spec.idempotency.key_fields = ['table_name', 'item']
        
        executor = ExecutorFactory.create_executor(spec)
        
        item_data = {
            'id': 'idempotent-item-001',
            'name': 'Idempotent Test',
            'price': 49.99
        }
        
        args = {
            'operation': 'put_item',
            'item': item_data
        }
        
        # First execution
        result1 = await executor.execute(args, base_context)
        assert result1.content['status'] == 'success'
        
        # Second execution - should use cached result
        result2 = await executor.execute(args, base_context)
        assert result2.content['status'] == 'success'
        
        # Verify cache usage
        memory: MockMemory = base_context.memory
        assert len(memory.storage) > 0
    
    @pytest.mark.asyncio
    async def test_dynamodb_minimal_context(self, minimal_context):
        """Test DynamoDB tool with minimal context"""
        spec = create_dynamodb_tool_spec()
        executor = ExecutorFactory.create_executor(spec)
        
        args = {
            'operation': 'put_item',
            'item': {
                'id': f'item-{uuid.uuid4()}',
                'name': 'Minimal Context Test',
                'price': 29.99
            }
        }
        
        result = await executor.execute(args, minimal_context)
        
        # Should work without optional services
        assert result.content['status'] == 'success'
    
    @pytest.mark.asyncio
    async def test_dynamodb_multiple_items(self, base_context):
        """Test adding multiple items to DynamoDB"""
        spec = create_dynamodb_tool_spec()
        executor = ExecutorFactory.create_executor(spec)
        
        items = [
            {'id': f'item-{i}', 'name': f'Item {i}', 'price': i * 10.0}
            for i in range(1, 4)
        ]
        
        results = []
        for item in items:
            args = {
                'operation': 'put_item',
                'item': item
            }
            result = await executor.execute(args, base_context)
            results.append(result)
        
        # All should succeed
        assert all(r.content['status'] == 'success' for r in results)
        
        # Verify metrics show multiple executions
        metrics: MockMetrics = base_context.metrics
        success_count = metrics.get_incr_count(
            'tool.executions',
            {'tool': 'dynamodb_add_item', 'status': 'success'}
        )
        assert success_count >= 3


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

@pytest.mark.integration
class TestToolIntegration:
    """
    Integration tests using multiple tools together.
    
    Tests cross-tool functionality and shared context:
    - All three tools sharing the same ToolContext
    - Parallel execution of multiple operations
    - Shared metrics and tracing across tools
    - Context state management across tool calls
    """
    
    @pytest.mark.asyncio
    async def test_all_tools_with_shared_context(self, base_context):
        """Test all three tools sharing the same context"""
        # 1. Division tool
        division_spec = create_division_tool_spec()
        division_executor = FunctionToolExecutor(division_spec, division_function)
        
        division_result = await division_executor.execute(
            {'numerator': 100, 'denominator': 4},
            base_context
        )
        assert division_result.content['result'] == 25.0
        
        # 2. HTTP tool
        http_spec = create_http_api_tool_spec()
        http_executor = HttpToolExecutor(http_spec)
        
        http_result = await http_executor.execute(
            {'method': 'GET'},
            base_context
        )
        assert 'status_code' in http_result.content
        
        # 3. DynamoDB tool
        db_spec = create_dynamodb_tool_spec()
        db_executor = ExecutorFactory.create_executor(db_spec)
        
        db_result = await db_executor.execute(
            {
                'operation': 'put_item',
                'item': {
                    'id': f'integration-{uuid.uuid4()}',
                    'name': 'Integration Test Item',
                    'price': 79.99
                }
            },
            base_context
        )
        assert db_result.content['status'] == 'success'
        
        # Verify shared context was used by all tools
        metrics: MockMetrics = base_context.metrics
        assert len(metrics.increments) >= 3  # At least one from each tool
        
        tracer: MockTracer = base_context.tracer
        assert len(tracer.spans) >= 3  # At least one from each tool
    
    @pytest.mark.asyncio
    async def test_parallel_execution(self, base_context):
        """Test executing multiple tools in parallel"""
        # Create executors
        division_spec = create_division_tool_spec()
        division_executor = FunctionToolExecutor(division_spec, division_function)
        
        # Execute multiple divisions in parallel
        tasks = [
            division_executor.execute(
                {'numerator': i * 10, 'denominator': 2},
                base_context
            )
            for i in range(1, 6)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Verify all completed
        assert len(results) == 5
        assert all('result' in r.content for r in results)
        
        # Expected results: 5, 10, 15, 20, 25
        expected = [5.0, 10.0, 15.0, 20.0, 25.0]
        actual = [r.content['result'] for r in results]
        assert actual == expected


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

