"""
Agent Context.

This module defines the context object that carries execution metadata,
configuration, and optional services through agent operations.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
import uuid

from ..constants import (
    CONTEXT_REQUEST_ID,
    CONTEXT_USER_ID,
    CONTEXT_SESSION_ID,
    CONTEXT_TENANT_ID,
    CONTEXT_TRACE_ID,
    CONTEXT_LOCALE,
    CONTEXT_METADATA,
    CONTEXT_CONFIG,
    DEFAULT_LOCALE,
    DEFAULT_TIMEZONE,
    PREFIX_REQUEST,
    ARBITRARY_TYPES_ALLOWED,
)


class AgentContext(BaseModel):
    """
    Context for Agent execution.
    
    Carries metadata, configuration, and optional service references
    through agent operations. Similar to LLMContext and ToolContext.
    
    Attributes:
        request_id: Unique request identifier
        user_id: User making the request
        session_id: Session identifier
        tenant_id: Tenant/organization identifier
        trace_id: Distributed tracing ID
        locale: User locale/language
        timezone: User timezone
        metadata: Additional context metadata
        config: Runtime configuration overrides
        
    Injected Dependencies:
        memory: Memory implementation
        scratchpad: Scratchpad implementation
        checklist: Checklist implementation
        observers: List of observer implementations
        input_processor: Input processor implementation
        output_processor: Output processor implementation
        
    Example:
        context = AgentContext(
            user_id="user-123",
            session_id="session-456",
            metadata={"app": "chatbot"}
        )
    """
    
    model_config = {ARBITRARY_TYPES_ALLOWED: True}
    
    # Identifiers
    request_id: str = Field(
        default_factory=lambda: f"{PREFIX_REQUEST}{uuid.uuid4()}",
        description="Unique request identifier"
    )
    user_id: Optional[str] = Field(
        default=None,
        description="User making the request"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Session identifier"
    )
    tenant_id: Optional[str] = Field(
        default=None,
        description="Tenant/organization identifier"
    )
    trace_id: Optional[str] = Field(
        default=None,
        description="Distributed tracing ID"
    )
    parent_span_id: Optional[str] = Field(
        default=None,
        description="Parent span ID for tracing"
    )
    
    # Localization
    locale: str = Field(
        default=DEFAULT_LOCALE,
        description="User locale/language"
    )
    timezone: str = Field(
        default=DEFAULT_TIMEZONE,
        description="User timezone"
    )
    
    # Additional data
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context metadata"
    )
    config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Runtime configuration overrides"
    )
    
    # Conversation/Agent history
    conversation_id: Optional[str] = Field(
        default=None,
        description="Conversation identifier for multi-turn"
    )
    parent_agent_id: Optional[str] = Field(
        default=None,
        description="Parent agent ID for hierarchical agents"
    )
    
    # Injected dependencies (optional)
    # Note: Using Any type for interface fields to avoid Pydantic issues with Protocol types
    memory: Optional[Any] = Field(
        default=None,
        description="Memory implementation (IAgentMemory)"
    )
    scratchpad: Optional[Any] = Field(
        default=None,
        description="Scratchpad implementation (IAgentScratchpad)"
    )
    checklist: Optional[Any] = Field(
        default=None,
        description="Checklist implementation (IAgentChecklist)"
    )
    observers: List[Any] = Field(
        default_factory=list,
        description="Observer implementations (List[IAgentObserver])"
    )
    input_processor: Optional[Any] = Field(
        default=None,
        description="Input processor implementation (IAgentInputProcessor)"
    )
    output_processor: Optional[Any] = Field(
        default=None,
        description="Output processor implementation (IAgentOutputProcessor)"
    )
    
    def with_metadata(self, **kwargs) -> 'AgentContext':
        """
        Create a new context with additional metadata.
        
        Args:
            **kwargs: Metadata key-value pairs to add
            
        Returns:
            New AgentContext with merged metadata
            
        Example:
            new_ctx = context.with_metadata(iteration=1, tool="search")
        """
        new_metadata = self.metadata.copy()
        new_metadata.update(kwargs)
        return self.model_copy(update={CONTEXT_METADATA: new_metadata})
    
    def with_config(self, **kwargs) -> 'AgentContext':
        """
        Create a new context with additional config.
        
        Args:
            **kwargs: Config key-value pairs to add
            
        Returns:
            New AgentContext with merged config
            
        Example:
            new_ctx = context.with_config(max_iterations=20, timeout=60)
        """
        new_config = self.config.copy()
        new_config.update(kwargs)
        return self.model_copy(update={CONTEXT_CONFIG: new_config})
    
    def with_trace(self, trace_id: str, parent_span_id: Optional[str] = None) -> 'AgentContext':
        """
        Create a new context with tracing information.
        
        Args:
            trace_id: Trace ID
            parent_span_id: Optional parent span ID
            
        Returns:
            New AgentContext with tracing info
        """
        updates = {CONTEXT_TRACE_ID: trace_id}
        if parent_span_id:
            updates["parent_span_id"] = parent_span_id
        return self.model_copy(update=updates)
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get a metadata value."""
        return self.metadata.get(key, default)
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get a config value."""
        return self.config.get(key, default)
    
    def to_log_dict(self) -> Dict[str, Any]:
        """
        Convert context to a dictionary suitable for logging.
        
        Returns:
            Dictionary with loggable context data
        """
        return {
            CONTEXT_REQUEST_ID: self.request_id,
            CONTEXT_USER_ID: self.user_id,
            CONTEXT_SESSION_ID: self.session_id,
            CONTEXT_TENANT_ID: self.tenant_id,
            CONTEXT_TRACE_ID: self.trace_id,
            CONTEXT_LOCALE: self.locale,
        }
    
    def child_context(self, **overrides) -> 'AgentContext':
        """
        Create a child context for sub-agents or nested operations.
        
        Args:
            **overrides: Fields to override in child context
            
        Returns:
            New AgentContext with parent reference
        """
        child_data = self.model_dump(exclude={'memory', 'scratchpad', 'checklist', 'observers', 'input_processor', 'output_processor'})
        child_data['parent_span_id'] = self.trace_id
        child_data['request_id'] = f"{PREFIX_REQUEST}{uuid.uuid4()}"
        child_data.update(overrides)
        return AgentContext(**child_data)


# Helper functions

def create_context(
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    **kwargs
) -> AgentContext:
    """
    Helper to create an AgentContext.
    
    Args:
        user_id: Optional user ID
        session_id: Optional session ID
        **kwargs: Additional context fields
        
    Returns:
        AgentContext instance
    """
    return AgentContext(
        user_id=user_id,
        session_id=session_id,
        **kwargs
    )

