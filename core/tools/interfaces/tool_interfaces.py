from __future__ import annotations

from typing import Any, Dict, Protocol, runtime_checkable, Callable, Awaitable, AsyncContextManager, Optional, TYPE_CHECKING
from contextlib import asynccontextmanager

if TYPE_CHECKING:
    from ..spec.tool_result import ToolResult
    from ..spec.tool_types import ToolSpec
    from ..spec.tool_context import ToolContext


@runtime_checkable
class IToolExecutor(Protocol):
    """Interface for tool execution"""
    async def execute(self, args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
        ...


@runtime_checkable
class IToolValidator(Protocol):
    """Interface for parameter validation"""
    async def validate(self, args: Dict[str, Any], spec: ToolSpec) -> None:
        ...


@runtime_checkable
class IToolSecurity(Protocol):
    """Interface for security checks"""
    async def authorize(self, ctx: ToolContext, spec: ToolSpec) -> None:
        ...

    async def check_egress(self, args: Dict[str, Any], spec: ToolSpec) -> None:
        ...


@runtime_checkable
class IToolPolicy(Protocol):
    """Interface for execution policies (retries, circuit breaker, etc.)"""
    async def with_policy(
        self,
        attempt_coro_factory: Callable[[], Awaitable[ToolResult]],
        *,
        idempotent: bool,
        spec: ToolSpec,
        ctx: ToolContext
    ) -> ToolResult:
        ...


@runtime_checkable
class IToolEmitter(Protocol):
    """Interface for event emission"""
    async def emit(self, event_type: str, payload: Dict[str, Any]) -> None:
        ...


@runtime_checkable
class IToolMemory(Protocol):
    """Interface for memory/caching operations"""
    async def get(self, key: str) -> Any:
        ...

    async def set(self, key: str, value: Any, ttl_s: Optional[int] = None) -> None:
        ...

    async def set_if_absent(self, key: str, value: Any, ttl_s: Optional[int] = None) -> bool:
        ...

    async def delete(self, key: str) -> None:
        ...

    @asynccontextmanager
    async def lock(self, key: str, ttl_s: int = 10) -> AsyncContextManager[None]:
        yield


@runtime_checkable
class IToolMetrics(Protocol):
    """Interface for metrics collection"""
    async def incr(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None) -> None:
        ...

    async def observe(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        ...

    async def timing_ms(self, name: str, value_ms: int, tags: Optional[Dict[str, str]] = None) -> None:
        ...


@runtime_checkable
class IToolTracer(Protocol):
    """Interface for distributed tracing"""
    @asynccontextmanager
    async def span(self, name: str, attrs: Optional[Dict[str, Any]] = None) -> AsyncContextManager[str]:
        # yields span_id
        yield ""


@runtime_checkable
class IToolLimiter(Protocol):
    """Interface for rate limiting"""
    @asynccontextmanager
    async def acquire(self, key: str, limit: Optional[int] = None) -> AsyncContextManager[None]:
        yield
