"""
Tracer Factory for Tools Specification System.

Provides a centralized way to create and register tracer implementations by name.
"""

from typing import Dict

from ...interfaces.tool_interfaces import IToolTracer
from .noop_tracer import NoOpTracer

from ...constants import (
    NOOP,
    UNKNOWN_TRACER_ERROR,
    COMMA,
    SPACE
)


class TracerFactory:
    """
    Factory for creating distributed tracer instances.
    
    Built-in Tracer Implementations:
        - 'noop': NoOpTracer - No tracing (for testing/development)
    
    Usage:
        # Get built-in tracer
        tracer = TracerFactory.get_tracer('noop')
        
        # Register custom tracer implementation
        TracerFactory.register('opentelemetry', OpenTelemetryTracer())
        tracer = TracerFactory.get_tracer('opentelemetry')
    """
    
    _tracers: Dict[str, IToolTracer] = {
        NOOP: NoOpTracer(),
    }
    
    @classmethod
    def get_tracer(cls, name: str = NOOP) -> IToolTracer:
        """
        Get a tracer implementation by name.
        
        Args:
            name: Tracer implementation name ('noop', 'opentelemetry', etc.)
            
        Returns:
            IToolTracer instance
            
        Raises:
            ValueError: If tracer name is not registered
        """
        tracer = cls._tracers.get(name)
        
        if not tracer:
            available = (COMMA + SPACE).join(cls._tracers.keys())
            raise ValueError(
                UNKNOWN_TRACER_ERROR.format(TRACER_NAME=name, AVAILABLE_TRACERS=available)
            )
        
        return tracer
    
    @classmethod
    def register(cls, name: str, tracer: IToolTracer):
        """
        Register a custom tracer implementation.
        
        Args:
            name: Name to register the tracer under
            tracer: Tracer instance implementing IToolTracer
        
        Example:
            class OpenTelemetryTracer(IToolTracer):
                @asynccontextmanager
                async def span(self, name: str, attrs=None):
                    with tracer.start_span(name) as span:
                        yield span.get_span_context().span_id
            
            TracerFactory.register('opentelemetry', OpenTelemetryTracer())
        """
        cls._tracers[name] = tracer

