"""
Base Metadata for LLM Models.

This module provides the base class for model metadata definitions.
"""

from typing import Dict, Any, Set
from abc import ABC


class BaseMetadata(ABC):
    """
    Base class for model metadata.
    
    Defines the interface for model-specific configuration and capabilities.
    Each model should subclass this and define its specific attributes.
    
    Attributes:
        NAME: Model identifier
        DISPLAY_NAME: Human-readable model name
        PROVIDER: Provider name (azure, openai, etc.)
        MAX_TOKENS: Maximum output tokens
        MAX_CONTEXT_LENGTH: Maximum context window
        COST_PER_1K_INPUT: Cost per 1K input tokens (USD)
        COST_PER_1K_OUTPUT: Cost per 1K output tokens (USD)
        SUPPORTED_PARAMS: Set of supported parameter names
    """
    
    NAME: str
    DISPLAY_NAME: str
    PROVIDER: str
    MAX_TOKENS: int
    MAX_CONTEXT_LENGTH: int
    COST_PER_1K_INPUT: float
    COST_PER_1K_OUTPUT: float
    SUPPORTED_PARAMS: Set[str]
    
    @classmethod
    def validate_params(cls, params: Dict[str, Any]) -> None:
        """
        Validate parameters for this model.
        
        Args:
            params: Parameters to validate
            
        Raises:
            ValueError: If parameters are invalid
        """
        for param in params:
            if param not in cls.SUPPORTED_PARAMS:
                raise ValueError(
                    f"Parameter '{param}' not supported by {cls.NAME}. "
                    f"Supported: {cls.SUPPORTED_PARAMS}"
                )



