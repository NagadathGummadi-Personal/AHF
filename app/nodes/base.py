"""
Base Node Classes

Abstract base classes for tool and agent nodes.
Implements INode from core.workflows.interfaces.

Version: 1.0.0
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, AsyncIterator, Dict, List, Optional
import uuid

from pydantic import BaseModel, Field

from core.workflows.interfaces import INode
from core.workflows.spec import NodeSpec, NodeResult, WorkflowExecutionContext, NodeType
from core.tools.interfaces import IToolExecutor
from core.agents.interfaces import IAgent

from app.memory.session import VoiceAgentSession


class NodeConfig(BaseModel):
    """Configuration for a node that can be overridden at runtime."""
    
    timeout_ms: int = Field(default=30000, description="Node execution timeout")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    
    # Error handling
    fallback_node: Optional[str] = Field(default=None, description="Node to call on error")
    error_action: Optional[str] = Field(default=None, description="Action on error")
    
    # Customer instructions
    customer_instructions: Optional[str] = Field(
        default=None,
        description="Additional instructions from customer"
    )


class NodeContext(BaseModel):
    """Context passed to node execution."""
    
    session: Any = Field(..., description="VoiceAgentSession instance")
    user_input: Optional[str] = Field(default=None, description="Current user input")
    
    # Pass-through data from previous node
    pass_through: Dict[str, Any] = Field(default_factory=dict)
    
    # Configuration overrides
    config_overrides: Dict[str, Any] = Field(default_factory=dict)
    
    # Background task results
    background_results: Dict[str, Any] = Field(default_factory=dict)
    
    model_config = {"arbitrary_types_allowed": True}


class BaseToolNode(ABC):
    """
    Base class for tool nodes.
    
    Tool nodes execute a specific tool (HTTP call, function, etc.)
    and return structured data.
    
    Implements INode protocol from core.workflows.
    """
    
    def __init__(
        self,
        node_id: str,
        name: str,
        description: str = "",
        config: Optional[NodeConfig] = None,
    ):
        self._node_id = node_id
        self._name = name
        self._description = description
        self._config = config or NodeConfig()
        
        # Build spec
        self._spec = NodeSpec(
            node_id=node_id,
            node_name=name,
            description=description,
            node_type=NodeType.TOOL,
        )
    
    @property
    def spec(self) -> NodeSpec:
        """Get node specification."""
        return self._spec
    
    @property
    def node_id(self) -> str:
        """Get node ID."""
        return self._node_id
    
    @property
    def config(self) -> NodeConfig:
        """Get node configuration."""
        return self._config
    
    async def execute(
        self,
        input_data: Any,
        context: WorkflowExecutionContext,
        user_prompt: Optional[str] = None,
        **kwargs,
    ) -> NodeResult:
        """
        Execute the node.
        
        Args:
            input_data: Input from previous node or user
            context: Workflow execution context
            user_prompt: Optional user prompt override
            **kwargs: Additional arguments including session
            
        Returns:
            NodeResult with output data
        """
        start_time = datetime.utcnow()
        
        # Get session from kwargs
        session: Optional[VoiceAgentSession] = kwargs.get("session")
        node_context = kwargs.get("node_context")
        
        try:
            # Execute tool-specific logic
            output = await self._execute_tool(
                input_data=input_data,
                context=context,
                session=session,
                node_context=node_context,
                **kwargs,
            )
            
            latency = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return NodeResult(
                node_id=self._node_id,
                success=True,
                output=output,
                latency_ms=latency,
            )
            
        except Exception as e:
            latency = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return NodeResult(
                node_id=self._node_id,
                success=False,
                error=str(e),
                latency_ms=latency,
                metadata={"fallback_node": self._config.fallback_node},
            )
    
    @abstractmethod
    async def _execute_tool(
        self,
        input_data: Any,
        context: WorkflowExecutionContext,
        session: Optional[VoiceAgentSession] = None,
        node_context: Optional[NodeContext] = None,
        **kwargs,
    ) -> Any:
        """
        Execute the tool logic. Override in subclasses.
        
        Returns:
            Tool output data
        """
        ...
    
    async def stream(
        self,
        input_data: Any,
        context: WorkflowExecutionContext,
        user_prompt: Optional[str] = None,
        **kwargs,
    ) -> AsyncIterator[Any]:
        """Stream execution - tool nodes typically don't stream."""
        result = await self.execute(input_data, context, user_prompt, **kwargs)
        yield result


class BaseAgentNode(ABC):
    """
    Base class for agent nodes.
    
    Agent nodes use an LLM to process input and generate
    conversational responses.
    
    Implements INode protocol from core.workflows.
    """
    
    def __init__(
        self,
        node_id: str,
        name: str,
        description: str = "",
        config: Optional[NodeConfig] = None,
        agent: Optional[IAgent] = None,
    ):
        self._node_id = node_id
        self._name = name
        self._description = description
        self._config = config or NodeConfig()
        self._agent = agent
        
        # Build spec
        self._spec = NodeSpec(
            node_id=node_id,
            node_name=name,
            description=description,
            node_type=NodeType.AGENT,
        )
    
    @property
    def spec(self) -> NodeSpec:
        """Get node specification."""
        return self._spec
    
    @property
    def node_id(self) -> str:
        """Get node ID."""
        return self._node_id
    
    @property
    def config(self) -> NodeConfig:
        """Get node configuration."""
        return self._config
    
    def set_agent(self, agent: IAgent) -> None:
        """Set the agent instance."""
        self._agent = agent
    
    @abstractmethod
    def get_system_prompt(
        self,
        session: VoiceAgentSession,
        **kwargs,
    ) -> str:
        """Get the system prompt for this agent node."""
        ...
    
    @abstractmethod
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get tool definitions for LLM function calling."""
        ...
    
    async def execute(
        self,
        input_data: Any,
        context: WorkflowExecutionContext,
        user_prompt: Optional[str] = None,
        **kwargs,
    ) -> NodeResult:
        """Execute the agent node."""
        start_time = datetime.utcnow()
        
        session: Optional[VoiceAgentSession] = kwargs.get("session")
        node_context = kwargs.get("node_context")
        
        try:
            # Build messages
            system_prompt = self.get_system_prompt(session, **kwargs)
            
            # Add customer instructions if provided
            if self._config.customer_instructions:
                system_prompt += f"\n\n<Customer Instructions>\n{self._config.customer_instructions}\n</Customer Instructions>"
            
            # Execute agent logic
            output = await self._execute_agent(
                input_data=input_data,
                system_prompt=system_prompt,
                context=context,
                session=session,
                node_context=node_context,
                **kwargs,
            )
            
            latency = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return NodeResult(
                node_id=self._node_id,
                success=True,
                output=output,
                latency_ms=latency,
            )
            
        except Exception as e:
            latency = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return NodeResult(
                node_id=self._node_id,
                success=False,
                error=str(e),
                latency_ms=latency,
                metadata={"fallback_node": self._config.fallback_node},
            )
    
    @abstractmethod
    async def _execute_agent(
        self,
        input_data: Any,
        system_prompt: str,
        context: WorkflowExecutionContext,
        session: Optional[VoiceAgentSession] = None,
        node_context: Optional[NodeContext] = None,
        **kwargs,
    ) -> Any:
        """Execute agent logic. Override in subclasses."""
        ...
    
    async def stream(
        self,
        input_data: Any,
        context: WorkflowExecutionContext,
        user_prompt: Optional[str] = None,
        **kwargs,
    ) -> AsyncIterator[Any]:
        """Stream agent execution."""
        # Default: yield full result
        # Override for true streaming
        result = await self.execute(input_data, context, user_prompt, **kwargs)
        yield result

