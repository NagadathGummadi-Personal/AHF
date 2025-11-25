"""
No-Op LLM Validator Implementation.

Disables validation for development/testing or gradual rollouts.
"""

from typing import Any, Dict, List
from ...interfaces.llm_interfaces import ILLMValidator, Messages, Parameters
from ...spec.llm_schema import ModelMetadata


class NoOpLLMValidator(ILLMValidator):
    """
    No-op implementation of ILLMValidator that doesn't perform validation.
    
    Useful for:
    - Development/testing
    - Disabling validation for specific use cases
    - Performance-critical paths where validation is done elsewhere
    - Gradually rolling out validation
    
    Usage:
        validator = NoOpLLMValidator()
        await validator.validate_messages(messages, metadata)  # Always passes
        await validator.validate_parameters(params, metadata)  # Always passes
    """
    
    async def validate_messages(
        self,
        messages: Messages,
        metadata: ModelMetadata
    ) -> None:
        """Validate messages (no-op implementation)."""
        pass
    
    async def validate_parameters(
        self,
        params: Parameters,
        metadata: ModelMetadata
    ) -> None:
        """Validate parameters (no-op implementation)."""
        pass
    
    async def validate_token_limits(
        self,
        messages: Messages,
        max_output_tokens: int,
        metadata: ModelMetadata
    ) -> None:
        """Validate token limits (no-op implementation)."""
        pass

