"""
No-Op Security Implementation.

Disables security checks for development/testing environments.
"""

from typing import Any, Dict

from ...interfaces.tool_interfaces import IToolSecurity
from ...spec.tool_context import ToolContext
from ...spec.tool_types import ToolSpec


class NoOpSecurity(IToolSecurity):
    """
    No-op implementation of IToolSecurity that doesn't perform security checks.
    
    Useful for:
    - Development/testing environments
    - Disabling security for specific tools
    - Prototyping without auth setup
    
    Usage:
        security = NoOpSecurity()
        await security.authorize(ctx, spec)  # Always passes
        await security.check_egress(args, spec)  # Always passes
    """
    
    async def authorize(self, ctx: ToolContext, spec: ToolSpec) -> None:
        """
        Authorize execution (no-op implementation).
        
        Args:
            ctx: Tool execution context (ignored)
            spec: Tool specification (ignored)
        """
        pass
    
    async def check_egress(self, args: Dict[str, Any], spec: ToolSpec) -> None:
        """
        Check egress permissions (no-op implementation).
        
        Args:
            args: Tool arguments (ignored)
            spec: Tool specification (ignored)
        """
        pass

