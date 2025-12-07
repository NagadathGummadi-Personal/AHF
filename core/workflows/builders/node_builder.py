"""
Node Builder

Fluent builder for creating workflow nodes.

Version: 1.0.0
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

from ..spec.node_models import (
    NodeSpec,
    NodeMetadata,
    NodeConfig,
    BackgroundAgentConfig,
    UserPromptConfig,
)
from ..spec.io_types import InputSpec, OutputSpec, IOTypeSpec
from ..spec.workflow_config import NodeVariableAssignment, NodeDynamicVariableConfig
from ..enum import (
    NodeType,
    WorkflowStatus,
    IOType,
    IOFormat,
    BackgroundAgentMode,
    PromptPrecedence,
    PromptMergeStrategy,
)
from ..defaults import DEFAULT_NODE_VERSION

if TYPE_CHECKING:
    from core.agents import IAgent
    from core.tools import ToolSpec
    from core.llms import ILLM


class NodeBuilder:
    """
    Fluent builder for creating NodeSpec instances.
    
    Usage:
        # Create a node with an agent
        node = (NodeBuilder()
            .with_id("greeting-node")
            .with_name("Greeting Node")
            .with_description("Handles user greetings")
            .with_agent(greeting_agent)
            .with_input_type(IOType.TEXT)
            .with_output_type(IOType.TEXT)
            .with_user_prompt_config(allow_user_prompt=True)
            .build())
        
        # Create a node with just a tool
        node = (NodeBuilder()
            .with_id("lookup-node")
            .with_name("Database Lookup")
            .with_tool(db_tool)
            .with_input_type(IOType.JSON)
            .with_output_type(IOType.JSON)
            .build())
    """
    
    def __init__(self):
        """Initialize the builder."""
        self._id: Optional[str] = None
        self._name: Optional[str] = None
        self._description: str = ""
        self._node_type: NodeType = NodeType.AGENT
        
        # Component references
        self._agent_ref: Optional[str] = None
        self._agent_instance: Optional[Any] = None
        self._tool_ref: Optional[str] = None
        self._tool_instance: Optional[Any] = None
        self._llm_ref: Optional[str] = None
        self._llm_instance: Optional[Any] = None
        self._prompt_ref: Optional[str] = None
        self._prompt_content: Optional[str] = None
        self._memory_ref: Optional[str] = None
        
        # IO specs
        self._input_spec: Optional[InputSpec] = None
        self._output_spec: Optional[OutputSpec] = None
        
        # Metadata
        self._version: str = DEFAULT_NODE_VERSION
        self._status: WorkflowStatus = WorkflowStatus.DRAFT
        self._tags: List[str] = []
        self._owner: Optional[str] = None
        self._environment: str = "dev"
        
        # Config
        self._timeout_s: int = 300
        self._max_retries: int = 3
        self._cache_enabled: bool = False
        
        # Background agents
        self._background_agents: List[BackgroundAgentConfig] = []
        
        # User prompt config
        self._user_prompt_config: Optional[UserPromptConfig] = None
        
        # Dynamic variables
        self._dynamic_variables: Optional[NodeDynamicVariableConfig] = None
        
        # Display
        self._display_name: Optional[str] = None
        self._display_description: Optional[str] = None
        self._icon: Optional[str] = None
        self._color: Optional[str] = None
        
        # Additional properties
        self._properties: Dict[str, Any] = {}
    
    def with_id(self, node_id: str) -> NodeBuilder:
        """Set the node ID."""
        self._id = node_id
        return self
    
    def with_name(self, name: str) -> NodeBuilder:
        """Set the node name."""
        self._name = name
        return self
    
    def with_description(self, description: str) -> NodeBuilder:
        """Set the node description."""
        self._description = description
        return self
    
    def with_type(self, node_type: NodeType) -> NodeBuilder:
        """Set the node type."""
        self._node_type = node_type
        return self
    
    # =========================================================================
    # Component methods
    # =========================================================================
    
    def with_agent(self, agent: Any, ref: Optional[str] = None) -> NodeBuilder:
        """
        Set the agent for this node.
        
        Args:
            agent: Agent instance
            ref: Optional reference ID for persisted agents
        """
        self._agent_instance = agent
        self._agent_ref = ref
        self._node_type = NodeType.AGENT
        return self
    
    def with_agent_ref(self, agent_ref: str) -> NodeBuilder:
        """Set agent by reference ID only."""
        self._agent_ref = agent_ref
        self._node_type = NodeType.AGENT
        return self
    
    def with_tool(self, tool: Any, ref: Optional[str] = None) -> NodeBuilder:
        """
        Set the tool for this node.
        
        Args:
            tool: Tool instance
            ref: Optional reference ID for persisted tools
        """
        self._tool_instance = tool
        self._tool_ref = ref
        self._node_type = NodeType.TOOL
        return self
    
    def with_tool_ref(self, tool_ref: str) -> NodeBuilder:
        """Set tool by reference ID only."""
        self._tool_ref = tool_ref
        self._node_type = NodeType.TOOL
        return self
    
    def with_llm(self, llm: Any, ref: Optional[str] = None) -> NodeBuilder:
        """Set the LLM for this node."""
        self._llm_instance = llm
        self._llm_ref = ref
        return self
    
    def with_prompt(self, content: str) -> NodeBuilder:
        """Set prompt content directly."""
        self._prompt_content = content
        self._node_type = NodeType.PROMPT
        return self
    
    def with_prompt_ref(self, prompt_ref: str) -> NodeBuilder:
        """Set prompt by reference ID."""
        self._prompt_ref = prompt_ref
        return self
    
    def with_memory_ref(self, memory_ref: str) -> NodeBuilder:
        """Set memory by reference ID."""
        self._memory_ref = memory_ref
        return self
    
    # =========================================================================
    # IO methods
    # =========================================================================
    
    def with_input_type(
        self,
        io_type: IOType,
        format: IOFormat = IOFormat.PLAIN,
        required: bool = True,
        accepts_multiple: bool = False
    ) -> NodeBuilder:
        """Set the input type specification."""
        self._input_spec = InputSpec(
            type_spec=IOTypeSpec(io_type=io_type, format=format),
            required=required,
            accepts_multiple=accepts_multiple,
        )
        return self
    
    def with_input_spec(self, input_spec: InputSpec) -> NodeBuilder:
        """Set the input specification directly."""
        self._input_spec = input_spec
        return self
    
    def with_output_type(
        self,
        io_type: IOType,
        format: IOFormat = IOFormat.PLAIN,
        optional: bool = False,
        streaming: bool = False
    ) -> NodeBuilder:
        """Set the output type specification."""
        self._output_spec = OutputSpec(
            type_spec=IOTypeSpec(io_type=io_type, format=format),
            optional=optional,
            streaming=streaming,
        )
        return self
    
    def with_output_spec(self, output_spec: OutputSpec) -> NodeBuilder:
        """Set the output specification directly."""
        self._output_spec = output_spec
        return self
    
    # =========================================================================
    # Metadata methods
    # =========================================================================
    
    def with_version(self, version: str) -> NodeBuilder:
        """Set the version."""
        self._version = version
        return self
    
    def with_status(self, status: WorkflowStatus) -> NodeBuilder:
        """Set the status."""
        self._status = status
        return self
    
    def with_tags(self, tags: List[str]) -> NodeBuilder:
        """Set tags."""
        self._tags = tags
        return self
    
    def with_owner(self, owner: str) -> NodeBuilder:
        """Set the owner."""
        self._owner = owner
        return self
    
    def with_environment(self, environment: str) -> NodeBuilder:
        """Set the target environment."""
        self._environment = environment
        return self
    
    # =========================================================================
    # Config methods
    # =========================================================================
    
    def with_timeout(self, timeout_s: int) -> NodeBuilder:
        """Set the execution timeout."""
        self._timeout_s = timeout_s
        return self
    
    def with_max_retries(self, max_retries: int) -> NodeBuilder:
        """Set max retry attempts."""
        self._max_retries = max_retries
        return self
    
    def with_caching(self, enabled: bool = True, ttl_s: int = 300) -> NodeBuilder:
        """Enable/disable caching."""
        self._cache_enabled = enabled
        self._properties["cache_ttl_s"] = ttl_s
        return self
    
    # =========================================================================
    # Background agent methods
    # =========================================================================
    
    def add_background_agent(
        self,
        agent_ref: str,
        mode: BackgroundAgentMode = BackgroundAgentMode.MONITOR,
        triggers: Optional[List[str]] = None,
        tools: Optional[List[str]] = None,
        description: str = ""
    ) -> NodeBuilder:
        """Add a background agent."""
        self._background_agents.append(BackgroundAgentConfig(
            enabled=True,
            agent_ref=agent_ref,
            mode=mode,
            triggers=triggers or [],
            tools=tools or [],
            description=description,
        ))
        return self
    
    # =========================================================================
    # User prompt config methods
    # =========================================================================
    
    def with_user_prompt_config(
        self,
        allow_user_prompt: bool = True,
        show_main_prompt: bool = False,
        precedence: PromptPrecedence = PromptPrecedence.MERGE,
        merge_strategy: PromptMergeStrategy = PromptMergeStrategy.APPEND,
        max_length: Optional[int] = None,
        placeholder: str = "",
        description: str = ""
    ) -> NodeBuilder:
        """Configure user prompt settings."""
        self._user_prompt_config = UserPromptConfig(
            allow_user_prompt=allow_user_prompt,
            show_main_prompt=show_main_prompt,
            precedence=precedence,
            merge_strategy=merge_strategy,
            max_length=max_length,
            placeholder=placeholder,
            description=description,
        )
        return self
    
    # =========================================================================
    # Dynamic variable methods
    # =========================================================================
    
    def with_variable_assignment(
        self,
        target_variable: str,
        source_field: str,
        operator: str = "set",
        default_value: Any = None,
        transform_expr: Optional[str] = None
    ) -> NodeBuilder:
        """Add a variable assignment."""
        if not self._dynamic_variables:
            self._dynamic_variables = NodeDynamicVariableConfig(enabled=True, assignments=[])
        
        self._dynamic_variables.assignments.append(NodeVariableAssignment(
            target_variable=target_variable,
            source_field=source_field,
            operator=operator,
            default_value=default_value,
            transform_expr=transform_expr,
        ))
        return self
    
    # =========================================================================
    # Display methods
    # =========================================================================
    
    def with_display_name(self, display_name: str) -> NodeBuilder:
        """Set the display name for UI."""
        self._display_name = display_name
        return self
    
    def with_display_description(self, display_description: str) -> NodeBuilder:
        """Set the display description for UI."""
        self._display_description = display_description
        return self
    
    def with_icon(self, icon: str) -> NodeBuilder:
        """Set the icon identifier."""
        self._icon = icon
        return self
    
    def with_color(self, color: str) -> NodeBuilder:
        """Set the UI color."""
        self._color = color
        return self
    
    # =========================================================================
    # Build method
    # =========================================================================
    
    def build(self) -> NodeSpec:
        """
        Build the NodeSpec.
        
        Raises:
            ValueError: If required fields are missing
        """
        if not self._id:
            raise ValueError("Node ID is required")
        if not self._name:
            raise ValueError("Node name is required")
        
        # Build metadata
        metadata = NodeMetadata(
            version=self._version,
            status=self._status,
            tags=self._tags,
            owner=self._owner,
            environment=self._environment,
        )
        
        # Build config
        config = NodeConfig(
            timeout_s=self._timeout_s,
            max_retries=self._max_retries,
            cache_enabled=self._cache_enabled,
            cache_ttl_s=self._properties.get("cache_ttl_s", 300),
        )
        
        return NodeSpec(
            id=self._id,
            name=self._name,
            description=self._description,
            node_type=self._node_type,
            agent_ref=self._agent_ref,
            agent_instance=self._agent_instance,
            tool_ref=self._tool_ref,
            tool_instance=self._tool_instance,
            llm_ref=self._llm_ref,
            llm_instance=self._llm_instance,
            prompt_ref=self._prompt_ref,
            prompt_content=self._prompt_content,
            memory_ref=self._memory_ref,
            input_spec=self._input_spec or InputSpec(),
            output_spec=self._output_spec or OutputSpec(),
            metadata=metadata,
            config=config,
            background_agents=self._background_agents,
            user_prompt_config=self._user_prompt_config or UserPromptConfig(),
            dynamic_variables=self._dynamic_variables or NodeDynamicVariableConfig(),
            display_name=self._display_name,
            display_description=self._display_description,
            icon=self._icon,
            color=self._color,
            properties=self._properties,
        )
