"""
No-Op Observer Implementation.

Provides a no-op observer for agents.
"""

from typing import Any, Dict, List, TYPE_CHECKING

from ...interfaces.agent_interfaces import IAgentObserver

if TYPE_CHECKING:
    from ...spec.agent_context import AgentContext
    from ...spec.agent_result import AgentResult


class NoOpObserver(IAgentObserver):
    """
    No-op implementation of IAgentObserver.
    
    All methods are no-ops. Useful for testing or when no observation is needed.
    """
    
    async def on_agent_start(self, input_data: Any, ctx: 'AgentContext') -> None:
        """Called when agent execution starts (no-op)."""
        pass
    
    async def on_agent_end(self, result: 'AgentResult', ctx: 'AgentContext') -> None:
        """Called when agent execution ends (no-op)."""
        pass
    
    async def on_iteration_start(self, iteration: int, ctx: 'AgentContext') -> None:
        """Called at the start of each iteration (no-op)."""
        pass
    
    async def on_iteration_end(self, iteration: int, ctx: 'AgentContext') -> None:
        """Called at the end of each iteration (no-op)."""
        pass
    
    async def on_tool_call(
        self,
        tool_name: str,
        args: Dict[str, Any],
        ctx: 'AgentContext'
    ) -> None:
        """Called when a tool is invoked (no-op)."""
        pass
    
    async def on_tool_result(
        self,
        tool_name: str,
        result: Any,
        ctx: 'AgentContext'
    ) -> None:
        """Called when a tool returns a result (no-op)."""
        pass
    
    async def on_llm_call(
        self,
        messages: List[Dict[str, Any]],
        ctx: 'AgentContext'
    ) -> None:
        """Called when the LLM is invoked (no-op)."""
        pass
    
    async def on_llm_response(self, response: Any, ctx: 'AgentContext') -> None:
        """Called when the LLM returns a response (no-op)."""
        pass
    
    async def on_error(self, error: Exception, ctx: 'AgentContext') -> None:
        """Called when an error occurs (no-op)."""
        pass

