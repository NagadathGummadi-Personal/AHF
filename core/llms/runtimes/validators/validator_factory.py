"""
LLM Validator Factory.

Provides a centralized way to create and register validators by name.
"""

from typing import Dict
from ...interfaces.llm_interfaces import ILLMValidator
from .basic_validator import BasicLLMValidator
from .noop_validator import NoOpLLMValidator


# Constants
BASIC = "basic"
NOOP = "noop"


class LLMValidatorFactory:
    """
    Factory for creating LLM validator instances.
    
    Built-in Validators:
        - 'basic': BasicLLMValidator - Comprehensive validation
        - 'noop': NoOpLLMValidator - No validation (for testing)
    
    Usage:
        # Get built-in validator
        validator = LLMValidatorFactory.get_validator('basic')
        
        # Register custom validator
        LLMValidatorFactory.register('my_custom', MyCustomValidator())
        validator = LLMValidatorFactory.get_validator('my_custom')
    """
    
    _validators: Dict[str, ILLMValidator] = {
        BASIC: BasicLLMValidator(),
        NOOP: NoOpLLMValidator(),
    }
    
    @classmethod
    def get_validator(cls, name: str = BASIC) -> ILLMValidator:
        """
        Get a validator by name.
        
        Args:
            name: Validator name ('basic', 'noop', etc.)
            
        Returns:
            ILLMValidator instance
            
        Raises:
            ValueError: If validator name is not registered
        """
        validator = cls._validators.get(name)
        
        if not validator:
            available = ", ".join(cls._validators.keys())
            raise ValueError(
                f"Unknown validator: '{name}'. Available validators: {available}"
            )
        
        return validator
    
    @classmethod
    def register(cls, name: str, validator: ILLMValidator) -> None:
        """
        Register a custom validator.
        
        Args:
            name: Name to register the validator under
            validator: Validator instance implementing ILLMValidator
        
        Example:
            class MyValidator:
                async def validate_messages(self, messages, metadata):
                    # Custom validation logic
                    pass
            
            LLMValidatorFactory.register('my_validator', MyValidator())
        """
        cls._validators[name] = validator
    
    @classmethod
    def list_validators(cls) -> list:
        """
        List all registered validator names.
        
        Returns:
            List of validator names
        """
        return list(cls._validators.keys())

