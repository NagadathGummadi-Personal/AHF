"""
NoOp Executor - Placeholder executor that does nothing.

This executor is used for testing, mocking, or as a placeholder
when an executor is required but no actual execution should occur.
"""

from typing import Any, Dict
from .base_executor import BaseToolExecutor
from ...spec.tool_types import ToolSpec, ToolReturnType, ToolReturnTarget
from ...spec.tool_context import ToolContext
from ...spec.tool_result import ToolResult


class NoOpExecutor(BaseToolExecutor):
    """
    No-operation executor that does nothing and returns an empty result.
    
    This is useful for:
    - Testing without executing actual operations
    - Placeholder during development
    - Dry-run scenarios
    - Mocking in test environments
    
    Example:
        ```python
        from core.tools.runtimes.executors import NoOpExecutor
        from core.tools.spec import ToolSpec, ToolContext
        
        spec = ToolSpec(...)
        executor = NoOpExecutor(spec)
        
        # Execute - does nothing, returns empty result
        result = await executor.execute({}, ToolContext())
        ```
    """
    
    def __init__(self, spec: ToolSpec):
        """
        Initialize NoOpExecutor.
        
        Args:
            spec: Tool specification (required but not used)
        """
        super().__init__(spec)
    
    async def execute(self, args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
        """
        Execute the no-op operation (does nothing).
        
        Args:
            args: Input arguments (ignored)
            ctx: Tool context (ignored)
            
        Returns:
            Empty ToolResult with success status
        """
        # Do nothing, return empty result
        return ToolResult(
            return_type=self.spec.return_type or ToolReturnType.JSON,
            return_target=self.spec.return_target or ToolReturnTarget.STEP,
            content={
                "status": "noop",
                "message": "NoOp executor - no operation performed",
                "executor": "NoOpExecutor",
                "tool_name": self.spec.tool_name
            }
        )

