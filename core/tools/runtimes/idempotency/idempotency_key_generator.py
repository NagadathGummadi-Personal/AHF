from abc import ABC, abstractmethod
from typing import Any, Dict

class IIdempotencyKeyGenerator(ABC):
    """
    Interface for idempotency key generation strategies.
    
    This abstract base class defines the contract for all idempotency key
    generators. Each implementation can use different approaches to generate
    unique, deterministic keys based on tool arguments and context.
    
    Methods:
        generate_key: Generate an idempotency key from args, context, and spec
    
    Implementing Classes:
        DefaultIdempotencyKeyGenerator: Standard hash-based generation
        FieldBasedIdempotencyKeyGenerator: Uses specific fields only
        HashBasedIdempotencyKeyGenerator: Cryptographic hash approach
        CustomIdempotencyKeyGenerator: Custom function-based generation
    """
    
    @abstractmethod
    def generate_key(self, args: Dict[str, Any], ctx: Any, spec: Any) -> str:
        """
        Generate an idempotency key.
        
        Args:
            args: Tool execution arguments
            ctx: Tool execution context (ToolContext)
            spec: Tool specification (ToolSpec)
            
        Returns:
            str: Unique idempotency key for this specific execution
            
        Note:
            Keys should be deterministic - same inputs should always produce
            the same key to enable idempotency checking.
        """
        pass


