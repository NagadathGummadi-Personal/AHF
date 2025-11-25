"""
Parameter Transformer Factory.

Provides a centralized way to create and register transformers by name.
"""

from typing import Dict
from ...interfaces.llm_interfaces import IParameterTransformer
from .azure_gpt4_transformer import AzureGPT4Transformer
from .noop_transformer import NoOpTransformer


# Constants
AZURE_GPT4 = "azure_gpt4"
NOOP = "noop"


class TransformerFactory:
    """
    Factory for creating parameter transformer instances.
    
    Built-in Transformers:
        - 'azure_gpt4': AzureGPT4Transformer - GPT-4.x specific transformations
        - 'noop': NoOpTransformer - No transformation (pass-through)
    
    Usage:
        # Get built-in transformer
        transformer = TransformerFactory.get_transformer('azure_gpt4')
        
        # Register custom transformer
        TransformerFactory.register('my_custom', MyCustomTransformer())
    """
    
    _transformers: Dict[str, IParameterTransformer] = {
        AZURE_GPT4: AzureGPT4Transformer(),
        NOOP: NoOpTransformer(),
    }
    
    @classmethod
    def get_transformer(cls, name: str = AZURE_GPT4) -> IParameterTransformer:
        """
        Get a transformer by name.
        
        Args:
            name: Transformer name ('azure_gpt4', 'noop', etc.)
            
        Returns:
            IParameterTransformer instance
            
        Raises:
            ValueError: If transformer name is not registered
        """
        transformer = cls._transformers.get(name)
        
        if not transformer:
            available = ", ".join(cls._transformers.keys())
            raise ValueError(
                f"Unknown transformer: '{name}'. Available transformers: {available}"
            )
        
        return transformer
    
    @classmethod
    def register(cls, name: str, transformer: IParameterTransformer) -> None:
        """
        Register a custom transformer.
        
        Args:
            name: Name to register the transformer under
            transformer: Transformer instance implementing IParameterTransformer
        """
        cls._transformers[name] = transformer
    
    @classmethod
    def list_transformers(cls) -> list:
        """
        List all registered transformer names.
        
        Returns:
            List of transformer names
        """
        return list(cls._transformers.keys())

