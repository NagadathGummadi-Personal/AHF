"""
Test suite for Idempotency Key Generation Strategies.

This module tests the various idempotency key generation strategies to ensure
they produce correct, deterministic keys and can be configured at tool build time.

Test Structure:
===============
1. TestDefaultStrategy - Default hash-based strategy tests
2. TestFieldBasedStrategy - Field-based strategy tests
3. TestHashBasedStrategy - Configurable hash strategy tests
4. TestCustomStrategy - Custom function strategy tests
5. TestFactory - Factory pattern tests
6. TestIntegration - Integration with tool specs

Pytest Markers:
===============
- unit: Individual strategy tests
- tools: Tool executor related tests
"""

import pytest
from typing import Dict, Any

# Local imports
from core.tools.runtimes.idempotency import (
    IIdempotencyKeyGenerator,
    DefaultIdempotencyKeyGenerator,
    FieldBasedIdempotencyKeyGenerator,
    HashBasedIdempotencyKeyGenerator,
    CustomIdempotencyKeyGenerator,
    IdempotencyKeyGeneratorFactory,
)
from core.tools.spec.tool_types import FunctionToolSpec
from core.tools.spec.tool_context import ToolContext
from core.tools.spec.tool_config import IdempotencyConfig
from core.tools.enum import ToolType


@pytest.mark.unit
@pytest.mark.tools
class TestDefaultStrategy:
    """Test suite for DefaultIdempotencyKeyGenerator."""
    
    def test_deterministic_key_generation(self):
        """Test that same inputs produce same key."""
        generator = DefaultIdempotencyKeyGenerator()
        
        spec = FunctionToolSpec(
            id="test-tool-1",
            tool_name="test",
            description="Test tool",
            tool_type=ToolType.FUNCTION,
            parameters=[]
        )
        spec.idempotency = IdempotencyConfig()
        
        ctx = ToolContext(user_id="user123", session_id="session456")
        args = {"param1": "value1", "param2": "value2"}
        
        key1 = generator.generate_key(args, ctx, spec)
        key2 = generator.generate_key(args, ctx, spec)
        
        assert key1 == key2
        assert len(key1) == 64  # SHA-256 hex = 64 chars
    
    def test_different_args_produce_different_keys(self):
        """Test that different arguments produce different keys."""
        generator = DefaultIdempotencyKeyGenerator()
        
        spec = FunctionToolSpec(
            id="test-tool-1",
            tool_name="test",
            description="Test tool",
            tool_type=ToolType.FUNCTION,
            parameters=[]
        )
        spec.idempotency = IdempotencyConfig()
        
        ctx = ToolContext(user_id="user123", session_id="session456")
        
        key1 = generator.generate_key({"param": "value1"}, ctx, spec)
        key2 = generator.generate_key({"param": "value2"}, ctx, spec)
        
        assert key1 != key2
    
    def test_different_users_produce_different_keys(self):
        """Test that different users produce different keys."""
        generator = DefaultIdempotencyKeyGenerator()
        
        spec = FunctionToolSpec(
            id="test-tool-1",
            tool_name="test",
            description="Test tool",
            tool_type=ToolType.FUNCTION,
            parameters=[]
        )
        spec.idempotency = IdempotencyConfig()
        
        args = {"param": "value"}
        
        ctx1 = ToolContext(user_id="user1", session_id="session")
        ctx2 = ToolContext(user_id="user2", session_id="session")
        
        key1 = generator.generate_key(args, ctx1, spec)
        key2 = generator.generate_key(args, ctx2, spec)
        
        assert key1 != key2
    
    def test_key_fields_respected(self):
        """Test that key_fields configuration is respected."""
        generator = DefaultIdempotencyKeyGenerator()
        
        spec = FunctionToolSpec(
            id="test-tool-1",
            tool_name="test",
            description="Test tool",
            tool_type=ToolType.FUNCTION,
            parameters=[]
        )
        spec.idempotency = IdempotencyConfig(key_fields=['transaction_id'])
        
        ctx = ToolContext(user_id="user123")
        
        # Different args, but same transaction_id
        args1 = {"transaction_id": "tx-123", "amount": 100}
        args2 = {"transaction_id": "tx-123", "amount": 200}
        
        key1 = generator.generate_key(args1, ctx, spec)
        key2 = generator.generate_key(args2, ctx, spec)
        
        assert key1 == key2  # Should be same because transaction_id is same


@pytest.mark.unit
@pytest.mark.tools
class TestFieldBasedStrategy:
    """Test suite for FieldBasedIdempotencyKeyGenerator."""
    
    def test_only_specified_fields_used(self):
        """Test that only specified fields affect the key."""
        generator = FieldBasedIdempotencyKeyGenerator()
        
        spec = FunctionToolSpec(
            id="payment-tool",
            tool_name="payment",
            description="Payment tool",
            tool_type=ToolType.FUNCTION,
            parameters=[]
        )
        spec.idempotency = IdempotencyConfig(key_fields=['transaction_id'])
        
        ctx = ToolContext(user_id="user123")
        
        args1 = {"transaction_id": "tx-456", "amount": 100, "currency": "USD"}
        args2 = {"transaction_id": "tx-456", "amount": 500, "currency": "EUR"}
        
        key1 = generator.generate_key(args1, ctx, spec)
        key2 = generator.generate_key(args2, ctx, spec)
        
        assert key1 == key2  # Same because transaction_id is same
    
    def test_user_context_not_included(self):
        """Test that user context does not affect field-based keys."""
        generator = FieldBasedIdempotencyKeyGenerator()
        
        spec = FunctionToolSpec(
            id="order-tool",
            tool_name="order",
            description="Order tool",
            tool_type=ToolType.FUNCTION,
            parameters=[]
        )
        spec.idempotency = IdempotencyConfig(key_fields=['order_id'])
        
        args = {"order_id": "order-789"}
        
        ctx1 = ToolContext(user_id="user1")
        ctx2 = ToolContext(user_id="user2")
        
        key1 = generator.generate_key(args, ctx1, spec)
        key2 = generator.generate_key(args, ctx2, spec)
        
        assert key1 == key2  # Same because user context not included


@pytest.mark.unit
@pytest.mark.tools
class TestHashBasedStrategy:
    """Test suite for HashBasedIdempotencyKeyGenerator."""
    
    def test_sha256_algorithm(self):
        """Test SHA-256 algorithm produces 64-char hex."""
        generator = HashBasedIdempotencyKeyGenerator(algorithm='sha256')
        
        spec = FunctionToolSpec(
            id="test-tool",
            tool_name="test",
            description="Test",
            tool_type=ToolType.FUNCTION,
            parameters=[]
        )
        spec.idempotency = IdempotencyConfig()
        
        ctx = ToolContext(user_id="user123")
        args = {"param": "value"}
        
        key = generator.generate_key(args, ctx, spec)
        
        assert len(key) == 64  # SHA-256 = 64 hex chars
    
    def test_sha512_algorithm(self):
        """Test SHA-512 algorithm produces 128-char hex."""
        generator = HashBasedIdempotencyKeyGenerator(algorithm='sha512')
        
        spec = FunctionToolSpec(
            id="test-tool",
            tool_name="test",
            description="Test",
            tool_type=ToolType.FUNCTION,
            parameters=[]
        )
        spec.idempotency = IdempotencyConfig()
        
        ctx = ToolContext(user_id="user123")
        args = {"param": "value"}
        
        key = generator.generate_key(args, ctx, spec)
        
        assert len(key) == 128  # SHA-512 = 128 hex chars
    
    def test_exclude_session_context(self):
        """Test that session context can be excluded."""
        generator = HashBasedIdempotencyKeyGenerator(
            include_user_context=True,
            include_session_context=False
        )
        
        spec = FunctionToolSpec(
            id="test-tool",
            tool_name="test",
            description="Test",
            tool_type=ToolType.FUNCTION,
            parameters=[]
        )
        spec.idempotency = IdempotencyConfig()
        
        args = {"param": "value"}
        
        ctx1 = ToolContext(user_id="user123", session_id="session1")
        ctx2 = ToolContext(user_id="user123", session_id="session2")
        
        key1 = generator.generate_key(args, ctx1, spec)
        key2 = generator.generate_key(args, ctx2, spec)
        
        assert key1 == key2  # Same because session not included


@pytest.mark.unit
@pytest.mark.tools
class TestCustomStrategy:
    """Test suite for CustomIdempotencyKeyGenerator."""
    
    def test_custom_function_called(self):
        """Test that custom function is called with correct arguments."""
        calls = []
        
        def custom_key_fn(args, ctx, spec):
            calls.append((args, ctx, spec))
            return "custom-key-123"
        
        generator = CustomIdempotencyKeyGenerator(custom_key_fn)
        
        spec = FunctionToolSpec(
            id="test-tool",
            tool_name="test",
            description="Test",
            tool_type=ToolType.FUNCTION,
            parameters=[]
        )
        
        ctx = ToolContext(user_id="user123")
        args = {"param": "value"}
        
        key = generator.generate_key(args, ctx, spec)
        
        assert key == "custom-key-123"
        assert len(calls) == 1
        assert calls[0][0] == args
        assert calls[0][1] == ctx
        assert calls[0][2] == spec
    
    def test_custom_time_based_key(self):
        """Test custom time-based key generation."""
        from datetime import datetime
        
        def time_based_key(args, ctx, spec):
            timestamp = datetime.now().strftime('%Y-%m-%d-%H')  # hour precision
            return f"{spec.id}:{args.get('request_id')}:{timestamp}"
        
        generator = CustomIdempotencyKeyGenerator(time_based_key)
        
        spec = FunctionToolSpec(
            id="timed-tool",
            tool_name="timed",
            description="Timed tool",
            tool_type=ToolType.FUNCTION,
            parameters=[]
        )
        
        ctx = ToolContext()
        args = {"request_id": "req-456"}
        
        key = generator.generate_key(args, ctx, spec)
        
        assert key.startswith("timed-tool:req-456:")
        assert len(key.split(':')) == 3
    
    def test_non_callable_raises_error(self):
        """Test that non-callable raises TypeError."""
        with pytest.raises(TypeError, match="must be callable"):
            CustomIdempotencyKeyGenerator("not-a-function")


@pytest.mark.unit
@pytest.mark.tools
class TestFactory:
    """Test suite for IdempotencyKeyGeneratorFactory."""
    
    def test_get_default_generator(self):
        """Test getting default generator from factory."""
        generator = IdempotencyKeyGeneratorFactory.get_generator('default')
        
        assert isinstance(generator, DefaultIdempotencyKeyGenerator)
    
    def test_get_field_based_generator(self):
        """Test getting field-based generator from factory."""
        generator = IdempotencyKeyGeneratorFactory.get_generator('field_based')
        
        assert isinstance(generator, FieldBasedIdempotencyKeyGenerator)
    
    def test_get_hash_based_generator(self):
        """Test getting hash-based generator from factory."""
        generator = IdempotencyKeyGeneratorFactory.get_generator('hash_based')
        
        assert isinstance(generator, HashBasedIdempotencyKeyGenerator)
    
    def test_register_custom_generator(self):
        """Test registering and retrieving custom generator."""
        class CustomGen(IIdempotencyKeyGenerator):
            def generate_key(self, args, ctx, spec):
                return "custom-gen-key"
        
        IdempotencyKeyGeneratorFactory.register('my_custom', CustomGen())
        generator = IdempotencyKeyGeneratorFactory.get_generator('my_custom')
        
        assert isinstance(generator, CustomGen)
        
        # Test it works
        spec = FunctionToolSpec(
            id="test",
            tool_name="test",
            description="Test",
            tool_type=ToolType.FUNCTION,
            parameters=[]
        )
        spec.idempotency = IdempotencyConfig()
        
        key = generator.generate_key({}, ToolContext(), spec)
        assert key == "custom-gen-key"
    
    def test_unknown_generator_raises_error(self):
        """Test that unknown generator name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown idempotency key generator"):
            IdempotencyKeyGeneratorFactory.get_generator('nonexistent')


@pytest.mark.integration
@pytest.mark.tools
class TestIntegration:
    """Integration tests with tool specs."""
    
    def test_spec_with_custom_generator(self):
        """Test that tool spec can be configured with custom generator."""
        spec = FunctionToolSpec(
            id="payment-tool-v1",
            tool_name="payment",
            description="Payment processing",
            tool_type=ToolType.FUNCTION,
            parameters=[]
        )
        
        # Configure with field-based generator
        spec.idempotency.enabled = True
        spec.idempotency.key_fields = ['transaction_id']
        spec.idempotency_key_generator = FieldBasedIdempotencyKeyGenerator()
        
        # Verify configuration
        assert spec.idempotency_key_generator is not None
        assert isinstance(spec.idempotency_key_generator, FieldBasedIdempotencyKeyGenerator)
        
        # Test key generation
        ctx = ToolContext(user_id="user123")
        args = {"transaction_id": "tx-789", "amount": 100}
        
        key = spec.idempotency_key_generator.generate_key(args, ctx, spec)
        assert isinstance(key, str)
        assert len(key) > 0
    
    def test_spec_without_generator_uses_default(self):
        """Test that spec without generator defaults to default strategy."""
        from core.tools.runtimes.executors import BaseToolExecutor
        
        spec = FunctionToolSpec(
            id="default-tool-v1",
            tool_name="default",
            description="Uses default",
            tool_type=ToolType.FUNCTION,
            parameters=[]
        )
        
        # No generator specified
        assert spec.idempotency_key_generator is None
        
        # BaseExecutor should use default
        executor = BaseToolExecutor(spec)
        ctx = ToolContext(user_id="user123")
        args = {"param": "value"}
        
        key = executor._generate_idempotency_key(args, ctx)
        
        assert isinstance(key, str)
        assert len(key) == 64  # Default uses SHA-256


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

