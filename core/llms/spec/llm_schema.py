"""
LLM Type Specifications.

This module defines the metadata schema for LLM models, including
capabilities, parameters, and provider-specific configuration.
"""

from typing import Dict, Any, Optional, Set, Tuple
from pydantic import BaseModel, Field
from ..enum import (
    LLMProvider,
    ModelFamily,
    InputMediaType,
    OutputMediaType,
    OutputFormatType,
    LLMCapability,
    LLMType,
    ModelDisplayName,
)
from ..constants import (
    UNIQUE_MODEL_IDENTIFIER,
    PROVIDER_HOSTING_THE_MODEL,
    MODEL_FAMILY_GROUPING,
    HUMAN_READABLE_NAME,
    TYPE_OF_LLM,
    INPUT_MEDIA_TYPES_SUPPORTED,
    OUTPUT_MEDIA_TYPES_SUPPORTED,
    STREAMING_SUPPORT,
    FUNCTION_CALLING_SUPPORT,
    VISION_SUPPORT,
    JSON_MODE_SUPPORT,
    MAXIMUM_CONTEXT_WINDOW_IN_TOKENS,
    MAXIMUM_OUTPUT_TOKENS,
    MAXIMUM_INPUT_TOKENS,
    MAPS_STANDARD_PARAMETER_NAMES_TO_PROVIDER_SPECIFIC_NAMES,
    DEFAULT_PARAMETER_VALUES,
    VALID_PARAMETER_RANGES_FOR_THIS_MODEL,
    SET_OF_PARAMETER_NAMES_SUPPORTED_BY_THIS_MODEL,
    PROVIDER_SPECIFIC_API_REQUIREMENTS,
    OPTIONAL_FUNCTION_NAME_TO_CONVERT_RESPONSES,
    COST_PER_1000_INPUT_TOKENS_IN_USD,
    COST_PER_1000_OUTPUT_TOKENS_IN_USD,
    WHETHER_MODEL_IS_DEPRECATED,
    DEPRECATION_DATE_ISO_FORMAT,
    RECOMMENDED_REPLACEMENT,
    ARBITRARY_TYPES_ALLOWED,
    USE_ENUM_VALUES,
    JSON_SCHEMA_EXTRA,
    EXAMPLES,
    MODEL_NAME,
    PROVIDER,
    MODEL_FAMILY,
    DISPLAY_NAME,
    SUPPORTED_INPUT_TYPES,
    SUPPORTED_OUTPUT_TYPES,
    SUPPORTS_STREAMING,
    SUPPORTS_FUNCTION_CALLING,
    SUPPORTS_PARALLEL_FUNCTION_CALLING,
    SUPPORTS_VISION,
    SUPPORTS_JSON_MODE,
    PARALLEL_FUNCTION_CALLING_SUPPORT
)

class ModelMetadata(BaseModel):
    """
    Complete metadata specification for an LLM model.
    
    This is the core configuration object that defines everything about
    a model: capabilities, limits, parameters, costs, etc.
    
    Attributes:
        model_name: Unique model identifier
        provider: Provider hosting the model
        model_family: Model family grouping
        display_name: Human-readable name
        llm_type: Type of LLM (chat, completion, etc.)
        supported_input_types: Input media types supported
        supported_output_types: Output media types supported
        supports_streaming: Whether streaming is supported
        supports_function_calling: Whether function calling is supported
        supports_vision: Whether vision/image inputs are supported
        supports_json_mode: Whether JSON mode is supported
        max_context_length: Maximum context window in tokens
        max_output_tokens: Maximum output tokens
        max_input_tokens: Maximum input tokens
        parameter_mappings: Maps standard params to provider params
        default_parameters: Default parameter values
        api_requirements: Provider-specific API requirements
        converter_fn: Optional function to convert responses
        cost_per_1k_input_tokens: Cost per 1000 input tokens (USD)
        cost_per_1k_output_tokens: Cost per 1000 output tokens (USD)
        is_deprecated: Whether model is deprecated
        deprecation_date: When model was/will be deprecated
        replacement_model: Recommended replacement model
        
    Example:
        metadata = ModelMetadata(
            model_name="gpt-4-turbo",
            provider=LLMProvider.OPENAI,
            model_family=ModelFamily.GPT_4_TURBO,
            display_name="GPT-4 Turbo",
            supported_input_types={InputMediaType.TEXT, InputMediaType.IMAGE},
            supported_output_types={OutputMediaType.TEXT},
            supported_output_formats={OutputFormatType.TEXT, OutputFormatType.JSON},
            supports_streaming=True,
            max_context_length=128000,
            max_output_tokens=4096
        )
    """
    
    # Core identification
    model_name: str = Field(description=UNIQUE_MODEL_IDENTIFIER)
    provider: LLMProvider = Field(description=PROVIDER_HOSTING_THE_MODEL)
    model_family: ModelFamily = Field(description=MODEL_FAMILY_GROUPING)
    display_name: str = Field(description=HUMAN_READABLE_NAME)
    llm_type: LLMType = Field(default=LLMType.CHAT, description=TYPE_OF_LLM)
    
    # Capabilities
    supported_input_types: Set[InputMediaType] = Field(
        default_factory=lambda: {InputMediaType.TEXT},
        description=INPUT_MEDIA_TYPES_SUPPORTED)
    supported_output_types: Set[OutputMediaType] = Field(
        default_factory=lambda: {OutputMediaType.TEXT},
        description=OUTPUT_MEDIA_TYPES_SUPPORTED)
    supported_output_formats: Set[OutputFormatType] = Field(
        default_factory=lambda: {OutputFormatType.TEXT},
        description="Supported output formats for TEXT media type (text, json, toon, etc.)")
    supports_streaming: bool = Field(default=False, description=STREAMING_SUPPORT)
    supports_function_calling: bool = Field(default=False, description=FUNCTION_CALLING_SUPPORT)
    supports_vision: bool = Field(default=False, description=VISION_SUPPORT)
    supports_json_mode: bool = Field(default=False, description=JSON_MODE_SUPPORT)
    supports_parallel_function_calling : bool = Field(default=False, description=PARALLEL_FUNCTION_CALLING_SUPPORT)
    
    # Limits
    max_context_length: int = Field(default=8192, ge=1, description=MAXIMUM_CONTEXT_WINDOW_IN_TOKENS)
    max_output_tokens: int = Field(default=4096, ge=1, description=MAXIMUM_OUTPUT_TOKENS)
    max_input_tokens: Optional[int] = Field(default=None, ge=1, description=MAXIMUM_INPUT_TOKENS)
    
    # Parameters
    parameter_mappings: Dict[str, str] = Field(
        default_factory=dict,
        description=MAPS_STANDARD_PARAMETER_NAMES_TO_PROVIDER_SPECIFIC_NAMES)
    default_parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description=DEFAULT_PARAMETER_VALUES)
    parameter_ranges: Dict[str, tuple[float, float]] = Field(
        default_factory=dict,
        description=VALID_PARAMETER_RANGES_FOR_THIS_MODEL)
    supported_parameters: Optional[set[str]] = Field(
        default=None,
        description=SET_OF_PARAMETER_NAMES_SUPPORTED_BY_THIS_MODEL)
    
    # Provider-specific
    api_requirements: Dict[str, Any] = Field(
        default_factory=dict,
        description=PROVIDER_SPECIFIC_API_REQUIREMENTS)
    converter_fn: Optional[str] = Field(
        default=None,
        description=OPTIONAL_FUNCTION_NAME_TO_CONVERT_RESPONSES)
    
    # Pricing
    cost_per_1k_input_tokens: Optional[float] = Field(
        default=None,
        ge=0,
        description=COST_PER_1000_INPUT_TOKENS_IN_USD)
    cost_per_1k_output_tokens: Optional[float] = Field(
        default=None,
        ge=0,
        description=COST_PER_1000_OUTPUT_TOKENS_IN_USD)
    
    # Lifecycle
    is_deprecated: bool = Field(default=False, description=WHETHER_MODEL_IS_DEPRECATED)
    deprecation_date: Optional[str] = Field(default=None, description=DEPRECATION_DATE_ISO_FORMAT)
    replacement_model: Optional[str] = Field(default=None, description=RECOMMENDED_REPLACEMENT)
    
    model_config = {
        ARBITRARY_TYPES_ALLOWED: True,
        USE_ENUM_VALUES: True,
        JSON_SCHEMA_EXTRA: {
            EXAMPLES: [
                {
                    MODEL_NAME: ModelFamily.GPT_4_1_MINI,
                    PROVIDER: LLMProvider.OPENAI,
                    MODEL_FAMILY: ModelFamily.GPT_4_1_MINI,
                    DISPLAY_NAME: ModelDisplayName.GPT_4_1_MINI,
                    SUPPORTED_INPUT_TYPES: {InputMediaType.TEXT, InputMediaType.IMAGE},
                    SUPPORTED_OUTPUT_TYPES: {OutputMediaType.TEXT},
                    "supported_output_formats": {OutputFormatType.TEXT, OutputFormatType.JSON},
                    SUPPORTS_STREAMING: True,
                    SUPPORTS_FUNCTION_CALLING: True,
                    SUPPORTS_PARALLEL_FUNCTION_CALLING: True,
                    SUPPORTS_VISION: True,
                    SUPPORTS_JSON_MODE: True
                }
            ]
        }
    }
    
    def supports_capability(self, capability: LLMCapability) -> bool:
        """
        Check if model supports a specific capability.
        
        Args:
            capability: Capability to check
            
        Returns:
            True if capability is supported
        """
        capability_map = {
            LLMCapability.STREAMING: self.supports_streaming,
            LLMCapability.FUNCTION_CALLING: self.supports_function_calling,
            LLMCapability.VISION: self.supports_vision,
            LLMCapability.JSON_MODE: self.supports_json_mode,
            LLMCapability.PARALLEL_FUNCTION_CALLING: self.supports_parallel_function_calling,
            LLMCapability.MULTI_TURN: self.supports_multi_turn,
            LLMCapability.CONTEXT_CACHING: self.supports_context_caching,
        }
        return capability_map.get(capability, False)
    
    def supports_input_type(self, input_type: InputMediaType) -> bool:
        """
        Check if model supports an input type.
        
        Args:
            input_type: Input media type to check
            
        Returns:
            True if input type is supported
        """
        return input_type in self.supported_input_types
    
    def supports_output_type(self, output_type: OutputMediaType) -> bool:
        """
        Check if model supports an output type.
        
        Args:
            output_type: Output media type to check
            
        Returns:
            True if output type is supported
        """
        return output_type in self.supported_output_types
    
    def supports_output_format(self, output_format: OutputFormatType) -> bool:
        """
        Check if model supports an output format (for TEXT media).
        
        Args:
            output_format: Output format type to check
            
        Returns:
            True if output format is supported
        """
        return output_format in self.supported_output_formats
    
    def get_parameter_mapping(self, standard_param: str) -> str:
        """
        Get provider-specific parameter name.
        
        Args:
            standard_param: Standard parameter name
            
        Returns:
            Provider-specific parameter name (or original if no mapping)
        """
        return self.parameter_mappings.get(standard_param, standard_param)
    
    def get_default_parameter(self, param: str, default: Any = None) -> Any:
        """
        Get default value for a parameter.
        
        Args:
            param: Parameter name
            default: Fallback default
            
        Returns:
            Default parameter value
        """
        return self.default_parameters.get(param, default)
    
    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> Optional[float]:
        """
        Estimate cost for token usage.
        
        Args:
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            
        Returns:
            Estimated cost in USD, or None if pricing not available
        """
        if self.cost_per_1k_input_tokens is None or self.cost_per_1k_output_tokens is None:
            return None
        
        input_cost = (prompt_tokens / 1000) * self.cost_per_1k_input_tokens
        output_cost = (completion_tokens / 1000) * self.cost_per_1k_output_tokens
        return input_cost + output_cost
    
    def validate_parameter(self, param: str, value: Any) -> bool:
        """
        Validate a parameter value for this model.
        
        Args:
            param: Parameter name
            value: Parameter value
            
        Returns:
            True if valid
            
        Raises:
            ValueError: If parameter is not supported or value is out of range
        """
        # Check if parameter is supported
        if self.supported_parameters is not None and param not in self.supported_parameters:
            raise ValueError(
                f"Parameter '{param}' not supported by {self.model_name}. "
                f"Supported: {self.supported_parameters}"
            )
        
        # Check parameter range
        if param in self.parameter_ranges:
            min_val, max_val = self.parameter_ranges[param]
            if not (min_val <= value <= max_val):
                raise ValueError(
                    f"Parameter '{param}' value {value} out of range [{min_val}, {max_val}] "
                    f"for {self.model_name}"
                )
        
        return True
    
    def get_parameter_range(self, param: str) -> Optional[Tuple[float, float]]:
        """
        Get valid range for a parameter.
        
        Args:
            param: Parameter name
            
        Returns:
            (min, max) tuple or None if no range defined
        """
        return self.parameter_ranges.get(param)
    
    def is_parameter_supported(self, param: str) -> bool:
        """
        Check if a parameter is supported by this model.
        
        Args:
            param: Parameter name
            
        Returns:
            True if supported (or if no restrictions defined)
        """
        if self.supported_parameters is None:
            return True  # No restrictions = all standard params supported
        return param in self.supported_parameters
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert metadata to dictionary.
        
        Returns:
            Dictionary representation
        """
        return self.model_dump(exclude_none=True)


# Helper function to create model metadata

def create_model_metadata(
    model_name: str,
    provider: LLMProvider,
    model_family: ModelFamily,
    display_name: str,
    **kwargs
) -> ModelMetadata:
    """
    Helper to create ModelMetadata with required fields.
    
    Args:
        model_name: Model identifier
        provider: Provider
        model_family: Model family
        display_name: Display name
        **kwargs: Additional metadata fields
        
    Returns:
        ModelMetadata instance
    """
    return ModelMetadata(
        model_name=model_name,
        provider=provider,
        model_family=model_family,
        display_name=display_name,
        **kwargs
    )

