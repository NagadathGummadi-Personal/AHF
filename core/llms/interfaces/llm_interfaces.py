"""
Interfaces for LLM Subsystem.

This module defines the core protocols (interfaces) that all LLM implementations
must follow, ensuring a consistent API across all providers.

Pluggable Components:
- ILLMValidator: Message and parameter validation
- IParameterTransformer: Parameter transformations (model-specific mappings)
- IResponseParser: Response parsing and content extraction
- IStructuredOutputHandler: Structured output validation and retry logic
"""

from __future__ import annotations
from typing import Any, AsyncIterator, Dict, List, Protocol, runtime_checkable, Optional, Type, Union, TYPE_CHECKING
from pydantic import BaseModel

if TYPE_CHECKING:
    from ..spec.llm_result import LLMResponse, LLMStreamChunk
    from ..spec.llm_schema import ModelMetadata
    from ..spec.llm_context import LLMContext
    from ..spec.llm_output_config import OutputConfig, ParseResult

# Type aliases for clarity
Messages = List[Dict[str, Any]]
Parameters = Dict[str, Any]


@runtime_checkable
class ILLM(Protocol):
    """
    Core LLM interface - all LLMs implement just 2 required methods.
    
    This protocol defines the minimal, consistent API that all LLM
    implementations (OpenAI, Azure, Bedrock, etc.) must implement.
    
    Required Methods (Text Output):
    1. get_answer() - Complete text response (non-streaming)
    2. stream_answer() - Streaming text response
    
    Optional Methods (Media Output - via BaseLLM):
    - Models that support image/audio/video generation can implement:
      * get_image() / stream_image() - Image generation
      * get_audio() / stream_audio() - Audio generation (TTS, music)
      * get_video() / stream_video() - Video generation
    - Models that don't support these will raise UnsupportedOperationError
    
    Multimodal Input:
    - All models accept multimodal content in messages (text + images)
    - Vision-enabled models can process images via message content structure
    - Use BaseLLM.get_answer_with_vision() helper for convenience
    """
    
    async def get_answer(
        self,
        messages: Messages,
        ctx: 'LLMContext',
        **kwargs: Any
    ) -> 'LLMResponse':
        """
        Get a complete response from the LLM (non-streaming).
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            ctx: LLM context with request metadata
            **kwargs: Additional parameters (temperature, max_tokens, etc.)
            
        Returns:
            LLMResponse with generated content and usage
            
        Raises:
            InputValidationError: If input is invalid
            ProviderError: If provider returns an error
            TokenLimitError: If token limits exceeded
            TimeoutError: If request times out
            
        Example:
            messages = [{"role": "user", "content": "What is 2+2?"}]
            response = await llm.get_answer(messages, ctx, temperature=0.7)
            print(response.content)
        """
        ...
    
    async def stream_answer(
        self,
        messages: Messages,
        ctx: 'LLMContext',
        **kwargs: Any
    ) -> AsyncIterator['LLMStreamChunk']:
        """
        Get a streaming response from the LLM.
        
        Yields chunks of content as they are generated.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            ctx: LLM context with request metadata
            **kwargs: Additional parameters (temperature, max_tokens, etc.)
            
        Yields:
            LLMStreamChunk objects with content fragments
            
        Raises:
            InputValidationError: If input is invalid
            StreamingError: If streaming encounters an error
            TokenLimitError: If token limits exceeded
            
        Example:
            messages = [{"role": "user", "content": "Tell me a story"}]
            async for chunk in llm.stream_answer(messages, ctx):
                print(chunk.content, end='', flush=True)
                if chunk.is_final:
                    print(f"\nUsage: {chunk.usage}")
        """
        ...


# ============================================================================
# PLUGGABLE COMPONENT INTERFACES
# ============================================================================

@runtime_checkable
class ILLMValidator(Protocol):
    """
    Interface for LLM message and parameter validation.
    
    Validators check messages and parameters before sending to the LLM.
    Different validators can be swapped for different validation strategies.
    
    Built-in implementations:
    - BasicValidator: Comprehensive validation (messages, tokens, params)
    - NoOpValidator: Skip validation (for testing/development)
    
    Example:
        class CustomValidator(ILLMValidator):
            async def validate_messages(self, messages, metadata):
                # Custom message validation
                pass
            
            async def validate_parameters(self, params, metadata):
                # Custom parameter validation
                pass
    """
    
    async def validate_messages(
        self,
        messages: Messages,
        metadata: 'ModelMetadata'
    ) -> None:
        """
        Validate messages before sending to LLM.
        
        Args:
            messages: List of message dicts
            metadata: Model metadata with constraints
            
        Raises:
            InputValidationError: If messages are invalid
        """
        ...
    
    async def validate_parameters(
        self,
        params: Parameters,
        metadata: 'ModelMetadata'
    ) -> None:
        """
        Validate parameters against model constraints.
        
        Args:
            params: Parameters to validate
            metadata: Model metadata with constraints
            
        Raises:
            InputValidationError: If parameters are invalid
        """
        ...
    
    async def validate_token_limits(
        self,
        messages: Messages,
        max_output_tokens: int,
        metadata: 'ModelMetadata'
    ) -> None:
        """
        Validate that token limits won't be exceeded.
        
        Args:
            messages: Input messages
            max_output_tokens: Requested max output tokens
            metadata: Model metadata with token limits
            
        Raises:
            TokenLimitError: If limits would be exceeded
        """
        ...


@runtime_checkable
class IParameterTransformer(Protocol):
    """
    Interface for parameter transformation.
    
    Transformers convert standard parameters to model-specific format.
    Different models may use different parameter names or formats.
    
    Built-in implementations:
    - AzureGPT4Transformer: For GPT-4.x models (max_tokens → max_completion_tokens)
    - NoOpTransformer: No transformation (pass-through)
    
    Example:
        class CustomTransformer(IParameterTransformer):
            def transform(self, params, metadata):
                # Custom transformation
                transformed = params.copy()
                if 'max_tokens' in transformed:
                    transformed['max_completion_tokens'] = transformed.pop('max_tokens')
                return transformed
    """
    
    def transform(
        self,
        params: Parameters,
        metadata: 'ModelMetadata'
    ) -> Parameters:
        """
        Transform parameters for the target model.
        
        Args:
            params: Standard parameters
            metadata: Model metadata
            
        Returns:
            Transformed parameters
        """
        ...
    
    def get_supported_parameters(self) -> List[str]:
        """
        Get list of parameters this transformer handles.
        
        Returns:
            List of parameter names
        """
        ...


@runtime_checkable
class IResponseParser(Protocol):
    """
    Interface for response parsing.
    
    Parsers extract content from provider-specific response formats.
    Different providers return responses in different structures.
    
    Built-in implementations:
    - AzureResponseParser: Parse Azure OpenAI responses
    - NoOpParser: Return raw response (for debugging)
    
    Example:
        class CustomParser(IResponseParser):
            def parse_response(self, response, start_time, metadata):
                # Custom parsing logic
                return LLMResponse(...)
    """
    
    def parse_response(
        self,
        response: Dict[str, Any],
        start_time: float,
        metadata: 'ModelMetadata'
    ) -> 'LLMResponse':
        """
        Parse provider response into LLMResponse.
        
        Args:
            response: Raw provider response
            start_time: Request start time
            metadata: Model metadata
            
        Returns:
            Parsed LLMResponse
            
        Raises:
            InvalidResponseError: If response format is invalid
        """
        ...
    
    def parse_stream_chunk(
        self,
        chunk_data: Dict[str, Any],
        metadata: 'ModelMetadata'
    ) -> Optional['LLMStreamChunk']:
        """
        Parse streaming chunk.
        
        Args:
            chunk_data: Raw chunk data
            metadata: Model metadata
            
        Returns:
            Parsed LLMStreamChunk or None if chunk should be skipped
        """
        ...


@runtime_checkable
class IStructuredOutputHandler(Protocol):
    """
    Interface for structured output handling.
    
    Handlers manage structured output (JSON/Pydantic) validation,
    retries, and error handling.
    
    Built-in implementations:
    - BasicStructuredHandler: Full validation with retries
    - NoOpHandler: Return raw content without validation
    
    Example:
        class CustomHandler(IStructuredOutputHandler):
            async def validate_output(self, content, output_config):
                # Custom validation logic
                return ParseResult(success=True, parsed_output=obj)
    """
    
    def prepare_request(
        self,
        params: Parameters,
        output_config: 'OutputConfig'
    ) -> Parameters:
        """
        Prepare request parameters for structured output.
        
        Args:
            params: Request parameters
            output_config: Output configuration
            
        Returns:
            Modified parameters with response_format
        """
        ...
    
    def validate_output(
        self,
        content: str,
        output_config: 'OutputConfig'
    ) -> 'ParseResult':
        """
        Validate response content against output configuration.
        
        Args:
            content: Response content
            output_config: Output configuration with schema
            
        Returns:
            ParseResult with validation status and parsed output
        """
        ...
    
    def handle_validation_failure(
        self,
        error: Exception,
        output_config: 'OutputConfig',
        attempt: int
    ) -> bool:
        """
        Handle validation failure and decide whether to retry.
        
        Args:
            error: Validation error
            output_config: Output configuration
            attempt: Current attempt number
            
        Returns:
            True if should retry, False otherwise
        """
        ...


@runtime_checkable
class IPayloadBuilder(Protocol):
    """
    Interface for building request payloads.
    
    Builders construct provider-specific request payloads.
    
    Example:
        class CustomBuilder(IPayloadBuilder):
            def build_payload(self, messages, params, metadata):
                return {"messages": messages, **params}
    """
    
    def build_payload(
        self,
        messages: Messages,
        params: Parameters,
        metadata: 'ModelMetadata'
    ) -> Dict[str, Any]:
        """
        Build request payload.
        
        Args:
            messages: Validated messages
            params: Transformed parameters
            metadata: Model metadata
            
        Returns:
            Request payload dict
        """
        ...


# ============================================================================
# CONNECTOR INTERFACE
# ============================================================================

@runtime_checkable
class IConnector(Protocol):
    """
    Connector interface for LLM provider communication.
    
    Connectors handle the low-level details of communicating with
    LLM providers (authentication, requests, retries, etc.).
    No explicit connection lifecycle needed for HTTP APIs.
    """
    
    async def request(
        self,
        endpoint: str,
        payload: Dict[str, Any],
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Make a request to the provider API.
        
        Args:
            endpoint: API endpoint to call
            payload: Request payload
            **kwargs: Additional request options
            
        Returns:
            Response dictionary
            
        Raises:
            ProviderError: If provider returns an error
            TimeoutError: If request times out
            RateLimitError: If rate limited
        """
        ...
    
    async def stream_request(
        self,
        endpoint: str,
        payload: Dict[str, Any],
        **kwargs: Any
    ) -> AsyncIterator[str]:
        """
        Make a streaming request to the provider API.
        
        Args:
            endpoint: API endpoint to call
            payload: Request payload
            **kwargs: Additional request options
            
        Yields:
            Response lines as strings
        """
        ...
    
    async def test_connection(self) -> bool:
        """
        Test connectivity and authentication (optional).
        
        Returns:
            True if connector is ready
            
        Raises:
            AuthenticationError: If credentials are invalid
            ServiceUnavailableError: If service is down
        """
        ...


# ============================================================================
# REGISTRY INTERFACE
# ============================================================================

@runtime_checkable
class IModelRegistry(Protocol):
    """
    Model registry interface for managing model metadata.
    
    The registry stores and provides access to metadata for all
    registered models.
    """
    
    def register_model(self, metadata: 'ModelMetadata') -> None:
        """
        Register a model with the registry.
        
        Args:
            metadata: Model metadata to register
            
        Raises:
            ValueError: If model is already registered
        """
        ...
    
    def get_model(self, model_name: str) -> Optional['ModelMetadata']:
        """
        Get metadata for a specific model.
        
        Args:
            model_name: Name of the model
            
        Returns:
            ModelMetadata if found, None otherwise
        """
        ...
    
    def get_all_models(self) -> Dict[str, 'ModelMetadata']:
        """
        Get all registered models.
        
        Returns:
            Dictionary mapping model names to metadata
        """
        ...
    
    def get_provider_models(self, provider: str) -> List[str]:
        """
        Get all models for a specific provider.
        
        Args:
            provider: Provider identifier
            
        Returns:
            List of model names
        """
        ...
    
    def get_family_models(self, family: str) -> List[str]:
        """
        Get all models in a specific family.
        
        Args:
            family: Model family identifier
            
        Returns:
            List of model names
        """
        ...
