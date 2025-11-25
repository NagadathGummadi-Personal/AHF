"""
LLM Result Models.

This module defines the data models for LLM responses, including
complete responses and streaming chunks.
"""

from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field
from ..enum import FinishReason
from ..constants import DEFAULT_RESPONSE_ROLE


class LLMUsage(BaseModel):
    """
    Usage statistics for an LLM request.
    
    Tracks token consumption and timing information.
    
    Attributes:
        prompt_tokens: Number of tokens in the prompt
        completion_tokens: Number of tokens in the completion
        total_tokens: Total tokens used (prompt + completion)
        duration_ms: Request duration in milliseconds
        cost_usd: Estimated cost in USD (optional)
    """
    
    prompt_tokens: int = Field(default=0, ge=0, description="Number of tokens in the prompt")
    completion_tokens: int = Field(default=0, ge=0, description="Number of tokens in the completion")
    total_tokens: int = Field(default=0, ge=0, description="Total tokens used")
    duration_ms: Optional[int] = Field(default=None, ge=0, description="Request duration in milliseconds")
    cost_usd: Optional[float] = Field(default=None, ge=0, description="Estimated cost in USD")
    
    def model_post_init(self, __context: Any) -> None:
        """Calculate total_tokens if not provided."""
        if self.total_tokens == 0 and (self.prompt_tokens > 0 or self.completion_tokens > 0):
            self.total_tokens = self.prompt_tokens + self.completion_tokens


class LLMResponse(BaseModel):
    """
    Complete response from an LLM (non-streaming).
    
    Contains the generated content, metadata, and usage statistics.
    
    Attributes:
        content: The generated content (usually text)
        role: Role of the response (usually 'assistant')
        finish_reason: Why generation stopped
        usage: Token usage and timing statistics
        metadata: Additional response metadata
        function_call: Function call data if applicable
        tool_calls: Tool calls if applicable
    
    Example:
        response = LLMResponse(
            content="The answer is 42",
            role="assistant",
            finish_reason=FinishReason.STOP,
            usage=LLMUsage(prompt_tokens=10, completion_tokens=5)
        )
    """
    
    content: Any = Field(description="Generated content")
    role: str = Field(default=DEFAULT_RESPONSE_ROLE, description="Response role")
    finish_reason: Optional[FinishReason] = Field(default=None, description="Why generation stopped")
    usage: Optional[LLMUsage] = Field(default=None, description="Token usage statistics")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    function_call: Optional[Dict[str, Any]] = Field(default=None, description="Function call data")
    tool_calls: Optional[List[Dict[str, Any]]] = Field(default=None, description="Tool calls")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "content": "Hello! How can I help you today?",
                    "role": "assistant",
                    "finish_reason": "stop",
                    "usage": {
                        "prompt_tokens": 10,
                        "completion_tokens": 8,
                        "total_tokens": 18
                    }
                }
            ]
        }
    }
    
    def get_text_content(self) -> str:
        """
        Get content as text string.
        
        Returns:
            Text content, converting if necessary
        """
        if isinstance(self.content, str):
            return self.content
        elif isinstance(self.content, dict) and 'text' in self.content:
            return self.content['text']
        return str(self.content)
    
    def has_function_call(self) -> bool:
        """Check if response contains a function call."""
        return self.function_call is not None
    
    def has_parallel_function_call(self) -> bool:
        """Check if response contains a parallel function call."""
        return self.parallel_function_call is not None 

    def has_tool_calls(self) -> bool:
        """Check if response contains tool calls."""
        return self.tool_calls is not None and len(self.tool_calls) > 0


class LLMStreamChunk(BaseModel):
    """
    A chunk from a streaming LLM response.
    
    Represents a fragment of content as it's being generated.
    
    Attributes:
        content: Content fragment (usually partial text)
        role: Role of the content (usually 'assistant')
        is_final: Whether this is the last chunk
        finish_reason: Why generation stopped (only on final chunk)
        usage: Usage statistics (usually only on final chunk)
        metadata: Additional chunk metadata
        delta: Raw delta object from provider
    
    Example:
        chunk = LLMStreamChunk(
            content="Hello",
            role="assistant",
            is_final=False
        )
    """
    
    content: str = Field(default="", description="Content fragment")
    role: Optional[str] = Field(default=DEFAULT_RESPONSE_ROLE, description="Content role")
    is_final: bool = Field(default=False, description="Whether this is the last chunk")
    finish_reason: Optional[FinishReason] = Field(default=None, description="Why generation stopped")
    usage: Optional[LLMUsage] = Field(default=None, description="Usage statistics")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    delta: Optional[Dict[str, Any]] = Field(default=None, description="Raw delta from provider")
    
    def is_empty(self) -> bool:
        """Check if chunk has no content."""
        return len(self.content) == 0
    
    def has_usage(self) -> bool:
        """Check if chunk includes usage statistics."""
        return self.usage is not None


class LLMError(BaseModel):
    """
    Error information from an LLM request.
    
    Used to structure error responses in a consistent way.
    
    Attributes:
        error_type: Type/category of error
        message: Error message
        code: Provider-specific error code
        details: Additional error details
    """
    
    error_type: str = Field(description="Error type/category")
    message: str = Field(description="Error message")
    code: Optional[str] = Field(default=None, description="Provider error code")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional error details")


# ============================================================================
# Media Output Response Types
# ============================================================================

class LLMImageResponse(BaseModel):
    """
    Image generation response.
    
    Contains generated image data or URL along with metadata.
    
    Attributes:
        image_url: URL to the generated image (if hosted)
        image_data: Raw image bytes (if returned directly)
        revised_prompt: Actual prompt used by model (if modified)
        format: Image format (png, jpg, webp, etc.)
        size: Image dimensions (e.g., "1024x1024")
        usage: Token usage and cost statistics
        metadata: Additional response metadata
    
    Example:
        response = LLMImageResponse(
            image_url="https://cdn.example.com/generated.png",
            revised_prompt="A realistic photo of a sunset",
            format="png",
            size="1024x1024"
        )
    """
    
    image_url: Optional[str] = Field(default=None, description="URL to generated image")
    image_data: Optional[bytes] = Field(default=None, description="Raw image bytes")
    revised_prompt: Optional[str] = Field(default=None, description="Revised prompt used")
    format: str = Field(default="png", description="Image format")
    size: Optional[str] = Field(default=None, description="Image dimensions")
    usage: Optional[LLMUsage] = Field(default=None, description="Usage statistics")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    def has_url(self) -> bool:
        """Check if response has image URL."""
        return self.image_url is not None
    
    def has_data(self) -> bool:
        """Check if response has raw image data."""
        return self.image_data is not None


class LLMImageChunk(BaseModel):
    """
    Streaming image generation chunk.
    
    For progressive image generation (if supported by model).
    
    Attributes:
        chunk_data: Image data fragment
        is_final: Whether this is the last chunk
        progress_percent: Generation progress (0-100)
        metadata: Additional chunk metadata
    """
    
    chunk_data: bytes = Field(description="Image data fragment")
    is_final: bool = Field(default=False, description="Whether this is the last chunk")
    progress_percent: Optional[float] = Field(default=None, ge=0, le=100, description="Progress percentage")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class LLMAudioResponse(BaseModel):
    """
    Audio generation response.
    
    Contains generated audio data or URL along with metadata.
    
    Attributes:
        audio_url: URL to the generated audio (if hosted)
        audio_data: Raw audio bytes (if returned directly)
        format: Audio format (mp3, wav, opus, etc.)
        duration_seconds: Audio duration in seconds
        sample_rate: Sample rate in Hz
        usage: Token usage and cost statistics
        metadata: Additional response metadata
    
    Example:
        response = LLMAudioResponse(
            audio_data=audio_bytes,
            format="mp3",
            duration_seconds=5.2,
            sample_rate=24000
        )
    """
    
    audio_url: Optional[str] = Field(default=None, description="URL to generated audio")
    audio_data: Optional[bytes] = Field(default=None, description="Raw audio bytes")
    format: str = Field(default="mp3", description="Audio format")
    duration_seconds: Optional[float] = Field(default=None, ge=0, description="Duration in seconds")
    sample_rate: Optional[int] = Field(default=None, ge=0, description="Sample rate in Hz")
    usage: Optional[LLMUsage] = Field(default=None, description="Usage statistics")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    def has_url(self) -> bool:
        """Check if response has audio URL."""
        return self.audio_url is not None
    
    def has_data(self) -> bool:
        """Check if response has raw audio data."""
        return self.audio_data is not None


class LLMAudioChunk(BaseModel):
    """
    Streaming audio generation chunk.
    
    For realtime audio generation (TTS, music, etc.).
    
    Attributes:
        chunk_data: Audio data fragment
        is_final: Whether this is the last chunk
        format: Audio format of the chunk
        sample_rate: Sample rate in Hz
        duration_ms: Duration of this chunk in milliseconds
        metadata: Additional chunk metadata
    """
    
    chunk_data: bytes = Field(description="Audio data fragment")
    is_final: bool = Field(default=False, description="Whether this is the last chunk")
    format: str = Field(default="mp3", description="Audio format")
    sample_rate: Optional[int] = Field(default=None, ge=0, description="Sample rate in Hz")
    duration_ms: Optional[int] = Field(default=None, ge=0, description="Chunk duration in ms")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class LLMVideoResponse(BaseModel):
    """
    Video generation response.
    
    Contains generated video data or URL along with metadata.
    
    Attributes:
        video_url: URL to the generated video (if hosted)
        video_data: Raw video bytes (if returned directly)
        format: Video format (mp4, webm, etc.)
        duration_seconds: Video duration in seconds
        resolution: Video resolution (e.g., "1920x1080")
        frame_rate: Frames per second
        usage: Token usage and cost statistics
        metadata: Additional response metadata
    
    Example:
        response = LLMVideoResponse(
            video_url="https://cdn.example.com/generated.mp4",
            format="mp4",
            duration_seconds=10.5,
            resolution="1920x1080",
            frame_rate=30
        )
    """
    
    video_url: Optional[str] = Field(default=None, description="URL to generated video")
    video_data: Optional[bytes] = Field(default=None, description="Raw video bytes")
    format: str = Field(default="mp4", description="Video format")
    duration_seconds: Optional[float] = Field(default=None, ge=0, description="Duration in seconds")
    resolution: Optional[str] = Field(default=None, description="Video resolution")
    frame_rate: Optional[int] = Field(default=None, ge=0, description="Frames per second")
    usage: Optional[LLMUsage] = Field(default=None, description="Usage statistics")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    def has_url(self) -> bool:
        """Check if response has video URL."""
        return self.video_url is not None
    
    def has_data(self) -> bool:
        """Check if response has raw video data."""
        return self.video_data is not None


class LLMVideoChunk(BaseModel):
    """
    Streaming video generation chunk.
    
    For progressive video generation.
    
    Attributes:
        chunk_data: Video data fragment
        is_final: Whether this is the last chunk
        progress_percent: Generation progress (0-100)
        format: Video format
        metadata: Additional chunk metadata
    """
    
    chunk_data: bytes = Field(description="Video data fragment")
    is_final: bool = Field(default=False, description="Whether this is the last chunk")
    progress_percent: Optional[float] = Field(default=None, ge=0, le=100, description="Progress percentage")
    format: str = Field(default="mp4", description="Video format")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


# Helper functions for creating responses

def create_response(
    content: Any,
    usage: Optional[LLMUsage] = None,
    finish_reason: Optional[FinishReason] = None,
    **kwargs
) -> LLMResponse:
    """
    Helper to create an LLMResponse.
    
    Args:
        content: Generated content
        usage: Optional usage statistics
        finish_reason: Optional finish reason
        **kwargs: Additional fields
        
    Returns:
        LLMResponse instance
    """
    return LLMResponse(
        content=content,
        usage=usage,
        finish_reason=finish_reason,
        **kwargs
    )


def create_chunk(
    content: str,
    is_final: bool = False,
    usage: Optional[LLMUsage] = None,
    **kwargs
) -> LLMStreamChunk:
    """
    Helper to create an LLMStreamChunk.
    
    Args:
        content: Content fragment
        is_final: Whether this is the final chunk
        usage: Optional usage statistics
        **kwargs: Additional fields
        
    Returns:
        LLMStreamChunk instance
    """
    return LLMStreamChunk(
        content=content,
        is_final=is_final,
        usage=usage,
        **kwargs
    )

