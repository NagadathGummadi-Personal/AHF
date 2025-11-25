"""
Agent Context Builder.

Provides a fluent interface for building AgentContext instances.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from ..spec.agent_context import AgentContext

if TYPE_CHECKING:
    from ..interfaces.agent_interfaces import (
        IAgentMemory,
        IAgentScratchpad,
        IAgentChecklist,
        IAgentObserver,
        IAgentInputProcessor,
        IAgentOutputProcessor,
    )


class AgentContextBuilder:
    """
    Builder for creating AgentContext instances with fluent interface.
    
    Usage:
        # Simple context
        context = (AgentContextBuilder()
            .with_user("user-123")
            .with_session("session-456")
            .build())
        
        # Full context with all dependencies
        context = (AgentContextBuilder()
            .with_user("user-123")
            .with_session("session-456")
            .with_tenant("tenant-789")
            .with_trace("trace-abc")
            .with_memory(DictMemory())
            .with_scratchpad(BasicScratchpad())
            .with_checklist(Checklist())
            .with_observer(LoggingObserver())
            .build())
        
        # Using factory names
        context = (AgentContextBuilder()
            .with_user("user-123")
            .with_memory_by_name('dict')
            .with_scratchpad_by_name('basic')
            .build())
    """
    
    def __init__(self):
        """Initialize builder with default values."""
        self._user_id: Optional[str] = None
        self._session_id: Optional[str] = None
        self._tenant_id: Optional[str] = None
        self._trace_id: Optional[str] = None
        self._parent_span_id: Optional[str] = None
        self._locale: str = "en-US"
        self._timezone: str = "UTC"
        self._metadata: Dict[str, Any] = {}
        self._config: Dict[str, Any] = {}
        self._conversation_id: Optional[str] = None
        self._parent_agent_id: Optional[str] = None
        self._memory: Optional['IAgentMemory'] = None
        self._scratchpad: Optional['IAgentScratchpad'] = None
        self._checklist: Optional['IAgentChecklist'] = None
        self._observers: List['IAgentObserver'] = []
        self._input_processor: Optional['IAgentInputProcessor'] = None
        self._output_processor: Optional['IAgentOutputProcessor'] = None
    
    def with_user(self, user_id: str) -> 'AgentContextBuilder':
        """Set user ID."""
        self._user_id = user_id
        return self
    
    def with_session(self, session_id: str) -> 'AgentContextBuilder':
        """Set session ID."""
        self._session_id = session_id
        return self
    
    def with_tenant(self, tenant_id: str) -> 'AgentContextBuilder':
        """Set tenant ID."""
        self._tenant_id = tenant_id
        return self
    
    def with_trace(
        self,
        trace_id: str,
        parent_span_id: Optional[str] = None
    ) -> 'AgentContextBuilder':
        """Set tracing IDs."""
        self._trace_id = trace_id
        self._parent_span_id = parent_span_id
        return self
    
    def with_locale(self, locale: str) -> 'AgentContextBuilder':
        """Set locale."""
        self._locale = locale
        return self
    
    def with_timezone(self, timezone: str) -> 'AgentContextBuilder':
        """Set timezone."""
        self._timezone = timezone
        return self
    
    def with_metadata(self, **kwargs) -> 'AgentContextBuilder':
        """Add metadata."""
        self._metadata.update(kwargs)
        return self
    
    def with_config(self, **kwargs) -> 'AgentContextBuilder':
        """Add config."""
        self._config.update(kwargs)
        return self
    
    def with_conversation(self, conversation_id: str) -> 'AgentContextBuilder':
        """Set conversation ID for multi-turn."""
        self._conversation_id = conversation_id
        return self
    
    def with_parent_agent(self, parent_agent_id: str) -> 'AgentContextBuilder':
        """Set parent agent ID for hierarchical agents."""
        self._parent_agent_id = parent_agent_id
        return self
    
    def with_memory(self, memory: 'IAgentMemory') -> 'AgentContextBuilder':
        """Set memory implementation."""
        self._memory = memory
        return self
    
    def with_scratchpad(self, scratchpad: 'IAgentScratchpad') -> 'AgentContextBuilder':
        """Set scratchpad implementation."""
        self._scratchpad = scratchpad
        return self
    
    def with_checklist(self, checklist: 'IAgentChecklist') -> 'AgentContextBuilder':
        """Set checklist implementation."""
        self._checklist = checklist
        return self
    
    def with_observer(self, observer: 'IAgentObserver') -> 'AgentContextBuilder':
        """Add an observer."""
        self._observers.append(observer)
        return self
    
    def with_observers(self, observers: List['IAgentObserver']) -> 'AgentContextBuilder':
        """Add multiple observers."""
        self._observers.extend(observers)
        return self
    
    def with_input_processor(self, processor: 'IAgentInputProcessor') -> 'AgentContextBuilder':
        """Set input processor."""
        self._input_processor = processor
        return self
    
    def with_output_processor(self, processor: 'IAgentOutputProcessor') -> 'AgentContextBuilder':
        """Set output processor."""
        self._output_processor = processor
        return self
    
    def with_memory_by_name(self, name: str) -> 'AgentContextBuilder':
        """Set memory by factory name."""
        from ..runtimes.memory.memory_factory import AgentMemoryFactory
        self._memory = AgentMemoryFactory.get_memory(name)
        return self
    
    def with_scratchpad_by_name(self, name: str) -> 'AgentContextBuilder':
        """Set scratchpad by factory name."""
        from ..runtimes.scratchpad.scratchpad_factory import ScratchpadFactory
        self._scratchpad = ScratchpadFactory.get_scratchpad(name)
        return self
    
    def with_defaults(self, profile: str = 'noop') -> 'AgentContextBuilder':
        """
        Set all components to default implementations.
        
        Args:
            profile: Profile name ('noop', 'basic')
        """
        if profile == 'noop':
            self.with_memory_by_name('noop')
            self.with_scratchpad_by_name('basic')
        elif profile == 'basic':
            self.with_memory_by_name('dict')
            self.with_scratchpad_by_name('basic')
        return self
    
    def build(self) -> AgentContext:
        """
        Build and return the AgentContext instance.
        
        Returns:
            Configured AgentContext instance
        """
        return AgentContext(
            user_id=self._user_id,
            session_id=self._session_id,
            tenant_id=self._tenant_id,
            trace_id=self._trace_id,
            parent_span_id=self._parent_span_id,
            locale=self._locale,
            timezone=self._timezone,
            metadata=self._metadata,
            config=self._config,
            conversation_id=self._conversation_id,
            parent_agent_id=self._parent_agent_id,
            memory=self._memory,
            scratchpad=self._scratchpad,
            checklist=self._checklist,
            observers=self._observers,
            input_processor=self._input_processor,
            output_processor=self._output_processor,
        )

