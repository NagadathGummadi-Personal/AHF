"""
Scratchpad implementations for Agents.

Note: Scratchpad implementations are now located in core.memory.agent.scratchpad
and re-exported here for backward compatibility.
"""

# Re-export from core.memory.agent.scratchpad for backward compatibility
from core.memory.agent.scratchpad import (
    BasicScratchpad,
    StructuredScratchpad,
    ScratchpadFactory,
)

__all__ = [
    "BasicScratchpad",
    "StructuredScratchpad",
    "ScratchpadFactory",
]
