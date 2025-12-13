"""
Base Node Classes

Abstract base classes for tool and agent nodes.
Implements INode from core.workflows.interfaces.

IMPORTANT - Request Isolation (Fargate/Container Safety):
- Nodes are stateless - all state is passed via session parameter
- Node instances can be shared (they're just logic containers)
- All request-specific data must be in VoiceAgentSession
- NEVER store mutable per-request state in node instances

Standalone Testing:
- Each node supports standalone execution via run_standalone() method
- Use MockSession for testing without full workflow setup
- run_standalone() creates default context/session if not provided

Version: 1.1.0
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, TYPE_CHECKING, Union
import uuid
import asyncio

from pydantic import BaseModel, Field

from core.workflows.interfaces import INode
from core.workflows.spec import NodeSpec, NodeResult, WorkflowExecutionContext, NodeType
from core.tools.interfaces import IToolExecutor
from core.agents.interfaces import IAgent

if TYPE_CHECKING:
    from air.memory.session import VoiceAgentSession


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


class MockSession:
    """
    Lightweight mock session for standalone node testing.
    
    Provides minimal session interface without full VoiceAgentSession dependencies.
    Use this for unit testing nodes in isolation.
    
    Example:
        session = MockSession()
        session.set_dynamic_variable("center_id", "test-center")
        result = await node.run_standalone(input_data, session=session)
    """
    
    def __init__(
        self,
        session_id: Optional[str] = None,
        dynamic_vars: Optional[Dict[str, Any]] = None,
        workflow_vars: Optional[Dict[str, Any]] = None,
    ):
        self._session_id = session_id or str(uuid.uuid4())
        self._dynamic_vars = dynamic_vars or {}
        self._workflow_vars = workflow_vars or {}
        self._messages: List[Dict[str, str]] = []
        self._completed_steps: set = set()
        self._variables: Dict[str, Any] = {}
    
    @property
    def session_id(self) -> str:
        return self._session_id
    
    @property
    def dynamic_vars(self) -> Optional[Any]:
        """Return a mock dynamic vars object."""
        return MockDynamicVars(self._dynamic_vars)
    
    def set_dynamic_variables(self, variables: Any) -> None:
        """Set dynamic variables from DynamicVariables object."""
        if hasattr(variables, 'to_context_dict'):
            self._dynamic_vars = variables.to_context_dict()
        elif isinstance(variables, dict):
            self._dynamic_vars = variables
    
    def get_dynamic_variable(self, key: str, default: Any = None) -> Any:
        return self._dynamic_vars.get(key, default)
    
    def update_dynamic_variable(self, key: str, value: Any) -> None:
        self._dynamic_vars[key] = value
    
    def set_workflow_variable(self, key: str, value: Any) -> None:
        self._workflow_vars[key] = value
    
    def get_workflow_variable(self, key: str, default: Any = None) -> Any:
        return self._workflow_vars.get(key, default)
    
    def set_variable(self, key: str, value: Any) -> None:
        self._variables[key] = value
    
    def get_variable(self, key: str, default: Any = None) -> Any:
        return self._variables.get(key, default)
    
    def add_user_message(self, content: str, **metadata) -> str:
        msg_id = str(uuid.uuid4())[:8]
        self._messages.append({"role": "user", "content": content})
        return msg_id
    
    def add_assistant_message(self, content: str, **metadata) -> str:
        msg_id = str(uuid.uuid4())[:8]
        self._messages.append({"role": "assistant", "content": content})
        return msg_id
    
    def get_llm_messages(self, max_messages: Optional[int] = None) -> List[Dict[str, str]]:
        if max_messages:
            return self._messages[-max_messages:]
        return self._messages.copy()
    
    def complete_step(self, step_id: str, data: Optional[Dict[str, Any]] = None) -> None:
        self._completed_steps.add(step_id)
    
    def is_step_completed(self, step_id: str) -> bool:
        return step_id in self._completed_steps
    
    def has_interrupt_sync(self) -> bool:
        return False
    
    def get_stashed_context(self) -> Optional[str]:
        return None
    
    def stash_response(self, content: str, interrupt_message: str, **kwargs) -> None:
        pass
    
    async def get_current_task(self) -> Optional[Any]:
        return None
    
    async def create_task(self, intent: str, original_input: str = "", **kwargs) -> Any:
        """Create a mock task."""
        return MockTask(intent=intent, original_input=original_input)
    
    async def start_task(self, task_id: str) -> Optional[Any]:
        return None
    
    @property
    def task_queue(self) -> "MockTaskQueue":
        return MockTaskQueue()


class MockDynamicVars:
    """Mock dynamic variables for testing."""
    
    def __init__(self, data: Dict[str, Any]):
        self._data = data
    
    def __getattr__(self, name: str) -> Any:
        return self._data.get(name, "")
    
    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)
    
    def to_context_dict(self) -> Dict[str, Any]:
        return self._data.copy()
    
    def get_guest_display_name(self) -> str:
        return self._data.get("guest_name", "Guest")


class MockTask:
    """Mock task for testing."""
    
    def __init__(self, intent: str, original_input: str = ""):
        self.task_id = str(uuid.uuid4())[:8]
        self.intent = intent
        self.original_input = original_input
        self.state = "pending"
        self.services: List[Dict[str, Any]] = []
        self.plan = None
    
    def add_service(self, service_id: str, service_name: str) -> None:
        self.services.append({"service_id": service_id, "service_name": service_name})
    
    def create_plan(self, **kwargs) -> Dict[str, Any]:
        self.plan = {"steps": [], **kwargs}
        return self.plan
    
    def start(self) -> None:
        self.state = "in_progress"
    
    def pause(self, reason: str = "") -> None:
        self.state = "paused"
    
    def complete(self) -> None:
        self.state = "completed"
    
    def set_data(self, key: str, value: Any) -> None:
        pass


class MockTaskQueue:
    """Mock task queue for testing."""
    
    async def update(self, task: Any) -> None:
        pass
    
    async def get_all_pending(self) -> List[Any]:
        return []
    
    async def get_pending_count(self) -> int:
        return 0


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
    
    # =========================================================================
    # Standalone Execution for Testing
    # =========================================================================
    
    async def run_standalone(
        self,
        input_data: Any,
        session: Optional[Union["VoiceAgentSession", MockSession]] = None,
        context: Optional[WorkflowExecutionContext] = None,
        **kwargs,
    ) -> NodeResult:
        """
        Execute node in standalone mode for testing.
        
        This method allows running the node without a full workflow,
        creating default context and session if not provided.
        
        Args:
            input_data: Input data for the node
            session: Optional session (uses MockSession if not provided)
            context: Optional workflow context (creates default if not provided)
            **kwargs: Additional arguments passed to execute()
            
        Returns:
            NodeResult with output data
            
        Example:
            # Simple standalone test
            node = WorkflowInitNode()
            result = await node.run_standalone({
                "caller_id": "+1234567890",
                "center_id": "test-center",
                "org_id": "test-org",
                "agent_id": "test-agent",
            })
            print(result.output)
            
            # With mock session
            session = MockSession()
            session.set_workflow_variable("custom_key", "custom_value")
            result = await node.run_standalone(input_data, session=session)
        """
        # Create default session if not provided
        if session is None:
            session = MockSession()
        
        # Create default context if not provided
        if context is None:
            context = WorkflowExecutionContext()
        
        return await self.execute(
            input_data=input_data,
            context=context,
            session=session,
            **kwargs,
        )
    
    def run_standalone_sync(
        self,
        input_data: Any,
        session: Optional[Union["VoiceAgentSession", MockSession]] = None,
        context: Optional[WorkflowExecutionContext] = None,
        **kwargs,
    ) -> NodeResult:
        """
        Synchronous wrapper for run_standalone.
        
        Useful for simple testing in non-async contexts.
        
        Example:
            result = node.run_standalone_sync({"key": "value"})
        """
        return asyncio.run(self.run_standalone(input_data, session, context, **kwargs))


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
    
    # =========================================================================
    # Standalone Execution for Testing
    # =========================================================================
    
    async def run_standalone(
        self,
        input_data: Any,
        session: Optional[Union["VoiceAgentSession", MockSession]] = None,
        context: Optional[WorkflowExecutionContext] = None,
        llm: Optional[Any] = None,
        **kwargs,
    ) -> NodeResult:
        """
        Execute agent node in standalone mode for testing.
        
        This method allows running the agent node without a full workflow,
        creating default context and session if not provided.
        
        Args:
            input_data: Input data for the node (e.g., {"user_input": "Hello"})
            session: Optional session (uses MockSession if not provided)
            context: Optional workflow context (creates default if not provided)
            llm: Optional LLM instance (required for agent nodes)
            **kwargs: Additional arguments passed to execute()
            
        Returns:
            NodeResult with output data
            
        Example:
            # Create agent with LLM
            from core.llms import LLMFactory
            
            llm = LLMFactory.create_llm("gpt-4o", connector_config={...})
            agent = GreetingRoutingAgent(llm=llm)
            
            # Run standalone test
            result = await agent.run_standalone(
                {"user_input": "I want to book an appointment"},
            )
            print(result.output["response"])
            
            # With mock session for custom context
            session = MockSession(dynamic_vars={
                "agent_name": "Test Agent",
                "org_name": "Test Org",
                "center_name": "Test Center",
            })
            result = await agent.run_standalone(
                {"user_input": "Hello"},
                session=session,
            )
        """
        # Set LLM if provided
        if llm is not None and hasattr(self, "set_llm"):
            self.set_llm(llm)
        
        # Create default session if not provided
        if session is None:
            session = MockSession(dynamic_vars={
                "agent_name": "Test Agent",
                "org_name": "Test Organization",
                "center_name": "Test Center",
                "supported_languages": "['English']",
            })
        
        # Create default context if not provided
        if context is None:
            context = WorkflowExecutionContext()
        
        return await self.execute(
            input_data=input_data,
            context=context,
            session=session,
            **kwargs,
        )
    
    def run_standalone_sync(
        self,
        input_data: Any,
        session: Optional[Union["VoiceAgentSession", MockSession]] = None,
        context: Optional[WorkflowExecutionContext] = None,
        llm: Optional[Any] = None,
        **kwargs,
    ) -> NodeResult:
        """
        Synchronous wrapper for run_standalone.
        
        Useful for simple testing in non-async contexts.
        
        Example:
            result = agent.run_standalone_sync({"user_input": "Hello"})
        """
        return asyncio.run(self.run_standalone(input_data, session, context, llm, **kwargs))

