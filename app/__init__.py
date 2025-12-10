"""
AHF Voice Agent Application

Production-grade voice AI workflow application for salon booking.

Architecture:
- Modular nodes (tool_nodes, agent_nodes)
- Configurable edges with condition evaluation
- Task queue for user request management
- Interrupt handling with response stashing
- Lazy checkpointing for state persistence

Version: 1.0.0
"""

__version__ = "1.0.0"
__app_name__ = "ahf_voice_agent"

