"""
LLM Subsystem for AI Core.

This module provides a unified interface for working with Large Language Models
from different providers (OpenAI, Azure, etc.).

Architecture:
=============
All LLMs implement ILLM interface with just 2 methods:
1. get_answer() - Complete response
2. stream_answer() - Streaming response

Pluggable Components:
=====================
All components are pluggable and can be swapped out:
- ILLMValidator: Message and parameter validation
- IParameterTransformer: Parameter transformations
- IResponseParser: Response parsing
- IStructuredOutputHandler: Structured output handling

Usage:
======
    from core.llms import LLMFactory, LLMContext
    
    # Create LLM with default components
    llm = LLMFactory.create_llm(
        "gpt-4o",
        connector_config={"api_key": "sk-..."}
    )
    
    # Create LLM with custom validator
    from core.llms import LLMValidatorFactory
    llm = LLMFactory.create_llm(
        "gpt-4o",
        connector_config={"api_key": "sk-..."},
        validator=LLMValidatorFactory.get_validator('noop')
    )
    
    # Get answer
    messages = [{"role": "user", "content": "Hello!"}]
    response = await llm.get_answer(messages, LLMContext(), temperature=0.7)
    print(response.content)
    
    # Stream answer
    async for chunk in llm.stream_answer(messages, LLMContext()):
        print(chunk.content, end='', flush=True)

Available Models:
=================
    from core.llms import LLMFactory
    
    models = LLMFactory.list_available_models()
    print(f"Available: {models}")
"""

# Core interfaces
from .interfaces import (
    ILLM,
    IConnector,
    IModelRegistry,
    ILLMValidator,
    IParameterTransformer,
    IResponseParser,
    IStructuredOutputHandler,
    IPayloadBuilder,
)

# Enums
from .enum import (
    LLMProvider,
    ModelFamily,
    InputMediaType,
    OutputMediaType,
    MessageRole,
    LLMCapability,
    LLMType,
    StreamEventType,
    FinishReason,
)

# Exceptions
from .exceptions import (
    LLMError,
    InputValidationError,
    ProviderError,
    ConfigurationError,
    AuthenticationError,
    RateLimitError,
    TimeoutError,
    QuotaExceededError,
    ServiceUnavailableError,
    JSONParsingError,
    InvalidResponseError,
    TokenLimitError,
    ModelNotFoundError,
    StreamingError,
    ContentFilterError,
    UnsupportedOperationError,
)

# Spec
from .spec import (
    ModelMetadata,
    LLMResponse,
    LLMStreamChunk,
    LLMUsage,
    LLMContext,
    OutputConfig,
    OutputFormat,
    ResponseMode,
    ParseResult,
    create_model_metadata,
    create_response,
    create_chunk,
    create_context,
)

# Runtimes - Pluggable Components
from .runtimes import (
    # Validators
    BasicLLMValidator,
    NoOpLLMValidator,
    LLMValidatorFactory,
    # Transformers
    AzureGPT4Transformer,
    NoOpTransformer,
    TransformerFactory,
    # Parsers
    AzureResponseParser,
    NoOpResponseParser,
    ParserFactory,
    # Handlers
    BasicStructuredHandler,
    NoOpStructuredHandler,
    StructuredHandlerFactory,
)

# Runtimes - Model Registry and Factory
from .runtimes import (
    ModelRegistry,
    get_model_registry,
    reset_registry,
    LLMFactory,
)

# Providers - Base classes and implementations
from .providers.base import (
    BaseLLM,
    BaseConnector,
)

from .providers.azure import (
    AzureConnector,
    AzureBaseLLM as AzureLLM,
)

# OpenAI not yet migrated - placeholder
class OpenAIConnector:
    def __init__(self, *args, **kwargs):
        raise NotImplementedError("OpenAI not yet migrated to providers structure. Use the new providers.azure for Azure models.")

class OpenAILLM:
    def __init__(self, *args, **kwargs):
        raise NotImplementedError("OpenAI not yet migrated to providers structure. Use the new providers.azure for Azure models.")

__all__ = [
    # Core Interfaces
    "ILLM",
    "IConnector",
    "IModelRegistry",
    # Pluggable Component Interfaces
    "ILLMValidator",
    "IParameterTransformer",
    "IResponseParser",
    "IStructuredOutputHandler",
    "IPayloadBuilder",
    # Enums
    "LLMProvider",
    "ModelFamily",
    "InputMediaType",
    "OutputMediaType",
    "MessageRole",
    "LLMCapability",
    "LLMType",
    "StreamEventType",
    "FinishReason",
    # Exceptions
    "LLMError",
    "InputValidationError",
    "ProviderError",
    "ConfigurationError",
    "AuthenticationError",
    "RateLimitError",
    "TimeoutError",
    "QuotaExceededError",
    "ServiceUnavailableError",
    "JSONParsingError",
    "InvalidResponseError",
    "TokenLimitError",
    "ModelNotFoundError",
    "StreamingError",
    "ContentFilterError",
    "UnsupportedOperationError",
    # Spec
    "ModelMetadata",
    "LLMResponse",
    "LLMStreamChunk",
    "LLMUsage",
    "LLMContext",
    "OutputConfig",
    "OutputFormat",
    "ResponseMode",
    "ParseResult",
    "create_model_metadata",
    "create_response",
    "create_chunk",
    "create_context",
    # Validators
    "BasicLLMValidator",
    "NoOpLLMValidator",
    "LLMValidatorFactory",
    # Transformers
    "AzureGPT4Transformer",
    "NoOpTransformer",
    "TransformerFactory",
    # Parsers
    "AzureResponseParser",
    "NoOpResponseParser",
    "ParserFactory",
    # Handlers
    "BasicStructuredHandler",
    "NoOpStructuredHandler",
    "StructuredHandlerFactory",
    # Runtimes
    "BaseLLM",
    "BaseConnector",
    "ModelRegistry",
    "get_model_registry",
    "reset_registry",
    "LLMFactory",
    "OpenAIConnector",
    "OpenAILLM",
    "AzureConnector",
    "AzureLLM",
]
