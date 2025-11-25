"""
No-Op Emitter Implementation.

Disables event emission for simple execution without event tracking.
"""

from typing import Any, Dict

from ...interfaces.tool_interfaces import IToolEmitter


class NoOpEmitter(IToolEmitter):
    """
    No-op implementation of IToolEmitter that doesn't emit events.
    
    Useful for:
    - Simple executions without event tracking
    - Testing environments
    - Development without event infrastructure
    - Reducing overhead in high-performance scenarios
    
    Usage:
        emitter = NoOpEmitter()
        await emitter.emit("tool.executed", {"tool": "my_tool"})  # No-op
    """
    
    async def emit(self, event_type: str, payload: Dict[str, Any]) -> None:
        """
        Emit event (no-op implementation).
        
        Args:
            event_type: Type of event to emit (ignored)
            payload: Event payload data (ignored)
        """
        pass

