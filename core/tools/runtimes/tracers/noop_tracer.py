"""
No-Op Tracer Implementation.

Disables distributed tracing for simple execution without tracing overhead.
"""

from contextlib import asynccontextmanager
from typing import Any, AsyncContextManager, Dict, Optional

from ...interfaces.tool_interfaces import IToolTracer


class NoOpTracer(IToolTracer):
    """
    No-op implementation of IToolTracer that doesn't create trace spans.
    
    Useful for:
    - Development/testing without tracing infrastructure
    - Reducing overhead in performance-critical scenarios
    - Simple executions that don't need distributed tracing
    - Prototyping without tracing backend
    
    Usage:
        tracer = NoOpTracer()
        
        # Span is a no-op context manager
        async with tracer.span("operation", {"attr": "value"}) as span_id:
            # span_id will be empty string ""
            # No actual tracing occurs
            await do_work()
    """
    
    @asynccontextmanager
    async def span(self, name: str, attrs: Optional[Dict[str, Any]] = None) -> AsyncContextManager[str]:
        """
        Create tracing span (no-op implementation).
        
        Provides a no-op context manager that doesn't create actual spans.
        
        Args:
            name: Span name (ignored)
            attrs: Span attributes (ignored)
            
        Yields:
            Empty string (representing span ID)
        """
        yield ""

