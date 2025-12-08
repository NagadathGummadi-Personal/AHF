"""
Node Specification Models

Defines the structure for workflow nodes including metadata,
configuration, and runtime data.

Version: 1.0.0
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from pydantic import BaseModel, Field, PrivateAttr

from ..enum import (
    NodeType,
    WorkflowStatus,
    BackgroundAgentMode,
    PromptPrecedence,
    PromptMergeStrategy,
    ExecutionState,
)
from ..defaults import (
    DEFAULT_NODE_VERSION,
    DEFAULT_NODE_STATUS,
    DEFAULT_NODE_TYPE,
    DEFAULT_TIMEOUT_S,
    DEFAULT_MAX_RETRIES,
    DEFAULT_BG_AGENT_MODE,
    DEFAULT_BG_AGENT_ENABLED,
    DEFAULT_PROMPT_PRECEDENCE,
    DEFAULT_PROMPT_MERGE_STRATEGY,
    DEFAULT_SHOW_PROMPT_TO_USER,
    DEFAULT_ALLOW_USER_PROMPT,
    DEFAULT_VARIABLE_ASSIGNMENT_ENABLED,
)
from ..constants import (
    ARBITRARY_TYPES_ALLOWED,
    POPULATE_BY_NAME,
    ERROR_VERSION_EXISTS,
)
from .io_types import InputSpec, OutputSpec
from .workflow_config import NodeDynamicVariableConfig

if TYPE_CHECKING:
    from core.agents import IAgent
    from core.tools import ToolSpec
    from core.llms import ILLM


class BackgroundAgentConfig(BaseModel):
    """
    Configuration for background agents that run alongside the main node execution.
    
    Background agents can monitor conversation flow, raise flags, or call tools
    without interfering with the main workflow.
    
    Attributes:
        enabled: Whether background agent is active
        agent_ref: Reference to the agent (ID or instance)
        mode: Operating mode (MONITOR, ACTIVE, SILENT)
        triggers: Conditions that activate the background agent
        tools: Tools available to the background agent
        description: What this background agent monitors/does
    """
    enabled: bool = Field(default=DEFAULT_BG_AGENT_ENABLED, description="Whether background agent is active")
    agent_ref: Optional[str] = Field(default=None, description="Reference to the background agent")
    agent_instance: Optional[Any] = Field(default=None, description="Agent instance (if available)")
    mode: BackgroundAgentMode = Field(default=BackgroundAgentMode(DEFAULT_BG_AGENT_MODE), description="Operating mode")
    triggers: List[str] = Field(
        default_factory=list,
        description="Conditions that trigger background agent (e.g., keywords, intents)"
    )
    tools: List[str] = Field(
        default_factory=list,
        description="Tool references available to background agent"
    )
    description: str = Field(default="", description="Description of what this agent monitors")
    
    model_config = {ARBITRARY_TYPES_ALLOWED: True}


class UserPromptConfig(BaseModel):
    """
    Configuration for user-provided additional prompts.
    
    When nodes are displayed to users, they may provide additional context
    or instructions. This config determines how to handle those inputs.
    
    Attributes:
        allow_user_prompt: Whether to accept additional prompts from users
        show_main_prompt: Whether to show the main agent prompt to users
        precedence: How to prioritize user vs agent prompts
        merge_strategy: How to merge prompts when precedence is MERGE
        max_length: Maximum length for user prompt
        placeholder: Placeholder text for user input
        description: Description shown to users about what prompt to provide
    """
    allow_user_prompt: bool = Field(
        default=DEFAULT_ALLOW_USER_PROMPT,
        description="Whether to accept additional prompts from users"
    )
    show_main_prompt: bool = Field(
        default=DEFAULT_SHOW_PROMPT_TO_USER,
        description="Whether to show the main agent prompt to users"
    )
    precedence: PromptPrecedence = Field(
        default=PromptPrecedence(DEFAULT_PROMPT_PRECEDENCE),
        description="How to prioritize user vs agent prompts"
    )
    merge_strategy: PromptMergeStrategy = Field(
        default=PromptMergeStrategy(DEFAULT_PROMPT_MERGE_STRATEGY),
        description="How to merge prompts when precedence is MERGE"
    )
    max_length: Optional[int] = Field(
        default=None,
        description="Maximum length for user-provided prompt"
    )
    placeholder: str = Field(
        default="",
        description="Placeholder text shown in user prompt input"
    )
    description: str = Field(
        default="",
        description="Description shown to users about what additional context to provide"
    )


class NodeMetadata(BaseModel):
    """
    Metadata for a node.
    
    Attributes:
        version: Node version string
        status: Current status (draft, published, etc.)
        created_at: Creation timestamp
        updated_at: Last update timestamp
        created_by: User who created the node
        tags: Tags for categorization
        owner: Owner identifier
        environment: Target environment (prod, staging, etc.)
    """
    version: str = Field(default=DEFAULT_NODE_VERSION, description="Node version")
    status: WorkflowStatus = Field(default=WorkflowStatus(DEFAULT_NODE_STATUS), description="Node status")
    created_at: Optional[datetime] = Field(default=None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")
    created_by: Optional[str] = Field(default=None, description="Creator user ID")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    owner: Optional[str] = Field(default=None, description="Owner identifier")
    environment: str = Field(default="dev", description="Target environment")


class NodeConfig(BaseModel):
    """
    Execution configuration for a node.
    
    Attributes:
        timeout_s: Execution timeout in seconds
        max_retries: Maximum retry attempts
        retry_delay_s: Delay between retries
        cache_enabled: Whether to cache results
        cache_ttl_s: Cache time-to-live in seconds
    """
    timeout_s: int = Field(default=DEFAULT_TIMEOUT_S, description="Execution timeout in seconds")
    max_retries: int = Field(default=DEFAULT_MAX_RETRIES, description="Maximum retry attempts")
    retry_delay_s: float = Field(default=1.0, description="Delay between retries")
    cache_enabled: bool = Field(default=False, description="Whether to cache results")
    cache_ttl_s: int = Field(default=300, description="Cache TTL in seconds")


class NodeSpec(BaseModel):
    """
    Complete specification for a workflow node.
    
    A node is the fundamental building block of a workflow. It can contain:
    - An Agent (with LLM, tools, and prompt)
    - Just a Tool (HTTP, DB, Function)
    - Just a Prompt template
    - Custom logic
    
    Attributes:
        id: Unique identifier
        name: Human-readable name
        description: Node description
        node_type: Type of node (AGENT, TOOL, PROMPT, etc.)
        
        # Component references (pluggable)
        agent_ref: Reference to agent ID
        agent_instance: Direct agent instance (for runtime)
        tool_ref: Reference to tool ID
        tool_instance: Direct tool instance (for runtime)
        llm_ref: Reference to LLM ID
        llm_instance: Direct LLM instance (for runtime)
        prompt_ref: Reference to prompt ID
        prompt_content: Direct prompt content
        memory_ref: Reference to memory component
        
        # IO specifications
        input_spec: Input type specification
        output_spec: Output type specification
        
        # Configuration
        metadata: Node metadata
        config: Execution configuration
        
        # Background agents
        background_agents: List of background agent configurations
        
        # User prompt configuration
        user_prompt_config: Configuration for user-provided prompts
        
        # Dynamic variables
        dynamic_variables: Variable assignment configuration
        
        # Display configuration
        display_name: Name shown to users
        display_description: Description shown to users (instead of main description)
        icon: Icon identifier for UI
        color: Color for UI
    """
    # Identity
    id: str = Field(..., description="Unique node identifier")
    name: str = Field(..., description="Human-readable name")
    description: str = Field(default="", description="Node description")
    node_type: NodeType = Field(default=NodeType(DEFAULT_NODE_TYPE), description="Type of node")
    
    # Component references - pluggable design
    # Reference IDs (for persisted components)
    agent_ref: Optional[str] = Field(default=None, description="Reference to agent ID")
    tool_ref: Optional[str] = Field(default=None, description="Reference to tool ID")
    llm_ref: Optional[str] = Field(default=None, description="Reference to LLM ID")
    prompt_ref: Optional[str] = Field(default=None, description="Reference to prompt ID in registry")
    memory_ref: Optional[str] = Field(default=None, description="Reference to memory component")
    
    # Direct instances (for runtime - not persisted)
    agent_instance: Optional[Any] = Field(default=None, description="Agent instance", exclude=True)
    tool_instance: Optional[Any] = Field(default=None, description="Tool instance", exclude=True)
    llm_instance: Optional[Any] = Field(default=None, description="LLM instance", exclude=True)
    
    # Direct content (for simple cases)
    prompt_content: Optional[str] = Field(default=None, description="Direct prompt content")
    
    # IO specifications
    input_spec: InputSpec = Field(default_factory=InputSpec, description="Input specification")
    output_spec: OutputSpec = Field(default_factory=OutputSpec, description="Output specification")
    
    # Metadata and config
    metadata: NodeMetadata = Field(default_factory=NodeMetadata, description="Node metadata")
    config: NodeConfig = Field(default_factory=NodeConfig, description="Execution configuration")
    
    # Background agents
    background_agents: List[BackgroundAgentConfig] = Field(
        default_factory=list,
        description="Background agents for monitoring/parallel processing"
    )
    
    # User prompt configuration
    user_prompt_config: UserPromptConfig = Field(
        default_factory=UserPromptConfig,
        description="Configuration for user-provided additional prompts"
    )
    
    # Dynamic variable assignments
    dynamic_variables: NodeDynamicVariableConfig = Field(
        default_factory=lambda: NodeDynamicVariableConfig(enabled=DEFAULT_VARIABLE_ASSIGNMENT_ENABLED),
        description="Dynamic variable assignment configuration"
    )
    
    # Display configuration (for UI)
    display_name: Optional[str] = Field(default=None, description="Name shown to users")
    display_description: Optional[str] = Field(
        default=None,
        description="Description shown to users (instead of technical description)"
    )
    icon: Optional[str] = Field(default=None, description="Icon identifier for UI")
    color: Optional[str] = Field(default=None, description="Color for UI display")
    
    # Additional properties for extensibility
    properties: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional custom properties for future extensions"
    )
    
    model_config = {
        ARBITRARY_TYPES_ALLOWED: True,
        POPULATE_BY_NAME: True,
    }
    
    def get_display_name(self) -> str:
        """Get the display name (falls back to name if not set)."""
        return self.display_name or self.name
    
    def get_display_description(self) -> str:
        """Get the display description (falls back to description if not set)."""
        return self.display_description or self.description
    
    def has_agent(self) -> bool:
        """Check if node has an agent configured (via reference or instance)."""
        return self.agent_ref is not None or self.agent_instance is not None
    
    def has_tool(self) -> bool:
        """Check if node has a tool configured (via reference or instance)."""
        return self.tool_ref is not None or self.tool_instance is not None
    
    def has_background_agents(self) -> bool:
        """Check if node has any enabled background agents."""
        return any(bg.enabled for bg in self.background_agents)
    
    def get_agent(self) -> Optional[Any]:
        """Get the agent instance if available."""
        return self.agent_instance
    
    def get_tool(self) -> Optional[Any]:
        """Get the tool instance if available."""
        return self.tool_instance
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return self.model_dump(exclude={"agent_instance", "tool_instance", "llm_instance"})
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> NodeSpec:
        """Create from dictionary."""
        return cls(**data)


class NodeResult(BaseModel):
    """
    Result from node execution.
    
    Attributes:
        node_id: ID of the executed node
        success: Whether execution succeeded
        output: Output data from the node
        error: Error message if failed
        execution_time_ms: Execution time in milliseconds
        state: Final execution state
        metadata: Additional result metadata
    """
    node_id: str = Field(..., description="ID of the executed node")
    success: bool = Field(default=True, description="Whether execution succeeded")
    output: Any = Field(default=None, description="Output data")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    execution_time_ms: float = Field(default=0.0, description="Execution time in ms")
    state: ExecutionState = Field(default=ExecutionState.COMPLETED, description="Final state")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class NodeVersion(BaseModel):
    """
    A specific version of a node.
    
    Versions are immutable once published.
    """
    version: str = Field(..., description="Version string")
    spec: NodeSpec = Field(..., description="Node specification")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation time")
    is_published: bool = Field(default=False, description="Whether version is published")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "version": self.version,
            "spec": self.spec.to_dict(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_published": self.is_published,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> NodeVersion:
        """Create from dictionary."""
        spec_data = data.get("spec", {})
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        return cls(
            version=data["version"],
            spec=NodeSpec.from_dict(spec_data),
            created_at=created_at or datetime.utcnow(),
            is_published=data.get("is_published", False),
        )


class NodeEntry(BaseModel):
    """
    Entry containing all versions of a node.
    
    Similar to PromptEntry, manages multiple versions of a node.
    """
    id: str = Field(..., description="Node ID")
    versions: Dict[str, NodeVersion] = Field(default_factory=dict, description="Version map")
    
    # Private attrs for tracking
    _latest_version: str = PrivateAttr(default="")
    
    def model_post_init(self, __context: Any) -> None:
        """Initialize after model creation."""
        if self.versions:
            # Find latest version
            versions = sorted(self.versions.keys(), key=lambda v: [int(x) for x in v.split(".")])
            self._latest_version = versions[-1] if versions else ""
    
    def get_version(self, version: str) -> Optional[NodeVersion]:
        """Get a specific version."""
        return self.versions.get(version)
    
    def get_latest_version(self) -> Optional[str]:
        """Get the latest version string."""
        return self._latest_version or None
    
    def get_latest(self) -> Optional[NodeVersion]:
        """Get the latest version entry."""
        if self._latest_version:
            return self.versions.get(self._latest_version)
        return None
    
    def version_exists(self, version: str) -> bool:
        """Check if version exists."""
        return version in self.versions
    
    def add_version(self, node_version: NodeVersion) -> None:
        """Add a new version."""
        if self.version_exists(node_version.version):
            raise ValueError(
                ERROR_VERSION_EXISTS.format(
                    version=node_version.version,
                    entity_type="node",
                    id=self.id
                )
            )
        self.versions[node_version.version] = node_version
        
        # Update latest version tracking
        versions = sorted(self.versions.keys(), key=lambda v: [int(x) for x in v.split(".")])
        self._latest_version = versions[-1]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "versions": {v: nv.to_dict() for v, nv in self.versions.items()},
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> NodeEntry:
        """Create from dictionary."""
        versions = {
            v: NodeVersion.from_dict(nv_data)
            for v, nv_data in data.get("versions", {}).items()
        }
        return cls(id=data["id"], versions=versions)
