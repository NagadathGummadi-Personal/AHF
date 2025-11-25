"""
Base LLM Implementation.

This module provides the abstract base class for all LLM implementations.
All LLMs implement just 2 core methods: get_answer and stream_answer.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, AsyncIterator, Optional
from ...spec.llm_schema import ModelMetadata
from ...spec.llm_result import (
    LLMResponse,
    LLMStreamChunk,
    LLMUsage,
    LLMImageResponse,
    LLMImageChunk,
    LLMAudioResponse,
    LLMAudioChunk,
    LLMVideoResponse,
    LLMVideoChunk,
)
from ...spec.llm_context import LLMContext
from ...exceptions import InputValidationError, TokenLimitError, UnsupportedOperationError
from ...enum import OutputMediaType
from .connector import BaseConnector
from ...constants import (
    CHARS_PER_TOKEN_ESTIMATE,
    TOKENS_PER_MESSAGE_OVERHEAD,
    META_PROVIDER,
    META_MODEL_NAME,
    MESSAGE_FIELD_ROLE,
    MESSAGE_FIELD_CONTENT,
    ERROR_MSG_EMPTY_MESSAGES,
    ERROR_MSG_MESSAGE_NOT_DICT,
    ERROR_MSG_MISSING_ROLE,
    ERROR_MSG_MISSING_CONTENT,
)


class BaseLLM(ABC):
    """
    Abstract base class for all LLM implementations.
    
    All LLMs must implement 2 core methods:
    1. get_answer() - Complete response (non-streaming)
    2. stream_answer() - Streaming response
    
    The base class provides:
    - Metadata storage and access
    - Parameter validation and merging
    - Token estimation
    - Cost calculation
    - Capability queries
    
    Attributes:
        metadata: Model metadata with capabilities and limits
        connector: Provider connector for API communication
    """
    
    def __init__(self, metadata: ModelMetadata, connector: 'BaseConnector'):
        """
        Initialize base LLM.
        
        Args:
            metadata: Model metadata
            connector: Provider connector
        """
        self.metadata = metadata
        self.connector = connector
    
    def _check_text_output_support(self) -> None:
        """
        Check if model supports text output.
        
        Call this at the start of get_answer() and stream_answer() implementations.
        
        Raises:
            UnsupportedOperationError: If model doesn't support text output
        """
        if not self.metadata.supports_output_type(OutputMediaType.TEXT):
            raise UnsupportedOperationError(
                f"{self.metadata.model_name} does not support text output",
                model_name=self.metadata.model_name,
                operation="get_answer",
                details={
                    "supported_output_types": [t.value for t in self.metadata.supported_output_types],
                    "hint": "This model is for media generation only. Use get_image(), get_audio(), or get_video()."
                }
            )
    
    @abstractmethod
    async def get_answer(
        self,
        messages: List[Dict[str, Any]],
        ctx: LLMContext,
        **kwargs: Any
    ) -> LLMResponse:
        """
        Get a complete response from the LLM (non-streaming).
        
        IMPORTANT: Implementations should call self._check_text_output_support()
        at the start to ensure the model supports text output.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            ctx: LLM context with request metadata
            **kwargs: Additional parameters (temperature, max_tokens, etc.)
            
        Returns:
            LLMResponse with generated content and usage
            
        Raises:
            UnsupportedOperationError: If model doesn't support text output
            InputValidationError: If input is invalid
            TokenLimitError: If token limits exceeded
            
        Example:
            messages = [{"role": "user", "content": "Hello!"}]
            response = await llm.get_answer(messages, ctx, temperature=0.7)
            print(response.content)
        """
        pass
    
    @abstractmethod
    async def stream_answer(
        self,
        messages: List[Dict[str, Any]],
        ctx: LLMContext,
        **kwargs: Any
    ) -> AsyncIterator[LLMStreamChunk]:
        """
        Get a streaming response from the LLM.
        
        IMPORTANT: Implementations should call self._check_text_output_support()
        at the start to ensure the model supports text output.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            ctx: LLM context with request metadata
            **kwargs: Additional parameters (temperature, max_tokens, etc.)
            
        Yields:
            LLMStreamChunk objects as content is generated
            
        Raises:
            UnsupportedOperationError: If model doesn't support text output
            InputValidationError: If input is invalid
            TokenLimitError: If token limits exceeded
            
        Example:
            messages = [{"role": "user", "content": "Tell a story"}]
            async for chunk in llm.stream_answer(messages, ctx):
                print(chunk.content, end='', flush=True)
        """
        pass
    
    # ============================================================================
    # UTILITY METHODS
    # ============================================================================
    
    def get_supported_capabilities(self) -> Dict[str, Any]:
        """
        Get capabilities supported by this LLM.
        
        Returns:
            Dictionary with capability information
        """
        provider = self.metadata.provider
        provider_str = provider if isinstance(provider, str) else provider.value
        
        return {
            META_PROVIDER: provider_str,
            META_MODEL_NAME: self.metadata.model_name,
            "supported_input_types": [
                t if isinstance(t, str) else t.value 
                for t in self.metadata.supported_input_types
            ],
            "supported_output_types": [
                t if isinstance(t, str) else t.value 
                for t in self.metadata.supported_output_types
            ],
            "supports_streaming": self.metadata.supports_streaming,
            "supports_function_calling": self.metadata.supports_function_calling,
            "supports_vision": self.metadata.supports_vision,
            "supports_json_mode": self.metadata.supports_json_mode,
            "max_context_length": self.metadata.max_context_length,
            "max_output_tokens": self.metadata.max_output_tokens,
        }
    
    def _merge_parameters(self, user_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge user parameters with model defaults.
        
        Args:
            user_params: User-provided parameters
            
        Returns:
            Merged parameters
        """
        merged = self.metadata.default_parameters.copy()
        merged.update({k: v for k, v in user_params.items() if v is not None})
        return merged
    
    def _apply_parameter_mappings(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map standard parameter names to provider-specific names.
        
        Args:
            params: Parameters with standard names
            
        Returns:
            Parameters with provider-specific names
        """
        mapped = {}
        for key, value in params.items():
            mapped_key = self.metadata.get_parameter_mapping(key)
            mapped[mapped_key] = value
        return mapped
    
    def _validate_messages(self, messages: List[Dict[str, Any]]) -> None:
        """
        Validate message format and content.
        
        Args:
            messages: Messages to validate
            
        Raises:
            InputValidationError: If messages are invalid
        """
        if not messages:
            raise InputValidationError(
                ERROR_MSG_EMPTY_MESSAGES,
                model_name=self.metadata.model_name
            )
        
        for i, msg in enumerate(messages):
            if not isinstance(msg, dict):
                raise InputValidationError(
                    ERROR_MSG_MESSAGE_NOT_DICT.format(i=i),
                    model_name=self.metadata.model_name
                )
            
            if MESSAGE_FIELD_ROLE not in msg:
                raise InputValidationError(
                    ERROR_MSG_MISSING_ROLE.format(i=i),
                    model_name=self.metadata.model_name
                )
            
            if MESSAGE_FIELD_CONTENT not in msg:
                raise InputValidationError(
                    ERROR_MSG_MISSING_CONTENT.format(i=i),
                    model_name=self.metadata.model_name
                )
    
    def _estimate_tokens(self, messages: List[Dict[str, Any]]) -> int:
        """
        Estimate token count for messages.
        
        Uses simple heuristic: ~4 chars per token + message overhead.
        
        Args:
            messages: Messages to estimate
            
        Returns:
            Estimated token count
        """
        total_chars = sum(len(str(msg.get(MESSAGE_FIELD_CONTENT, ""))) for msg in messages)
        estimated_tokens = (total_chars // CHARS_PER_TOKEN_ESTIMATE) + (len(messages) * TOKENS_PER_MESSAGE_OVERHEAD)
        return estimated_tokens
    
    def _validate_token_limits(
        self,
        messages: List[Dict[str, Any]],
        max_output_tokens: Optional[int] = None
    ) -> None:
        """
        Validate that token limits won't be exceeded.
        
        Args:
            messages: Input messages
            max_output_tokens: Requested max output tokens
            
        Raises:
            TokenLimitError: If limits would be exceeded
        """
        estimated_input = self._estimate_tokens(messages)
        requested_output = max_output_tokens or self.metadata.max_output_tokens
        
        if estimated_input > self.metadata.max_context_length:
            raise TokenLimitError(
                f"Input tokens ({estimated_input}) exceed max context length ({self.metadata.max_context_length})",
                model_name=self.metadata.model_name,
                token_count=estimated_input,
                token_limit=self.metadata.max_context_length
            )
        
        total_estimated = estimated_input + requested_output
        if total_estimated > self.metadata.max_context_length:
            raise TokenLimitError(
                f"Total tokens ({total_estimated}) would exceed max context length ({self.metadata.max_context_length})",
                model_name=self.metadata.model_name,
                token_count=total_estimated,
                token_limit=self.metadata.max_context_length
            )
    
    def _calculate_cost(self, usage: LLMUsage) -> Optional[float]:
        """
        Calculate cost based on usage.
        
        Args:
            usage: Usage statistics
            
        Returns:
            Estimated cost in USD, or None if pricing unavailable
        """
        return self.metadata.estimate_cost(
            usage.prompt_tokens,
            usage.completion_tokens
        )
    
    # ============================================================================
    # VISION HELPER (MULTIMODAL INPUT)
    # ============================================================================
    
    async def get_answer_with_vision(
        self,
        prompt: str,
        images: List[str],
        ctx: LLMContext,
        **kwargs: Any
    ) -> LLMResponse:
        """
        Convenience method for vision-enabled models.
        
        Generates response with both text and image inputs. This is a helper
        that constructs multimodal messages and calls get_answer().
        
        Args:
            prompt: Text prompt
            images: List of image URLs or base64-encoded images
            ctx: LLM context
            **kwargs: Additional parameters (temperature, max_tokens, etc.)
            
        Returns:
            LLMResponse with generated content
            
        Raises:
            UnsupportedOperationError: If model doesn't support vision
            InputValidationError: If input is invalid
            
        Example:
            response = await llm.get_answer_with_vision(
                prompt="What's in this image?",
                images=["https://example.com/image.jpg"],
                ctx=ctx,
                max_tokens=500
            )
        """
        # Check if model supports vision
        if not self.metadata.supports_vision:
            raise UnsupportedOperationError(
                f"{self.metadata.model_name} does not support vision/image inputs",
                model_name=self.metadata.model_name,
                operation="get_answer_with_vision",
                details={
                    "supported_input_types": [t.value for t in self.metadata.supported_input_types]
                }
            )
        
        # Build multimodal message
        content = [{"type": "text", "text": prompt}]
        
        # Add images
        for image in images:
            content.append({
                "type": "image_url",
                "image_url": {"url": image}
            })
        
        messages = [{"role": "user", "content": content}]
        
        # Use standard get_answer with multimodal messages
        return await self.get_answer(messages, ctx, **kwargs)
    
    # ============================================================================
    # MEDIA OUTPUT METHODS (IMAGE, AUDIO, VIDEO GENERATION)
    # ============================================================================
    
    async def get_image(
        self,
        messages: List[Dict[str, Any]],
        ctx: LLMContext,
        **kwargs: Any
    ) -> LLMImageResponse:
        """
        Generate an image (non-streaming).
        
        For models that support image generation (DALL-E, Stable Diffusion, etc.).
        Text-only models will raise UnsupportedOperationError.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            ctx: LLM context
            **kwargs: Additional parameters (size, quality, style, etc.)
            
        Returns:
            LLMImageResponse with generated image
            
        Raises:
            UnsupportedOperationError: If model doesn't support image output
            
        Example:
            response = await llm.get_image(
                messages=[{"role": "user", "content": "A sunset over mountains"}],
                ctx=ctx,
                size="1024x1024"
            )
        """
        if not self.metadata.supports_output_type(OutputMediaType.IMAGE):
            raise UnsupportedOperationError(
                f"{self.metadata.model_name} does not support image generation",
                model_name=self.metadata.model_name,
                operation="get_image",
                details={
                    "supported_output_types": [t.value for t in self.metadata.supported_output_types],
                    "hint": "This model only supports text output. Use get_answer() instead."
                }
            )
        
        # Subclasses that support image generation must override this
        raise NotImplementedError(
            f"Image generation not implemented for {self.metadata.model_name}"
        )
    
    async def stream_image(
        self,
        messages: List[Dict[str, Any]],
        ctx: LLMContext,
        **kwargs: Any
    ) -> AsyncIterator[LLMImageChunk]:
        """
        Generate an image (streaming/progressive).
        
        For progressive image generation if supported by the model.
        
        Args:
            messages: List of message dicts
            ctx: LLM context
            **kwargs: Additional parameters
            
        Yields:
            LLMImageChunk objects as image is generated
            
        Raises:
            UnsupportedOperationError: If model doesn't support streaming image output
        """
        if not self.metadata.supports_output_type(OutputMediaType.IMAGE):
            raise UnsupportedOperationError(
                f"{self.metadata.model_name} does not support image generation",
                model_name=self.metadata.model_name,
                operation="stream_image",
                details={
                    "supported_output_types": [t.value for t in self.metadata.supported_output_types]
                }
            )
        
        # Most image generation models don't support streaming
        raise UnsupportedOperationError(
            f"{self.metadata.model_name} does not support streaming image generation",
            model_name=self.metadata.model_name,
            operation="stream_image",
            details={"hint": "Use get_image() for non-streaming image generation"}
        )
    
    async def get_audio(
        self,
        messages: List[Dict[str, Any]],
        ctx: LLMContext,
        **kwargs: Any
    ) -> LLMAudioResponse:
        """
        Generate audio (non-streaming).
        
        For models that support audio generation (TTS, music generation, etc.).
        Text-only models will raise UnsupportedOperationError.
        
        Args:
            messages: List of message dicts
            ctx: LLM context
            **kwargs: Additional parameters (voice, speed, format, etc.)
            
        Returns:
            LLMAudioResponse with generated audio
            
        Raises:
            UnsupportedOperationError: If model doesn't support audio output
            
        Example:
            response = await llm.get_audio(
                messages=[{"role": "user", "content": "Hello, how are you?"}],
                ctx=ctx,
                voice="alloy",
                format="mp3"
            )
        """
        if not self.metadata.supports_output_type(OutputMediaType.AUDIO):
            raise UnsupportedOperationError(
                f"{self.metadata.model_name} does not support audio generation",
                model_name=self.metadata.model_name,
                operation="get_audio",
                details={
                    "supported_output_types": [t.value for t in self.metadata.supported_output_types],
                    "hint": "This model only supports text output. Use get_answer() instead."
                }
            )
        
        raise NotImplementedError(
            f"Audio generation not implemented for {self.metadata.model_name}"
        )
    
    async def stream_audio(
        self,
        messages: List[Dict[str, Any]],
        ctx: LLMContext,
        **kwargs: Any
    ) -> AsyncIterator[LLMAudioChunk]:
        """
        Generate audio (streaming/realtime).
        
        For realtime audio generation (streaming TTS, realtime voice, etc.).
        
        Args:
            messages: List of message dicts
            ctx: LLM context
            **kwargs: Additional parameters
            
        Yields:
            LLMAudioChunk objects as audio is generated
            
        Raises:
            UnsupportedOperationError: If model doesn't support streaming audio output
            
        Example:
            async for chunk in llm.stream_audio(messages, ctx, voice="nova"):
                audio_player.play(chunk.chunk_data)
        """
        if not self.metadata.supports_output_type(OutputMediaType.AUDIO):
            raise UnsupportedOperationError(
                f"{self.metadata.model_name} does not support audio generation",
                model_name=self.metadata.model_name,
                operation="stream_audio",
                details={
                    "supported_output_types": [t.value for t in self.metadata.supported_output_types]
                }
            )
        
        raise NotImplementedError(
            f"Streaming audio generation not implemented for {self.metadata.model_name}"
        )
    
    async def get_video(
        self,
        messages: List[Dict[str, Any]],
        ctx: LLMContext,
        **kwargs: Any
    ) -> LLMVideoResponse:
        """
        Generate video (non-streaming).
        
        For models that support video generation (Sora, etc.).
        Text-only models will raise UnsupportedOperationError.
        
        Args:
            messages: List of message dicts
            ctx: LLM context
            **kwargs: Additional parameters (duration, resolution, fps, etc.)
            
        Returns:
            LLMVideoResponse with generated video
            
        Raises:
            UnsupportedOperationError: If model doesn't support video output
            
        Example:
            response = await llm.get_video(
                messages=[{"role": "user", "content": "A cat playing piano"}],
                ctx=ctx,
                duration=5,
                resolution="1920x1080"
            )
        """
        if not self.metadata.supports_output_type(OutputMediaType.VIDEO):
            raise UnsupportedOperationError(
                f"{self.metadata.model_name} does not support video generation",
                model_name=self.metadata.model_name,
                operation="get_video",
                details={
                    "supported_output_types": [t.value for t in self.metadata.supported_output_types],
                    "hint": "This model only supports text output. Use get_answer() instead."
                }
            )
        
        raise NotImplementedError(
            f"Video generation not implemented for {self.metadata.model_name}"
        )
    
    async def stream_video(
        self,
        messages: List[Dict[str, Any]],
        ctx: LLMContext,
        **kwargs: Any
    ) -> AsyncIterator[LLMVideoChunk]:
        """
        Generate video (streaming/progressive).
        
        For progressive video generation if supported by the model.
        
        Args:
            messages: List of message dicts
            ctx: LLM context
            **kwargs: Additional parameters
            
        Yields:
            LLMVideoChunk objects as video is generated
            
        Raises:
            UnsupportedOperationError: If model doesn't support streaming video output
        """
        if not self.metadata.supports_output_type(OutputMediaType.VIDEO):
            raise UnsupportedOperationError(
                f"{self.metadata.model_name} does not support video generation",
                model_name=self.metadata.model_name,
                operation="stream_video",
                details={
                    "supported_output_types": [t.value for t in self.metadata.supported_output_types]
                }
            )
        
        raise NotImplementedError(
            f"Streaming video generation not implemented for {self.metadata.model_name}"
        )

