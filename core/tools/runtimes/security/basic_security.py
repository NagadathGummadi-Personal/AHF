"""
Basic Security Implementation with authorization checks.

Provides user-based and role-based authorization.
"""

from typing import Any, Dict, List, Optional

from ...interfaces.tool_interfaces import IToolSecurity
from ...spec.tool_context import ToolContext
from ...spec.tool_result import ToolError
from ...spec.tool_types import ToolSpec
from ...constants import (
    ERROR_UNAUTHORIZED,
    ERROR_INSUFFICIENT_PERMISSIONS,
    ERROR_UNAUTHORIZED_ROLE,
    MSG_UNAUTHORIZED_USER,
    MSG_MISSING_REQUIRED_PERMISSIONS,
    MSG_UNAUTHORIZED_ROLE,
)


class BasicSecurity(IToolSecurity):
    """
    Basic implementation of IToolSecurity with authorization.
    
    Provides:
    - User-based authorization
    - Permission-based authorization
    - Role-based authorization
    
    Usage:
        # User-based only
        security = BasicSecurity(authorized_users=["user1", "user2"])
        
        # Role-based only
        security = BasicSecurity(authorized_roles=["admin", "developer"])
        
        # Combined
        security = BasicSecurity(
            authorized_users=["user1"],
            authorized_roles=["admin"]
        )
        
        await security.authorize(ctx, spec)
    """
    
    def __init__(
        self, 
        authorized_users: Optional[List[str]] = None, 
        authorized_roles: Optional[List[str]] = None
    ):
        """
        Initialize BasicSecurity with authorization lists.
        
        Args:
            authorized_users: List of authorized user IDs (empty = all users)
            authorized_roles: List of authorized roles (empty = all roles)
        """
        self.authorized_users = authorized_users or []
        self.authorized_roles = authorized_roles or []
    
    async def authorize(self, ctx: ToolContext, spec: ToolSpec) -> None:
        """
        Authorize execution based on user and permissions.
        
        Args:
            ctx: Tool execution context with user info
            spec: Tool specification with required permissions
            
        Raises:
            ToolError: If authorization fails
        """
        # Check if user is authorized
        if self.authorized_users and ctx.user_id not in self.authorized_users:
            raise ToolError(
                MSG_UNAUTHORIZED_USER.format(user_id=ctx.user_id, tool_name=spec.tool_name),
                retryable=False,
                code=ERROR_UNAUTHORIZED,
            )
        
        # Check if user has required permissions
        if spec.permissions:
            user_permissions = ctx.auth.get("permissions", [])
            if not all(perm in user_permissions for perm in spec.permissions):
                missing_perms = [perm for perm in spec.permissions if perm not in user_permissions]
                raise ToolError(
                    MSG_MISSING_REQUIRED_PERMISSIONS.format(user_id=ctx.user_id, missing_perms=missing_perms),
                    retryable=False,
                    code=ERROR_INSUFFICIENT_PERMISSIONS,
                )
        
        # Check role-based authorization
        if self.authorized_roles:
            user_role = ctx.auth.get("user_role")
            if user_role not in self.authorized_roles:
                raise ToolError(
                    MSG_UNAUTHORIZED_ROLE.format(user_role=user_role, tool_name=spec.tool_name),
                    retryable=False,
                    code=ERROR_UNAUTHORIZED_ROLE,
                )
    
    async def check_egress(self, args: Dict[str, Any], spec: ToolSpec) -> None:
        """
        Check egress permissions (basic implementation).
        
        In a real implementation, this would check if the tool is allowed
        to access external resources, send data to external systems, etc.
        
        Args:
            args: Tool arguments
            spec: Tool specification
        """
        # For now, just pass - in a real implementation, this would check
        # if the tool is allowed to access external resources
        pass

