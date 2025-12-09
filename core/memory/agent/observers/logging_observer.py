"""
Logging Observer Implementation.

Provides an observer that logs agent execution events.
"""

import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from ...interfaces import IAgentObserver

if TYPE_CHECKING:
    from core.agents.spec.agent_context import AgentContext
    from core.agents.spec.agent_result import AgentResult


class LoggingObserver(IAgentObserver):
    """
    Observer that logs agent execution events.
    
    Logs events at configurable log levels for debugging and monitoring.
    
    Usage:
        observer = LoggingObserver(logger=my_logger, level=logging.DEBUG)
        
        agent = (AgentBuilder()
            .with_name("my_agent")
            .with_llm(llm)
            .with_observer(observer)
            .build())
    """
    
    def __init__(
        self,
        logger: Optional[logging.Logger] = None,
        level: int = logging.DEBUG
    ):
        """
        Initialize logging observer.
        
        Args:
            logger: Logger to use (defaults to module logger)
            level: Log level for events
        """
        self._logger = logger or logging.getLogger(__name__)
        self._level = level
    
    async def on_agent_start(self, input_data: Any, ctx: 'AgentContext') -> None:
        """Log agent start."""
        self._logger.log(
            self._level,
            "Agent started",
            extra={
                "request_id": ctx.request_id,
                "user_id": ctx.user_id,
                "input_type": type(input_data).__name__,
            }
        )
    
    async def on_agent_end(self, result: 'AgentResult', ctx: 'AgentContext') -> None:
        """Log agent completion."""
        self._logger.log(
            self._level,
            "Agent completed",
            extra={
                "request_id": ctx.request_id,
                "state": result.state.value,
                "iterations": result.usage.iterations if result.usage else 0,
            }
        )
    
    async def on_iteration_start(self, iteration: int, ctx: 'AgentContext') -> None:
        """Log iteration start."""
        self._logger.log(
            self._level,
            f"Iteration {iteration} started",
            extra={
                "request_id": ctx.request_id,
                "iteration": iteration,
            }
        )
    
    async def on_iteration_end(self, iteration: int, ctx: 'AgentContext') -> None:
        """Log iteration end."""
        self._logger.log(
            self._level,
            f"Iteration {iteration} completed",
            extra={
                "request_id": ctx.request_id,
                "iteration": iteration,
            }
        )
    
    async def on_tool_call(
        self,
        tool_name: str,
        args: Dict[str, Any],
        ctx: 'AgentContext'
    ) -> None:
        """Log tool call."""
        self._logger.log(
            self._level,
            f"Tool call: {tool_name}",
            extra={
                "request_id": ctx.request_id,
                "tool_name": tool_name,
                "args": args,
            }
        )
    
    async def on_tool_result(
        self,
        tool_name: str,
        result: Any,
        ctx: 'AgentContext'
    ) -> None:
        """Log tool result."""
        self._logger.log(
            self._level,
            f"Tool result: {tool_name}",
            extra={
                "request_id": ctx.request_id,
                "tool_name": tool_name,
                "result_type": type(result).__name__,
            }
        )
    
    async def on_llm_call(
        self,
        messages: List[Dict[str, Any]],
        ctx: 'AgentContext'
    ) -> None:
        """Log LLM call."""
        self._logger.log(
            self._level,
            f"LLM call with {len(messages)} messages",
            extra={
                "request_id": ctx.request_id,
                "message_count": len(messages),
            }
        )
    
    async def on_llm_response(self, response: Any, ctx: 'AgentContext') -> None:
        """Log LLM response."""
        self._logger.log(
            self._level,
            "LLM response received",
            extra={
                "request_id": ctx.request_id,
                "response_type": type(response).__name__,
            }
        )
    
    async def on_error(self, error: Exception, ctx: 'AgentContext') -> None:
        """Log error."""
        self._logger.error(
            f"Agent error: {error}",
            extra={
                "request_id": ctx.request_id,
                "error_type": type(error).__name__,
                "error_message": str(error),
            },
            exc_info=True
        )


