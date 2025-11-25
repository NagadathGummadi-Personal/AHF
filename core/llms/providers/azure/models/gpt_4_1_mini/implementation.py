"""
Azure GPT-4.1 Mini LLM Implementation.

Model-specific implementation that uses pluggable components from AzureBaseLLM.

Official Model: https://ai.azure.com/catalog/models/gpt-4.1
Capabilities: https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/batch

This implementation:
- Uses the pluggable architecture from AzureBaseLLM
- Provides a custom transformer for GPT-4.1 specific parameter handling
- Can accept custom validators, parsers, and handlers

Example Usage:
    # Default components
    llm = GPT_4_1_MiniLLM(connector)
    
    # Custom validator (skip validation)
    llm = GPT_4_1_MiniLLM(
        connector,
        validator=LLMValidatorFactory.get_validator('noop')
    )
    
    # Custom transformer
    llm = GPT_4_1_MiniLLM(
        connector,
        transformer=MyCustomTransformer()
    )
"""

from typing import Dict, Any, List, Optional
from ...base_implementation import AzureBaseLLM
from .metadata import GPT_4_1_MiniMetadata
from .....interfaces.llm_interfaces import (
    ILLMValidator,
    IParameterTransformer,
    IResponseParser,
    IStructuredOutputHandler,
)
from .....runtimes.transformers import AzureGPT4Transformer
from utils.logging.LoggerAdaptor import LoggerAdaptor


class GPT_4_1_MiniLLM(AzureBaseLLM):
    """
    GPT-4.1 Mini specific LLM implementation with pluggable components.
    
    Uses the pluggable architecture from AzureBaseLLM with a default
    AzureGPT4Transformer for parameter handling.
    
    Default Components:
    - Validator: BasicLLMValidator
    - Transformer: AzureGPT4Transformer (max_tokens → max_completion_tokens)
    - Parser: AzureResponseParser
    - StructuredHandler: BasicStructuredHandler
    
    All components can be overridden at construction time.
    
    Example:
        # Use default components
        llm = GPT_4_1_MiniLLM(connector)
        
        # Use custom validator
        from core.llms.runtimes.validators import LLMValidatorFactory
        llm = GPT_4_1_MiniLLM(
            connector,
            validator=LLMValidatorFactory.get_validator('noop')
        )
    """
    
    def __init__(
        self,
        connector,
        metadata=None,
        validator: Optional[ILLMValidator] = None,
        transformer: Optional[IParameterTransformer] = None,
        parser: Optional[IResponseParser] = None,
        structured_handler: Optional[IStructuredOutputHandler] = None,
    ):
        """
        Initialize GPT-4.1 Mini LLM with pluggable components.
        
        Args:
            connector: AzureConnector instance
            metadata: GPT_4_1_MiniMetadata (optional, defaults to class metadata)
            validator: Custom validator (default: BasicLLMValidator)
            transformer: Custom transformer (default: AzureGPT4Transformer)
            parser: Custom parser (default: AzureResponseParser)
            structured_handler: Custom handler (default: BasicStructuredHandler)
        """
        if metadata is None:
            metadata = GPT_4_1_MiniMetadata
        
        # Use AzureGPT4Transformer by default for this model
        if transformer is None:
            transformer = AzureGPT4Transformer(
                remove_temperature=True,  # GPT-4.1 doesn't support temperature
                convert_response_format=True
            )
        
        super().__init__(
            metadata=metadata,
            connector=connector,
            validator=validator,
            transformer=transformer,
            parser=parser,
            structured_handler=structured_handler,
        )
        
        self.logger = LoggerAdaptor.get_logger(f"llm.{GPT_4_1_MiniMetadata.NAME}")
    
    # ============================================================================
    # HOOK METHOD OVERRIDES - GPT-4.1 Mini Specific
    # ============================================================================
    
    def _validate_model_specific(
        self,
        messages: List[Dict[str, Any]],
        params: Dict[str, Any]
    ) -> None:
        """
        Perform GPT-4.1 Mini specific validations.
        
        Validates:
        - Vision content in messages (if present)
        
        Args:
            messages: Messages to validate
            params: Parameters to validate
        """
        # Check for vision content in messages
        for msg in messages:
            content = msg.get("content")
            if isinstance(content, list):
                # Multimodal message - validate image URLs
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "image_url":
                        image_url = item.get("image_url", {})
                        if not image_url.get("url"):
                            self.logger.warning(
                                "Image URL in message is empty",
                                message_role=msg.get("role")
                            )
    
    def _build_model_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply GPT-4.1 Mini specific payload modifications.
        
        Currently no additional modifications needed.
        
        Args:
            payload: Base payload
            
        Returns:
            Modified payload
        """
        return payload
    
    # ============================================================================
    # MODEL-SPECIFIC PROPERTIES
    # ============================================================================
    
    @property
    def supports_temperature(self) -> bool:
        """GPT-4.1 Mini does not support temperature parameter."""
        return False
    
    @property
    def uses_max_completion_tokens(self) -> bool:
        """GPT-4.1 Mini uses max_completion_tokens instead of max_tokens."""
        return True
