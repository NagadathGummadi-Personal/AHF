#!/usr/bin/env python3
"""
Simple Test Runner for Tools System

This script runs the comprehensive test suite for the tools system
without requiring pytest to be installed.
"""

import asyncio
import sys
import traceback
from typing import Dict, Any, List
import time

# Add the current directory to Python path
sys.path.insert(0, '.')

# Import the tools system components we'll need for testing
from core.tools.tool_types import (
    ToolSpec, ToolParameter, ToolType, ToolReturnType, ToolReturnTarget,
    ToolContext, ToolError, RetryConfig, CircuitBreakerConfig, IdempotencyConfig
)

from core.tools.validators import BasicValidator
from core.tools.executors import FunctionToolExecutor
from core.tools import NoOpMemory, NoOpMetrics, NoOpTracer, NoOpLimiter


class LoggingAdditionTool:
    """Addition tool that logs everything"""

    def __init__(self):
        self.execution_log = []

    async def add_numbers(self, args: Dict[str, Any], ctx: ToolContext) -> Dict[str, Any]:
        """Add two numbers with comprehensive logging"""
        start_time = time.time()

        # Log input parameters
        self.execution_log.append({
            "event": "execution_started",
            "tool_name": "addition_tool",
            "args": args,
            "context": {
                "user_id": ctx.user_id,
                "session_id": ctx.session_id,
                "trace_id": ctx.trace_id
            },
            "timestamp": start_time
        })

        try:
            # Validate inputs
            a = args.get("a")
            b = args.get("b")

            if a is None or b is None:
                raise ToolError("Missing required parameters: 'a' and 'b' are required", retryable=False, code="MISSING_PARAMS")

            # Log parameter validation
            self.execution_log.append({
                "event": "parameters_validated",
                "a": a,
                "b": b,
                "a_type": type(a).__name__,
                "b_type": type(b).__name__,
                "timestamp": time.time()
            })

            # Perform addition with potential error simulation
            if args.get("simulate_error"):
                raise ToolError("Simulated error for testing", retryable=True, code="SIMULATED_ERROR")

            result = float(a) + float(b)

            # Log successful calculation
            self.execution_log.append({
                "event": "calculation_completed",
                "result": result,
                "timestamp": time.time()
            })

            # Log metrics if available
            if ctx.metrics:
                await ctx.metrics.incr("addition_operations", tags={"status": "success"})
                await ctx.metrics.timing_ms("addition_duration", int((time.time() - start_time) * 1000))

            # Log tracing if available
            if ctx.tracer:
                async with ctx.tracer.span("addition_calculation", {"operation": "add", "operands": [a, b]}) as span_id:
                    pass

            return {
                "result": result,
                "operation": "addition",
                "operands": [a, b],
                "execution_time_ms": int((time.time() - start_time) * 1000)
            }

        except Exception as e:
            # Log error
            error_time = time.time()
            self.execution_log.append({
                "event": "execution_error",
                "error": str(e),
                "error_type": type(e).__name__,
                "timestamp": error_time
            })

            # Log metrics for error
            if ctx.metrics:
                await ctx.metrics.incr("addition_operations", tags={"status": "error"})
                await ctx.metrics.timing_ms("addition_duration", int((error_time - start_time) * 1000))

            raise


class SimpleTestRunner:
    """Simple test runner that doesn't require pytest"""

    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failures = []

    def assert_equal(self, actual, expected, message=""):
        self.tests_run += 1
        if actual == expected:
            self.tests_passed += 1
            print(f"✅ PASS: {message}")
        else:
            self.tests_failed += 1
            failure_msg = f"❌ FAIL: {message} | Expected: {expected}, Got: {actual}"
            print(failure_msg)
            self.failures.append(failure_msg)

    def assert_true(self, condition, message=""):
        self.tests_run += 1
        if condition:
            self.tests_passed += 1
            print(f"✅ PASS: {message}")
        else:
            self.tests_failed += 1
            failure_msg = f"❌ FAIL: {message} | Condition was False"
            print(failure_msg)
            self.failures.append(failure_msg)

    def assert_is_instance(self, obj, cls, message=""):
        self.tests_run += 1
        if isinstance(obj, cls):
            self.tests_passed += 1
            print(f"✅ PASS: {message}")
        else:
            self.tests_failed += 1
            failure_msg = f"❌ FAIL: {message} | Expected instance of {cls.__name__}, got {type(obj).__name__}"
            print(failure_msg)
            self.failures.append(failure_msg)

    def run_async_test(self, coro_func):
        """Run an async test function"""
        try:
            asyncio.run(coro_func())
        except Exception as e:
            self.tests_failed += 1
            failure_msg = f"❌ FAIL: Async test failed with exception: {e}"
            print(failure_msg)
            self.failures.append(failure_msg)

    def print_summary(self):
        print("\n" + "="*60)
        print("🧪 TEST SUMMARY")
        print("="*60)
        print(f"Total Tests Run: {self.tests_run}")
        print(f"Tests Passed: ✅ {self.tests_passed}")
        print(f"Tests Failed: ❌ {self.tests_failed}")

        if self.failures:
            print("\n📋 FAILURES:")
            for i, failure in enumerate(self.failures, 1):
                print(f"  {i}. {failure}")

        success_rate = (self.tests_passed / self.tests_run) * 100 if self.tests_run > 0 else 0
        print(f"\n🎯 Success Rate: {success_rate:.1f}%")


def run_tests():
    """Run all tests"""
    print("🚀 Running Tools System Tests")
    print("="*60)

    runner = SimpleTestRunner()

    # Test 1: Tool specification creation
    print("\n📋 Test 1: Tool Specification Creation")
    print("-"*40)

    parameters = [
        ToolParameter(
            name="a",
            type="number",
            description="First number to add",
            required=True,
            examples=[10, 3.14]
        ),
        ToolParameter(
            name="b",
            type="number",
            description="Second number to add",
            required=True,
            examples=[5, 2.71]
        ),
        ToolParameter(
            name="simulate_error",
            type="boolean",
            description="Whether to simulate an error",
            required=False,
            default=False
        )
    ]

    tool_spec = ToolSpec(
        id="addition-tool-v1",
        version="1.0.0",
        tool_name="addition_tool",
        description="Adds two numbers with comprehensive logging",
        tool_type=ToolType.FUNCTION,
        parameters=parameters,
        return_type=ToolReturnType.JSON,
        return_target=ToolReturnTarget.STEP,
        timeout_s=30,
        retry=RetryConfig(max_attempts=2),
        circuit_breaker=CircuitBreakerConfig(enabled=True, failure_threshold=2),
        idempotency=IdempotencyConfig(enabled=True, key_fields=["a", "b"]),
        metrics_tags={"category": "math", "operation": "addition"}
    )

    runner.assert_equal(tool_spec.id, "addition-tool-v1", "Tool spec ID should match")
    runner.assert_equal(tool_spec.tool_name, "addition_tool", "Tool name should match")
    runner.assert_equal(tool_spec.tool_type, ToolType.FUNCTION, "Tool type should be FUNCTION")
    runner.assert_equal(len(tool_spec.parameters), 3, "Should have 3 parameters")
    runner.assert_equal(tool_spec.return_type, ToolReturnType.JSON, "Return type should be JSON")
    runner.assert_equal(tool_spec.timeout_s, 30, "Timeout should be 30 seconds")
    runner.assert_equal(tool_spec.retry.max_attempts, 2, "Retry attempts should be 2")
    runner.assert_true(tool_spec.circuit_breaker.enabled, "Circuit breaker should be enabled")
    runner.assert_equal(tool_spec.idempotency.key_fields, ["a", "b"], "Idempotency key fields should match")

    # Test 2: Parameter validation
    print("\n🔍 Test 2: Parameter Validation")
    print("-"*40)

    validator = BasicValidator()

    # Valid parameters
    valid_args = {"a": 10, "b": 5}
    try:
        asyncio.run(validator.validate(valid_args, tool_spec))
        runner.assert_true(True, "Valid parameters should pass validation")
    except Exception as e:
        runner.assert_true(False, f"Valid parameters should not raise exception: {e}")

    # Missing required parameter
    try:
        asyncio.run(validator.validate({"a": 10}, tool_spec))
        runner.assert_true(False, "Missing parameter should raise exception")
    except ToolError as e:
        runner.assert_true("Missing required parameter" in str(e), "Should detect missing required parameter")

    # Test 3: Successful addition
    print("\n➕ Test 3: Successful Addition")
    print("-"*40)

    async def test_successful_addition():
        logging_tool = LoggingAdditionTool()
        executor = FunctionToolExecutor(tool_spec, logging_tool.add_numbers)

        context = ToolContext(
            user_id="test_user",
            session_id="test_session",
            trace_id="test_trace_123",
            memory=NoOpMemory(),
            metrics=NoOpMetrics(),
            tracer=NoOpTracer(),
            limiter=NoOpLimiter()
        )

        result = await executor.execute({"a": 10, "b": 5}, context)

        runner.assert_equal(result.return_type, ToolReturnType.JSON, "Return type should be JSON")
        runner.assert_equal(result.content["result"], 15.0, "10 + 5 should equal 15")
        runner.assert_equal(result.content["operation"], "addition", "Operation should be addition")
        runner.assert_equal(result.content["operands"], [10, 5], "Operands should match input")

        # Check execution log
        log = logging_tool.execution_log
        runner.assert_true(len(log) >= 3, "Should have at least 3 log entries")
        runner.assert_equal(log[0]["event"], "execution_started", "First event should be execution_started")
        runner.assert_equal(log[-1]["event"], "calculation_completed", "Last event should be calculation_completed")

        print(f"📊 Logged {len(log)} events for successful addition")

    runner.run_async_test(test_successful_addition)

    # Test 4: Addition with floats
    print("\n🔢 Test 4: Float Addition")
    print("-"*40)

    async def test_float_addition():
        logging_tool = LoggingAdditionTool()
        executor = FunctionToolExecutor(tool_spec, logging_tool.add_numbers)
        context = ToolContext(user_id="test_user", session_id="test_session")

        result = await executor.execute({"a": 3.14, "b": 2.86}, context)

        runner.assert_equal(result.content["result"], 6.0, "3.14 + 2.86 should equal 6.0")
        runner.assert_equal(result.content["operands"], [3.14, 2.86], "Operands should be floats")

        print("✅ Float addition test passed")

    runner.run_async_test(test_float_addition)

    # Test 5: Error simulation
    print("\n💥 Test 5: Error Simulation")
    print("-"*40)

    async def test_error_simulation():
        logging_tool = LoggingAdditionTool()
        executor = FunctionToolExecutor(tool_spec, logging_tool.add_numbers)
        context = ToolContext(user_id="test_user", session_id="test_session")

        try:
            await executor.execute({"a": 10, "b": 5, "simulate_error": True}, context)
            runner.assert_true(False, "Simulated error should raise exception")
        except ToolError as e:
            runner.assert_equal(e.code, "SIMULATED_ERROR", "Error code should be SIMULATED_ERROR")
            runner.assert_true(e.retryable, "Error should be retryable")

            # Check execution log includes error
            log = logging_tool.execution_log
            error_events = [entry for entry in log if entry["event"] == "execution_error"]
            runner.assert_true(len(error_events) > 0, "Should log execution error")

            print(f"✅ Error simulation test passed - logged {len(error_events)} error events")

    runner.run_async_test(test_error_simulation)

    # Test 6: Missing parameters
    print("\n❓ Test 6: Missing Parameters")
    print("-"*40)

    async def test_missing_parameters():
        logging_tool = LoggingAdditionTool()
        executor = FunctionToolExecutor(tool_spec, logging_tool.add_numbers)
        context = ToolContext(user_id="test_user", session_id="test_session")

        try:
            await executor.execute({"a": 10}, context)  # Missing 'b'
            runner.assert_true(False, "Missing parameter should raise exception")
        except ToolError as e:
            runner.assert_equal(e.code, "MISSING_PARAMS", "Error code should be MISSING_PARAMS")
            print("✅ Missing parameters test passed")

    runner.run_async_test(test_missing_parameters)

    # Test 7: Context metadata logging
    print("\n📝 Test 7: Context Metadata Logging")
    print("-"*40)

    async def test_context_metadata():
        logging_tool = LoggingAdditionTool()
        executor = FunctionToolExecutor(tool_spec, logging_tool.add_numbers)

        context = ToolContext(
            user_id="user123",
            session_id="session456",
            trace_id="trace789",
            locale="en-US",
            timezone="UTC"
        )

        result = await executor.execute({"a": 1, "b": 2}, context)

        # Check that context was logged
        log = logging_tool.execution_log
        context_log = log[0]["context"]
        runner.assert_equal(context_log["user_id"], "user123", "User ID should be logged")
        runner.assert_equal(context_log["session_id"], "session456", "Session ID should be logged")
        runner.assert_equal(context_log["trace_id"], "trace789", "Trace ID should be logged")

        print("✅ Context metadata logging test passed")

    runner.run_async_test(test_context_metadata)

    # Test 8: Parameter coercion
    print("\n🔄 Test 8: Parameter Type Coercion")
    print("-"*40)

    async def test_parameter_coercion():
        logging_tool = LoggingAdditionTool()
        executor = FunctionToolExecutor(tool_spec, logging_tool.add_numbers)
        context = ToolContext(user_id="test_user", session_id="test_session")

        result = await executor.execute({"a": "10", "b": "5"}, context)

        runner.assert_equal(result.content["result"], 15.0, "String numbers should be coerced to float")
        runner.assert_equal(result.content["operands"], [10, 5], "Coerced operands should be numbers")

        print("✅ Parameter coercion test passed")

    runner.run_async_test(test_parameter_coercion)

    # Test 9: ToolError structure
    print("\n🛠️ Test 9: ToolError Structure")
    print("-"*40)

    error = ToolError("Test error", retryable=True, code="TEST_ERROR")
    runner.assert_equal(str(error), "Test error", "Error message should match")
    runner.assert_true(error.retryable, "Error should be retryable")
    runner.assert_equal(error.code, "TEST_ERROR", "Error code should match")

    error2 = ToolError("Validation failed", retryable=False, code="VALIDATION_ERROR")
    runner.assert_true(not error2.retryable, "Validation error should not be retryable")

    error3 = ToolError("Default error")
    runner.assert_true(not error3.retryable, "Default error should not be retryable")
    runner.assert_equal(error3.code, "TOOL_ERROR", "Default error code should be TOOL_ERROR")

    print("✅ ToolError structure tests passed")

    # Test 10: Array parameter logging (comprehensive test)
    print("\n📊 Test 10: Array Parameter Comprehensive Logging")
    print("-"*40)

    # Create tool spec with array parameters
    array_parameters = [
        ToolParameter(
            name="operation",
            type="string",
            description="Operation to perform",
            required=True,
            enum=["add", "subtract", "multiply", "divide"]
        ),
        ToolParameter(
            name="values",
            type="array",
            description="Array of numbers",
            required=True,
            items=ToolParameter(
                name="value",
                type="number",
                description="A number"
            ),
            min_items=2
        )
    ]

    array_tool_spec = ToolSpec(
        id="array-operations-v1",
        version="1.0.0",
        tool_name="array_operations",
        description="Tool that logs every aspect of array operations",
        tool_type=ToolType.FUNCTION,
        parameters=array_parameters,
        return_type=ToolReturnType.JSON,
        return_target=ToolReturnTarget.STEP,
        timeout_s=60,
        metrics_tags={"category": "array", "level": "comprehensive"}
    )

    class ArrayOperationTool:
        def __init__(self):
            self.log = []

        async def operate(self, args: Dict[str, Any], ctx: ToolContext) -> Dict[str, Any]:
            operation = args["operation"]
            values = args["values"]

            # Log array processing
            self.log.append({
                "event": "array_processing_started",
                "operation": operation,
                "array_length": len(values),
                "array_sum": sum(values),
                "timestamp": time.time()
            })

            if operation == "add":
                result = sum(values)
            elif operation == "multiply":
                result = 1
                for v in values:
                    result *= v
            else:
                raise ToolError(f"Unsupported operation: {operation}", retryable=False)

            self.log.append({
                "event": "array_processing_completed",
                "result": result,
                "timestamp": time.time()
            })

            return {"result": result, "operation": operation, "processed_values": values}

    async def test_array_operations():
        tool = ArrayOperationTool()
        executor = FunctionToolExecutor(array_tool_spec, tool.operate)
        context = ToolContext(user_id="test_user", session_id="test_session")

        result = await executor.execute({
            "operation": "add",
            "values": [1, 2, 3, 4, 5]
        }, context)

        runner.assert_equal(result.content["result"], 15, "Array addition should sum to 15")
        runner.assert_equal(result.content["operation"], "add", "Operation should be add")
        runner.assert_equal(result.content["processed_values"], [1, 2, 3, 4, 5], "Values should match input")

        # Check comprehensive logging
        runner.assert_true(len(tool.log) >= 2, "Should have at least 2 log entries")
        runner.assert_equal(tool.log[0]["event"], "array_processing_started", "First event should be array_processing_started")
        runner.assert_equal(tool.log[1]["event"], "array_processing_completed", "Last event should be array_processing_completed")

        print(f"✅ Array operations test passed - logged {len(tool.log)} events")

    runner.run_async_test(test_array_operations)

    # Print final summary
    runner.print_summary()

    return runner.tests_failed == 0


if __name__ == "__main__":
    success = run_tests()
    if success:
        print("\n🎉 All tests passed! The tools system is working correctly.")
        sys.exit(0)
    else:
        print("\n💥 Some tests failed. Please check the output above.")
        sys.exit(1)
