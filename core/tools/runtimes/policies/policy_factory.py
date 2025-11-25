"""
Policy Factory for Tools Specification System.

Provides a centralized way to create and register policy implementations by name.
"""

from typing import Dict

from ...interfaces.tool_interfaces import IToolPolicy
from .noop_policy import NoOpPolicy

from ...constants import (
    NOOP,
    UNKNOWN_POLICY_ERROR,
    COMMA,
    SPACE
)


class PolicyFactory:
    """
    Factory for creating execution policy instances.
    
    Built-in Policy Implementations:
        - 'noop': NoOpPolicy - No policy controls (single execution attempt)
    
    Note:
        For retry and circuit breaker policies, use RetryPolicyFactory and
        CircuitBreakerPolicyFactory instead, as they use specialized interfaces.
    
    Usage:
        # Get built-in policy
        policy = PolicyFactory.get_policy('noop')
        
        # Register custom policy implementation
        PolicyFactory.register('custom', CustomPolicy())
        policy = PolicyFactory.get_policy('custom')
    """
    
    _policies: Dict[str, IToolPolicy] = {
        NOOP: NoOpPolicy(),
    }
    
    @classmethod
    def get_policy(cls, name: str = NOOP) -> IToolPolicy:
        """
        Get a policy implementation by name.
        
        Args:
            name: Policy implementation name ('noop', etc.)
            
        Returns:
            IToolPolicy instance
            
        Raises:
            ValueError: If policy name is not registered
        """
        policy = cls._policies.get(name)
        
        if not policy:
            available = (COMMA + SPACE).join(cls._policies.keys())
            raise ValueError(
                UNKNOWN_POLICY_ERROR.format(POLICY_NAME=name, AVAILABLE_POLICIES=available)
            )
        
        return policy
    
    @classmethod
    def register(cls, name: str, policy: IToolPolicy):
        """
        Register a custom policy implementation.
        
        Args:
            name: Name to register the policy under
            policy: Policy instance implementing IToolPolicy
        
        Example:
            class CustomPolicy(IToolPolicy):
                async def with_policy(self, attempt_coro_factory, *, idempotent, spec, ctx):
                    # Custom policy logic
                    return await attempt_coro_factory()
            
            PolicyFactory.register('custom', CustomPolicy())
        """
        cls._policies[name] = policy

