"""
Comprehensive Custom Tool Scenario Test

Tests all customization points:
- Custom Security Policy (email-based authorization)
- Custom Validator (positive numbers only)
- Custom Executor (with custom execution logic)
- Custom Memory operations
- Circuit breaker behavior
- Retry logic
- Idempotency with session tracking
"""

import pytest
import asyncio
import time
from typing import Dict, Any, Callable, Awaitable

from core.tools.spec import (
    FunctionToolSpec, 
    ToolContext, 
    IdempotencyConfig
)
from core.tools.interfaces import IToolSecurity, IToolValidator, IToolExecutor
from core.tools.spec.tool_types import ToolSpec
from core.tools.runtimes.executors import FunctionToolExecutor, BaseToolExecutor
from core.tools.spec.tool_parameters import NumericParameter
from core.tools.spec.tool_result import ToolResult
from core.tools.enum import ToolType
from tests.tools.mocks import MockMemory, MockMetrics
from core.tools.runtimes.policies import (
    FixedRetryPolicy,
    ExponentialBackoffRetryPolicy,
    StandardCircuitBreakerPolicy
)


# ============================================================================
# CUSTOM SECURITY POLICY - Email-based Authorization
# ============================================================================

class EmailBasedSecurity(IToolSecurity):
    """
    Custom security that only allows specific email address.
    
    Demonstrates custom authorization logic at tool execution time.
    """
    
    def __init__(self, allowed_email: str):
        self.allowed_email = allowed_email
    
    async def authorize(self, ctx: ToolContext, spec: ToolSpec) -> None:
        """Only allow specific email address"""
        if ctx.user_id != self.allowed_email:
            raise PermissionError(
                f"Access denied. User '{ctx.user_id}' is not authorized. "
                f"Only '{self.allowed_email}' is allowed to execute '{spec.tool_name}'."
            )
    
    async def check_egress(self, args: Dict[str, Any], spec: ToolSpec) -> None:
        """No egress restrictions for this test"""
        pass


# ============================================================================
# CUSTOM VALIDATOR - Positive Numbers Only
# ============================================================================

class PositiveNumberValidator(IToolValidator):
    """
    Custom validator ensuring all numeric parameters are > 0.
    
    Demonstrates custom validation logic for business rules.
    """
    
    async def validate(self, args: Dict[str, Any], spec: ToolSpec) -> None:
        """Validate all numeric parameters are positive"""
        for param_name, param_value in args.items():
            if isinstance(param_value, (int, float)):
                if param_value <= 0:
                    raise ValueError(
                        f"Parameter '{param_name}' must be greater than 0. "
                        f"Got: {param_value}"
                    )


# ============================================================================
# CUSTOM EXECUTOR - Logging Executor with Custom Behavior
# ============================================================================

class LoggingFunctionExecutor(BaseToolExecutor, IToolExecutor):
    """
    Custom executor that wraps FunctionToolExecutor with additional logging.
    
    Demonstrates how to create custom executors that extend base functionality
    while maintaining compatibility with the IToolExecutor interface.
    
    This executor:
    - Adds pre/post execution logging
    - Tracks execution count
    - Adds custom metadata to results
    """
    
    def __init__(self, spec: ToolSpec, func: Callable[[Dict[str, Any]], Awaitable[Any]]):
        """
        Initialize custom executor.
        
        Args:
            spec: Tool specification
            func: Async function to execute
        """
        super().__init__(spec)
        self.func = func
        self.execution_count = 0
        self.execution_history = []
    
    async def execute(self, args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
        """
        Execute the function with custom logging and tracking.
        
        This demonstrates how to:
        1. Use BaseToolExecutor's helper methods (_generate_idempotency_key, etc.)
        2. Add custom pre/post execution logic
        3. Wrap existing executors or implement from scratch
        4. Maintain IToolExecutor interface compliance
        """
        import time
        start_time = time.time()
        self.execution_count += 1
        
        # Custom pre-execution logging
        execution_id = f"{self.spec.tool_name}-{self.execution_count}"
        self.execution_history.append({
            'id': execution_id,
            'args': args,
            'timestamp': start_time
        })
        
        print(f"[CustomExecutor] Starting execution #{self.execution_count}: {execution_id}")
        print(f"[CustomExecutor] Args: {args}")
        
        try:
            # Execute the function (similar to FunctionToolExecutor)
            # In a real scenario, you might delegate to FunctionToolExecutor
            # or implement your own execution logic
            
            # Validate if validator is available
            if ctx.validator:
                await ctx.validator.validate(args, self.spec)
            
            # Authorize if security is available
            if ctx.security:
                await ctx.security.authorize(ctx, self.spec)
                await ctx.security.check_egress(args, self.spec)
            
            # Execute the function
            result_content = await self.func(args)
            
            execution_time = time.time() - start_time
            
            # Add custom metadata
            if isinstance(result_content, dict):
                result_content['_executor_metadata'] = {
                    'execution_id': execution_id,
                    'execution_count': self.execution_count,
                    'executor_type': 'LoggingFunctionExecutor'
                }
            
            # Calculate usage using base class helper
            usage = self._calculate_usage(start_time, args, result_content)
            
            # Create result using base class helper
            result = self._create_result(result_content, usage)
            
            print(f"[CustomExecutor] Completed execution #{self.execution_count} in {execution_time:.3f}s")
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            # Calculate usage for error case
            usage = self._calculate_usage(start_time, args, None)
            
            # Create error result
            error_result = self._create_result(
                content={'error': str(e)},
                usage=usage,
                warnings=[f"Execution failed: {str(e)}"]
            )
            
            print(f"[CustomExecutor] Failed execution #{self.execution_count}: {str(e)}")
            
            return error_result


class SimpleCustomExecutor(BaseToolExecutor, IToolExecutor):
    """
    Minimal custom executor example.
    
    Shows the simplest possible custom executor implementation.
    Useful when you need complete control over execution flow.
    """
    
    def __init__(self, spec: ToolSpec, custom_handler: Callable[[Dict[str, Any], ToolContext], Awaitable[Any]]):
        super().__init__(spec)
        self.handler = custom_handler
    
    async def execute(self, args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
        """Execute using custom handler"""
        import time
        start_time = time.time()
        
        try:
            # Call custom handler
            result_content = await self.handler(args, ctx)
            
            # Use base class helpers
            usage = self._calculate_usage(start_time, args, result_content)
            return self._create_result(result_content, usage)
            
        except Exception as e:
            usage = self._calculate_usage(start_time, args, None)
            return self._create_result(
                content={'error': str(e)},
                usage=usage,
                warnings=[str(e)]
            )


# ============================================================================
# TEST SUITE
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestCustomToolScenario:
    """Comprehensive test demonstrating all customization points."""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.call_count = 0
        self.memory = MockMemory()
        self.metrics = MockMetrics()
        
        # Store initial session_id in memory
        asyncio.run(self.memory.set("session_id", "1234"))
    
    async def multiplication_tool_impl(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Multiplication tool implementation with conditional sleep.
        
        - First call: Sleep 2 seconds (simulate slow operation)
        - Subsequent calls: No sleep (simulate fast cached operation)
        """
        self.call_count += 1
        
        # Sleep on first call only
        if self.call_count == 1:
            await asyncio.sleep(2.0)
        
        # Perform multiplication
        result = args['num1'] * args['num2']
        
        # Get session_id from memory and calculate difference
        stored_session = await self.memory.get("session_id")
        current_session = args.get('session_id', '0')
        
        # Session ID arithmetic (for demonstration)
        try:
            session_diff = int(current_session) - int(stored_session)
        except (ValueError, TypeError):
            session_diff = 0
        
        return {
            'product': result,
            'call_count': self.call_count,
            'session_diff': session_diff,
            'stored_session': stored_session,
            'current_session': current_session
        }
    
    async def test_authorized_user_with_valid_params(self):
        """Test successful execution with authorized user and valid parameters."""
        
        # Create spec with custom security and validator
        spec = FunctionToolSpec(
            id="multiply-tool-v1",
            tool_name="multiply",
            description="Multiply two positive numbers",
            tool_type=ToolType.FUNCTION,
            parameters=[
                NumericParameter(name="num1", description="First number", required=True, min=0),
                NumericParameter(name="num2", description="Second number", required=True, min=0),
            ]
        )
        
        # Configure idempotency
        spec.idempotency = IdempotencyConfig(
            enabled=True,
            key_fields=['num1', 'num2'],
            persist_result=True,
            ttl_s=300
        )
        
        # Create context with authorized user
        ctx = ToolContext(
            user_id="nagadathg@zenoti.com",
            session_id="5678",
            memory=self.memory,
            metrics=self.metrics,
            validator=PositiveNumberValidator(),
            security=EmailBasedSecurity(allowed_email="nagadathg@zenoti.com")
        )
        
        # Create executor
        executor = FunctionToolExecutor(spec, self.multiplication_tool_impl)
        
        # Execute tool
        args = {"num1": 5, "num2": 3, "session_id": "5678"}
        result = await executor.execute(args, ctx)
        
        # Assertions
        assert result.content['product'] == 15
        assert result.content['call_count'] == 1
        assert result.content['session_diff'] == 5678 - 1234  # 4444
        assert result.content['stored_session'] == "1234"
        assert result.content['current_session'] == "5678"
        
        # Verify metrics were recorded
        assert self.metrics.get_incr_count('tool.executions') > 0
    
    async def test_unauthorized_user_blocked(self):
        """Test that unauthorized user is blocked by custom security."""
        
        spec = FunctionToolSpec(
            id="multiply-tool-v1",
            tool_name="multiply",
            description="Multiply two positive numbers",
            tool_type=ToolType.FUNCTION,
            parameters=[
                NumericParameter(name="num1", description="First number", required=True),
                NumericParameter(name="num2", description="Second number", required=True),
            ]
        )
        
        # Create context with UNAUTHORIZED user
        ctx = ToolContext(
            user_id="unauthorized@example.com",
            session_id="9999",
            memory=self.memory,
            validator=PositiveNumberValidator(),
            security=EmailBasedSecurity(allowed_email="nagadathg@zenoti.com")
        )
        
        executor = FunctionToolExecutor(spec, self.multiplication_tool_impl)
        
        # Execution should return error result (executor catches exceptions)
        result = await executor.execute({"num1": 5, "num2": 3}, ctx)
        
        # Verify error is in result
        assert 'error' in result.content
        assert 'Access denied' in result.content['error']
        assert 'unauthorized@example.com' in result.content['error']
        assert len(result.warnings) > 0
    
    async def test_negative_number_rejected(self):
        """Test that negative numbers are rejected by custom validator."""
        
        spec = FunctionToolSpec(
            id="multiply-tool-v1",
            tool_name="multiply",
            description="Multiply two positive numbers",
            tool_type=ToolType.FUNCTION,
            parameters=[
                NumericParameter(name="num1", description="First number", required=True),
                NumericParameter(name="num2", description="Second number", required=True),
            ]
        )
        
        ctx = ToolContext(
            user_id="nagadathg@zenoti.com",
            session_id="5678",
            memory=self.memory,
            validator=PositiveNumberValidator(),
            security=EmailBasedSecurity(allowed_email="nagadathg@zenoti.com")
        )
        
        executor = FunctionToolExecutor(spec, self.multiplication_tool_impl)
        
        # Negative number should be rejected (executor catches and returns error)
        result1 = await executor.execute({"num1": -5, "num2": 3}, ctx)
        assert 'error' in result1.content
        assert 'must be greater than 0' in result1.content['error']
        assert 'num1' in result1.content['error']
        
        # Zero should also be rejected
        result2 = await executor.execute({"num1": 5, "num2": 0}, ctx)
        assert 'error' in result2.content
        assert 'must be greater than 0' in result2.content['error']
        assert 'num2' in result2.content['error']
    
    async def test_idempotency_with_cached_result(self):
        """Test idempotency - second call returns cached result without executing."""
        
        spec = FunctionToolSpec(
            id="multiply-tool-v1",
            tool_name="multiply",
            description="Multiply two positive numbers",
            tool_type=ToolType.FUNCTION,
            parameters=[
                NumericParameter(name="num1", description="First number", required=True),
                NumericParameter(name="num2", description="Second number", required=True),
            ]
        )
        
        spec.idempotency = IdempotencyConfig(
            enabled=True,
            key_fields=['num1', 'num2'],
            persist_result=True,
            ttl_s=300
        )
        
        ctx = ToolContext(
            user_id="nagadathg@zenoti.com",
            session_id="5678",
            memory=self.memory,
            validator=PositiveNumberValidator(),
            security=EmailBasedSecurity(allowed_email="nagadathg@zenoti.com")
        )
        
        executor = FunctionToolExecutor(spec, self.multiplication_tool_impl)
        args = {"num1": 7, "num2": 6, "session_id": "5678"}
        
        # First execution - should sleep 2 seconds
        start = time.time()
        result1 = await executor.execute(args, ctx)
        duration1 = time.time() - start
        
        assert result1.content['product'] == 42
        assert result1.content['call_count'] == 1
        assert duration1 >= 2.0  # Should take at least 2 seconds
        
        # Second execution - should return cached result immediately
        start = time.time()
        result2 = await executor.execute(args, ctx)
        duration2 = time.time() - start
        
        assert result2.content['product'] == 42
        assert result2.content['call_count'] == 1  # Same as first (cached)
        assert duration2 < 0.5  # Should be much faster (cached)
        
        # Verify both results are identical
        assert result1.content == result2.content
        
        print("\n[PASS] Idempotency test passed!")
        print(f"   First call: {duration1:.2f}s (with 2s sleep)")
        print(f"   Second call: {duration2:.2f}s (cached, no sleep)")
    
    async def test_memory_operations(self):
        """Test memory operations with session tracking."""
        
        # Verify initial session_id in memory
        stored = await self.memory.get("session_id")
        assert stored == "1234"
        
        # Update session_id
        await self.memory.set("session_id", "5678")
        updated = await self.memory.get("session_id")
        assert updated == "5678"
        
        # Delete session_id
        await self.memory.delete("session_id")
        deleted = await self.memory.get("session_id")
        assert deleted is None
        
        print("\n[PASS] Memory operations test passed!")
    
    async def test_timing_differences_first_vs_second_call(self):
        """Test that first call is slow (2s sleep) and second is fast."""
        
        spec = FunctionToolSpec(
            id="multiply-tool-v1",
            tool_name="multiply",
            description="Multiply two positive numbers",
            tool_type=ToolType.FUNCTION,
            parameters=[
                NumericParameter(name="num1", description="First number", required=True),
                NumericParameter(name="num2", description="Second number", required=True),
            ]
        )
        
        # Disable idempotency to test actual execution time
        spec.idempotency.enabled = False
        
        ctx = ToolContext(
            user_id="nagadathg@zenoti.com",
            session_id="5678",
            memory=self.memory,
            validator=PositiveNumberValidator(),
            security=EmailBasedSecurity(allowed_email="nagadathg@zenoti.com")
        )
        
        executor = FunctionToolExecutor(spec, self.multiplication_tool_impl)
        
        # First call - 2 second sleep
        start = time.time()
        result1 = await executor.execute({"num1": 3, "num2": 4}, ctx)
        duration1 = time.time() - start
        
        assert result1.content['call_count'] == 1
        assert duration1 >= 2.0
        
        # Second call - no sleep
        start = time.time()
        result2 = await executor.execute({"num1": 3, "num2": 4}, ctx)
        duration2 = time.time() - start
        
        assert result2.content['call_count'] == 2
        assert duration2 < 0.5  # Much faster
        
        print("\n[PASS] Timing test passed!")
        print(f"   First call: {duration1:.2f}s (with 2s sleep)")
        print(f"   Second call: {duration2:.2f}s (no sleep)")
    
    async def test_retry_policy_with_transient_failures(self):
        """Test retry policy handles transient failures."""
        
        # Create a failing tool that succeeds on 3rd attempt
        attempt_count = 0
        
        async def failing_then_succeeding_tool(args: Dict[str, Any]) -> Dict[str, Any]:
            nonlocal attempt_count
            attempt_count += 1
            
            if attempt_count < 3:
                # Fail on first 2 attempts
                raise TimeoutError(f"Transient failure (attempt {attempt_count})")
            
            # Succeed on 3rd attempt
            return {
                'result': args['num1'] + args['num2'],
                'attempts': attempt_count
            }
        
        spec = FunctionToolSpec(
            id="retry-tool-v1",
            tool_name="retry_test",
            description="Tool that tests retry policy",
            tool_type=ToolType.FUNCTION,
            parameters=[
                NumericParameter(name="num1", description="First number", required=True),
                NumericParameter(name="num2", description="Second number", required=True),
            ]
        )
        
        # Configure retry policy - max 3 attempts, fixed delay
        spec.retry_policy = FixedRetryPolicy(
            max_attempts=3,
            delay_seconds=0.1,  # Short delay for testing
            jitter=0.0
        )
        
        # Note: Current executor doesn't directly use retry_policy yet
        # This test demonstrates the configuration capability
        # In a full implementation, executor would wrap execution with retry policy
        
        # Manually test the retry policy
        retry_policy = spec.retry_policy
        
        async def execute_once():
            return await failing_then_succeeding_tool({"num1": 5, "num2": 3})
        
        result = await retry_policy.execute_with_retry(execute_once, "retry_test")
        
        assert result['result'] == 8
        assert result['attempts'] == 3  # Should have taken 3 attempts
        
        print("\n[PASS] Retry policy test passed!")
        print(f"   Tool succeeded after {result['attempts']} attempts")
    
    async def test_exponential_backoff_retry_policy(self):
        """Test exponential backoff retry with increasing delays."""
        
        call_times = []
        
        async def track_timing_tool(args: Dict[str, Any]) -> Dict[str, Any]:
            call_times.append(time.time())
            
            if len(call_times) < 3:
                raise ConnectionError(f"Connection failed (attempt {len(call_times)})")
            
            return {'success': True, 'attempts': len(call_times)}
        
        spec = FunctionToolSpec(
            id="exponential-retry-v1",
            tool_name="exponential_retry",
            description="Test exponential backoff",
            tool_type=ToolType.FUNCTION,
            parameters=[]
        )
        
        # Configure exponential backoff: 0.1s, 0.2s, 0.4s delays
        spec.retry_policy = ExponentialBackoffRetryPolicy(
            max_attempts=3,
            base_delay=0.1,
            multiplier=2.0,
            jitter=0.0
        )
        
        retry_policy = spec.retry_policy
        
        async def execute_once():
            return await track_timing_tool({})
        
        start_time = time.time()
        result = await retry_policy.execute_with_retry(execute_once, "exponential_retry")
        total_time = time.time() - start_time
        
        assert result['success'] is True
        assert result['attempts'] == 3
        
        # Verify exponential delays (0.1s + 0.2s = 0.3s minimum)
        assert total_time >= 0.3
        
        # Check delay between attempts
        if len(call_times) >= 2:
            delay1 = call_times[1] - call_times[0]
            assert delay1 >= 0.1  # First retry after ~0.1s
        
        if len(call_times) >= 3:
            delay2 = call_times[2] - call_times[1]
            assert delay2 >= 0.2  # Second retry after ~0.2s
        
        print("\n[PASS] Exponential backoff retry test passed!")
        print(f"   Total time: {total_time:.2f}s")
        print(f"   Attempts: {result['attempts']}")
    
    async def test_circuit_breaker_opens_after_failures(self):
        """Test circuit breaker opens after repeated failures."""
        
        failure_count = 0
        
        async def always_failing_tool(args: Dict[str, Any]) -> Dict[str, Any]:
            nonlocal failure_count
            failure_count += 1
            raise Exception(f"Service unavailable (failure {failure_count})")
        
        spec = FunctionToolSpec(
            id="circuit-breaker-v1",
            tool_name="circuit_test",
            description="Test circuit breaker",
            tool_type=ToolType.FUNCTION,
            parameters=[
                NumericParameter(name="value", description="Test value", required=True),
            ]
        )
        
        # Configure circuit breaker - open after 3 failures
        circuit_breaker = StandardCircuitBreakerPolicy(
            failure_threshold=3,
            recovery_timeout=1
        )
        spec.circuit_breaker_policy = circuit_breaker
        
        # Execute 3 times to open the circuit
        for i in range(3):
            try:
                await circuit_breaker.execute_with_breaker(
                    lambda: always_failing_tool({"value": 1}),
                    "circuit_test"
                )
            except Exception:
                pass  # Expected to fail
        
        assert failure_count == 3
        
        # Verify circuit is open
        state = circuit_breaker.get_state("circuit_test")
        assert state == 'open'
        
        # Try to execute again - should fail immediately without calling function
        failure_count = 0  # Reset counter
        
        with pytest.raises(Exception, match="Circuit breaker is open"):
            await circuit_breaker.execute_with_breaker(
                lambda: always_failing_tool({"value": 1}),
                "circuit_test"
            )
        
        # Function should NOT have been called (circuit is open)
        assert failure_count == 0
        
        print("\n[PASS] Circuit breaker test passed!")
        print("   Circuit opened after 3 failures")
        print("   Subsequent calls blocked without execution")
    
    async def test_circuit_breaker_with_successful_tool(self):
        """Test circuit breaker stays closed for successful operations."""
        
        call_count = 0
        
        async def successful_tool(args: Dict[str, Any]) -> Dict[str, Any]:
            nonlocal call_count
            call_count += 1
            return {'result': args['value'] * 2, 'call': call_count}
        
        spec = FunctionToolSpec(
            id="success-circuit-v1",
            tool_name="success_test",
            description="Test circuit with success",
            tool_type=ToolType.FUNCTION,
            parameters=[
                NumericParameter(name="value", description="Test value", required=True),
            ]
        )
        
        circuit_breaker = StandardCircuitBreakerPolicy(
            failure_threshold=3,
            recovery_timeout=1
        )
        spec.circuit_breaker_policy = circuit_breaker
        
        # Execute successfully multiple times
        for i in range(5):
            result = await circuit_breaker.execute_with_breaker(
                lambda: successful_tool({"value": i}),
                "success_test"
            )
            assert result['result'] == i * 2
        
        assert call_count == 5
        
        # Circuit should remain closed
        state = circuit_breaker.get_state("success_test")
        assert state == 'closed'
        
        print("\n[PASS] Circuit breaker with successful tool test passed!")
        print(f"   Executed {call_count} times successfully")
        print("   Circuit remained closed")
    
    async def test_combined_retry_and_circuit_breaker(self):
        """Test retry policy with circuit breaker for complete resilience."""
        
        attempt_count = 0
        
        async def intermittent_failure_tool(args: Dict[str, Any]) -> Dict[str, Any]:
            nonlocal attempt_count
            attempt_count += 1
            
            # Fail on attempts 1 and 2, succeed on 3
            if attempt_count <= 2:
                raise TimeoutError(f"Timeout on attempt {attempt_count}")
            
            return {'result': 'success', 'total_attempts': attempt_count}
        
        spec = FunctionToolSpec(
            id="combined-resilience-v1",
            tool_name="combined_test",
            description="Test combined retry and circuit breaker",
            tool_type=ToolType.FUNCTION,
            parameters=[]
        )
        
        # Configure both retry and circuit breaker
        spec.retry_policy = FixedRetryPolicy(
            max_attempts=3,
            delay_seconds=0.05,
            jitter=0.0
        )
        
        spec.circuit_breaker_policy = StandardCircuitBreakerPolicy(
            failure_threshold=5,  # Higher threshold for retry test
            recovery_timeout=1
        )
        
        # Test: Retry should handle transient failures before circuit opens
        retry_policy = spec.retry_policy
        circuit_breaker = spec.circuit_breaker_policy
        
        async def execute_with_breaker():
            async def execute_once():
                return await intermittent_failure_tool({})
            return await retry_policy.execute_with_retry(execute_once, "combined_test")
        
        result = await circuit_breaker.execute_with_breaker(
            execute_with_breaker,
            "combined_test"
        )
        
        assert result['result'] == 'success'
        assert result['total_attempts'] == 3
        
        # Circuit should still be closed (didn't reach failure threshold)
        state = circuit_breaker.get_state("combined_test")
        assert state == 'closed'
        
        print("\n[PASS] Combined retry + circuit breaker test passed!")
        print(f"   Retry policy handled {result['total_attempts']} attempts")
        print("   Circuit breaker remained closed")
    
    async def test_custom_executor_with_logging(self):
        """Test custom executor with logging and execution tracking."""
        
        spec = FunctionToolSpec(
            id="custom-executor-v1",
            tool_name="multiply_with_logging",
            description="Multiply with custom executor",
            tool_type=ToolType.FUNCTION,
            parameters=[
                NumericParameter(name="num1", description="First number", required=True),
                NumericParameter(name="num2", description="Second number", required=True),
            ]
        )
        
        ctx = ToolContext(
            user_id="nagadathg@zenoti.com",
            session_id="5678",
            memory=self.memory,
            metrics=self.metrics,
            validator=PositiveNumberValidator(),
            security=EmailBasedSecurity(allowed_email="nagadathg@zenoti.com")
        )
        
        # Use custom executor instead of standard FunctionToolExecutor
        executor = LoggingFunctionExecutor(spec, self.multiplication_tool_impl)
        
        # Execute tool
        args = {"num1": 4, "num2": 5, "session_id": "5678"}
        result = await executor.execute(args, ctx)
        
        # Assertions
        assert result.content['product'] == 20
        assert result.content['call_count'] == 1
        
        # Verify custom metadata was added
        assert '_executor_metadata' in result.content
        assert result.content['_executor_metadata']['executor_type'] == 'LoggingFunctionExecutor'
        assert result.content['_executor_metadata']['execution_count'] == 1
        
        # Verify execution history was tracked
        assert len(executor.execution_history) == 1
        assert executor.execution_count == 1
        
        # Execute again to verify tracking
        result2 = await executor.execute(args, ctx)
        assert executor.execution_count == 2
        assert len(executor.execution_history) == 2
        assert result2.content['_executor_metadata']['execution_count'] == 2
        
        print("\n[PASS] Custom executor with logging test passed!")
        print(f"   Executions tracked: {executor.execution_count}")
        print(f"   History entries: {len(executor.execution_history)}")
    
    async def test_standard_vs_custom_executor_comparison(self):
        """Compare standard FunctionToolExecutor vs custom LoggingFunctionExecutor."""
        
        spec = FunctionToolSpec(
            id="comparison-v1",
            tool_name="compare_executors",
            description="Compare executors",
            tool_type=ToolType.FUNCTION,
            parameters=[
                NumericParameter(name="num1", description="First number", required=True),
                NumericParameter(name="num2", description="Second number", required=True),
            ]
        )
        
        ctx = ToolContext(
            user_id="nagadathg@zenoti.com",
            session_id="5678",
            memory=self.memory,
            metrics=self.metrics,
            validator=PositiveNumberValidator(),
            security=EmailBasedSecurity(allowed_email="nagadathg@zenoti.com")
        )
        
        args = {"num1": 6, "num2": 7, "session_id": "5678"}
        
        # Test with standard executor
        standard_executor = FunctionToolExecutor(spec, self.multiplication_tool_impl)
        standard_result = await standard_executor.execute(args, ctx)
        
        # Test with custom executor
        custom_executor = LoggingFunctionExecutor(spec, self.multiplication_tool_impl)
        custom_result = await custom_executor.execute(args, ctx)
        
        # Both should produce same core result
        assert standard_result.content['product'] == custom_result.content['product']
        assert standard_result.content['product'] == 42
        
        # Custom executor adds extra metadata
        assert '_executor_metadata' in custom_result.content
        assert '_executor_metadata' not in standard_result.content
        
        # Both return ToolResult with same structure
        assert standard_result.return_type == custom_result.return_type
        assert standard_result.return_target == custom_result.return_target
        
        print("\n[PASS] Standard vs custom executor comparison test passed!")
        print("   Both executors produce same core results")
        print("   Custom executor adds additional metadata")
    
    async def test_simple_custom_executor(self):
        """Test minimal custom executor implementation."""
        
        spec = FunctionToolSpec(
            id="simple-executor-v1",
            tool_name="simple_test",
            description="Test simple custom executor",
            tool_type=ToolType.FUNCTION,
            parameters=[
                NumericParameter(name="value", description="Test value", required=True),
            ]
        )
        
        ctx = ToolContext(
            user_id="nagadathg@zenoti.com",
            session_id="5678",
            memory=self.memory,
            metrics=self.metrics
        )
        
        # Define custom handler that receives both args and ctx
        async def custom_handler(args: Dict[str, Any], ctx: ToolContext) -> Dict[str, Any]:
            value = args['value']
            return {
                'doubled': value * 2,
                'user': ctx.user_id,
                'session': ctx.session_id
            }
        
        # Use simple custom executor
        executor = SimpleCustomExecutor(spec, custom_handler)
        result = await executor.execute({"value": 10}, ctx)
        
        # Verify result
        assert result.content['doubled'] == 20
        assert result.content['user'] == "nagadathg@zenoti.com"
        assert result.content['session'] == "5678"
        
        # Verify result structure
        assert result.usage is not None
        assert isinstance(result, ToolResult)
        
        print("\n[PASS] Simple custom executor test passed!")
        print(f"   Result: {result.content}")
    
    async def test_executor_interface_compliance(self):
        """Verify custom executors properly implement IToolExecutor interface."""
        
        spec = FunctionToolSpec(
            id="interface-test-v1",
            tool_name="interface_test",
            description="Test interface compliance",
            tool_type=ToolType.FUNCTION,
            parameters=[
                NumericParameter(name="x", description="Test param", required=True),
            ]
        )
        
        ctx = ToolContext(
            user_id="nagadathg@zenoti.com",
            session_id="5678",
            memory=self.memory
        )
        
        # Verify LoggingFunctionExecutor implements IToolExecutor
        executor1 = LoggingFunctionExecutor(spec, self.multiplication_tool_impl)
        assert isinstance(executor1, IToolExecutor)
        assert isinstance(executor1, BaseToolExecutor)
        
        # Verify SimpleCustomExecutor implements IToolExecutor
        async def handler(args, ctx):
            return {'result': args['x'] * 2}
        
        executor2 = SimpleCustomExecutor(spec, handler)
        assert isinstance(executor2, IToolExecutor)
        assert isinstance(executor2, BaseToolExecutor)
        
        # Both should execute successfully
        result1 = await executor1.execute({"x": 5, "num1": 5, "num2": 1}, ctx)
        result2 = await executor2.execute({"x": 5}, ctx)
        
        # Both should return ToolResult
        assert isinstance(result1, ToolResult)
        assert isinstance(result2, ToolResult)
        
        print("\n[PASS] Executor interface compliance test passed!")
        print("   All custom executors properly implement IToolExecutor")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

