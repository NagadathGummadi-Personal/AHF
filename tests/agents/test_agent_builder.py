"""
Test suite for Agent Builder.

Tests the fluent builder pattern for creating agents.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from core.agents.builders import AgentBuilder, AgentContextBuilder
from core.agents.enum import AgentType, AgentInputType, AgentOutputType, AgentOutputFormat
from core.agents.spec import AgentSpec, AgentContext
from core.agents.runtimes import (
    DictMemory,
    BasicScratchpad,
    BasicChecklist,
    NoOpObserver,
)
from core.agents.exceptions import AgentBuildError


# ============================================================================
# AGENT BUILDER TESTS
# ============================================================================

@pytest.mark.unit
class TestAgentBuilder:
    """Test AgentBuilder functionality."""
    
    def test_builder_initialization(self):
        """Test builder initializes with defaults."""
        builder = AgentBuilder()
        assert builder._agent_type == AgentType.REACT
        assert builder._max_iterations == 10
        assert builder._tools == []
    
    def test_builder_with_name(self):
        """Test setting agent name."""
        builder = AgentBuilder().with_name("test_agent")
        assert builder._name == "test_agent"
    
    def test_builder_with_description(self):
        """Test setting agent description."""
        builder = AgentBuilder().with_description("A test agent")
        assert builder._description == "A test agent"
    
    def test_builder_as_type(self):
        """Test setting agent type."""
        builder = AgentBuilder().as_type(AgentType.GOAL_BASED)
        assert builder._agent_type == AgentType.GOAL_BASED
    
    def test_builder_with_llm(self):
        """Test setting LLM."""
        mock_llm = MagicMock()
        builder = AgentBuilder().with_llm(mock_llm)
        assert builder._llm == mock_llm
    
    def test_builder_with_backup_llm(self):
        """Test setting backup LLM."""
        mock_llm = MagicMock()
        builder = AgentBuilder().with_backup_llm(mock_llm)
        assert builder._backup_llm == mock_llm
    
    def test_builder_with_tools(self):
        """Test adding tools."""
        tool1 = MagicMock()
        tool2 = MagicMock()
        
        builder = AgentBuilder().with_tools([tool1, tool2])
        assert len(builder._tools) == 2
        
        tool3 = MagicMock()
        builder.with_tool(tool3)
        assert len(builder._tools) == 3
    
    def test_builder_with_memory(self):
        """Test setting memory."""
        memory = DictMemory()
        builder = AgentBuilder().with_memory(memory)
        assert builder._memory == memory
    
    def test_builder_with_scratchpad(self):
        """Test setting scratchpad."""
        scratchpad = BasicScratchpad()
        builder = AgentBuilder().with_scratchpad(scratchpad)
        assert builder._scratchpad == scratchpad
    
    def test_builder_with_checklist(self):
        """Test setting checklist."""
        checklist = BasicChecklist()
        builder = AgentBuilder().with_checklist(checklist)
        assert builder._checklist == checklist
    
    def test_builder_with_observer(self):
        """Test adding observer."""
        observer = NoOpObserver()
        builder = AgentBuilder().with_observer(observer)
        assert observer in builder._observers
    
    def test_builder_with_system_prompt(self):
        """Test setting system prompt."""
        builder = AgentBuilder().with_system_prompt("You are helpful")
        assert builder._system_prompt == "You are helpful"
    
    def test_builder_with_max_iterations(self):
        """Test setting max iterations."""
        builder = AgentBuilder().with_max_iterations(20)
        assert builder._max_iterations == 20
    
    def test_builder_with_timeout(self):
        """Test setting timeout."""
        builder = AgentBuilder().with_timeout(60)
        assert builder._timeout_seconds == 60
    
    def test_builder_with_input_types(self):
        """Test setting input types."""
        builder = AgentBuilder().with_input_types([
            AgentInputType.TEXT,
            AgentInputType.IMAGE
        ])
        assert AgentInputType.TEXT in builder._supported_input_types
        assert AgentInputType.IMAGE in builder._supported_input_types
    
    def test_builder_with_output_types(self):
        """Test setting output types."""
        builder = AgentBuilder().with_output_types([
            AgentOutputType.TEXT,
            AgentOutputType.STRUCTURED
        ])
        assert AgentOutputType.TEXT in builder._supported_output_types
        assert AgentOutputType.STRUCTURED in builder._supported_output_types
    
    def test_builder_with_output_format(self):
        """Test setting output format."""
        builder = AgentBuilder().with_output_format(AgentOutputFormat.JSON)
        assert builder._default_output_format == AgentOutputFormat.JSON
    
    def test_builder_fluent_chaining(self):
        """Test fluent method chaining."""
        mock_llm = MagicMock()
        
        builder = (AgentBuilder()
            .with_name("test_agent")
            .with_description("A test")
            .with_llm(mock_llm)
            .with_max_iterations(15)
            .as_type(AgentType.REACT))
        
        assert builder._name == "test_agent"
        assert builder._description == "A test"
        assert builder._llm == mock_llm
        assert builder._max_iterations == 15
        assert builder._agent_type == AgentType.REACT
    
    def test_build_spec_only(self):
        """Test building only the spec."""
        spec = (AgentBuilder()
            .with_name("test_agent")
            .with_description("Test description")
            .with_max_iterations(15)
            .with_input_types([AgentInputType.TEXT])
            .with_output_types([AgentOutputType.STRUCTURED])
            .with_output_format(AgentOutputFormat.JSON)
            .build_spec())
        
        assert isinstance(spec, AgentSpec)
        assert spec.name == "test_agent"
        assert spec.description == "Test description"
        assert spec.max_iterations == 15
        assert AgentInputType.TEXT in spec.supported_input_types
        assert AgentOutputType.STRUCTURED in spec.supported_output_types
        assert spec.default_output_format == AgentOutputFormat.JSON
    
    def test_build_without_name_raises(self):
        """Test building without name raises error."""
        with pytest.raises(AgentBuildError):
            AgentBuilder().build_spec()
    
    def test_build_without_llm_raises(self):
        """Test building agent without LLM raises error."""
        with pytest.raises(AgentBuildError):
            (AgentBuilder()
                .with_name("test")
                .build())


# ============================================================================
# AGENT CONTEXT BUILDER TESTS
# ============================================================================

@pytest.mark.unit
class TestAgentContextBuilder:
    """Test AgentContextBuilder functionality."""
    
    def test_context_builder_initialization(self):
        """Test context builder initializes with defaults."""
        builder = AgentContextBuilder()
        assert builder._locale == "en-US"
        assert builder._timezone == "UTC"
    
    def test_context_builder_with_user(self):
        """Test setting user ID."""
        builder = AgentContextBuilder().with_user("user-123")
        assert builder._user_id == "user-123"
    
    def test_context_builder_with_session(self):
        """Test setting session ID."""
        builder = AgentContextBuilder().with_session("session-456")
        assert builder._session_id == "session-456"
    
    def test_context_builder_with_tenant(self):
        """Test setting tenant ID."""
        builder = AgentContextBuilder().with_tenant("tenant-789")
        assert builder._tenant_id == "tenant-789"
    
    def test_context_builder_with_trace(self):
        """Test setting trace ID."""
        builder = AgentContextBuilder().with_trace("trace-abc", "parent-xyz")
        assert builder._trace_id == "trace-abc"
        assert builder._parent_span_id == "parent-xyz"
    
    def test_context_builder_with_metadata(self):
        """Test adding metadata."""
        builder = AgentContextBuilder().with_metadata(key1="value1", key2="value2")
        assert builder._metadata["key1"] == "value1"
        assert builder._metadata["key2"] == "value2"
    
    def test_context_builder_with_config(self):
        """Test adding config."""
        builder = AgentContextBuilder().with_config(timeout=60)
        assert builder._config["timeout"] == 60
    
    def test_context_builder_build(self):
        """Test building context."""
        context = (AgentContextBuilder()
            .with_user("user-123")
            .with_session("session-456")
            .with_metadata(app="test")
            .build())
        
        assert isinstance(context, AgentContext)
        assert context.user_id == "user-123"
        assert context.session_id == "session-456"
        assert context.metadata["app"] == "test"
    
    def test_context_builder_fluent_chaining(self):
        """Test fluent chaining for context builder."""
        context = (AgentContextBuilder()
            .with_user("user")
            .with_session("session")
            .with_tenant("tenant")
            .with_locale("en-GB")
            .with_timezone("Europe/London")
            .with_memory(DictMemory())
            .with_scratchpad(BasicScratchpad())
            .build())
        
        assert context.user_id == "user"
        assert context.session_id == "session"
        assert context.tenant_id == "tenant"
        assert context.locale == "en-GB"
        assert context.timezone == "Europe/London"
        assert context.memory is not None
        assert context.scratchpad is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

