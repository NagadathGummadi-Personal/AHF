"""
Factory for creating circuit breaker policy instances.
"""

from typing import Dict
from .circuit_breaker import ICircuitBreakerPolicy
from .standard_circuit_breaker_policy import StandardCircuitBreakerPolicy
from .adaptive_circuit_breaker_policy import AdaptiveCircuitBreakerPolicy
from .noop_circuit_breaker_policy import NoOpCircuitBreakerPolicy

from ....constants import (
    STANDARD,
    ADAPTIVE,
    NOOP,
    UNKNOWN_CIRCUIT_BREAKER_POLICY_ERROR,
    COMMA,
    SPACE
)


class CircuitBreakerPolicyFactory:
    """
    Factory for creating circuit breaker policy instances.
    
    Built-in Policies:
        - 'standard': StandardCircuitBreakerPolicy
        - 'adaptive': AdaptiveCircuitBreakerPolicy
        - 'noop': NoOpCircuitBreakerPolicy
    
    Usage:
        policy = CircuitBreakerPolicyFactory.get_policy('standard')
        spec.circuit_breaker_policy = policy
    """
    
    _policies: Dict[str, ICircuitBreakerPolicy] = {
        STANDARD: StandardCircuitBreakerPolicy(),
        ADAPTIVE: AdaptiveCircuitBreakerPolicy(),
        NOOP: NoOpCircuitBreakerPolicy(),
    }
    
    @classmethod
    def get_policy(cls, name: str = STANDARD) -> ICircuitBreakerPolicy:
        """
        Get a circuit breaker policy by name.
        
        Args:
            name: Policy name ('standard', 'adaptive', 'noop')
            
        Returns:
            ICircuitBreakerPolicy instance
            
        Raises:
            ValueError: If policy name not found
        """
        policy = cls._policies.get(name)
        
        if not policy:
            raise ValueError(
                UNKNOWN_CIRCUIT_BREAKER_POLICY_ERROR.format(
                    POLICY_NAME=name,
                    AVAILABLE_POLICIES=((COMMA+SPACE).join(cls._policies.keys()))
                )
            )
        
        return policy
    
    @classmethod
    def register(cls, name: str, policy: ICircuitBreakerPolicy):
        """
        Register a custom circuit breaker policy.
        
        Args:
            name: Policy name
            policy: Policy instance
        """
        cls._policies[name] = policy

