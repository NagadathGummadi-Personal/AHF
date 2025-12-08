"""
Prompt Registry Factory.

Factory for creating prompt registry implementations.
"""

from typing import Dict, Type

from ..interfaces.prompt_registry_interfaces import IPromptRegistry
from .storage import LocalPromptRegistry


class PromptRegistryFactory:
    """
    Factory for creating prompt registry implementations.
    
    Usage:
        # Get local registry
        registry = PromptRegistryFactory.get_registry('local')
        
        # Register custom registry
        PromptRegistryFactory.register('redis', RedisPromptRegistry)
    """
    
    _registry_map: Dict[str, Type[IPromptRegistry]] = {
        'local': LocalPromptRegistry,
        'file': LocalPromptRegistry,
        'default': LocalPromptRegistry,
    }
    
    @classmethod
    def get_registry(
        cls,
        name: str = 'default',
        **kwargs
    ) -> IPromptRegistry:
        """
        Get a prompt registry by name.
        
        Args:
            name: Registry implementation name
            **kwargs: Arguments to pass to registry constructor
            
        Returns:
            Registry instance
        """
        name_lower = name.lower()
        registry_class = cls._registry_map.get(name_lower)
        
        if not registry_class:
            raise ValueError(
                f"Unknown registry: {name}. Available: {list(cls._registry_map.keys())}"
            )
        
        return registry_class(**kwargs)
    
    @classmethod
    def register(cls, name: str, registry_class: Type[IPromptRegistry]) -> None:
        """Register a custom registry implementation."""
        cls._registry_map[name.lower()] = registry_class
    
    @classmethod
    def list_available(cls) -> list:
        """List all registered registry implementations."""
        return list(cls._registry_map.keys())

