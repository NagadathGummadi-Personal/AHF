"""
No-Op Validator Implementation.

Disables validation for development/testing or gradual rollouts.
"""

from typing import Any, Dict

from ...interfaces.tool_interfaces import IToolValidator
from ...spec.tool_types import ToolSpec


class NoOpValidator(IToolValidator):
    """
    No-op implementation of IValidator that doesn't perform validation.
    
    Useful for:
    - Development/testing
    - Disabling validation for specific tools
    - Gradually rolling out validation
    
    Usage:
        validator = NoOpValidator()
        await validator.validate(args, spec)  # Always passes
    """
    
    async def validate(self, args: Dict[str, Any], spec: ToolSpec) -> None:
        """Validate parameters (no-op implementation)."""
        pass

