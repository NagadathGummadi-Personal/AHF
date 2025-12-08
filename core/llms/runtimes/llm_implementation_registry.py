"""
LLM Implementation Registry.

Allows registering custom LLM implementations for models, enabling
users to define their own execution strategies on the fly.
"""

from typing import Dict, Any, Callable, Optional
from ..interfaces.llm_interfaces import ILLM, IConnector
from ..spec.llm_schema import ModelMetadata
from ..exceptions import ConfigurationError


# Type alias for factory functions
LLMFactory = Callable[[ModelMetadata, IConnector], ILLM]
ConnectorFactory = Callable[[Dict[str, Any]], IConnector]


class LLMImplementationRegistry:
    """
    Registry for custom LLM implementations.
    
    Allows users to register custom execution strategies for models,
    enabling complete flexibility in how models are used.
    
    Example:
        # Define custom GPT-4.1 implementation
        class MyCustomGPT41(BaseLLM):
            async def get_answer(self, messages, ctx, **kwargs):
                # Your custom logic here
                pass
        
        # Register it
        registry = LLMImplementationRegistry()
        registry.register_llm_implementation(
            "azure-gpt-4.1-mini",
            lambda metadata, connector: MyCustomGPT41(metadata, connector)
        )
        
        # Factory will now use your custom implementation
        llm = factory.create_llm("azure-gpt-4.1-mini", config)
    """
    
    def __init__(self):
        """Initialize empty registry."""
        self._llm_implementations: Dict[str, LLMFactory] = {}
        self._connector_implementations: Dict[str, ConnectorFactory] = {}
        self._default_llm_factory: Optional[LLMFactory] = None
        self._default_connector_factory: Optional[ConnectorFactory] = None
    
    def register_llm_implementation(
        self,
        model_name: str,
        factory: LLMFactory
    ) -> None:
        """
        Register a custom LLM implementation for a specific model.
        
        Args:
            model_name: Model identifier
            factory: Factory function that creates the LLM instance
            
        Example:
            def create_my_gpt41(metadata, connector):
                return MyCustomGPT41(metadata, connector)
            
            registry.register_llm_implementation(
                "azure-gpt-4.1-mini",
                create_my_gpt41
            )
        """
        self._llm_implementations[model_name] = factory
    
    def register_connector_implementation(
        self,
        provider: str,
        factory: ConnectorFactory
    ) -> None:
        """
        Register a custom connector implementation for a provider.
        
        Args:
            provider: Provider identifier (e.g., "azure", "openai")
            factory: Factory function that creates the connector
            
        Example:
            def create_my_azure_connector(config):
                return MyCustomAzureConnector(config)
            
            registry.register_connector_implementation(
                "azure",
                create_my_azure_connector
            )
        """
        self._connector_implementations[provider] = factory
    
    def set_default_llm_factory(self, factory: LLMFactory) -> None:
        """
        Set default LLM factory for models without specific implementation.
        
        Args:
            factory: Default factory function
        """
        self._default_llm_factory = factory
    
    def set_default_connector_factory(self, factory: ConnectorFactory) -> None:
        """
        Set default connector factory for providers without specific implementation.
        
        Args:
            factory: Default factory function
        """
        self._default_connector_factory = factory
    
    def create_llm(
        self,
        metadata: ModelMetadata,
        connector: IConnector
    ) -> ILLM:
        """
        Create LLM instance using registered implementation or default.
        
        Args:
            metadata: Model metadata
            connector: Provider connector
            
        Returns:
            LLM instance implementing ILLM
            
        Raises:
            ConfigurationError: If no implementation found
        """
        # Try model-specific implementation first
        factory = self._llm_implementations.get(metadata.model_name)
        
        if factory is None:
            # Fall back to default
            factory = self._default_llm_factory
        
        if factory is None:
            raise ConfigurationError(
                f"No LLM implementation registered for {metadata.model_name} "
                f"and no default factory set"
            )
        
        return factory(metadata, connector)
    
    def create_connector(
        self,
        provider: str,
        config: Dict[str, Any]
    ) -> IConnector:
        """
        Create connector instance using registered implementation or default.
        
        Args:
            provider: Provider identifier
            config: Connector configuration
            
        Returns:
            Connector instance implementing IConnector
            
        Raises:
            ConfigurationError: If no implementation found
        """
        # Try provider-specific implementation first
        factory = self._connector_implementations.get(provider)
        
        if factory is None:
            # Fall back to default
            factory = self._default_connector_factory
        
        if factory is None:
            raise ConfigurationError(
                f"No connector implementation registered for {provider} "
                f"and no default factory set"
            )
        
        return factory(config)
    
    def has_llm_implementation(self, model_name: str) -> bool:
        """Check if model has a registered implementation."""
        return model_name in self._llm_implementations or self._default_llm_factory is not None
    
    def has_connector_implementation(self, provider: str) -> bool:
        """Check if provider has a registered connector."""
        return provider in self._connector_implementations or self._default_connector_factory is not None
    
    def list_registered_models(self) -> list[str]:
        """Get list of models with custom implementations."""
        return list(self._llm_implementations.keys())
    
    def list_registered_providers(self) -> list[str]:
        """Get list of providers with custom connectors."""
        return list(self._connector_implementations.keys())


# Singleton instance
_implementation_registry: Optional[LLMImplementationRegistry] = None


def get_implementation_registry() -> LLMImplementationRegistry:
    """
    Get the global implementation registry (singleton).
    
    Returns:
        Global LLMImplementationRegistry instance
        
    Example:
        registry = get_implementation_registry()
        registry.register_llm_implementation("my-model", factory)
    """
    global _implementation_registry
    if _implementation_registry is None:
        _implementation_registry = LLMImplementationRegistry()
    return _implementation_registry


def reset_implementation_registry() -> None:
    """Reset the global implementation registry (for testing)."""
    global _implementation_registry
    _implementation_registry = None

