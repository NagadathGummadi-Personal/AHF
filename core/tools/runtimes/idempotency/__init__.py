"""
Idempotency Key Generation Strategies.

This module provides pluggable strategies for generating idempotency keys,
allowing different key generation approaches for different tool types and use cases.

Idempotency Key Generation Strategies.

This module provides various strategies for generating idempotency keys based on
tool arguments, context, and configuration. Different strategies can be used for
different tool types and use cases.

Strategy Pattern Implementation:
=================================
All key generators implement the IIdempotencyKeyGenerator interface, allowing
runtime selection of the appropriate strategy for each tool.

Available Strategies:
=====================
- DefaultIdempotencyKeyGenerator: Uses all args + tool ID + user/session IDs
- FieldBasedIdempotencyKeyGenerator: Uses only specified fields from config
- HashBasedIdempotencyKeyGenerator: Uses cryptographic hash of selected data
- CustomIdempotencyKeyGenerator: Accepts custom key generation function

Usage:
    from core.tools.executors.idempotency import DefaultIdempotencyKeyGenerator
    
    # Use default strategy
    generator = DefaultIdempotencyKeyGenerator()
    key = generator.generate_key(args, ctx, spec)
    
    # Use field-based strategy (specified in IdempotencyConfig)
    generator = FieldBasedIdempotencyKeyGenerator()
    key = generator.generate_key(args, ctx, spec)
    
    # Use custom function
    def custom_key_fn(args, ctx, spec):
        return f"{spec.id}:{args['user_id']}:{args['timestamp']}"
    
    generator = CustomIdempotencyKeyGenerator(custom_key_fn)
    key = generator.generate_key(args, ctx, spec)

Extending:
==========
To create a custom idempotency key generator:

1. Inherit from IIdempotencyKeyGenerator
2. Implement the generate_key method
3. Configure it in the tool spec

Example:
    class UUIDIdempotencyKeyGenerator(IIdempotencyKeyGenerator):
        def generate_key(self, args, ctx, spec):
            return str(uuid.uuid4())

    # Register custom generator
    IdempotencyKeyGeneratorFactory.register('uuid', UUIDIdempotencyKeyGenerator())

    # Use registered generator by name
    generator = IdempotencyKeyGeneratorFactory.get_generator('uuid')
    key = generator.generate_key(args, ctx, spec)
"""


from .idempotency_key_generator import IIdempotencyKeyGenerator
from .default_idempotency_key_gen import DefaultIdempotencyKeyGenerator
from .field_idempotency_key_gen import FieldBasedIdempotencyKeyGenerator
from .hash_idempotency_key_gen import HashBasedIdempotencyKeyGenerator
from .custom_idempotency_key_gen import CustomIdempotencyKeyGenerator
from .idempotency_key_gen_factory import IdempotencyKeyGeneratorFactory

__all__ = [
    "IIdempotencyKeyGenerator",
    "DefaultIdempotencyKeyGenerator",
    "FieldBasedIdempotencyKeyGenerator",
    "HashBasedIdempotencyKeyGenerator",
    "CustomIdempotencyKeyGenerator",
    "IdempotencyKeyGeneratorFactory",
]

