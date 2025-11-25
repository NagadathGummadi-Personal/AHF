"""
Security Factory for Tools Specification System.

Provides a centralized way to create and register security implementations by name.
"""

from typing import Dict

from ...interfaces.tool_interfaces import IToolSecurity
from .noop_security import NoOpSecurity
from .basic_security import BasicSecurity

from ...constants import (
    BASIC,
    NOOP,
    UNKNOWN_SECURITY_ERROR,
    COMMA,
    SPACE
)


class SecurityFactory:
    """
    Factory for creating security checker instances.
    
    Built-in Security Implementations:
        - 'basic': BasicSecurity - User and role-based authorization
        - 'noop': NoOpSecurity - No security checks (for testing/development)
    
    Usage:
        # Get built-in security
        security = SecurityFactory.get_security('basic')
        
        # Register custom security implementation
        SecurityFactory.register('oauth', OAuthSecurity())
        security = SecurityFactory.get_security('oauth')
    """
    
    _securities: Dict[str, IToolSecurity] = {
        BASIC: BasicSecurity(),
        NOOP: NoOpSecurity(),
    }
    
    @classmethod
    def get_security(cls, name: str = BASIC) -> IToolSecurity:
        """
        Get a security implementation by name.
        
        Args:
            name: Security implementation name ('basic', 'noop', etc.)
            
        Returns:
            IToolSecurity instance
            
        Raises:
            ValueError: If security name is not registered
        """
        security = cls._securities.get(name)
        
        if not security:
            available = (COMMA + SPACE).join(cls._securities.keys())
            raise ValueError(
                UNKNOWN_SECURITY_ERROR.format(SECURITY_NAME=name, AVAILABLE_SECURITIES=available)
            )
        
        return security
    
    @classmethod
    def register(cls, name: str, security: IToolSecurity):
        """
        Register a custom security implementation.
        
        Args:
            name: Name to register the security under
            security: Security instance implementing IToolSecurity
        
        Example:
            class OAuthSecurity(IToolSecurity):
                async def authorize(self, ctx, spec):
                    # OAuth authorization logic
                    pass
                
                async def check_egress(self, args, spec):
                    pass
            
            SecurityFactory.register('oauth', OAuthSecurity())
        """
        cls._securities[name] = security

