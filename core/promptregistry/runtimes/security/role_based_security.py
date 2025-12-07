"""
Role-Based Prompt Security Implementation.

Provides role-based access control for prompts.
"""

from typing import List, Set, Optional

from ...interfaces.prompt_registry_interfaces import (
    IPromptSecurity,
    SecurityContext,
    AccessDecision,
)


class RoleBasedPromptSecurity(IPromptSecurity):
    """
    Role-Based Prompt Security.
    
    Provides role-based access control where users are granted access
    based on their roles.
    
    Special values:
    - "*" in any role list means "all users"
    - Empty list means "no one"
    
    Usage:
        security = RoleBasedPromptSecurity(
            read_roles=["*"],  # Everyone can read
            write_roles=["developer", "content_manager"],
            delete_roles=["admin"],
            admin_roles=["admin", "prompt_admin"]
        )
        
        ctx = SecurityContext(user_id="user123", roles=["developer"])
        
        # Developer can read and write
        assert security.can_read("test", ctx).allowed
        assert security.can_write("test", ctx).allowed
        
        # But not delete
        assert not security.can_delete("test", ctx).allowed
    """
    
    def __init__(
        self,
        read_roles: Optional[List[str]] = None,
        write_roles: Optional[List[str]] = None,
        delete_roles: Optional[List[str]] = None,
        admin_roles: Optional[List[str]] = None,
        default_allow: bool = False,
    ):
        """
        Initialize role-based security.
        
        Args:
            read_roles: Roles that can read prompts (default: ["*"])
            write_roles: Roles that can write/create prompts (default: ["admin"])
            delete_roles: Roles that can delete prompts (default: ["admin"])
            admin_roles: Roles with admin access (default: ["admin"])
            default_allow: Default decision when no roles configured
        """
        self.read_roles: Set[str] = set(read_roles or ["*"])
        self.write_roles: Set[str] = set(write_roles or ["admin"])
        self.delete_roles: Set[str] = set(delete_roles or ["admin"])
        self.admin_roles: Set[str] = set(admin_roles or ["admin"])
        self.default_allow = default_allow
    
    def _check_access(
        self,
        allowed_roles: Set[str],
        context: SecurityContext,
        operation: str
    ) -> AccessDecision:
        """Check if context has any of the allowed roles."""
        # Wildcard allows everyone
        if "*" in allowed_roles:
            return AccessDecision(
                allowed=True,
                reason=f"All users allowed for {operation}"
            )
        
        # Empty roles means no one
        if not allowed_roles:
            return AccessDecision(
                allowed=self.default_allow,
                reason=f"No roles configured for {operation}",
                required_permissions=list(allowed_roles)
            )
        
        # Check if user has any allowed role
        user_roles = set(context.roles or [])
        matching_roles = user_roles & allowed_roles
        
        if matching_roles:
            return AccessDecision(
                allowed=True,
                reason=f"User has role(s): {', '.join(matching_roles)}"
            )
        
        return AccessDecision(
            allowed=False,
            reason=f"User lacks required role(s) for {operation}",
            required_permissions=list(allowed_roles)
        )
    
    def can_read(
        self,
        label: str,
        context: SecurityContext
    ) -> AccessDecision:
        """Check read access."""
        return self._check_access(self.read_roles, context, "read")
    
    def can_write(
        self,
        label: str,
        context: SecurityContext
    ) -> AccessDecision:
        """Check write access."""
        return self._check_access(self.write_roles, context, "write")
    
    def can_delete(
        self,
        label: str,
        context: SecurityContext
    ) -> AccessDecision:
        """Check delete access."""
        return self._check_access(self.delete_roles, context, "delete")
    
    def can_admin(
        self,
        label: str,
        context: SecurityContext
    ) -> AccessDecision:
        """Check admin access."""
        return self._check_access(self.admin_roles, context, "admin")
    
    def filter_accessible(
        self,
        labels: List[str],
        context: SecurityContext,
        operation: str = "read"
    ) -> List[str]:
        """Filter labels to only those accessible."""
        # Get the appropriate check method
        check_method = {
            "read": self.can_read,
            "write": self.can_write,
            "delete": self.can_delete,
            "admin": self.can_admin,
        }.get(operation, self.can_read)
        
        # Filter labels
        return [
            label for label in labels
            if check_method(label, context).allowed
        ]
    
    def get_required_permissions(
        self,
        label: str,
        operation: str
    ) -> List[str]:
        """Get required roles for an operation."""
        role_sets = {
            "read": self.read_roles,
            "write": self.write_roles,
            "delete": self.delete_roles,
            "admin": self.admin_roles,
        }
        
        roles = role_sets.get(operation, set())
        return list(roles)

