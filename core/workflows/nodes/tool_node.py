"""
Tool Node Implementation Module.

This module provides a node that executes a tool/function.
"""

import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from ..interfaces import IWorkflowContext
from ..enum import NodeType
from ..spec import NodeSpec
from ..exceptions import NodeExecutionError
from .base_node import BaseNode

if TYPE_CHECKING:
    from core.tools import IToolExecutor

logger = logging.getLogger(__name__)


class ToolNode(BaseNode):
    """
    A node that executes a tool/function.
    
    Configuration:
        tool_name: Name of the tool to execute
        tool: Direct tool instance (alternative to tool_name)
        tool_config: Additional configuration for the tool
        input_mapping: Map input fields to tool parameters
    """
    
    def __init__(
        self,
        spec: NodeSpec,
        tool: Optional[Any] = None,
        tool_executor: Optional["IToolExecutor"] = None,
    ):
        """
        Initialize the tool node.
        
        Args:
            spec: Node specification.
            tool: Optional direct tool instance.
            tool_executor: Optional tool executor for running tools.
        """
        if spec.node_type != NodeType.TOOL:
            spec.node_type = NodeType.TOOL
        
        super().__init__(spec)
        
        self._tool = tool
        self._tool_executor = tool_executor
        self._tool_name = self._config.get("tool_name")
    
    async def execute(
        self,
        input_data: Any,
        context: IWorkflowContext,
    ) -> Any:
        """
        Execute the tool with workflow input.
        
        Args:
            input_data: Input from previous node or workflow.
            context: Workflow execution context.
            
        Returns:
            Tool execution result.
        """
        logger.info(f"Executing tool node: {self._name}")
        
        # Resolve input
        resolved_input = self._resolve_input(context, input_data)
        
        try:
            # Execute tool directly if provided
            if self._tool:
                if callable(self._tool):
                    if isinstance(resolved_input, dict):
                        result = await self._call_tool(self._tool, **resolved_input)
                    else:
                        result = await self._call_tool(self._tool, resolved_input)
                else:
                    result = self._tool
            # Use tool executor
            elif self._tool_executor and self._tool_name:
                result = await self._tool_executor.execute(
                    self._tool_name,
                    resolved_input,
                )
            else:
                raise NodeExecutionError(
                    f"No tool available for node {self._name}",
                    node_id=self._id,
                    node_type=self._node_type.value,
                )
            
            logger.debug(f"Tool node {self._name} completed successfully")
            return result
            
        except NodeExecutionError:
            raise
        except Exception as e:
            logger.error(f"Tool node {self._name} failed: {e}")
            raise NodeExecutionError(
                f"Tool execution failed: {e}",
                node_id=self._id,
                node_type=self._node_type.value,
                details={"error": str(e), "tool_name": self._tool_name},
            ) from e
    
    async def _call_tool(self, tool: Any, *args, **kwargs) -> Any:
        """Call the tool, handling both sync and async."""
        import asyncio
        
        if asyncio.iscoroutinefunction(tool):
            return await tool(*args, **kwargs)
        else:
            return tool(*args, **kwargs)
    
    async def validate(self, context: IWorkflowContext) -> List[str]:
        """Validate tool node configuration."""
        errors = await super().validate(context)
        
        if not self._tool and not self._tool_name:
            errors.append(
                f"Tool node {self._name}: Must specify tool or tool_name"
            )
        
        return errors
    
    def set_tool(self, tool: Any) -> None:
        """Set the tool instance directly."""
        self._tool = tool
    
    def set_tool_executor(self, executor: "IToolExecutor") -> None:
        """Set the tool executor."""
        self._tool_executor = executor

