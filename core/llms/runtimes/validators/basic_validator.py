"""
Basic LLM Validator Implementation.

Provides comprehensive validation for messages and parameters.
This is the default validator used by all LLM implementations.
"""

from typing import Any, Dict, List, Optional
from ...interfaces.llm_interfaces import ILLMValidator, Messages, Parameters
from ...spec.llm_schema import ModelMetadata
from ...exceptions import InputValidationError, TokenLimitError
from ...constants import (
    MESSAGE_FIELD_ROLE,
    MESSAGE_FIELD_CONTENT,
    ERROR_MSG_EMPTY_MESSAGES,
    ERROR_MSG_MESSAGE_NOT_DICT,
    ERROR_MSG_MISSING_ROLE,
    ERROR_MSG_MISSING_CONTENT,
    CHARS_PER_TOKEN_ESTIMATE,
    TOKENS_PER_MESSAGE_OVERHEAD,
)


class BasicLLMValidator(ILLMValidator):
    """
    Basic implementation of ILLMValidator with comprehensive validation.
    
    Provides validation for:
    - Message structure and content
    - Required fields (role, content)
    - Token limit estimation
    - Parameter constraints
    
    This is the default validator for all LLM implementations.
    
    Usage:
        validator = BasicLLMValidator()
        await validator.validate_messages(messages, metadata)
        await validator.validate_parameters(params, metadata)
        await validator.validate_token_limits(messages, 1000, metadata)
    """
    
    async def validate_messages(
        self,
        messages: Messages,
        metadata: ModelMetadata
    ) -> None:
        """
        Validate messages before sending to LLM.
        
        Validates:
        - Messages list is not empty
        - Each message is a dictionary
        - Each message has 'role' field
        - Each message has 'content' field
        
        Args:
            messages: List of message dicts
            metadata: Model metadata with constraints
            
        Raises:
            InputValidationError: If messages are invalid
        """
        if not messages:
            raise InputValidationError(
                ERROR_MSG_EMPTY_MESSAGES,
                model_name=metadata.model_name
            )
        
        for i, msg in enumerate(messages):
            if not isinstance(msg, dict):
                raise InputValidationError(
                    ERROR_MSG_MESSAGE_NOT_DICT.format(i=i),
                    model_name=metadata.model_name
                )
            
            if MESSAGE_FIELD_ROLE not in msg:
                raise InputValidationError(
                    ERROR_MSG_MISSING_ROLE.format(i=i),
                    model_name=metadata.model_name
                )
            
            # Content can be string or list (for multimodal)
            if MESSAGE_FIELD_CONTENT not in msg:
                raise InputValidationError(
                    ERROR_MSG_MISSING_CONTENT.format(i=i),
                    model_name=metadata.model_name
                )
    
    async def validate_parameters(
        self,
        params: Parameters,
        metadata: ModelMetadata
    ) -> None:
        """
        Validate parameters against model constraints.
        
        Validates:
        - max_tokens within model limits
        - temperature in valid range (if supported)
        - Other model-specific constraints
        
        Args:
            params: Parameters to validate
            metadata: Model metadata with constraints
            
        Raises:
            InputValidationError: If parameters are invalid
        """
        # Validate max_tokens if present
        max_tokens = params.get('max_tokens') or params.get('max_completion_tokens')
        if max_tokens is not None:
            if max_tokens <= 0:
                raise InputValidationError(
                    f"max_tokens must be positive, got {max_tokens}",
                    model_name=metadata.model_name
                )
            if max_tokens > metadata.max_output_tokens:
                raise InputValidationError(
                    f"max_tokens ({max_tokens}) exceeds model limit ({metadata.max_output_tokens})",
                    model_name=metadata.model_name
                )
        
        # Validate temperature if present and supported
        temperature = params.get('temperature')
        if temperature is not None:
            if not isinstance(temperature, (int, float)):
                raise InputValidationError(
                    f"temperature must be a number, got {type(temperature).__name__}",
                    model_name=metadata.model_name
                )
            if temperature < 0 or temperature > 2:
                raise InputValidationError(
                    f"temperature must be between 0 and 2, got {temperature}",
                    model_name=metadata.model_name
                )
    
    async def validate_token_limits(
        self,
        messages: Messages,
        max_output_tokens: int,
        metadata: ModelMetadata
    ) -> None:
        """
        Validate that token limits won't be exceeded.
        
        Uses simple heuristic: ~4 chars per token + message overhead.
        
        Args:
            messages: Input messages
            max_output_tokens: Requested max output tokens
            metadata: Model metadata with token limits
            
        Raises:
            TokenLimitError: If limits would be exceeded
        """
        estimated_input = self._estimate_tokens(messages)
        
        if estimated_input > metadata.max_context_length:
            raise TokenLimitError(
                f"Input tokens ({estimated_input}) exceed max context length ({metadata.max_context_length})",
                model_name=metadata.model_name,
                token_count=estimated_input,
                token_limit=metadata.max_context_length
            )
        
        total_estimated = estimated_input + max_output_tokens
        if total_estimated > metadata.max_context_length:
            raise TokenLimitError(
                f"Total tokens ({total_estimated}) would exceed max context length ({metadata.max_context_length})",
                model_name=metadata.model_name,
                token_count=total_estimated,
                token_limit=metadata.max_context_length
            )
    
    def _estimate_tokens(self, messages: Messages) -> int:
        """
        Estimate token count for messages.
        
        Uses simple heuristic: ~4 chars per token + message overhead.
        
        Args:
            messages: Messages to estimate
            
        Returns:
            Estimated token count
        """
        total_chars = 0
        for msg in messages:
            content = msg.get(MESSAGE_FIELD_CONTENT, "")
            if isinstance(content, str):
                total_chars += len(content)
            elif isinstance(content, list):
                # Multimodal content
                for item in content:
                    if isinstance(item, dict) and 'text' in item:
                        total_chars += len(item['text'])
        
        estimated_tokens = (total_chars // CHARS_PER_TOKEN_ESTIMATE) + (len(messages) * TOKENS_PER_MESSAGE_OVERHEAD)
        return estimated_tokens

