"""
Prompt Validator Factory.

Factory for creating prompt validator implementations.
"""

from typing import Dict, Type, List

from ...interfaces.prompt_registry_interfaces import IPromptValidator
from .noop_validator import NoOpPromptValidator
from .basic_validator import BasicPromptValidator


class PromptValidatorFactory:
    """
    Factory for creating prompt validator implementations.
    
    Usage:
        # Get NoOp validator (no validation)
        validator = PromptValidatorFactory.get_validator('noop')
        
        # Get basic validator with defaults
        validator = PromptValidatorFactory.get_validator('basic')
        
        # Get basic validator with custom config
        validator = PromptValidatorFactory.get_validator(
            'basic',
            max_content_length=50000,
            blocked_patterns=['custom_pattern']
        )
        
        # Register custom validator
        PromptValidatorFactory.register('custom', MyCustomValidator)
    """
    
    _validator_map: Dict[str, Type[IPromptValidator]] = {
        'noop': NoOpPromptValidator,
        'none': NoOpPromptValidator,
        'basic': BasicPromptValidator,
        'default': BasicPromptValidator,
    }
    
    @classmethod
    def get_validator(
        cls,
        name: str = 'default',
        **kwargs
    ) -> IPromptValidator:
        """
        Get a validator by name.
        
        Args:
            name: Validator implementation name
            **kwargs: Arguments to pass to validator constructor
            
        Returns:
            Validator instance
            
        Raises:
            ValueError: If validator name is unknown
        """
        name_lower = name.lower()
        validator_class = cls._validator_map.get(name_lower)
        
        if not validator_class:
            raise ValueError(
                f"Unknown validator: {name}. Available: {list(cls._validator_map.keys())}"
            )
        
        return validator_class(**kwargs)
    
    @classmethod
    def register(
        cls,
        name: str,
        validator_class: Type[IPromptValidator]
    ) -> None:
        """
        Register a custom validator implementation.
        
        Args:
            name: Name to register under
            validator_class: Validator class implementing IPromptValidator
        """
        cls._validator_map[name.lower()] = validator_class
    
    @classmethod
    def list_available(cls) -> List[str]:
        """List all registered validator implementations."""
        return list(cls._validator_map.keys())
    
    @classmethod
    def unregister(cls, name: str) -> None:
        """Unregister a validator (for testing)."""
        cls._validator_map.pop(name.lower(), None)

