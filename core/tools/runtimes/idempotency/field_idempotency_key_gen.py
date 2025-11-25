from typing import Dict, Any
from .idempotency_key_generator import IIdempotencyKeyGenerator
from ...constants import SEPARATOR
import hashlib
import json

class FieldBasedIdempotencyKeyGenerator(IIdempotencyKeyGenerator):
    """
    Field-based idempotency key generator.
    
    This strategy uses only specified fields from the tool arguments to generate
    the key. If key_fields is defined in IdempotencyConfig, only those fields
    are used. This is useful when you want idempotency based on specific
    business logic fields rather than all arguments.
    
    Features:
        - Uses only specified key_fields from config
        - Falls back to all args if no key_fields specified
        - Includes tool ID for isolation
        - Does NOT include user/session IDs (can be added via key_fields)
    
    Usage:
        # In tool spec
        spec.idempotency.key_fields = ['order_id', 'payment_id']
        spec.idempotency_key_generator = FieldBasedIdempotencyKeyGenerator()
        
        # Key will only be based on order_id and payment_id
    
    Use Cases:
        - Payment processing (key by transaction ID)
        - Order fulfillment (key by order ID)
        - User registration (key by email or username)
        - API requests with unique request IDs
    """
    
    def generate_key(self, args: Dict[str, Any], ctx: Any, spec: Any) -> str:
        """
        Generate idempotency key using only specified fields.
        
        Args:
            args: Tool execution arguments
            ctx: Tool context (may be ignored depending on key_fields)
            spec: Tool specification with idempotency.key_fields
            
        Returns:
            str: SHA-256 hash based on specified fields only
        """
        # Extract only specified fields
        if spec.idempotency.key_fields:
            key_data = {k: args.get(k) for k in spec.idempotency.key_fields if k in args}
        else:
            # No fields specified, use all args
            key_data = args
        
        # Build key components (tool ID + field data only)
        key_components = [
            spec.id,
            json.dumps(key_data, sort_keys=True)
        ]
        
        # Generate hash
        combined = SEPARATOR.join(key_components)
        return hashlib.sha256(combined.encode()).hexdigest()

