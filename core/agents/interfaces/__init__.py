"""
Interfaces for Agents Subsystem.

This module exports all protocol interfaces that define the contracts
for pluggable components in the agents system.
"""

from .agent_interfaces import (
    IAgent,
    IAgentMemory,
    IAgentScratchpad,
    IAgentChecklist,
    IAgentPlanner,
    IAgentObserver,
    IAgentInputProcessor,
    IAgentOutputProcessor,
)

__all__ = [
    "IAgent",
    "IAgentMemory",
    "IAgentScratchpad",
    "IAgentChecklist",
    "IAgentPlanner",
    "IAgentObserver",
    "IAgentInputProcessor",
    "IAgentOutputProcessor",
]

