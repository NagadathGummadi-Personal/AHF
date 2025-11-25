"""
No-Op Policy Implementation.

Disables policy controls (retries, circuit breakers) for simple execution.
"""

from typing import Callable, Awaitable

from ...interfaces.tool_interfaces import IToolPolicy
from ...spec.tool_context import ToolContext
from ...spec.tool_result import ToolResult
from ...spec.tool_types import ToolSpec


class NoOpPolicy(IToolPolicy):
    """
    No-op implementation of IToolPolicy that doesn't apply policy controls.
    
    Useful for:
    - Simple, one-shot executions
    - Testing without retry/circuit breaker logic
    - Development environments
    - Tools that manage their own resilience
    
    Usage:
        policy = NoOpPolicy()
        result = await policy.with_policy(
            attempt_coro_factory=lambda: execute_tool(),
            idempotent=True,
            spec=spec,
            ctx=ctx
        )
    """
    
    async def with_policy(
        self,
        attempt_coro_factory: Callable[[], Awaitable[ToolResult]],
        *,
        idempotent: bool,
        spec: ToolSpec,
        ctx: ToolContext
    ) -> ToolResult:
        """
        Execute with policy controls (no-op implementation).
        
        Simply executes the coroutine factory once without any retry,
        circuit breaker, or other policy controls.
        
        Args:
            attempt_coro_factory: Factory function that creates execution coroutine
            idempotent: Whether the operation is idempotent (ignored)
            spec: Tool specification (ignored)
            ctx: Tool execution context (ignored)
            
        Returns:
            Result from single execution attempt
        """
        return await attempt_coro_factory()

