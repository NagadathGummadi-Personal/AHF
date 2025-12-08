"""
Agent Specification.

This module defines the AgentSpec model that describes an agent's
configuration, capabilities, and constraints.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import uuid

from ..enum import AgentType, AgentInputType, AgentOutputType, AgentOutputFormat
from ..constants import (
    DEFAULT_MAX_ITERATIONS,
    DEFAULT_TIMEOUT_SECONDS,
    ARBITRARY_TYPES_ALLOWED,
)


class AgentSpec(BaseModel):
    """
    Agent Specification.
    
    Describes an agent's configuration, capabilities, inputs/outputs,
    and operational constraints.
    
    Attributes:
        id: Unique agent identifier
        name: Human-readable agent name
        description: Description of what the agent does
        agent_type: Type of agent (react, goal_based, hierarchical, simple)
        
        Input/Output:
        - supported_input_types: Types of input the agent can accept
        - supported_output_types: Types of output the agent can produce
        - default_output_format: Default format for output
        
        Constraints:
        - max_iterations: Maximum iterations before stopping
        - timeout_seconds: Execution timeout
        
        Metadata:
        - version: Agent version
        - tags: Tags for categorization
        - metadata: Additional metadata
    
    Example:
        spec = AgentSpec(
            name="research_agent",
            description="Researches topics and provides summaries",
            agent_type=AgentType.REACT,
            supported_input_types=[AgentInputType.TEXT],
            supported_output_types=[AgentOutputType.TEXT, AgentOutputType.STRUCTURED],
            max_iterations=15
        )
    """
    
    model_config = {ARBITRARY_TYPES_ALLOWED: True}
    
    # Identity
    id: str = Field(
        default_factory=lambda: f"agent-{uuid.uuid4()}",
        description="Unique agent identifier"
    )
    name: str = Field(
        description="Human-readable agent name"
    )
    description: str = Field(
        default="",
        description="Description of what the agent does"
    )
    agent_type: AgentType = Field(
        default=AgentType.REACT,
        description="Type of agent"
    )
    
    # Input/Output specifications
    supported_input_types: List[AgentInputType] = Field(
        default_factory=lambda: [AgentInputType.TEXT],
        description="Types of input the agent can accept"
    )
    supported_output_types: List[AgentOutputType] = Field(
        default_factory=lambda: [AgentOutputType.TEXT],
        description="Types of output the agent can produce"
    )
    default_output_format: AgentOutputFormat = Field(
        default=AgentOutputFormat.TEXT,
        description="Default format for output"
    )
    
    # Output schema (for structured output)
    output_schema: Optional[Dict[str, Any]] = Field(
        default=None,
        description="JSON schema for structured output validation"
    )
    
    # Constraints
    max_iterations: int = Field(
        default=DEFAULT_MAX_ITERATIONS,
        ge=1,
        description="Maximum iterations before stopping"
    )
    timeout_seconds: float = Field(
        default=DEFAULT_TIMEOUT_SECONDS,
        gt=0,
        description="Execution timeout in seconds"
    )
    
    # System prompt / instructions
    system_prompt: Optional[str] = Field(
        default=None,
        description="System prompt/instructions for the agent"
    )
    system_prompt_label: Optional[str] = Field(
        default=None,
        description="Label to fetch system prompt from registry"
    )
    
    # Tool configuration
    allowed_tools: Optional[List[str]] = Field(
        default=None,
        description="List of allowed tool names (None = all tools)"
    )
    required_tools: Optional[List[str]] = Field(
        default=None,
        description="List of required tool names"
    )
    
    # Permissions and security
    permissions: List[str] = Field(
        default_factory=list,
        description="Required permissions to execute"
    )
    
    # Versioning and metadata
    version: str = Field(
        default="1.0.0",
        description="Agent version"
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Tags for categorization"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    
    # Deprecation
    deprecated: bool = Field(
        default=False,
        description="Whether agent is deprecated"
    )
    deprecation_message: Optional[str] = Field(
        default=None,
        description="Deprecation message"
    )
    replacement_agent: Optional[str] = Field(
        default=None,
        description="Recommended replacement agent ID"
    )
    
    def supports_input_type(self, input_type: AgentInputType) -> bool:
        """Check if agent supports the given input type."""
        return (
            input_type in self.supported_input_types or
            AgentInputType.MULTIMODAL in self.supported_input_types
        )
    
    def supports_output_type(self, output_type: AgentOutputType) -> bool:
        """Check if agent supports the given output type."""
        return (
            output_type in self.supported_output_types or
            AgentOutputType.MULTIMODAL in self.supported_output_types
        )
    
    def is_tool_allowed(self, tool_name: str) -> bool:
        """Check if a tool is allowed for this agent."""
        if self.allowed_tools is None:
            return True  # All tools allowed
        return tool_name in self.allowed_tools
    
    def get_required_tools(self) -> List[str]:
        """Get list of required tools."""
        return self.required_tools or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert spec to dictionary."""
        return self.model_dump()


def create_agent_spec(
    name: str,
    description: str = "",
    agent_type: AgentType = AgentType.REACT,
    **kwargs
) -> AgentSpec:
    """
    Helper to create an AgentSpec.
    
    Args:
        name: Agent name
        description: Agent description
        agent_type: Type of agent
        **kwargs: Additional spec fields
        
    Returns:
        AgentSpec instance
    """
    return AgentSpec(
        name=name,
        description=description,
        agent_type=agent_type,
        **kwargs
    )

