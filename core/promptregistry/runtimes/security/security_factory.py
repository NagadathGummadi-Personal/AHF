"""
Prompt Security Factory.

Factory for creating prompt security implementations.
"""

from typing import Dict, Type, List

from ...interfaces.prompt_registry_interfaces import IPromptSecurity
from .noop_security import NoOpPromptSecurity
from .role_based_security import RoleBasedPromptSecurity


class PromptSecurityFactory:
    """
    Factory for creating prompt security implementations.
    
    Usage:
        # Get NoOp security (no access control)
        security = PromptSecurityFactory.get_security('noop')
        
        # Get role-based security with defaults
        security = PromptSecurityFactory.get_security('role_based')
        
        # Get role-based security with custom config
        security = PromptSecurityFactory.get_security(
            'role_based',
            read_roles=["*"],
            write_roles=["developer", "admin"],
            delete_roles=["admin"]
        )
        
        # Register custom security
        PromptSecurityFactory.register('tenant', TenantPromptSecurity)
    """
    
    _security_map: Dict[str, Type[IPromptSecurity]] = {
        'noop': NoOpPromptSecurity,
        'none': NoOpPromptSecurity,
        'role_based': RoleBasedPromptSecurity,
        'rbac': RoleBasedPromptSecurity,
        'default': NoOpPromptSecurity,  # Default to no security
    }
    
    @classmethod
    def get_security(
        cls,
        name: str = 'default',
        **kwargs
    ) -> IPromptSecurity:
        """
        Get a security implementation by name.
        
        Args:
            name: Security implementation name
            **kwargs: Arguments to pass to security constructor
            
        Returns:
            Security instance
            
        Raises:
            ValueError: If security name is unknown
        """
        name_lower = name.lower()
        security_class = cls._security_map.get(name_lower)
        
        if not security_class:
            raise ValueError(
                f"Unknown security: {name}. Available: {list(cls._security_map.keys())}"
            )
        
        return security_class(**kwargs)
    
    @classmethod
    def register(
        cls,
        name: str,
        security_class: Type[IPromptSecurity]
    ) -> None:
        """
        Register a custom security implementation.
        
        Args:
            name: Name to register under
            security_class: Security class implementing IPromptSecurity
        """
        cls._security_map[name.lower()] = security_class
    
    @classmethod
    def list_available(cls) -> List[str]:
        """List all registered security implementations."""
        return list(cls._security_map.keys())
    
    @classmethod
    def unregister(cls, name: str) -> None:
        """Unregister a security (for testing)."""
        cls._security_map.pop(name.lower(), None)

