"""
Agent Node Implementation Module.

This module provides a node that executes an AI agent.
"""

import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from ..interfaces import IWorkflowContext
from ..enum import NodeType
from ..spec import NodeSpec
from ..exceptions import NodeExecutionError
from .base_node import BaseNode

if TYPE_CHECKING:
    from core.agents import IAgent

logger = logging.getLogger(__name__)


class AgentNode(BaseNode):
    """
    A node that executes an AI agent.
    
    Configuration:
        agent_id: ID of a registered agent to use
        agent: Direct agent instance (alternative to agent_id)
        agent_config: Configuration to pass to agent builder
        system_prompt: Optional system prompt override
        max_iterations: Optional max iterations override
        input_key: Key to extract from input for agent (default: all input)
        output_key: Key to store agent result (default: full result)
    """
    
    def __init__(
        self,
        spec: NodeSpec,
        agent: Optional["IAgent"] = None,
        agent_factory: Optional[Any] = None,
    ):
        """
        Initialize the agent node.
        
        Args:
            spec: Node specification.
            agent: Optional direct agent instance.
            agent_factory: Optional factory for creating agents.
        """
        if spec.node_type != NodeType.AGENT:
            spec.node_type = NodeType.AGENT
        
        super().__init__(spec)
        
        self._agent = agent
        self._agent_factory = agent_factory
        self._system_prompt = self._config.get("system_prompt")
        self._input_key = self._config.get("input_key")
        self._output_key = self._config.get("output_key")
    
    async def execute(
        self,
        input_data: Any,
        context: IWorkflowContext,
    ) -> Any:
        """
        Execute the agent with workflow input.
        
        Args:
            input_data: Input from previous node or workflow.
            context: Workflow execution context.
            
        Returns:
            Agent execution result.
        """
        logger.info(f"Executing agent node: {self._name}")
        
        # Get or create the agent
        agent = await self._get_agent(context)
        if not agent:
            raise NodeExecutionError(
                f"No agent available for node {self._name}",
                node_id=self._id,
                node_type=self._node_type.value,
            )
        
        # Resolve input
        resolved_input = self._resolve_input(context, input_data)
        
        # Extract agent input
        if self._input_key:
            agent_input = resolved_input.get(self._input_key, resolved_input)
        else:
            agent_input = resolved_input.get("$input", resolved_input)
        
        # Create agent context from workflow context
        agent_context = self._create_agent_context(context)
        
        try:
            # Execute agent
            result = await agent.run(agent_input, agent_context)
            
            # Extract output
            if self._output_key and hasattr(result, self._output_key):
                output = getattr(result, self._output_key)
            elif hasattr(result, "output"):
                output = result.output
            else:
                output = result
            
            logger.debug(f"Agent node {self._name} completed successfully")
            return output
            
        except Exception as e:
            logger.error(f"Agent node {self._name} failed: {e}")
            raise NodeExecutionError(
                f"Agent execution failed: {e}",
                node_id=self._id,
                node_type=self._node_type.value,
                details={"error": str(e)},
            ) from e
    
    async def validate(self, context: IWorkflowContext) -> List[str]:
        """Validate agent node configuration."""
        errors = await super().validate(context)
        
        # Check if we have an agent or can create one
        if not self._agent:
            if not self._config.get("agent_id") and not self._config.get("agent_config"):
                errors.append(
                    f"Agent node {self._name}: Must specify agent, agent_id, or agent_config"
                )
        
        return errors
    
    async def _get_agent(self, context: IWorkflowContext) -> Optional["IAgent"]:
        """Get or create the agent instance."""
        if self._agent:
            return self._agent
        
        # Try to get from factory by ID
        agent_id = self._config.get("agent_id")
        if agent_id and self._agent_factory:
            try:
                return self._agent_factory.create(agent_id)
            except Exception as e:
                logger.warning(f"Failed to create agent {agent_id}: {e}")
        
        # Try to build from config
        agent_config = self._config.get("agent_config")
        if agent_config and self._agent_factory:
            try:
                return self._agent_factory.build(**agent_config)
            except Exception as e:
                logger.warning(f"Failed to build agent from config: {e}")
        
        return None
    
    def _create_agent_context(self, workflow_context: IWorkflowContext) -> Any:
        """Create an agent context from workflow context."""
        # Import here to avoid circular dependency
        try:
            from core.agents import create_context
            
            return create_context(
                session_id=workflow_context.execution_id,
                metadata={
                    "workflow_id": workflow_context.workflow_id,
                    "node_id": self._id,
                    **workflow_context.metadata,
                }
            )
        except ImportError:
            logger.warning("Could not import agent context, using dict")
            return {
                "session_id": workflow_context.execution_id,
                "workflow_id": workflow_context.workflow_id,
                "node_id": self._id,
            }
    
    def set_agent(self, agent: "IAgent") -> None:
        """Set the agent instance directly."""
        self._agent = agent

