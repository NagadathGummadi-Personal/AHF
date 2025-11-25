"""
Azure GPT-4.1 Mini Model.

Complete model definition with metadata and implementation.
"""

from .metadata import GPT_4_1_MiniMetadata
from .implementation import GPT_4_1_MiniLLM


def get_model_metadata():
    """
    Get the complete ModelMetadata for Azure GPT-4.1 Mini.
    
    This function constructs and returns the ModelMetadata object
    that describes all capabilities, parameters, and requirements
    for the GPT-4.1 Mini model.
    
    Official Model Info: https://ai.azure.com/catalog/models/gpt-4.1
    
    Key Capabilities (per Azure AI Foundry):
    - Text and image processing (multimodal input)
    - Text output with JSON mode
    - Parallel function calling
    - Enhanced accuracy and responsiveness
    - Superior performance in non-English languages
    - Support for complex structured outputs
    
    Returns:
        ModelMetadata: Complete metadata for Azure GPT-4.1 Mini
        
    Example:
        from core.llms.providers.azure.models.gpt_4_1_mini import get_model_metadata
        metadata = get_model_metadata()
        print(f"Model: {metadata.model_name}")
        print(f"Max tokens: {metadata.max_output_tokens}")
    """
    from .....spec.llm_schema import ModelMetadata
    from .....enum import LLMProvider, ModelFamily, InputMediaType, OutputMediaType, OutputFormatType, LLMType
    from .....constants import (
        API_REQ_USES_DEPLOYMENT_NAME,
        API_REQ_REQUIRES_API_KEY,
        API_REQ_REQUIRES_ENDPOINT,
        API_REQ_REQUIRES_API_VERSION,
        API_REQ_SUPPORTS_STREAMING,
    )
    
    return ModelMetadata(
        model_name=GPT_4_1_MiniMetadata.NAME,
        provider=LLMProvider.AZURE,
        model_family=ModelFamily.AZURE_GPT_4_1_MINI,
        display_name=GPT_4_1_MiniMetadata.DISPLAY_NAME,
        llm_type=LLMType.CHAT,
        supported_input_types={
            InputMediaType.TEXT,
            InputMediaType.IMAGE,
            InputMediaType.MULTIMODAL
        },
        supported_output_types={
            OutputMediaType.TEXT
        },
        supported_output_formats={
            OutputFormatType.TEXT,
            OutputFormatType.JSON
        },
        supports_streaming=GPT_4_1_MiniMetadata.SUPPORTS_STREAMING,
        supports_function_calling=GPT_4_1_MiniMetadata.SUPPORTS_FUNCTION_CALLING,
        supports_vision=GPT_4_1_MiniMetadata.SUPPORTS_VISION,
        supports_json_mode=GPT_4_1_MiniMetadata.SUPPORTS_JSON_MODE,
        max_context_length=GPT_4_1_MiniMetadata.MAX_CONTEXT_LENGTH,
        max_output_tokens=GPT_4_1_MiniMetadata.MAX_TOKENS,
        max_input_tokens=GPT_4_1_MiniMetadata.MAX_INPUT_TOKENS,
        parameter_mappings=GPT_4_1_MiniMetadata.PARAMETER_MAPPINGS,
        default_parameters=GPT_4_1_MiniMetadata.DEFAULT_PARAMETERS,
        parameter_ranges=GPT_4_1_MiniMetadata.PARAMETER_RANGES,
        supported_parameters=GPT_4_1_MiniMetadata.SUPPORTED_PARAMS,
        api_requirements={
            API_REQ_USES_DEPLOYMENT_NAME: True,
            API_REQ_REQUIRES_API_KEY: True,
            API_REQ_REQUIRES_ENDPOINT: True,
            API_REQ_REQUIRES_API_VERSION: True,
            API_REQ_SUPPORTS_STREAMING: True,
        },
        cost_per_1k_input_tokens=GPT_4_1_MiniMetadata.COST_PER_1K_INPUT,
        cost_per_1k_output_tokens=GPT_4_1_MiniMetadata.COST_PER_1K_OUTPUT,
        is_deprecated=False,
    )


__all__ = [
    "GPT_4_1_MiniMetadata",
    "GPT_4_1_MiniLLM",
    "get_model_metadata",
]



