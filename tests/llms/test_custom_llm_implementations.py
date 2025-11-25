"""
Tests for Custom LLM Implementations.

These tests demonstrate and validate the ability to create and register
custom LLM implementations for existing models.
"""

import pytest
from typing import Dict, Any, List, AsyncIterator

from core.llms.providers.base.implementation import BaseLLM
from core.llms.providers.base.connector import BaseConnector
from core.llms.spec.llm_result import LLMResponse, LLMStreamChunk, LLMUsage
from core.llms.spec.llm_context import LLMContext, create_context
from core.llms.spec.llm_schema import ModelMetadata
from core.llms.runtimes.model_registry import reset_registry
from core.llms.runtimes.llm_implementation_registry import (
    get_implementation_registry,
    reset_implementation_registry
)
from core.llms.enum import FinishReason, LLMProvider, ModelFamily, InputMediaType, OutputMediaType
from core.llms.exceptions import UnsupportedOperationError


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def test_metadata():
    """Create test model metadata."""
    return ModelMetadata(
        model_name="test-gpt-4.1-mini",
        provider=LLMProvider.AZURE,
        model_family=ModelFamily.AZURE_GPT_4_1_MINI,
        display_name="Test GPT-4.1 Mini",
        max_context_length=128000,
        max_output_tokens=16384
    )


@pytest.fixture
def mock_connector():
    """Create mock connector for testing."""
    class MockConnector(BaseConnector):
        def __init__(self, config: Dict[str, Any]):
            super().__init__(config)
            self.call_count = 0
            self.last_payload = None
        
        async def request(
            self,
            endpoint: str,
            payload: Dict[str, Any],
            **kwargs: Any
        ) -> Dict[str, Any]:
            """Mock request that returns test data."""
            self.call_count += 1
            self.last_payload = payload
            
            return {
                "content": "Mock response",
                "role": "assistant",
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "total_tokens": 15
                }
            }
        
        async def test_connection(self) -> bool:
            """Mock connection test."""
            return True
    
    return MockConnector({"timeout": 30})


@pytest.fixture
def test_context():
    """Create test context."""
    return create_context(user_id="test-user", session_id="test-session")


@pytest.fixture(autouse=True)
def reset_registries():
    """Reset registries before and after each test."""
    reset_registry()
    reset_implementation_registry()
    yield
    reset_registry()
    reset_implementation_registry()


# ============================================================================
# Custom Implementation Classes
# ============================================================================

class CustomLoggingLLM(BaseLLM):
    """Custom implementation with logging capabilities."""
    
    def __init__(self, metadata: ModelMetadata, connector: BaseConnector):
        super().__init__(metadata, connector)
        self.call_log = []
    
    async def get_answer(
        self,
        messages: List[Dict[str, Any]],
        ctx: LLMContext,
        **kwargs: Any
    ) -> LLMResponse:
        """Enhanced get_answer with logging."""
        self.call_log.append({
            "method": "get_answer",
            "messages": len(messages),
            "params": kwargs
        })
        
        # Use base validation
        self._validate_messages(messages)
        params = self._merge_parameters(kwargs)
        
        # Call connector
        response = await self.connector.request(
            endpoint="chat/completions",
            payload={"messages": messages, **params}
        )
        
        return LLMResponse(
            content=response.get("content", ""),
            role="assistant",
            finish_reason=FinishReason.STOP,
            usage=LLMUsage(
                prompt_tokens=response.get("usage", {}).get("prompt_tokens", 0),
                completion_tokens=response.get("usage", {}).get("completion_tokens", 0)
            )
        )
    
    async def stream_answer(
        self,
        messages: List[Dict[str, Any]],
        ctx: LLMContext,
        **kwargs: Any
    ) -> AsyncIterator[LLMStreamChunk]:
        """Enhanced stream_answer with logging."""
        self.call_log.append({
            "method": "stream_answer",
            "messages": len(messages),
            "params": kwargs
        })
        
        yield LLMStreamChunk(content="Logged ", is_final=False)
        yield LLMStreamChunk(content="response", is_final=True)


class CachedLLM(BaseLLM):
    """Custom implementation with response caching."""
    
    def __init__(self, metadata: ModelMetadata, connector: BaseConnector):
        super().__init__(metadata, connector)
        self._cache: Dict[str, LLMResponse] = {}
        self.cache_hits = 0
        self.cache_misses = 0
    
    def _get_cache_key(self, messages: List[Dict[str, Any]], params: Dict[str, Any]) -> str:
        """Generate cache key."""
        import json
        return json.dumps({"messages": messages, "params": params}, sort_keys=True)
    
    async def get_answer(
        self,
        messages: List[Dict[str, Any]],
        ctx: LLMContext,
        **kwargs: Any
    ) -> LLMResponse:
        """get_answer with caching."""
        params = self._merge_parameters(kwargs)
        cache_key = self._get_cache_key(messages, params)
        
        if cache_key in self._cache:
            self.cache_hits += 1
            return self._cache[cache_key]
        
        self.cache_misses += 1
        
        # Make actual call
        response_data = await self.connector.request(
            endpoint="chat/completions",
            payload={"messages": messages, **params}
        )
        
        response = LLMResponse(
            content=response_data.get("content", ""),
            role="assistant",
            finish_reason=FinishReason.STOP,
            usage=LLMUsage(
                prompt_tokens=response_data.get("usage", {}).get("prompt_tokens", 0),
                completion_tokens=response_data.get("usage", {}).get("completion_tokens", 0)
            )
        )
        
        self._cache[cache_key] = response
        return response
    
    async def stream_answer(
        self,
        messages: List[Dict[str, Any]],
        ctx: LLMContext,
        **kwargs: Any
    ) -> AsyncIterator[LLMStreamChunk]:
        """Streaming not cached."""
        yield LLMStreamChunk(content="Streaming...", is_final=True)


class CustomValidationLLM(BaseLLM):
    """Custom implementation with overridden validation."""
    
    def __init__(self, metadata: ModelMetadata, connector: BaseConnector):
        super().__init__(metadata, connector)
        self.validation_log = []
    
    def _validate_messages(self, messages: List[Dict[str, Any]]) -> None:
        """Custom validation that requires a 'priority' field."""
        self.validation_log.append("Custom validation called")
        
        # Custom validation: Allow empty messages list
        if not messages:
            self.validation_log.append("Empty messages allowed")
            return
        
        # Custom validation: Require 'priority' field in each message
        for i, msg in enumerate(messages):
            if not isinstance(msg, dict):
                raise ValueError(f"Message {i} must be a dict")
            
            # Custom requirement
            if "priority" not in msg:
                raise ValueError(f"Message {i} missing required 'priority' field")
            
            # Still check for role/content but with custom error
            if "role" not in msg:
                raise ValueError(f"Message {i} needs a role!")
            if "content" not in msg:
                raise ValueError(f"Message {i} needs content!")
    
    async def get_answer(
        self,
        messages: List[Dict[str, Any]],
        ctx: LLMContext,
        **kwargs: Any
    ) -> LLMResponse:
        """Get answer with custom validation."""
        # Use our overridden validation
        self._validate_messages(messages)
        
        params = self._merge_parameters(kwargs)
        
        response = await self.connector.request(
            endpoint="chat/completions",
            payload={"messages": messages, **params}
        )
        
        return LLMResponse(
            content=f"Validated: {response.get('content', '')}",
            role="assistant",
            finish_reason=FinishReason.STOP,
            usage=LLMUsage(
                prompt_tokens=response.get("usage", {}).get("prompt_tokens", 0),
                completion_tokens=response.get("usage", {}).get("completion_tokens", 0)
            )
        )
    
    async def stream_answer(
        self,
        messages: List[Dict[str, Any]],
        ctx: LLMContext,
        **kwargs: Any
    ) -> AsyncIterator[LLMStreamChunk]:
        """Stream with custom validation."""
        self._validate_messages(messages)
        yield LLMStreamChunk(content="Custom validated stream", is_final=True)


class CompletelyCustomLLM:
    """Completely custom implementation not inheriting from BaseLLM."""
    
    def __init__(self, metadata: ModelMetadata, connector: BaseConnector):
        self.metadata = metadata
        self.connector = connector
        self.custom_flag = True
    
    async def get_answer(
        self,
        messages: List[Dict[str, Any]],
        ctx: LLMContext,
        **kwargs: Any
    ) -> LLMResponse:
        """Completely custom implementation."""
        return LLMResponse(
            content="Custom implementation response",
            role="assistant",
            finish_reason=FinishReason.STOP,
            usage=LLMUsage(prompt_tokens=5, completion_tokens=3)
        )
    
    async def stream_answer(
        self,
        messages: List[Dict[str, Any]],
        ctx: LLMContext,
        **kwargs: Any
    ) -> AsyncIterator[LLMStreamChunk]:
        """Custom streaming."""
        for word in ["Custom", " stream", "!"]:
            yield LLMStreamChunk(content=word, is_final=False)
        yield LLMStreamChunk(content="", is_final=True)


# ============================================================================
# Tests
# ============================================================================

@pytest.mark.asyncio
async def test_register_custom_logging_implementation(test_metadata, mock_connector, test_context):
    """Test registering and using custom logging implementation."""
    impl_registry = get_implementation_registry()
    
    # Register custom implementation
    impl_registry.register_llm_implementation(
        "test-gpt-4.1-mini",
        lambda metadata, connector: CustomLoggingLLM(metadata, connector)
    )
    
    # Create LLM using registry
    llm = impl_registry.create_llm(test_metadata, mock_connector)
    
    # Verify it's our custom implementation
    assert isinstance(llm, CustomLoggingLLM)
    assert hasattr(llm, 'call_log')
    assert len(llm.call_log) == 0
    
    # Make a call
    messages = [{"role": "user", "content": "Hello"}]
    response = await llm.get_answer(messages, test_context)
    
    # Verify logging worked
    assert len(llm.call_log) == 1
    assert llm.call_log[0]["method"] == "get_answer"
    assert llm.call_log[0]["messages"] == 1
    
    # Verify response
    assert response.content == "Mock response"


@pytest.mark.asyncio
async def test_cached_implementation(test_metadata, mock_connector, test_context):
    """Test caching implementation."""
    impl_registry = get_implementation_registry()
    
    # Register cached implementation
    impl_registry.register_llm_implementation(
        "test-gpt-4.1-mini",
        lambda metadata, connector: CachedLLM(metadata, connector)
    )
    
    llm = impl_registry.create_llm(test_metadata, mock_connector)
    
    assert isinstance(llm, CachedLLM)
    assert llm.cache_hits == 0
    assert llm.cache_misses == 0
    
    # First call - cache miss
    messages = [{"role": "user", "content": "Hello"}]
    response1 = await llm.get_answer(messages, test_context, temperature=0.7)
    
    assert llm.cache_misses == 1
    assert llm.cache_hits == 0
    assert mock_connector.call_count == 1
    
    # Second call with same params - cache hit
    response2 = await llm.get_answer(messages, test_context, temperature=0.7)
    
    assert llm.cache_hits == 1
    assert llm.cache_misses == 1
    assert mock_connector.call_count == 1  # No new API call
    
    # Responses should be identical
    assert response1.content == response2.content
    
    # Different params - cache miss
    response3 = await llm.get_answer(messages, test_context, temperature=0.9)
    
    assert llm.cache_misses == 2
    assert llm.cache_hits == 1
    assert mock_connector.call_count == 2


@pytest.mark.asyncio
async def test_completely_custom_implementation(test_metadata, mock_connector, test_context):
    """Test completely custom implementation that doesn't inherit from BaseLLM."""
    impl_registry = get_implementation_registry()
    
    # Register custom implementation
    impl_registry.register_llm_implementation(
        "test-gpt-4.1-mini",
        lambda metadata, connector: CompletelyCustomLLM(metadata, connector)
    )
    
    llm = impl_registry.create_llm(test_metadata, mock_connector)
    
    # Verify it's our custom type
    assert isinstance(llm, CompletelyCustomLLM)
    assert llm.custom_flag is True
    
    # Make a call
    messages = [{"role": "user", "content": "Test"}]
    response = await llm.get_answer(messages, test_context)
    
    # Verify custom response
    assert response.content == "Custom implementation response"
    assert response.usage.prompt_tokens == 5
    assert response.usage.completion_tokens == 3


@pytest.mark.asyncio
async def test_streaming_custom_implementation(test_metadata, mock_connector, test_context):
    """Test streaming with custom implementation."""
    impl_registry = get_implementation_registry()
    
    impl_registry.register_llm_implementation(
        "test-gpt-4.1-mini",
        lambda metadata, connector: CompletelyCustomLLM(metadata, connector)
    )
    
    llm = impl_registry.create_llm(test_metadata, mock_connector)
    
    # Collect streamed chunks
    messages = [{"role": "user", "content": "Stream test"}]
    chunks = []
    async for chunk in llm.stream_answer(messages, test_context):
        chunks.append(chunk)
    
    # Verify streaming worked
    assert len(chunks) == 4
    assert chunks[0].content == "Custom"
    assert chunks[1].content == " stream"
    assert chunks[2].content == "!"
    assert chunks[3].is_final is True


def test_implementation_registry_listing(test_metadata, mock_connector):
    """Test listing registered implementations."""
    impl_registry = get_implementation_registry()
    
    # Initially empty
    assert impl_registry.list_registered_models() == []
    
    # Register some implementations
    impl_registry.register_llm_implementation(
        "model-1",
        lambda m, c: CustomLoggingLLM(m, c)
    )
    impl_registry.register_llm_implementation(
        "model-2",
        lambda m, c: CachedLLM(m, c)
    )
    
    # Check listings
    registered = impl_registry.list_registered_models()
    assert len(registered) == 2
    assert "model-1" in registered
    assert "model-2" in registered


def test_has_implementation_checks(test_metadata, mock_connector):
    """Test checking for implementation existence."""
    impl_registry = get_implementation_registry()
    
    # Initially no implementations
    assert not impl_registry.has_llm_implementation("test-model")
    
    # Register one
    impl_registry.register_llm_implementation(
        "test-model",
        lambda m, c: CustomLoggingLLM(m, c)
    )
    
    # Now it exists
    assert impl_registry.has_llm_implementation("test-model")
    assert not impl_registry.has_llm_implementation("other-model")


def test_default_llm_factory(test_metadata, mock_connector):
    """Test setting and using default LLM factory."""
    impl_registry = get_implementation_registry()
    
    # Set default factory
    impl_registry.set_default_llm_factory(
        lambda metadata, connector: CustomLoggingLLM(metadata, connector)
    )
    
    # Create LLM for unregistered model - should use default
    llm = impl_registry.create_llm(test_metadata, mock_connector)
    
    assert isinstance(llm, CustomLoggingLLM)


def test_model_specific_overrides_default(test_metadata, mock_connector):
    """Test that model-specific implementation overrides default."""
    impl_registry = get_implementation_registry()
    
    # Set default
    impl_registry.set_default_llm_factory(
        lambda metadata, connector: CustomLoggingLLM(metadata, connector)
    )
    
    # Register specific implementation
    impl_registry.register_llm_implementation(
        "test-gpt-4.1-mini",
        lambda metadata, connector: CachedLLM(metadata, connector)
    )
    
    # Should use specific, not default
    llm = impl_registry.create_llm(test_metadata, mock_connector)
    
    assert isinstance(llm, CachedLLM)
    assert not isinstance(llm, CustomLoggingLLM)


@pytest.mark.asyncio
async def test_custom_validation_override(test_metadata, mock_connector, test_context):
    """Test overriding validation with custom logic."""
    impl_registry = get_implementation_registry()
    
    # Register custom validation implementation
    impl_registry.register_llm_implementation(
        "test-gpt-4.1-mini",
        lambda metadata, connector: CustomValidationLLM(metadata, connector)
    )
    
    llm = impl_registry.create_llm(test_metadata, mock_connector)
    
    assert isinstance(llm, CustomValidationLLM)
    assert len(llm.validation_log) == 0
    
    # Test 1: Message with custom 'priority' field should work
    messages_with_priority = [{
        "role": "user",
        "content": "Hello",
        "priority": "high"
    }]
    
    response = await llm.get_answer(messages_with_priority, test_context)
    
    assert "Custom validation called" in llm.validation_log
    assert response.content == "Validated: Mock response"
    
    # Test 2: Message without 'priority' field should fail
    messages_without_priority = [{
        "role": "user",
        "content": "Hello"
        # Missing 'priority' field
    }]
    
    with pytest.raises(ValueError) as exc_info:
        await llm.get_answer(messages_without_priority, test_context)
    
    assert "missing required 'priority' field" in str(exc_info.value)
    
    # Test 3: Empty messages allowed (unlike base validation)
    llm.validation_log.clear()
    empty_response = await llm.get_answer([], test_context)
    
    assert "Empty messages allowed" in llm.validation_log
    assert empty_response.content == "Validated: Mock response"


@pytest.mark.asyncio
async def test_custom_validation_different_error_messages(test_metadata, mock_connector, test_context):
    """Test that custom validation has different error messages."""
    impl_registry = get_implementation_registry()
    
    impl_registry.register_llm_implementation(
        "test-gpt-4.1-mini",
        lambda metadata, connector: CustomValidationLLM(metadata, connector)
    )
    
    llm = impl_registry.create_llm(test_metadata, mock_connector)
    
    # Missing role - custom error message
    messages = [{
        "content": "Hello",
        "priority": "low"
    }]
    
    with pytest.raises(ValueError) as exc_info:
        await llm.get_answer(messages, test_context)
    
    # Custom error message, not the base class one
    assert "needs a role!" in str(exc_info.value)
    assert "InputValidationError" not in str(type(exc_info.value))


def test_error_when_no_implementation():
    """Test error when no implementation available."""
    impl_registry = get_implementation_registry()
    
    metadata = ModelMetadata(
        model_name="unknown-model",
        provider=LLMProvider.AZURE,
        model_family=ModelFamily.AZURE_GPT_4_1_MINI,
        display_name="Unknown",
        max_context_length=1000,
        max_output_tokens=500
    )
    
    class DummyConnector(BaseConnector):
        async def request(self, endpoint, payload, **kwargs):
            return {}
        async def test_connection(self):
            return True
    
    connector = DummyConnector({})
    
    # Should raise error - no implementation and no default
    with pytest.raises(Exception) as exc_info:
        impl_registry.create_llm(metadata, connector)
    
    assert "No LLM implementation registered" in str(exc_info.value)


# ============================================================================
# Media Output Tests (Unsupported Operations)
# ============================================================================

@pytest.mark.asyncio
async def test_text_only_model_rejects_image_generation(test_metadata, mock_connector, test_context):
    """Test that text-only models reject image generation requests."""
    # Create text-only model implementation
    class TextOnlyLLM(BaseLLM):
        async def get_answer(self, messages, ctx, **kwargs):
            return LLMResponse(
                content="Text response",
                role="assistant",
                finish_reason=FinishReason.STOP,
                usage=LLMUsage(prompt_tokens=10, completion_tokens=5)
            )
        
        async def stream_answer(self, messages, ctx, **kwargs):
            yield LLMStreamChunk(content="Response", is_final=True)
    
    llm = TextOnlyLLM(test_metadata, mock_connector)
    
    messages = [{"role": "user", "content": "Generate a sunset"}]
    
    # get_image should raise UnsupportedOperationError
    with pytest.raises(UnsupportedOperationError) as exc_info:
        await llm.get_image(messages, test_context)
    
    assert "does not support image generation" in str(exc_info.value)
    assert test_metadata.model_name in str(exc_info.value)


@pytest.mark.asyncio
async def test_text_only_model_rejects_audio_generation(test_metadata, mock_connector, test_context):
    """Test that text-only models reject audio generation requests."""
    class TextOnlyLLM(BaseLLM):
        async def get_answer(self, messages, ctx, **kwargs):
            return LLMResponse(content="Text", role="assistant", finish_reason=FinishReason.STOP)
        async def stream_answer(self, messages, ctx, **kwargs):
            yield LLMStreamChunk(content="Response", is_final=True)
    
    llm = TextOnlyLLM(test_metadata, mock_connector)
    
    messages = [{"role": "user", "content": "Say hello"}]
    
    # get_audio should raise
    with pytest.raises(UnsupportedOperationError) as exc_info:
        await llm.get_audio(messages, test_context)
    
    assert "does not support audio generation" in str(exc_info.value)


@pytest.mark.asyncio
async def test_text_only_model_rejects_video_generation(test_metadata, mock_connector, test_context):
    """Test that text-only models reject video generation requests."""
    class TextOnlyLLM(BaseLLM):
        async def get_answer(self, messages, ctx, **kwargs):
            return LLMResponse(content="Text", role="assistant", finish_reason=FinishReason.STOP)
        async def stream_answer(self, messages, ctx, **kwargs):
            yield LLMStreamChunk(content="Response", is_final=True)
    
    llm = TextOnlyLLM(test_metadata, mock_connector)
    
    messages = [{"role": "user", "content": "A cat playing piano"}]
    
    # get_video should raise
    with pytest.raises(UnsupportedOperationError) as exc_info:
        await llm.get_video(messages, test_context)
    
    assert "does not support video generation" in str(exc_info.value)


@pytest.mark.asyncio
async def test_vision_enabled_model_accepts_multimodal_input(mock_connector, test_context):
    """Test that vision-enabled models accept image inputs."""
    # Create vision-enabled metadata
    vision_metadata = ModelMetadata(
        model_name="vision-model",
        provider=LLMProvider.AZURE,
        model_family=ModelFamily.AZURE_GPT_4_1_MINI,
        display_name="Vision Model",
        max_context_length=128000,
        max_output_tokens=4096,
        supports_vision=True,
        supported_input_types={InputMediaType.TEXT, InputMediaType.IMAGE}
    )
    
    class VisionLLM(BaseLLM):
        async def get_answer(self, messages, ctx, **kwargs):
            return LLMResponse(
                content="I see an image",
                role="assistant",
                finish_reason=FinishReason.STOP,
                usage=LLMUsage(prompt_tokens=10, completion_tokens=5)
            )
        
        async def stream_answer(self, messages, ctx, **kwargs):
            yield LLMStreamChunk(content="Response", is_final=True)
    
    llm = VisionLLM(vision_metadata, mock_connector)
    
    # Should work with vision helper
    response = await llm.get_answer_with_vision(
        prompt="What's in this image?",
        images=["https://example.com/image.jpg"],
        ctx=test_context
    )
    
    assert response.content == "I see an image"


@pytest.mark.asyncio
async def test_non_vision_model_rejects_vision_input(test_metadata, mock_connector, test_context):
    """Test that non-vision models reject vision helper."""
    class NonVisionLLM(BaseLLM):
        async def get_answer(self, messages, ctx, **kwargs):
            return LLMResponse(content="Text", role="assistant", finish_reason=FinishReason.STOP)
        async def stream_answer(self, messages, ctx, **kwargs):
            yield LLMStreamChunk(content="Response", is_final=True)
    
    # test_metadata has supports_vision=False by default
    llm = NonVisionLLM(test_metadata, mock_connector)
    
    # Should raise UnsupportedOperationError
    with pytest.raises(UnsupportedOperationError) as exc_info:
        await llm.get_answer_with_vision(
            prompt="What's in this image?",
            images=["https://example.com/image.jpg"],
            ctx=test_context
        )
    
    assert "does not support vision" in str(exc_info.value)
    assert "image inputs" in str(exc_info.value)


def test_unsupported_operation_error_details(test_metadata):
    """Test UnsupportedOperationError provides helpful details."""
    error = UnsupportedOperationError(
        "Image generation not supported",
        model_name=test_metadata.model_name,
        operation="get_image",
        details={
            "supported_output_types": ["text", "json"],
            "hint": "Use get_answer() instead"
        }
    )
    
    assert error.operation == "get_image"
    assert error.model_name == test_metadata.model_name
    assert "text" in error.details["supported_output_types"]
    assert "hint" in error.details

