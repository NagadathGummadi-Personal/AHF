from typing import Dict

from .idempotency_key_generator import IIdempotencyKeyGenerator
from .default_idempotency_key_gen import DefaultIdempotencyKeyGenerator
from .field_idempotency_key_gen import FieldBasedIdempotencyKeyGenerator
from .hash_idempotency_key_gen import HashBasedIdempotencyKeyGenerator

from ...constants import UNKNOWN_IDEMPOTENCY_KEY_GENERATOR, COMMA, SPACE, DEFAULT_IDEMPOTENCY_KEY_GENERATOR, FIELD_BASED_IDEMPOTENCY_KEY_GENERATOR, HASH_BASED_IDEMPOTENCY_KEY_GENERATOR

class IdempotencyKeyGeneratorFactory:
    """
    Factory for creating idempotency key generator instances.
    
    This factory provides a centralized way to create and register
    idempotency key generators by name.
    
    Built-in Generators:
        - 'default': DefaultIdempotencyKeyGenerator
        - 'field_based': FieldBasedIdempotencyKeyGenerator
        - 'hash_based': HashBasedIdempotencyKeyGenerator
    
    Usage:
        # Get built-in generator
        generator = IdempotencyKeyGeneratorFactory.get_generator('default')
        
        # Register custom generator
        IdempotencyKeyGeneratorFactory.register('my_custom', MyCustomGenerator())
        generator = IdempotencyKeyGeneratorFactory.get_generator('my_custom')
    """
    
    _generators: Dict[str, IIdempotencyKeyGenerator] = {
        DEFAULT_IDEMPOTENCY_KEY_GENERATOR: DefaultIdempotencyKeyGenerator(),
        FIELD_BASED_IDEMPOTENCY_KEY_GENERATOR: FieldBasedIdempotencyKeyGenerator(),
        HASH_BASED_IDEMPOTENCY_KEY_GENERATOR: HashBasedIdempotencyKeyGenerator(),
    }
    
    @classmethod
    def get_generator(cls, name: str = DEFAULT_IDEMPOTENCY_KEY_GENERATOR) -> IIdempotencyKeyGenerator:
        """
        Get an idempotency key generator by name.
        
        Args:
            name: Generator name ('default', 'field_based', 'hash_based', etc.)
            
        Returns:
            IIdempotencyKeyGenerator instance
            
        Raises:
            ValueError: If generator name is not registered
        """
        generator = cls._generators.get(name)
        
        if not generator:
            raise ValueError(
                UNKNOWN_IDEMPOTENCY_KEY_GENERATOR.format(GENERATOR_NAME=name, AVAILABLE_GENERATORS=((COMMA+SPACE).join(cls._generators.keys())))
            )
        
        return generator
    
    @classmethod
    def register(cls, name: str, generator: IIdempotencyKeyGenerator):
        """
        Register a custom idempotency key generator.
        
        Args:
            name: Name to register the generator under
            generator: Generator instance implementing IIdempotencyKeyGenerator
        
        Example:
            class MyGenerator(IIdempotencyKeyGenerator):
                def generate_key(self, args, ctx, spec):
                    return f"custom-{args['id']}"
            
            IdempotencyKeyGeneratorFactory.register('my_gen', MyGenerator())
        """
        cls._generators[name] = generator

