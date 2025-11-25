"""
Test suite for Agent Spec Models.

Tests AgentSpec, AgentContext, AgentResult, and related models.
"""

import pytest
import json

from core.agents.spec import (
    AgentContext,
    AgentResult,
    AgentStreamChunk,
    AgentUsage,
    AgentSpec,
    ChecklistItem,
    Checklist,
    create_context,
    create_result,
    create_chunk,
    create_agent_spec,
)
from core.agents.enum import (
    AgentType,
    AgentState,
    ChecklistStatus,
    AgentInputType,
    AgentOutputType,
    AgentOutputFormat,
)


# ============================================================================
# AGENT CONTEXT TESTS
# ============================================================================

@pytest.mark.unit
class TestAgentContext:
    """Test AgentContext model."""
    
    def test_context_creation(self):
        """Test basic context creation."""
        context = AgentContext(
            user_id="user-123",
            session_id="session-456"
        )
        
        assert context.user_id == "user-123"
        assert context.session_id == "session-456"
        assert context.request_id.startswith("req-")
    
    def test_context_defaults(self):
        """Test context defaults."""
        context = AgentContext()
        
        assert context.locale == "en-US"
        assert context.timezone == "UTC"
        assert context.metadata == {}
        assert context.config == {}
    
    def test_context_with_metadata(self):
        """Test with_metadata method."""
        context = AgentContext()
        new_context = context.with_metadata(app="test", version="1.0")
        
        # Original unchanged
        assert "app" not in context.metadata
        
        # New has metadata
        assert new_context.metadata["app"] == "test"
        assert new_context.metadata["version"] == "1.0"
    
    def test_context_with_config(self):
        """Test with_config method."""
        context = AgentContext()
        new_context = context.with_config(timeout=60)
        
        assert "timeout" not in context.config
        assert new_context.config["timeout"] == 60
    
    def test_context_child_context(self):
        """Test child_context method."""
        parent = AgentContext(user_id="user", trace_id="trace-123")
        child = parent.child_context(conversation_id="conv-456")
        
        assert child.user_id == parent.user_id
        assert child.conversation_id == "conv-456"
        assert child.parent_span_id == parent.trace_id
        assert child.request_id != parent.request_id
    
    def test_context_to_log_dict(self):
        """Test to_log_dict method."""
        context = AgentContext(
            user_id="user-123",
            session_id="session-456",
            trace_id="trace-789"
        )
        
        log_dict = context.to_log_dict()
        
        assert log_dict["user_id"] == "user-123"
        assert log_dict["session_id"] == "session-456"
        assert log_dict["trace_id"] == "trace-789"
    
    def test_create_context_helper(self):
        """Test create_context helper function."""
        context = create_context(
            user_id="user-123",
            session_id="session-456"
        )
        
        assert isinstance(context, AgentContext)
        assert context.user_id == "user-123"


# ============================================================================
# AGENT RESULT TESTS
# ============================================================================

@pytest.mark.unit
class TestAgentResult:
    """Test AgentResult model."""
    
    def test_result_creation(self):
        """Test basic result creation."""
        result = AgentResult(
            content="Hello, world!",
            state=AgentState.COMPLETED
        )
        
        assert result.content == "Hello, world!"
        assert result.state == AgentState.COMPLETED
    
    def test_result_defaults(self):
        """Test result defaults."""
        result = AgentResult(content="test")
        
        assert result.output_type == AgentOutputType.TEXT
        assert result.output_format == AgentOutputFormat.TEXT
        assert result.state == AgentState.COMPLETED
        assert result.warnings == []
        assert result.errors == []
    
    def test_result_is_success(self):
        """Test is_success method."""
        success = AgentResult(content="ok", state=AgentState.COMPLETED)
        assert success.is_success()
        
        failure = AgentResult(content=None, state=AgentState.FAILED)
        assert not failure.is_success()
    
    def test_result_is_failure(self):
        """Test is_failure method."""
        failure = AgentResult(content=None, state=AgentState.FAILED)
        assert failure.is_failure()
    
    def test_result_get_text_content(self):
        """Test get_text_content method."""
        # String content
        result1 = AgentResult(content="Hello")
        assert result1.get_text_content() == "Hello"
        
        # Dict with text key
        result2 = AgentResult(content={"text": "World"})
        assert result2.get_text_content() == "World"
        
        # Other type
        result3 = AgentResult(content=42)
        assert result3.get_text_content() == "42"
    
    def test_result_with_usage(self):
        """Test result with usage statistics."""
        usage = AgentUsage(
            iterations=3,
            tool_calls=5,
            llm_calls=4,
            total_tokens=1000
        )
        
        result = AgentResult(
            content="Done",
            usage=usage
        )
        
        assert result.usage.iterations == 3
        assert result.usage.tool_calls == 5
    
    def test_create_result_helper(self):
        """Test create_result helper function."""
        result = create_result(
            content="test",
            state=AgentState.COMPLETED
        )
        
        assert isinstance(result, AgentResult)
        assert result.content == "test"


# ============================================================================
# AGENT STREAM CHUNK TESTS
# ============================================================================

@pytest.mark.unit
class TestAgentStreamChunk:
    """Test AgentStreamChunk model."""
    
    def test_chunk_creation(self):
        """Test basic chunk creation."""
        chunk = AgentStreamChunk(
            content="Processing...",
            chunk_type="thought",
            iteration=1
        )
        
        assert chunk.content == "Processing..."
        assert chunk.chunk_type == "thought"
        assert chunk.iteration == 1
    
    def test_chunk_is_final(self):
        """Test is_final flag."""
        intermediate = AgentStreamChunk(content="...")
        assert not intermediate.is_final
        
        final = AgentStreamChunk(content="Done", is_final=True)
        assert final.is_final
    
    def test_chunk_is_empty(self):
        """Test is_empty method."""
        empty = AgentStreamChunk(content="")
        assert empty.is_empty()
        
        not_empty = AgentStreamChunk(content="data")
        assert not not_empty.is_empty()
    
    def test_chunk_is_tool_chunk(self):
        """Test is_tool_chunk method."""
        regular = AgentStreamChunk(content="thinking...")
        assert not regular.is_tool_chunk()
        
        tool_chunk = AgentStreamChunk(
            content="Searching...",
            tool_name="search"
        )
        assert tool_chunk.is_tool_chunk()
    
    def test_create_chunk_helper(self):
        """Test create_chunk helper."""
        chunk = create_chunk(
            content="test",
            chunk_type="output",
            iteration=2
        )
        
        assert isinstance(chunk, AgentStreamChunk)
        assert chunk.content == "test"


# ============================================================================
# AGENT SPEC TESTS
# ============================================================================

@pytest.mark.unit
class TestAgentSpec:
    """Test AgentSpec model."""
    
    def test_spec_creation(self):
        """Test basic spec creation."""
        spec = AgentSpec(
            name="test_agent",
            description="A test agent"
        )
        
        assert spec.name == "test_agent"
        assert spec.description == "A test agent"
        assert spec.id.startswith("agent-")
    
    def test_spec_defaults(self):
        """Test spec defaults."""
        spec = AgentSpec(name="test")
        
        assert spec.agent_type == AgentType.REACT
        assert spec.max_iterations == 10
        assert AgentInputType.TEXT in spec.supported_input_types
        assert AgentOutputType.TEXT in spec.supported_output_types
    
    def test_spec_supports_input_type(self):
        """Test supports_input_type method."""
        spec = AgentSpec(
            name="test",
            supported_input_types=[AgentInputType.TEXT, AgentInputType.IMAGE]
        )
        
        assert spec.supports_input_type(AgentInputType.TEXT)
        assert spec.supports_input_type(AgentInputType.IMAGE)
        assert not spec.supports_input_type(AgentInputType.AUDIO)
    
    def test_spec_supports_output_type(self):
        """Test supports_output_type method."""
        spec = AgentSpec(
            name="test",
            supported_output_types=[AgentOutputType.TEXT]
        )
        
        assert spec.supports_output_type(AgentOutputType.TEXT)
        assert not spec.supports_output_type(AgentOutputType.IMAGE)
    
    def test_spec_is_tool_allowed(self):
        """Test is_tool_allowed method."""
        # All tools allowed
        spec1 = AgentSpec(name="test")
        assert spec1.is_tool_allowed("any_tool")
        
        # Restricted
        spec2 = AgentSpec(
            name="test",
            allowed_tools=["search", "calculate"]
        )
        assert spec2.is_tool_allowed("search")
        assert not spec2.is_tool_allowed("delete")
    
    def test_create_agent_spec_helper(self):
        """Test create_agent_spec helper."""
        spec = create_agent_spec(
            name="my_agent",
            description="Test",
            agent_type=AgentType.SIMPLE
        )
        
        assert isinstance(spec, AgentSpec)
        assert spec.name == "my_agent"
        assert spec.agent_type == AgentType.SIMPLE


# ============================================================================
# CHECKLIST TESTS
# ============================================================================

@pytest.mark.unit
class TestChecklistModels:
    """Test Checklist and ChecklistItem models."""
    
    def test_checklist_item_creation(self):
        """Test ChecklistItem creation."""
        item = ChecklistItem(
            description="Test task",
            status=ChecklistStatus.PENDING,
            priority=1
        )
        
        assert item.description == "Test task"
        assert item.is_pending()
        assert item.priority == 1
    
    def test_checklist_item_status_methods(self):
        """Test ChecklistItem status methods."""
        item = ChecklistItem(description="Test")
        
        assert item.is_pending()
        assert not item.is_done()
        
        item.mark_in_progress()
        assert item.is_in_progress()
        
        item.mark_completed()
        assert item.is_completed()
        assert item.is_done()
        assert item.completed_at is not None
    
    def test_checklist_creation(self):
        """Test Checklist creation."""
        checklist = Checklist(
            name="Test Checklist",
            description="Test description"
        )
        
        assert checklist.name == "Test Checklist"
        assert checklist.items == []
        assert checklist.is_complete()  # Empty is complete
    
    def test_checklist_add_item(self):
        """Test Checklist add_item."""
        checklist = Checklist(name="Test")
        
        item_id = checklist.add_item("Task 1", priority=1)
        
        assert len(checklist.items) == 1
        assert not checklist.is_complete()
        
        item = checklist.get_item(item_id)
        assert item.description == "Task 1"
    
    def test_checklist_update_status(self):
        """Test Checklist update_status."""
        checklist = Checklist(name="Test")
        item_id = checklist.add_item("Task 1")
        
        checklist.update_status(item_id, ChecklistStatus.COMPLETED)
        
        item = checklist.get_item(item_id)
        assert item.is_completed()
    
    def test_checklist_progress(self):
        """Test Checklist progress tracking."""
        checklist = Checklist(name="Test")
        checklist.add_item("Task 1")
        checklist.add_item("Task 2")
        checklist.add_item("Task 3")
        
        progress = checklist.get_progress()
        assert progress["pending"] == 3
        assert progress["total"] == 3
        
        # Complete one
        item_id = checklist.items[0].id
        checklist.update_status(item_id, ChecklistStatus.COMPLETED)
        
        progress = checklist.get_progress()
        assert progress["completed"] == 1
        assert progress["pending"] == 2
        
        percentage = checklist.get_completion_percentage()
        assert percentage == pytest.approx(33.33, rel=0.1)
    
    def test_checklist_json_serialization(self):
        """Test Checklist JSON serialization."""
        checklist = Checklist(name="Test")
        checklist.add_item("Task 1")
        checklist.add_item("Task 2")
        
        json_str = checklist.to_json()
        
        # Should be valid JSON
        data = json.loads(json_str)
        assert data["name"] == "Test"
        assert len(data["items"]) == 2
        
        # Can reconstruct from JSON
        restored = Checklist.from_json(json_str)
        assert restored.name == "Test"
        assert len(restored.items) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

