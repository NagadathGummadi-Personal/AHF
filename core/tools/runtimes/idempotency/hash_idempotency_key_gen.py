from typing import Dict, Any
from .idempotency_key_generator import IIdempotencyKeyGenerator
from ...constants import USER_ID, SESSION_ID, EMPTY_STRING, SEPARATOR, SHA256_HASH_ALGORITHM
import hashlib
import json

class HashBasedIdempotencyKeyGenerator(IIdempotencyKeyGenerator):
    """
    Hash-based idempotency key generator with configurable algorithm.
    
    This strategy allows selection of different hash algorithms and
    provides more control over what gets included in the hash.
    
    Features:
        - Configurable hash algorithm (sha256, sha512, md5, etc.)
        - Option to include/exclude user context
        - Option to include/exclude session context
        - Deterministic ordering for consistent results
    
    Usage:
        generator = HashBasedIdempotencyKeyGenerator(
            algorithm='sha512',
            include_user_context=True,
            include_session_context=False
        )
        key = generator.generate_key(args, ctx, spec)
    
    Use Cases:
        - High-security scenarios (use SHA-512)
        - Performance-critical scenarios (use MD5, but less secure)
        - Multi-tenant systems (include user context)
        - Stateless APIs (exclude session context)
    """
    
    def __init__(
        self,
        algorithm: str = SHA256_HASH_ALGORITHM,
        include_user_context: bool = True,
        include_session_context: bool = True
    ):
        """
        Initialize hash-based generator with configuration.
        
        Args:
            algorithm: Hash algorithm name ('sha256', 'sha512', 'md5', etc.)
            include_user_context: Whether to include user_id in key
            include_session_context: Whether to include session_id in key
        """
        self.algorithm = algorithm
        self.include_user_context = include_user_context
        self.include_session_context = include_session_context
    
    def generate_key(self, args: Dict[str, Any], ctx: Any, spec: Any) -> str:
        """
        Generate idempotency key using configured hash algorithm.
        
        Args:
            args: Tool execution arguments
            ctx: Tool context
            spec: Tool specification
            
        Returns:
            str: Hash digest as hex string
        """
        # Determine which data to include
        if spec.idempotency.key_fields:
            key_data = {k: args.get(k) for k in spec.idempotency.key_fields if k in args}
        else:
            key_data = args
        
        # Build key components based on configuration
        key_components = [spec.id]
        
        if self.include_user_context:
            key_components.append(str(getattr(ctx, USER_ID, None) or EMPTY_STRING))
        
        if self.include_session_context:
            key_components.append(str(getattr(ctx, SESSION_ID, None) or EMPTY_STRING))
        
        key_components.append(json.dumps(key_data, sort_keys=True))
        
        # Generate hash using specified algorithm
        combined = SEPARATOR.join(key_components)
        hash_obj = hashlib.new(self.algorithm, combined.encode())
        return hash_obj.hexdigest()

