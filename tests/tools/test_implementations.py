"""
Test suite for No-Op and Basic Implementation Classes.

This module tests all the no-op and basic implementation classes that provide
default/testing behavior for the tool interfaces. These classes are used when
specific implementations aren't needed or during development/testing.

Test Structure:
===============
1. TestNoOpSecurity - No-op security implementation
2. TestBasicSecurity - Basic security with authorization
3. TestNoOpPolicy - No-op policy implementation
4. TestNoOpEmitter - No-op event emitter
5. TestNoOpMemory - No-op memory/caching
6. TestNoOpMetrics - No-op metrics collection
7. TestNoOpTracer - No-op distributed tracing
8. TestNoOpLimiter - No-op rate limiting
9. TestNoOpValidator - No-op validation
10. TestNoOpExecutor - No-op executor
11. TestImplementationsIntegration - Integration tests

Pytest Markers:
===============
- unit: Individual implementation tests
- implementations: Implementation-specific tests
- asyncio: Async test support (auto-enabled)

Test Coverage:
==============
- All methods return expected values
- No side effects occur
- Proper interface compliance
- Integration with ToolContext
- Drop-in replacement verification

Usage:
    pytest tests/tools/test_implementations.py -v
    pytest tests/tools/test_implementations.py::TestNoOpSecurity -v
"""

import pytest
import asyncio
from typing import Dict, Any

# Local imports
from core.tools import (
    NoOpSecurity,
    BasicSecurity,
    NoOpPolicy,
    NoOpEmitter,
    NoOpMemory,
    NoOpMetrics,
    NoOpTracer,
    NoOpLimiter,
    NoOpValidator,
)
from core.tools.runtimes.executors import NoOpExecutor
from core.tools.spec import (
    ToolContext,
    ToolSpec,
    FunctionToolSpec,
    ToolResult,
    ToolError,
)
from core.tools.spec.tool_parameters import NumericParameter
from core.tools.enum import ToolType, ToolReturnType, ToolReturnTarget


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def sample_spec() -> ToolSpec:
    """Create a sample tool spec for testing"""
    import uuid
    return FunctionToolSpec(
        id=f"test-tool-{uuid.uuid4()}",
        tool_name="test_tool",
        description="Test tool for implementation tests",
        tool_type=ToolType.FUNCTION,
        return_type=ToolReturnType.JSON,
        return_target=ToolReturnTarget.STEP,
        parameters=[
            NumericParameter(
                name="value",
                description="Test value",
                required=True
            )
        ]
    )


@pytest.fixture
def sample_context() -> ToolContext:
    """Create a sample tool context for testing"""
    return ToolContext(
        user_id="test-user-001",
        tenant_id="test-tenant-001",
        session_id="test-session-001",
        trace_id="test-trace-001"
    )


@pytest.fixture
def sample_args() -> Dict[str, Any]:
    """Create sample arguments for testing"""
    return {"value": 42}


# ============================================================================
# SECURITY TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.implementations
@pytest.mark.asyncio
class TestNoOpSecurity:
    """Test suite for NoOpSecurity implementation."""
    
    async def test_authorize_passes(self, sample_context, sample_spec):
        """Test that authorize always passes without error"""
        security = NoOpSecurity()
        
        # Should not raise any exception
        await security.authorize(sample_context, sample_spec)
        
        # Test with various contexts
        for user_id in ["user1", "user2", "unauthorized"]:
            ctx = ToolContext(user_id=user_id)
            await security.authorize(ctx, sample_spec)  # Should all pass
    
    @pytest.mark.asyncio
    async def test_check_egress_passes(self, sample_args, sample_spec):
        """Test that check_egress always passes without error"""
        security = NoOpSecurity()
        
        # Should not raise any exception
        await security.check_egress(sample_args, sample_spec)
        
        # Test with various args
        await security.check_egress({}, sample_spec)
        await security.check_egress({"external_url": "https://evil.com"}, sample_spec)


@pytest.mark.unit
@pytest.mark.implementations
@pytest.mark.asyncio
class TestBasicSecurity:
    """Test suite for BasicSecurity implementation."""
    
    async def test_authorize_passes_with_no_restrictions(self, sample_context, sample_spec):
        """Test that authorization passes when no restrictions are set"""
        security = BasicSecurity()  # No users or roles specified
        
        # Should pass for any user
        await security.authorize(sample_context, sample_spec)
    
    async def test_authorize_passes_for_authorized_user(self, sample_spec):
        """Test that authorization passes for authorized users"""
        security = BasicSecurity(authorized_users=["user1", "user2"])
        
        ctx = ToolContext(user_id="user1")
        await security.authorize(ctx, sample_spec)  # Should pass
    
    async def test_authorize_fails_for_unauthorized_user(self, sample_spec):
        """Test that authorization fails for unauthorized users"""
        security = BasicSecurity(authorized_users=["user1", "user2"])
        
        ctx = ToolContext(user_id="unauthorized")
        
        with pytest.raises(ToolError) as exc_info:
            await security.authorize(ctx, sample_spec)
        
        assert not exc_info.value.retryable
        assert "unauthorized" in str(exc_info.value).lower()
    
    async def test_authorize_checks_permissions(self, sample_spec):
        """Test that authorization checks required permissions"""
        security = BasicSecurity()
        spec_with_perms = sample_spec.model_copy()
        spec_with_perms.permissions = ["read:data", "write:data"]
        
        # User with permissions should pass
        ctx_with_perms = ToolContext(
            user_id="user1",
            auth={"permissions": ["read:data", "write:data", "admin"]}
        )
        await security.authorize(ctx_with_perms, spec_with_perms)
        
        # User without permissions should fail
        ctx_without_perms = ToolContext(
            user_id="user2",
            auth={"permissions": ["read:data"]}  # Missing write:data
        )
        
        with pytest.raises(ToolError) as exc_info:
            await security.authorize(ctx_without_perms, spec_with_perms)
        
        assert "permissions" in str(exc_info.value).lower()
    
    async def test_authorize_checks_roles(self, sample_spec):
        """Test that authorization checks required roles"""
        security = BasicSecurity(authorized_roles=["admin", "developer"])
        
        # User with authorized role should pass
        ctx_admin = ToolContext(
            user_id="user1",
            auth={"user_role": "admin"}
        )
        await security.authorize(ctx_admin, sample_spec)
        
        # User without authorized role should fail
        ctx_viewer = ToolContext(
            user_id="user2",
            auth={"user_role": "viewer"}
        )
        
        with pytest.raises(ToolError) as exc_info:
            await security.authorize(ctx_viewer, sample_spec)
        
        assert "role" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_check_egress_passes(self, sample_args, sample_spec):
        """Test that check_egress currently passes (basic implementation)"""
        security = BasicSecurity()
        
        # Should not raise any exception
        await security.check_egress(sample_args, sample_spec)


# ============================================================================
# POLICY TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.implementations
@pytest.mark.asyncio
class TestNoOpPolicy:
    """Test suite for NoOpPolicy implementation."""
    
    async def test_with_policy_executes_once(self, sample_spec, sample_context):
        """Test that with_policy executes the coroutine once without retry"""
        policy = NoOpPolicy()
        execution_count = 0
        
        async def attempt():
            nonlocal execution_count
            execution_count += 1
            return ToolResult(
                return_type=ToolReturnType.JSON,
                return_target=ToolReturnTarget.STEP,
                content={"count": execution_count}
            )
        
        result = await policy.with_policy(
            attempt_coro_factory=attempt,
            idempotent=True,
            spec=sample_spec,
            ctx=sample_context
        )
        
        assert execution_count == 1
        assert result.content["count"] == 1
    
    async def test_with_policy_propagates_errors(self, sample_spec, sample_context):
        """Test that errors propagate without retry"""
        policy = NoOpPolicy()
        
        async def failing_attempt():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError, match="Test error"):
            await policy.with_policy(
                attempt_coro_factory=failing_attempt,
                idempotent=True,
                spec=sample_spec,
                ctx=sample_context
            )


# ============================================================================
# EMITTER TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.implementations
@pytest.mark.asyncio
class TestNoOpEmitter:
    """Test suite for NoOpEmitter implementation."""
    
    async def test_emit_does_nothing(self):
        """Test that emit completes without side effects"""
        emitter = NoOpEmitter()
        
        # Should not raise any exception
        await emitter.emit("test.event", {"data": "value"})
        await emitter.emit("another.event", {})
        
        # No way to verify it did nothing, but shouldn't error


# ============================================================================
# MEMORY TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.implementations
@pytest.mark.asyncio
class TestNoOpMemory:
    """Test suite for NoOpMemory implementation."""
    
    async def test_get_returns_none(self):
        """Test that get always returns None"""
        memory = NoOpMemory()
        
        assert await memory.get("any-key") is None
        assert await memory.get("another-key") is None
    
    async def test_set_does_nothing(self):
        """Test that set completes but doesn't store"""
        memory = NoOpMemory()
        
        await memory.set("key1", "value1")
        await memory.set("key2", 42, ttl_s=100)
        
        # Values should not be stored
        assert await memory.get("key1") is None
        assert await memory.get("key2") is None
    
    async def test_set_if_absent_returns_false(self):
        """Test that set_if_absent always returns False"""
        memory = NoOpMemory()
        
        result1 = await memory.set_if_absent("key", "value")
        assert result1 is False
        
        result2 = await memory.set_if_absent("key", "value", ttl_s=60)
        assert result2 is False
    
    async def test_delete_does_nothing(self):
        """Test that delete completes without error"""
        memory = NoOpMemory()
        
        await memory.delete("any-key")
        await memory.delete("non-existent-key")
    
    async def test_lock_context_manager(self):
        """Test that lock provides a no-op context manager"""
        memory = NoOpMemory()
        
        async with memory.lock("resource-key"):
            # Should enter and exit without blocking
            pass
        
        async with memory.lock("another-key", ttl_s=30):
            await asyncio.sleep(0.01)  # Some async work


# ============================================================================
# METRICS TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.implementations
@pytest.mark.asyncio
class TestNoOpMetrics:
    """Test suite for NoOpMetrics implementation."""
    
    async def test_incr_does_nothing(self):
        """Test that incr completes without side effects"""
        metrics = NoOpMetrics()
        
        await metrics.incr("counter")
        await metrics.incr("counter", value=5)
        await metrics.incr("counter", value=10, tags={"env": "test"})
    
    async def test_observe_does_nothing(self):
        """Test that observe completes without side effects"""
        metrics = NoOpMetrics()
        
        await metrics.observe("gauge", 42.5)
        await metrics.observe("gauge", 100.0, tags={"env": "prod"})
    
    async def test_timing_ms_does_nothing(self):
        """Test that timing_ms completes without side effects"""
        metrics = NoOpMetrics()
        
        await metrics.timing_ms("latency", 150)
        await metrics.timing_ms("latency", 200, tags={"endpoint": "/api"})


# ============================================================================
# TRACER TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.implementations
@pytest.mark.asyncio
class TestNoOpTracer:
    """Test suite for NoOpTracer implementation."""
    
    async def test_span_context_manager(self):
        """Test that span provides a no-op context manager"""
        tracer = NoOpTracer()
        
        async with tracer.span("operation") as span_id:
            assert span_id == ""  # Should return empty string
            # Do some work
            await asyncio.sleep(0.01)
        
        async with tracer.span("another-op", {"attr": "value"}) as span_id:
            assert span_id == ""


# ============================================================================
# LIMITER TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.implementations
@pytest.mark.asyncio
class TestNoOpLimiter:
    """Test suite for NoOpLimiter implementation."""
    
    async def test_acquire_context_manager(self):
        """Test that acquire provides a no-op context manager"""
        limiter = NoOpLimiter()
        
        async with limiter.acquire("api-calls"):
            # Should not block
            pass
        
        async with limiter.acquire("api-calls", limit=100):
            await asyncio.sleep(0.01)  # Some async work


# ============================================================================
# VALIDATOR TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.implementations
@pytest.mark.asyncio
class TestNoOpValidator:
    """Test suite for NoOpValidator implementation."""
    
    async def test_validate_passes(self, sample_args, sample_spec):
        """Test that validate always passes"""
        validator = NoOpValidator()
        
        # Should not raise any exception
        await validator.validate(sample_args, sample_spec)
        await validator.validate({}, sample_spec)
        await validator.validate({"invalid": "data"}, sample_spec)


# ============================================================================
# EXECUTOR TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.implementations
@pytest.mark.asyncio
class TestNoOpExecutor:
    """Test suite for NoOpExecutor implementation."""
    
    async def test_execute_returns_empty_result(self, sample_spec, sample_context, sample_args):
        """Test that execute returns a no-op result"""
        executor = NoOpExecutor(sample_spec)
        
        result = await executor.execute(sample_args, sample_context)
        
        # Verify result structure
        assert isinstance(result, ToolResult)
        assert result.content["status"] == "noop"
        assert "message" in result.content
        assert result.content["executor"] == "NoOpExecutor"
        assert result.content["tool_name"] == sample_spec.tool_name
    
    async def test_execute_ignores_arguments(self, sample_spec, sample_context):
        """Test that execute ignores different arguments"""
        executor = NoOpExecutor(sample_spec)
        
        result1 = await executor.execute({"a": 1}, sample_context)
        result2 = await executor.execute({"b": 2}, sample_context)
        result3 = await executor.execute({}, sample_context)
        
        # All should return similar no-op results
        assert result1.content["status"] == "noop"
        assert result2.content["status"] == "noop"
        assert result3.content["status"] == "noop"


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.implementations
@pytest.mark.asyncio
class TestImplementationsIntegration:
    """Integration tests for no-op implementations working together."""
    
    async def test_full_noop_context(self, sample_spec):
        """Test ToolContext with all no-op implementations"""
        context = ToolContext(
            user_id="test-user",
            tenant_id="test-tenant",
            session_id="test-session",
            memory=NoOpMemory(),
            metrics=NoOpMetrics(),
            tracer=NoOpTracer(),
            limiter=NoOpLimiter(),
            validator=NoOpValidator(),
            security=NoOpSecurity()
        )
        
        # Use with NoOpExecutor
        executor = NoOpExecutor(sample_spec)
        result = await executor.execute({"value": 42}, context)
        
        assert result.content["status"] == "noop"
    
    async def test_noop_as_drop_in_replacement(self):
        """Test that no-op implementations can replace full implementations"""
        # Create two contexts - one with mocks, one with no-ops
        from tests.tools.mocks import MockMemory, MockMetrics, MockTracer
        
        mock_context = ToolContext(
            user_id="user1",
            memory=MockMemory(),
            metrics=MockMetrics(),
            tracer=MockTracer()
        )
        
        noop_context = ToolContext(
            user_id="user1",
            memory=NoOpMemory(),
            metrics=NoOpMetrics(),
            tracer=NoOpTracer()
        )
        
        # Both should work without errors
        import uuid
        spec = FunctionToolSpec(
            id=f"test-{uuid.uuid4()}",
            tool_name="test",
            description="Test",
            tool_type=ToolType.FUNCTION,
            return_type=ToolReturnType.JSON,
            return_target=ToolReturnTarget.STEP,
            parameters=[]
        )
        
        executor = NoOpExecutor(spec)
        
        result1 = await executor.execute({}, mock_context)
        result2 = await executor.execute({}, noop_context)
        
        # Both should succeed
        assert result1.content["status"] == "noop"
        assert result2.content["status"] == "noop"
    
    def test_all_noop_classes_importable(self):
        """Test that all no-op classes can be imported from core.tools module"""
        from core.tools import (
            NoOpSecurity,
            BasicSecurity,
            NoOpPolicy,
            NoOpEmitter,
            NoOpMemory,
            NoOpMetrics,
            NoOpTracer,
            NoOpLimiter,
            NoOpExecutor,
            NoOpValidator,
        )
        
        # Verify they're all classes
        assert isinstance(NoOpSecurity, type)
        assert isinstance(BasicSecurity, type)
        assert isinstance(NoOpPolicy, type)
        assert isinstance(NoOpEmitter, type)
        assert isinstance(NoOpMemory, type)
        assert isinstance(NoOpMetrics, type)
        assert isinstance(NoOpTracer, type)
        assert isinstance(NoOpLimiter, type)
        assert isinstance(NoOpExecutor, type)
        assert isinstance(NoOpValidator, type)
    
    def test_all_noop_classes_importable_from_runtimes(self):
        """Test that all classes can also be imported from runtimes module"""
        from core.tools.runtimes import (
            NoOpSecurity,
            BasicSecurity,
            NoOpPolicy,
            NoOpEmitter,
            NoOpMemory,
            NoOpMetrics,
            NoOpTracer,
            NoOpLimiter,
            NoOpExecutor,
            NoOpValidator,
        )
        
        # Verify they're all classes
        assert isinstance(NoOpSecurity, type)
        assert isinstance(BasicSecurity, type)
        assert isinstance(NoOpPolicy, type)
        assert isinstance(NoOpEmitter, type)
        assert isinstance(NoOpMemory, type)
        assert isinstance(NoOpMetrics, type)
        assert isinstance(NoOpTracer, type)
        assert isinstance(NoOpLimiter, type)
        assert isinstance(NoOpExecutor, type)
        assert isinstance(NoOpValidator, type)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

