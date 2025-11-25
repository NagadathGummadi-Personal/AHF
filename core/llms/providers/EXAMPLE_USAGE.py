"""
Example usage of the new provider-centric LLM structure.

This demonstrates how to use the refactored LLM providers.
"""

import asyncio
from core.llms.providers.azure import create_azure_llm
from core.llms.spec.llm_context import LLMContext


async def example_basic_usage():
    """Basic example: Create LLM and get a response."""
    
    # Create LLM instance
    llm = create_azure_llm(
        model_name="gpt-4.1-mini",
        api_key="your-api-key-here",
        endpoint="https://your-resource.openai.azure.com",
        deployment_name="gpt-4.1-mini",
        api_version="2024-02-15-preview"
    )
    
    # Create context for tracking
    context = LLMContext(
        user_id="demo-user",
        session_id="demo-session"
    )
    
    # Prepare messages
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the capital of France?"}
    ]
    
    # Get response
    response = await llm.get_answer(
        messages=messages,
        ctx=context,
        max_tokens=100,
        top_p=0.9
    )
    
    print(f"Response: {response.content}")
    print(f"Tokens used: {response.usage.total_tokens}")
    print(f"Cost: ${response.usage.total_tokens / 1000 * 0.00015:.6f}")


async def example_with_env_vars():
    """Example using environment variables for configuration."""
    import os
    
    # Set environment variables
    os.environ['AZURE_OPENAI_KEY'] = 'your-api-key'
    os.environ['AZURE_OPENAI_ENDPOINT'] = 'https://your-resource.openai.azure.com'
    os.environ['AZURE_OPENAI_DEPLOYMENT'] = 'gpt-4.1-mini'
    
    # Create LLM (automatically uses env vars)
    llm = create_azure_llm("gpt-4.1-mini")
    
    context = LLMContext()
    messages = [{"role": "user", "content": "Hello!"}]
    
    response = await llm.get_answer(messages, context)
    print(response.content)


async def example_vision():
    """Example using GPT-4.1 Mini's vision capabilities."""
    
    llm = create_azure_llm(
        "gpt-4.1-mini",
        api_key="your-api-key",
        endpoint="https://your-resource.openai.azure.com",
        deployment_name="gpt-4.1-mini"
    )
    
    context = LLMContext(user_id="vision-demo")
    
    # Use vision helper from BaseLLM
    response = await llm.get_answer_with_vision(
        prompt="What objects do you see in this image?",
        images=["https://example.com/image.jpg"],
        ctx=context,
        max_tokens=500
    )
    
    print(f"Vision Response: {response.content}")


async def example_streaming():
    """Example using streaming responses."""
    
    llm = create_azure_llm(
        "gpt-4.1-mini",
        api_key="your-api-key",
        endpoint="https://your-resource.openai.azure.com",
        deployment_name="gpt-4.1-mini"
    )
    
    context = LLMContext()
    messages = [{"role": "user", "content": "Write a short poem about Python programming."}]
    
    print("Streaming response:")
    async for chunk in llm.stream_answer(messages, context, max_tokens=200):
        if chunk.content:
            print(chunk.content, end='', flush=True)
    print()  # Newline at end


async def example_parameter_validation():
    """Example showing automatic parameter validation."""
    
    llm = create_azure_llm("gpt-4.1-mini", ...)
    context = LLMContext()
    messages = [{"role": "user", "content": "Hello"}]
    
    try:
        # This will fail - temperature not supported by GPT-4.1 Mini
        response = await llm.get_answer(
            messages,
            context,
            temperature=0.7  # ❌ Not supported!
        )
    except ValueError as e:
        print(f"Validation error (expected): {e}")
    
    # This works - only supported parameters
    response = await llm.get_answer(
        messages,
        context,
        max_tokens=100,  # ✅ Supported
        top_p=0.9,       # ✅ Supported
    )
    print(f"Success: {response.content}")


async def example_accessing_metadata():
    """Example showing how to access model metadata."""
    from core.llms.providers.azure.models.gpt41_mini import GPT41MiniMetadata
    
    print(f"Model: {GPT41MiniMetadata.NAME}")
    print(f"Display Name: {GPT41MiniMetadata.DISPLAY_NAME}")
    print(f"Max Tokens: {GPT41MiniMetadata.MAX_TOKENS}")
    print(f"Context Length: {GPT41MiniMetadata.MAX_CONTEXT_LENGTH}")
    print(f"Cost (Input): ${GPT41MiniMetadata.COST_PER_1K_INPUT}/1K tokens")
    print(f"Cost (Output): ${GPT41MiniMetadata.COST_PER_1K_OUTPUT}/1K tokens")
    print(f"Supports Vision: {GPT41MiniMetadata.SUPPORTS_VISION}")
    print(f"Supports Streaming: {GPT41MiniMetadata.SUPPORTS_STREAMING}")
    print(f"Supported Parameters: {GPT41MiniMetadata.SUPPORTED_PARAMS}")
    
    # Validate parameters before using
    params = {"max_tokens": 100, "top_p": 0.9}
    GPT41MiniMetadata.validate_params(params)
    print("✅ Parameters are valid!")


if __name__ == "__main__":
    # Run examples
    print("=" * 60)
    print("EXAMPLE: Basic Usage")
    print("=" * 60)
    # asyncio.run(example_basic_usage())
    
    print("\n" + "=" * 60)
    print("EXAMPLE: Accessing Metadata")
    print("=" * 60)
    asyncio.run(example_accessing_metadata())
    
    # Uncomment to run other examples:
    # asyncio.run(example_with_env_vars())
    # asyncio.run(example_vision())
    # asyncio.run(example_streaming())
    # asyncio.run(example_parameter_validation())



