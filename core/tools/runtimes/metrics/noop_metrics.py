"""
No-Op Metrics Implementation.

Disables metrics collection for simple execution without observability overhead.
"""

from typing import Dict, Optional

from ...interfaces.tool_interfaces import IToolMetrics


class NoOpMetrics(IToolMetrics):
    """
    No-op implementation of IToolMetrics that doesn't collect metrics.
    
    Useful for:
    - Development/testing without metrics infrastructure
    - Reducing overhead in performance-critical scenarios
    - Simple executions that don't need observability
    - Prototyping without metrics backend
    
    Usage:
        metrics = NoOpMetrics()
        
        # All operations are no-ops
        await metrics.incr("tool.execution.count")  # No-op
        await metrics.observe("tool.execution.duration", 1.5)  # No-op
        await metrics.timing_ms("tool.latency", 150)  # No-op
    """
    
    async def incr(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None) -> None:
        """
        Increment metric (no-op implementation).
        
        Args:
            name: Metric name (ignored)
            value: Value to increment by (ignored)
            tags: Metric tags for grouping/filtering (ignored)
        """
        pass
    
    async def observe(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """
        Observe metric value (no-op implementation).
        
        Args:
            name: Metric name (ignored)
            value: Observed value (ignored)
            tags: Metric tags for grouping/filtering (ignored)
        """
        pass
    
    async def timing_ms(self, name: str, value_ms: int, tags: Optional[Dict[str, str]] = None) -> None:
        """
        Record timing metric (no-op implementation).
        
        Args:
            name: Metric name (ignored)
            value_ms: Timing value in milliseconds (ignored)
            tags: Metric tags for grouping/filtering (ignored)
        """
        pass

