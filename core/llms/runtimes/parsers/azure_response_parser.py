"""
Azure OpenAI Response Parser.

Parses Azure OpenAI API responses into standard LLMResponse objects.
"""

import time
from typing import Any, Dict, Optional
from ...interfaces.llm_interfaces import IResponseParser
from ...spec.llm_result import LLMResponse, LLMStreamChunk, LLMUsage
from ...spec.llm_schema import ModelMetadata
from ...exceptions import InvalidResponseError
from ...enum import FinishReason
from ...constants import (
    RESPONSE_FIELD_CHOICES,
    RESPONSE_FIELD_MESSAGE,
    RESPONSE_FIELD_CONTENT,
    RESPONSE_FIELD_FINISH_REASON,
    RESPONSE_FIELD_USAGE,
    RESPONSE_FIELD_PROMPT_TOKENS,
    RESPONSE_FIELD_COMPLETION_TOKENS,
    RESPONSE_FIELD_TOTAL_TOKENS,
    STREAM_FIELD_DELTA,
    STREAM_FIELD_CONTENT,
    MESSAGE_FIELD_ROLE,
    META_MODEL,
    META_ID,
    PROVIDER_AZURE,
    ERROR_MSG_RESPONSE_MISSING_CHOICES,
    FINISH_REASON_STOP,
    FINISH_REASON_LENGTH,
    FINISH_REASON_CONTENT_FILTER,
    FINISH_REASON_FUNCTION_CALL,
    DEFAULT_RESPONSE_ROLE,
)


class AzureResponseParser(IResponseParser):
    """
    Response parser for Azure OpenAI responses.
    
    Handles:
    - Standard chat completion responses
    - Streaming chunks
    - Usage statistics
    - Finish reasons
    
    Usage:
        parser = AzureResponseParser()
        response = parser.parse_response(raw_response, start_time, metadata)
    """
    
    def __init__(self, deployment_name: Optional[str] = None):
        """
        Initialize parser.
        
        Args:
            deployment_name: Azure deployment name (for metadata)
        """
        self.deployment_name = deployment_name
    
    def parse_response(
        self,
        response: Dict[str, Any],
        start_time: float,
        metadata: ModelMetadata
    ) -> LLMResponse:
        """
        Parse Azure OpenAI API response into LLMResponse.
        
        Args:
            response: Raw API response
            start_time: Request start time
            metadata: Model metadata
            
        Returns:
            LLMResponse object
            
        Raises:
            InvalidResponseError: If response format is invalid
        """
        try:
            choices = response.get(RESPONSE_FIELD_CHOICES, [])
            if not choices:
                raise InvalidResponseError(
                    ERROR_MSG_RESPONSE_MISSING_CHOICES,
                    provider=PROVIDER_AZURE,
                    details={"response": response}
                )
            
            message = choices[0].get(RESPONSE_FIELD_MESSAGE, {})
            content = message.get(RESPONSE_FIELD_CONTENT)
            
            # Handle null content
            if content is None:
                content = ""
            finish_reason = choices[0].get(RESPONSE_FIELD_FINISH_REASON)
            
            # Parse usage
            usage_data = response.get(RESPONSE_FIELD_USAGE, {})
            duration_ms = int((time.time() - start_time) * 1000)
            
            usage = LLMUsage(
                prompt_tokens=usage_data.get(RESPONSE_FIELD_PROMPT_TOKENS, 0),
                completion_tokens=usage_data.get(RESPONSE_FIELD_COMPLETION_TOKENS, 0),
                total_tokens=usage_data.get(RESPONSE_FIELD_TOTAL_TOKENS, 0),
                duration_ms=duration_ms
            )
            
            # Calculate cost if metadata provides pricing
            if usage.prompt_tokens > 0 and metadata:
                usage.cost_usd = metadata.estimate_cost(
                    usage.prompt_tokens,
                    usage.completion_tokens
                )
            
            return LLMResponse(
                content=content,
                role=message.get(MESSAGE_FIELD_ROLE, DEFAULT_RESPONSE_ROLE),
                finish_reason=self._map_finish_reason(finish_reason) if finish_reason else None,
                usage=usage,
                metadata={
                    META_MODEL: response.get(META_MODEL),
                    META_ID: response.get(META_ID),
                    "deployment": self.deployment_name,
                }
            )
        
        except (KeyError, TypeError, AttributeError) as e:
            raise InvalidResponseError(
                f"Failed to parse Azure OpenAI response: {str(e)}",
                provider=PROVIDER_AZURE,
                details={"error": str(e), "response": response}
            )
    
    def parse_stream_chunk(
        self,
        chunk_data: Dict[str, Any],
        metadata: ModelMetadata
    ) -> Optional[LLMStreamChunk]:
        """
        Parse streaming chunk.
        
        Args:
            chunk_data: Raw chunk data
            metadata: Model metadata
            
        Returns:
            Parsed LLMStreamChunk or None if chunk should be skipped
        """
        try:
            choices = chunk_data.get(RESPONSE_FIELD_CHOICES, [])
            if not choices:
                return None
            
            delta = choices[0].get(STREAM_FIELD_DELTA, {})
            content = delta.get(STREAM_FIELD_CONTENT, "")
            finish_reason = choices[0].get(RESPONSE_FIELD_FINISH_REASON)
            
            if content:
                return LLMStreamChunk(
                    content=content,
                    is_final=False
                )
            
            if finish_reason:
                return LLMStreamChunk(
                    content="",
                    is_final=True,
                    finish_reason=self._map_finish_reason(finish_reason)
                )
            
            return None
            
        except (KeyError, TypeError):
            return None
    
    def _map_finish_reason(self, reason: str) -> FinishReason:
        """Map Azure finish reason to standard enum."""
        mapping = {
            FINISH_REASON_STOP: FinishReason.STOP,
            FINISH_REASON_LENGTH: FinishReason.LENGTH,
            FINISH_REASON_CONTENT_FILTER: FinishReason.CONTENT_FILTER,
            FINISH_REASON_FUNCTION_CALL: FinishReason.FUNCTION_CALL,
            "tool_calls": FinishReason.FUNCTION_CALL,
        }
        return mapping.get(reason, FinishReason.STOP)

