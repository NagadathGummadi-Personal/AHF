"""
LLM Factory for creating LLM instances.

This module provides a unified factory for creating LLM instances
based on model metadata and provider configuration.
"""

from typing import Dict, Any, Optional, List
from ..providers.base.implementation import BaseLLM
from .model_registry import get_model_registry
from ..providers.azure.connector import AzureConnector
from ..providers.azure.models.gpt_4_1_mini import GPT_4_1_MiniLLM
from ..spec.llm_schema import ModelMetadata
from ..enum import LLMProvider, ModelFamily
from ..exceptions import ConfigurationError
from ..constants import PROVIDER_OPENAI, PROVIDER_AZURE


# OpenAI not yet migrated - placeholders
class OpenAIConnector:
    def __init__(self, *args, **kwargs):
        raise NotImplementedError("OpenAI not yet migrated to providers structure")


class OpenAILLM:
    def __init__(self, *args, **kwargs):
        raise NotImplementedError("OpenAI not yet migrated to providers structure")


class LLMFactory:
    """
    Unified factory for creating LLM instances.
    
    Automatically selects the appropriate connector and LLM implementation
    based on the model metadata and provider configuration.
    
    Usage:
        # Create LLM by model name
        llm = LLMFactory.create_llm("gpt-4o", connector_config={"api_key": "sk-..."})
        
        # Create LLM from metadata
        metadata = registry.get_model("azure-gpt-4o")
        llm = LLMFactory.create_llm_from_metadata(metadata, connector_config={...})
    """
    
    @classmethod
    def create_llm(
        cls,
        model_name: str,
        connector_config: Dict[str, Any],
    ) -> BaseLLM:
        """
        Create an LLM instance by model name.
        
        Args:
            model_name: Name of the model (e.g., "gpt-4o", "azure-gpt-4o")
            connector_config: Configuration for the connector (api_key, endpoint, etc.)
            
        Returns:
            Configured LLM instance implementing ILLM
            
        Raises:
            ModelNotFoundError: If model is not registered
            ConfigurationError: If configuration is invalid
            
        Example:
            # OpenAI
            llm = LLMFactory.create_llm(
                "gpt-4o",
                connector_config={"api_key": "sk-..."}
            )
            
            # Azure
            llm = LLMFactory.create_llm(
                "azure-gpt-4o",
                connector_config={
                    "api_key": "...",
                    "endpoint": "https://my-resource.openai.azure.com",
                    "deployment_name": "gpt-4"
                }
            )
        """
        # Get model metadata from registry
        registry = get_model_registry()
        metadata = registry.get_model_or_raise(model_name)
        
        # Create LLM from metadata
        return cls.create_llm_from_metadata(metadata, connector_config)
    
    @classmethod
    def create_llm_from_metadata(
        cls,
        metadata: ModelMetadata,
        connector_config: Dict[str, Any],
    ) -> BaseLLM:
        """
        Create an LLM instance from model metadata.
        
        Args:
            metadata: Model metadata
            connector_config: Configuration for the connector
            
        Returns:
            Configured LLM instance
            
        Raises:
            ConfigurationError: If provider is not supported or config is invalid
            
        Example:
            metadata = ModelMetadata(...)
            llm = LLMFactory.create_llm_from_metadata(
                metadata,
                connector_config={"api_key": "..."}
            )
        """
        provider = metadata.provider
        
        if provider == LLMProvider.OPENAI:
            connector = OpenAIConnector(connector_config)
            return OpenAILLM(metadata, connector)
        
        elif provider == LLMProvider.AZURE:
            connector = AzureConnector(connector_config)
            
            # Route to model-specific implementation based on model family
            if metadata.model_family == ModelFamily.AZURE_GPT_4_1_MINI:
                return GPT_4_1_MiniLLM(connector=connector, metadata=metadata)
            
            # Add more Azure models here as they're implemented
            # elif metadata.model_family == ModelFamily.AZURE_GPT_4:
            #     return GPT4LLM(connector=connector, metadata=metadata)
            # elif metadata.model_family == ModelFamily.AZURE_GPT_35_TURBO:
            #     return GPT35TurboLLM(connector=connector, metadata=metadata)
            
            else:
                raise ConfigurationError(
                    f"No implementation available for Azure model family: {metadata.model_family}",
                    provider=PROVIDER_AZURE,
                    details={
                        "model_name": metadata.model_name,
                        "model_family": metadata.model_family,
                        "supported_families": [ModelFamily.AZURE_GPT_4_1_MINI]
                    }
                )
        
        else:
            raise ConfigurationError(
                f"Unsupported provider: {provider}",
                provider=provider.value if hasattr(provider, 'value') else str(provider),
                details={"supported_providers": [PROVIDER_OPENAI, PROVIDER_AZURE]}
            )
    
    @classmethod
    def list_available_models(cls) -> List[str]:
        """
        List all available models.
        
        Returns:
            List of model names
            
        Example:
            models = LLMFactory.list_available_models()
            print(f"Available models: {models}")
        """
        registry = get_model_registry()
        return list(registry.get_all_models().keys())
    
    @classmethod
    def list_provider_models(cls, provider: LLMProvider) -> List[str]:
        """
        List all models for a specific provider.
        
        Args:
            provider: Provider to filter by
            
        Returns:
            List of model names
            
        Example:
            openai_models = LLMFactory.list_provider_models(LLMProvider.OPENAI)
        """
        registry = get_model_registry()
        return registry.get_provider_models(provider)
    
    @classmethod
    def get_model_metadata(cls, model_name: str) -> ModelMetadata:
        """
        Get metadata for a model without creating an LLM instance.
        
        Args:
            model_name: Name of the model
            
        Returns:
            ModelMetadata
            
        Raises:
            ModelNotFoundError: If model not found
            
        Example:
            metadata = LLMFactory.get_model_metadata("gpt-4o")
            print(f"Max tokens: {metadata.max_output_tokens}")
        """
        registry = get_model_registry()
        return registry.get_model_or_raise(model_name)

