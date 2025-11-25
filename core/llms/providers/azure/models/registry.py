"""
Azure Models Registry.

Registers all Azure OpenAI models with the global model registry.
Each model is defined in its own subfolder with metadata and implementation.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ....runtimes.model_registry import ModelRegistry


def register_azure_models(registry: 'ModelRegistry') -> None:
    """
    Register all Azure OpenAI models with the model registry.
    
    This function is called during registry initialization to register
    all available Azure models. Each model's metadata is imported from
    its dedicated subfolder.
    
    Args:
        registry: The ModelRegistry instance to register models with
        
    Example:
        from ....runtimes.model_registry import get_model_registry
        registry = get_model_registry()
        register_azure_models(registry)
    """
    # Register GPT-4.1 Mini
    _register_gpt_4_1_mini(registry)
    
    # TODO: Add more Azure models as they're implemented
    # _register_gpt4o(registry)
    # _register_gpt35_turbo(registry)


def _register_gpt_4_1_mini(registry: 'ModelRegistry') -> None:
    """
    Register Azure GPT-4.1 Mini model.
    
    GPT-4.1 Mini is a fast, cost-effective multimodal model with:
    - 128K context window
    - Vision capabilities
    - Function calling
    - JSON mode
    - Multiple output formats
    
    Args:
        registry: The ModelRegistry instance
    """
    from .gpt_4_1_mini import get_model_metadata
    
    metadata = get_model_metadata()
    registry.register_model(metadata)


__all__ = [
    "register_azure_models",
]

