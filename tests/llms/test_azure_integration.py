"""
Azure OpenAI Integration Test.

This test file demonstrates real usage with Azure OpenAI configuration.
Tests both get_answer() and stream_answer() methods.
"""

import pytest
from core.llms import (
    LLMFactory,
    create_context,
)
from utils.logging.LoggerAdaptor import LoggerAdaptor

# Setup logger
logger = LoggerAdaptor.get_logger("tests.llms.azure_integration")


# ============================================================================
# CONFIGURATION
# ============================================================================

AZURE_CONFIG = {
    "endpoint": "https://zeenie-sweden.openai.azure.com/",
    "deployment_name": "gpt-4.1-mini",  # Using GPT-4.1 Mini deployment
    "api_version": "2024-02-15-preview",
    "api_key": "ss",
    "timeout": 60,
}

# NOTE: Ensure your Azure deployment name matches the one configured above


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
async def azure_llm():
    """Create Azure LLM instance with test configuration."""
    # Use azure-gpt-4.1-mini model
    llm = LLMFactory.create_llm(
        "azure-gpt-4.1-mini",
        connector_config=AZURE_CONFIG
    )
    
    yield llm
    
    # Cleanup: close the connector session
    if hasattr(llm.connector, 'close'):
        await llm.connector.close()


@pytest.fixture
def test_context():
    """Create test context."""
    return create_context(
        user_id="test-user-azure",
        session_id="test-session-001",
        metadata={"test": "azure_integration"}
    )


# ============================================================================
# BASIC TESTS
# ============================================================================

@pytest.mark.asyncio
class TestAzureBasic:
    """Basic Azure OpenAI tests."""
    
    async def test_simple_question(self, azure_llm, test_context):
        """Test simple question with get_answer."""
        messages = [
            {"role": "user", "content": "What is 2+2? Answer with just the number."}
        ]
        
        response = await azure_llm.get_answer(
            messages,
            test_context,
            max_tokens=100  # Increased for full response
            # Note: GPT-4.1 Mini on Azure only supports default temperature (1.0)
        )
        
        logger.info(f"Response: {response.content}")
        logger.info(f"Usage: {response.usage}")
        logger.info(f"Finish reason: {response.finish_reason}")
        
        # Verify response structure
        assert response.content is not None
        assert len(response.content) > 0
        assert response.usage is not None
        assert response.usage.prompt_tokens > 0
        assert response.usage.completion_tokens > 0
        
        # Check if cost was calculated
        if response.usage.cost_usd:
            logger.info(f"Cost: ${response.usage.cost_usd:.6f}")
    
    async def test_conversation(self, azure_llm, test_context):
        """Test multi-turn conversation."""
        messages = [
            {"role": "system", "content": "You are a helpful math tutor."},
            {"role": "user", "content": "What is 5 * 7?"},
            {"role": "assistant", "content": "5 * 7 = 35"},
            {"role": "user", "content": "And what is 35 + 10?"}
        ]
        
        response = await azure_llm.get_answer(
            messages,
            test_context,
            max_tokens=100
        )
        
        logger.info(f"Conversation response: {response.content}")
        logger.info(f"Total tokens: {response.usage.total_tokens}")
        
        assert response.content is not None
        assert "45" in response.content or "forty-five" in response.content.lower()
    
    async def test_with_different_temperatures(self, azure_llm, test_context):
        """Test with different temperature settings."""
        messages = [
            {"role": "user", "content": "Say 'Hello World' and nothing else."}
        ]
        
        # Note: GPT-5 only supports default temperature, so we'll test with different max_tokens instead
        response_low = await azure_llm.get_answer(
            messages,
            test_context,
            max_tokens=20
        )
        
        # Second call
        response_high = await azure_llm.get_answer(
            messages,
            test_context,
            max_tokens=20
        )
        
        logger.info(f"First call: {response_low.content}")
        logger.info(f"Second call: {response_high.content}")
        
        assert response_low.content is not None
        assert response_high.content is not None


# ============================================================================
# STREAMING TESTS
# ============================================================================

@pytest.mark.asyncio
class TestAzureStreaming:
    """Azure OpenAI streaming tests."""
    
    async def test_stream_simple(self, azure_llm, test_context):
        """Test streaming a simple response."""
        messages = [
            {"role": "user", "content": "Count from 1 to 5 in english"}
        ]
        
        chunks = []
        final_chunk = None
        
        logger.info("Starting streaming response")
        async for chunk in azure_llm.stream_answer(
            messages,
            test_context,
            max_tokens=100
        ):
            if chunk.content:
                logger.debug(f"Chunk: {chunk.content}")
                chunks.append(chunk.content)
            
            if chunk.is_final:
                final_chunk = chunk
                logger.info("Stream completed")
                if chunk.usage:
                    logger.info(f"Usage: {chunk.usage}")
        
        # Verify we got content
        assert len(chunks) > 0
        full_content = "".join(chunks)
        assert len(full_content) > 0
        
        # Verify final chunk has usage
        assert final_chunk is not None
        assert final_chunk.is_final is True
    
    async def test_stream_story(self, azure_llm, test_context):
        """Test streaming a longer response."""
        messages = [
            {"role": "user", "content": "Tell me a very short story about a robot in exactly 3 sentences."}
        ]
        
        chunks = []
        
        logger.info("Starting story stream")
        async for chunk in azure_llm.stream_answer(
            messages,
            test_context,
            max_tokens=100
        ):
            if chunk.content:
                logger.debug(f"Chunk: {chunk.content}")
                chunks.append(chunk.content)
            
            if chunk.is_final and chunk.usage:
                logger.info(f"Total tokens: {chunk.usage.total_tokens}")
                if chunk.usage.cost_usd:
                    logger.info(f"Cost: ${chunk.usage.cost_usd:.6f}")
        
        full_story = "".join(chunks)
        assert len(full_story) > 20  # Should be a decent story
        logger.info(f"Full story length: {len(full_story)} chars")
        logger.info(f"Full story: {full_story}")


# ============================================================================
# CAPABILITY TESTS
# ============================================================================

@pytest.mark.asyncio
class TestAzureCapabilities:
    """Test Azure LLM capabilities."""
    
    async def test_model_capabilities(self, azure_llm):
        """Test querying model capabilities."""
        caps = azure_llm.get_supported_capabilities()
        
        logger.info(f"Model: {caps['model_name']}")
        logger.info(f"Provider: {caps['provider']}")
        logger.info(f"Streaming: {caps['supports_streaming']}")
        logger.info(f"Function calling: {caps['supports_function_calling']}")
        logger.info(f"Vision: {caps['supports_vision']}")
        logger.info(f"JSON mode: {caps['supports_json_mode']}")
        logger.info(f"Max context: {caps['max_context_length']} tokens")
        logger.info(f"Max output: {caps['max_output_tokens']} tokens")
        
        assert caps['provider'] == 'azure'
        assert caps['supports_streaming'] is True
        assert caps['max_context_length'] > 0
    
    async def test_model_metadata(self, azure_llm):
        """Test accessing model metadata."""
        metadata = azure_llm.metadata
        
        logger.info(f"Display name: {metadata.display_name}")
        logger.info(f"Model family: {metadata.model_family}")
        logger.info(f"Supported inputs: {[t.value if hasattr(t, 'value') else t for t in metadata.supported_input_types]}")
        logger.info(f"Supported outputs: {[t.value if hasattr(t, 'value') else t for t in metadata.supported_output_types]}")
        
        if metadata.cost_per_1k_input_tokens:
            logger.info(f"Input cost: ${metadata.cost_per_1k_input_tokens}/1K tokens")
        if metadata.cost_per_1k_output_tokens:
            logger.info(f"Output cost: ${metadata.cost_per_1k_output_tokens}/1K tokens")
        
        assert metadata.model_name == "azure-gpt-4.1-mini"


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

@pytest.mark.asyncio
class TestAzureErrorHandling:
    """Test error handling scenarios."""
    
    async def test_empty_messages(self, azure_llm, test_context):
        """Test with empty messages list."""
        from core.llms import InputValidationError
        
        with pytest.raises(InputValidationError):
            await azure_llm.get_answer([], test_context)
    
    async def test_invalid_message_format(self, azure_llm, test_context):
        """Test with invalid message format."""
        from core.llms import InputValidationError
        
        # Missing 'role' field
        messages = [{"content": "Hello"}]
        
        with pytest.raises(InputValidationError):
            await azure_llm.get_answer(messages, test_context)
    
    async def test_excessive_max_tokens(self, azure_llm, test_context):
        """Test requesting more tokens than allowed."""
        from core.llms import InputValidationError
        
        messages = [{"role": "user", "content": "Hello"}]
        
        # Request way more than max_output_tokens
        # The validator now raises InputValidationError for parameter validation
        with pytest.raises(InputValidationError):
            await azure_llm.get_answer(
                messages,
                test_context,
                max_tokens=1000000  # Way over limit
            )


# ============================================================================
# COMPARISON TEST
# ============================================================================

@pytest.mark.asyncio
class TestStreamVsNonStream:
    """Compare streaming vs non-streaming responses."""
    
    async def test_same_content(self, azure_llm, test_context):
        """Test that streaming and non-streaming give similar results."""
        messages = [
            {"role": "user", "content": "What is the capital of France? Answer with just the city name."}
        ]
        
        # Non-streaming
        response = await azure_llm.get_answer(
            messages,
            test_context,
            max_tokens=50
        )
        
        # Streaming
        chunks = []
        async for chunk in azure_llm.stream_answer(
            messages,
            test_context,
            max_tokens=50
        ):
            if chunk.content:
                chunks.append(chunk.content)
        
        streamed_content = "".join(chunks)
        
        logger.info(f"Non-streaming: {response.content}")
        logger.info(f"Streaming: {streamed_content}")
        
        # Both should mention Paris
        assert "Paris" in response.content or "paris" in response.content.lower()
        assert "Paris" in streamed_content or "paris" in streamed_content.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

