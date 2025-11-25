"""
Metrics Factory for Tools Specification System.

Provides a centralized way to create and register metrics implementations by name.
"""

from typing import Dict

from ...interfaces.tool_interfaces import IToolMetrics
from .noop_metrics import NoOpMetrics

from ...constants import (
    NOOP,
    UNKNOWN_METRICS_ERROR,
    COMMA,
    SPACE
)


class MetricsFactory:
    """
    Factory for creating metrics collector instances.
    
    Built-in Metrics Implementations:
        - 'noop': NoOpMetrics - No metrics collection (for testing/development)
    
    Usage:
        # Get built-in metrics
        metrics = MetricsFactory.get_metrics('noop')
        
        # Register custom metrics implementation
        MetricsFactory.register('prometheus', PrometheusMetrics())
        metrics = MetricsFactory.get_metrics('prometheus')
    """
    
    _metrics: Dict[str, IToolMetrics] = {
        NOOP: NoOpMetrics(),
    }
    
    @classmethod
    def get_metrics(cls, name: str = NOOP) -> IToolMetrics:
        """
        Get a metrics implementation by name.
        
        Args:
            name: Metrics implementation name ('noop', 'prometheus', etc.)
            
        Returns:
            IToolMetrics instance
            
        Raises:
            ValueError: If metrics name is not registered
        """
        metrics = cls._metrics.get(name)
        
        if not metrics:
            available = (COMMA + SPACE).join(cls._metrics.keys())
            raise ValueError(
                UNKNOWN_METRICS_ERROR.format(METRICS_NAME=name, AVAILABLE_METRICS=available)
            )
        
        return metrics
    
    @classmethod
    def register(cls, name: str, metrics: IToolMetrics):
        """
        Register a custom metrics implementation.
        
        Args:
            name: Name to register the metrics under
            metrics: Metrics instance implementing IToolMetrics
        
        Example:
            class PrometheusMetrics(IToolMetrics):
                async def incr(self, name: str, value: int = 1, tags=None):
                    prometheus_client.inc(name, value)
                # ... implement other methods
            
            MetricsFactory.register('prometheus', PrometheusMetrics())
        """
        cls._metrics[name] = metrics

