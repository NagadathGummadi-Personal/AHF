"""
Azure OpenAI Provider.

Complete Azure OpenAI provider implementation with connector, base implementation,
and model-specific configurations.
"""

from .connector import AzureConnector
from .base_implementation import AzureBaseLLM
from .models.gpt_4_1_mini import GPT_4_1_MiniMetadata, GPT_4_1_MiniLLM
from .models.registry import register_azure_models


def create_azure_llm(
    model_name: str,
    api_key: str = None,
    endpoint: str = None,
    deployment_name: str = None,
    api_version: str = None,
    **kwargs
):
    """
    Factory function to create Azure LLM instances.
    
    Args:
        model_name: Model identifier (e.g., "gpt-4.1-mini", "gpt-4o")
        api_key: Azure OpenAI API key (or use AZURE_OPENAI_KEY env var)
        endpoint: Azure OpenAI endpoint (or use AZURE_OPENAI_ENDPOINT env var)
        deployment_name: Deployment name (or use AZURE_OPENAI_DEPLOYMENT env var)
        api_version: API version (defaults to 2024-02-15-preview)
        **kwargs: Additional connector configuration
        
    Returns:
        Configured LLM instance for the specified model
        
    Raises:
        ValueError: If model_name is not recognized
        ConfigurationError: If required configuration is missing
        
    Example:
        llm = create_azure_llm(
            "gpt-4.1-mini",
            api_key="your-key",
            endpoint="https://your-resource.openai.azure.com",
            deployment_name="gpt-4.1-mini"
        )
        
        response = await llm.get_answer(
            messages=[{"role": "user", "content": "Hello!"}],
            ctx=context,
            max_tokens=100
        )
    """
    # Create shared connector configuration
    connector_config = {
        "api_key": api_key,
        "endpoint": endpoint,
        "deployment_name": deployment_name,
        "api_version": api_version,
        **kwargs
    }
    
    # Create connector
    connector = AzureConnector(connector_config)
    
    # Route to model-specific implementation
    if model_name in ["gpt-4.1-mini", "azure-gpt-4.1-mini"]:
        return GPT_4_1_MiniLLM(
            connector=connector,
            metadata=GPT_4_1_MiniMetadata
        )
    # Add more models here as they're implemented
    # elif model_name in ["gpt-4o", "azure-gpt-4o"]:
    #     return GPT4oLLM(connector=connector)
    # elif model_name in ["gpt-3.5-turbo", "azure-gpt-3.5-turbo"]:
    #     # Uses base implementation
    #     return AzureBaseLLM(
    #         connector=connector,
    #         metadata=GPT35TurboMetadata
    #     )
    else:
        raise ValueError(
            f"Unknown Azure model: {model_name}. "
            f"Supported models: gpt-4.1-mini"
        )


__all__ = [
    "AzureConnector",
    "AzureBaseLLM",
    "GPT_4_1_MiniMetadata",
    "GPT_4_1_MiniLLM",
    "create_azure_llm",
    "register_azure_models",
]



