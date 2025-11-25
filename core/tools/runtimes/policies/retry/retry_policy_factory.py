from typing import Dict
from .retry_policy import IRetryPolicy
from .no_retry_policy import NoRetryPolicy
from .fixed_retry_policy import FixedRetryPolicy
from .exponential_backoff_retry_policy import ExponentialBackoffRetryPolicy

from ....constants import (
    NONE,
    FIXED,
    EXPONENTIAL,
    UNKNOWN_RETRY_POLICY_ERROR,
    COMMA,
    SPACE
)

class RetryPolicyFactory:
    """
    Factory for creating retry policy instances.
    
    Built-in Policies:
        - 'none': NoRetryPolicy
        - 'fixed': FixedRetryPolicy
        - 'exponential': ExponentialBackoffRetryPolicy
    
    Usage:
        policy = RetryPolicyFactory.get_policy('exponential')
        spec.retry_policy = policy
    """
    
    _policies: Dict[str, IRetryPolicy] = {
        NONE: NoRetryPolicy(),
        FIXED: FixedRetryPolicy(),
        EXPONENTIAL: ExponentialBackoffRetryPolicy(),
    }
    
    @classmethod
    def get_policy(cls, name: str = NONE) -> IRetryPolicy:
        """
        Get a retry policy by name.
        
        Args:
            name: Policy name ('none', 'fixed', 'exponential')
            
        Returns:
            IRetryPolicy instance
            
        Raises:
            ValueError: If policy name not found
        """
        policy = cls._policies.get(name)
        
        if not policy:
            raise ValueError(
                UNKNOWN_RETRY_POLICY_ERROR.format(POLICY_NAME=name, AVAILABLE_POLICIES=((COMMA+SPACE).join(cls._policies.keys())))
            )
        
        return policy
    
    @classmethod
    def register(cls, name: str, policy: IRetryPolicy):
        """
        Register a custom retry policy.
        
        Args:
            name: Policy name
            policy: Policy instance
        """
        cls._policies[name] = policy

