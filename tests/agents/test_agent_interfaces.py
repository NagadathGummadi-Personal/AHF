"""
Test suite for Agent Interfaces.

Tests protocol compliance and basic contract verification.
"""

import pytest
from typing import Any, Dict, List

from core.agents.interfaces import (
    IAgent,
    IAgentMemory,
    IAgentScratchpad,
    IAgentChecklist,
    IAgentObserver,
)
from core.agents.runtimes import (
    NoOpAgentMemory,
    DictMemory,
    BasicScratchpad,
    StructuredScratchpad,
    BasicChecklist,
    NoOpObserver,
    LoggingObserver,
)


# ============================================================================
# MEMORY INTERFACE TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestIAgentMemory:
    """Test IAgentMemory interface compliance."""
    
    async def test_noop_memory_implements_interface(self):
        """Test NoOpAgentMemory implements IAgentMemory."""
        memory = NoOpAgentMemory()
        assert isinstance(memory, IAgentMemory)
    
    async def test_dict_memory_implements_interface(self):
        """Test DictMemory implements IAgentMemory."""
        memory = DictMemory()
        assert isinstance(memory, IAgentMemory)
    
    async def test_noop_memory_operations(self):
        """Test NoOpMemory basic operations."""
        memory = NoOpAgentMemory()
        
        # All operations should be no-ops
        await memory.add("key", "value")
        result = await memory.get("key")
        assert result is None
        
        await memory.update("key", "new_value")
        await memory.delete("key")
        await memory.clear()
        
        keys = await memory.list_keys()
        assert keys == []
    
    async def test_dict_memory_operations(self):
        """Test DictMemory basic operations."""
        memory = DictMemory()
        
        # Add and get
        await memory.add("key1", "value1")
        result = await memory.get("key1")
        assert result == "value1"
        
        # Update
        await memory.update("key1", "updated")
        result = await memory.get("key1")
        assert result == "updated"
        
        # Add with metadata
        await memory.add("key2", "value2", metadata={"type": "test"})
        
        # List keys
        keys = await memory.list_keys()
        assert "key1" in keys
        assert "key2" in keys
        
        # Delete
        await memory.delete("key1")
        result = await memory.get("key1")
        assert result is None
        
        # Clear
        await memory.clear()
        keys = await memory.list_keys()
        assert keys == []


# ============================================================================
# SCRATCHPAD INTERFACE TESTS
# ============================================================================

@pytest.mark.unit
class TestIAgentScratchpad:
    """Test IAgentScratchpad interface compliance."""
    
    def test_basic_scratchpad_implements_interface(self):
        """Test BasicScratchpad implements IAgentScratchpad."""
        scratchpad = BasicScratchpad()
        assert isinstance(scratchpad, IAgentScratchpad)
    
    def test_structured_scratchpad_implements_interface(self):
        """Test StructuredScratchpad implements IAgentScratchpad."""
        scratchpad = StructuredScratchpad()
        assert isinstance(scratchpad, IAgentScratchpad)
    
    def test_basic_scratchpad_operations(self):
        """Test BasicScratchpad operations."""
        scratchpad = BasicScratchpad()
        
        # Initially empty
        assert scratchpad.read() == ""
        assert scratchpad.is_empty()
        
        # Append
        scratchpad.append("First entry")
        scratchpad.append("Second entry")
        
        # Read
        content = scratchpad.read()
        assert "First entry" in content
        assert "Second entry" in content
        
        # Get last N entries
        last = scratchpad.get_last_n_entries(1)
        assert "Second entry" in last
        
        # Write (overwrite)
        scratchpad.write("New content")
        content = scratchpad.read()
        assert content == "New content"
        
        # Clear
        scratchpad.clear()
        assert scratchpad.is_empty()
    
    def test_structured_scratchpad_operations(self):
        """Test StructuredScratchpad operations."""
        scratchpad = StructuredScratchpad()
        
        # Add structured entries
        scratchpad.add_thought("I need to search")
        scratchpad.add_action("search", {"query": "test"})
        scratchpad.add_observation("Found results")
        
        # Read formatted
        content = scratchpad.read()
        assert "Thought:" in content
        assert "Action:" in content
        assert "Observation:" in content
        
        # Get by type
        thoughts = scratchpad.get_thoughts()
        assert "I need to search" in thoughts
        
        actions = scratchpad.get_actions()
        assert len(actions) == 1
        assert actions[0]["content"] == "search"
        
        # Clear
        scratchpad.clear()
        assert scratchpad.is_empty()


# ============================================================================
# CHECKLIST INTERFACE TESTS
# ============================================================================

@pytest.mark.unit
class TestIAgentChecklist:
    """Test IAgentChecklist interface compliance."""
    
    def test_basic_checklist_implements_interface(self):
        """Test BasicChecklist implements IAgentChecklist."""
        checklist = BasicChecklist()
        assert isinstance(checklist, IAgentChecklist)
    
    def test_checklist_operations(self):
        """Test BasicChecklist operations."""
        checklist = BasicChecklist()
        
        # Initially complete (no items)
        assert checklist.is_complete()
        
        # Add items
        item1_id = checklist.add_item("Task 1", priority=1)
        item2_id = checklist.add_item("Task 2", priority=2)
        
        # Not complete
        assert not checklist.is_complete()
        
        # Get pending
        pending = checklist.get_pending_items()
        assert len(pending) == 2
        
        # Update status
        checklist.update_status(item1_id, "in_progress")
        in_progress = checklist.get_in_progress_items()
        assert len(in_progress) == 1
        
        checklist.update_status(item1_id, "completed")
        completed = checklist.get_completed_items()
        assert len(completed) == 1
        
        checklist.update_status(item2_id, "completed")
        
        # Now complete
        assert checklist.is_complete()
        
        # Progress
        progress = checklist.get_progress()
        assert progress["completed"] == 2
        assert progress["total"] == 2
        
        # JSON serialization
        json_str = checklist.to_json()
        assert "Task 1" in json_str


# ============================================================================
# OBSERVER INTERFACE TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestIAgentObserver:
    """Test IAgentObserver interface compliance."""
    
    async def test_noop_observer_implements_interface(self):
        """Test NoOpObserver implements IAgentObserver."""
        observer = NoOpObserver()
        assert isinstance(observer, IAgentObserver)
    
    async def test_logging_observer_implements_interface(self):
        """Test LoggingObserver implements IAgentObserver."""
        observer = LoggingObserver()
        assert isinstance(observer, IAgentObserver)
    
    async def test_noop_observer_operations(self):
        """Test NoOpObserver doesn't raise errors."""
        from core.agents.spec import AgentContext, AgentResult
        from core.agents.enum import AgentState
        
        observer = NoOpObserver()
        ctx = AgentContext()
        result = AgentResult(content="test", state=AgentState.COMPLETED)
        
        # None of these should raise
        await observer.on_agent_start("input", ctx)
        await observer.on_agent_end(result, ctx)
        await observer.on_iteration_start(1, ctx)
        await observer.on_iteration_end(1, ctx)
        await observer.on_tool_call("tool", {}, ctx)
        await observer.on_tool_result("tool", "result", ctx)
        await observer.on_llm_call([], ctx)
        await observer.on_llm_response("response", ctx)
        await observer.on_error(Exception("test"), ctx)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

