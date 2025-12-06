"""
Delay Node Implementation Module.

This module provides a node that introduces a delay in workflow execution.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from ..interfaces import IWorkflowContext
from ..enum import NodeType
from ..spec import NodeSpec
from ..constants import DEFAULT_DELAY_SECONDS
from .base_node import BaseNode

logger = logging.getLogger(__name__)


class DelayNode(BaseNode):
    """
    A node that introduces a delay in workflow execution.
    
    Configuration:
        delay_seconds: Number of seconds to delay (default: 0)
        delay_ms: Delay in milliseconds (alternative to seconds)
        message: Optional message to log during delay
        pass_through: Whether to pass input through unchanged (default: True)
    """
    
    def __init__(self, spec: NodeSpec):
        """
        Initialize the delay node.
        
        Args:
            spec: Node specification.
        """
        if spec.node_type != NodeType.DELAY:
            spec.node_type = NodeType.DELAY
        
        super().__init__(spec)
        
        # Get delay configuration
        delay_seconds = self._config.get("delay_seconds", DEFAULT_DELAY_SECONDS)
        delay_ms = self._config.get("delay_ms")
        
        if delay_ms is not None:
            self._delay = delay_ms / 1000.0
        else:
            self._delay = delay_seconds
        
        self._message = self._config.get("message")
        self._pass_through = self._config.get("pass_through", True)
    
    async def execute(
        self,
        input_data: Any,
        context: IWorkflowContext,
    ) -> Any:
        """
        Delay execution and optionally pass through input.
        
        Args:
            input_data: Input from previous node.
            context: Workflow execution context.
            
        Returns:
            Input data (pass through) or delay info.
        """
        if self._message:
            logger.info(f"Delay node {self._name}: {self._message}")
        else:
            logger.info(f"Delay node {self._name}: Waiting {self._delay}s")
        
        # Perform the delay
        await asyncio.sleep(self._delay)
        
        logger.debug(f"Delay node {self._name}: Delay completed")
        
        if self._pass_through:
            return input_data
        
        return {
            "delayed": True,
            "delay_seconds": self._delay,
            "node_name": self._name,
        }
    
    async def validate(self, context: IWorkflowContext) -> List[str]:
        """Validate delay node configuration."""
        errors = await super().validate(context)
        
        if self._delay < 0:
            errors.append(
                f"Delay node {self._name}: delay_seconds must be non-negative"
            )
        
        return errors
    
    def set_delay(self, seconds: float) -> None:
        """Set the delay in seconds."""
        self._delay = seconds



