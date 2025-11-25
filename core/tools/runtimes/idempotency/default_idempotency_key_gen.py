from typing import Dict, Any
from .idempotency_key_generator import IIdempotencyKeyGenerator
from ...constants import USER_ID, SESSION_ID, EMPTY_STRING, SEPARATOR
import hashlib
import json



class DefaultIdempotencyKeyGenerator(IIdempotencyKeyGenerator):
    """
    Default idempotency key generator using SHA-256 hash.
    
    This strategy generates keys by hashing a combination of:
    - Tool ID
    - User ID (if available)
    - Session ID (if available)
    - All tool arguments (unless key_fields is specified)
    
    The key is a SHA-256 hash of these components, ensuring uniqueness
    while maintaining determinism.
    
    Usage:
        generator = DefaultIdempotencyKeyGenerator()
        key = generator.generate_key(args, ctx, spec)
    
    Note:
        This is the default strategy if no generator is specified in the tool spec.
    """
    
    def generate_key(self, args: Dict[str, Any], ctx: Any, spec: Any) -> str:
        """
        Generate idempotency key using SHA-256 hash of tool ID, context, and args.
        
        Args:
            args: Tool execution arguments
            ctx: Tool context containing user_id, session_id, etc.
            spec: Tool specification containing id and idempotency config
            
        Returns:
            str: SHA-256 hash as hex string (64 characters)
        """
        # Determine which data to include in key
        if spec.idempotency.key_fields:
            key_data = {k: args.get(k) for k in spec.idempotency.key_fields if k in args}
        else:
            key_data = args
        
        # Build key components
        key_components = [
            spec.id,
            str(getattr(ctx, USER_ID, None) or EMPTY_STRING),
            str(getattr(ctx, SESSION_ID, None) or EMPTY_STRING),
            json.dumps(key_data, sort_keys=True)
        ]
        
        # Generate hash
        combined = SEPARATOR.join(key_components)
        return hashlib.sha256(combined.encode()).hexdigest()

