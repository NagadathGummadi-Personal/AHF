"""
Tests for the Memory Module.

Tests conversation history, state tracking, checkpoints, and working memory.

Version: 1.0.0
"""

import pytest
from datetime import datetime

from core.memory import (
    WorkingMemory,
    ConversationHistory,
    InMemoryStateTracker,
    MemoryFactory,
    Checkpoint,
    StateSnapshot,
    Message,
)


# =============================================================================
# CONVERSATION HISTORY TESTS
# =============================================================================

class TestConversationHistory:
    """Tests for ConversationHistory."""
    
    def test_add_message(self):
        """Test adding messages."""
        history = ConversationHistory()
        
        msg_id = history.add_message("user", "Hello!")
        
        assert msg_id is not None
        assert history.get_message_count() == 1
    
    def test_add_multiple_messages(self):
        """Test adding multiple messages."""
        history = ConversationHistory()
        
        history.add_message("system", "You are a helpful assistant.")
        history.add_message("user", "Hello!")
        history.add_message("assistant", "Hi there!")
        
        assert history.get_message_count() == 3
    
    def test_get_last_message(self):
        """Test getting last message."""
        history = ConversationHistory()
        
        history.add_message("user", "First")
        history.add_message("assistant", "Second")
        history.add_message("user", "Third")
        
        last = history.get_last_message()
        assert last["content"] == "Third"
        assert last["role"] == "user"
    
    def test_get_last_message_by_role(self):
        """Test getting last message by role."""
        history = ConversationHistory()
        
        history.add_message("user", "User message 1")
        history.add_message("assistant", "Assistant message")
        history.add_message("user", "User message 2")
        
        last_assistant = history.get_last_message(role="assistant")
        assert last_assistant["content"] == "Assistant message"
    
    def test_to_llm_messages(self):
        """Test converting to LLM format."""
        history = ConversationHistory()
        
        history.add_message("system", "You are helpful.")
        history.add_message("user", "Hello")
        history.add_message("assistant", "Hi!")
        
        llm_messages = history.to_llm_messages()
        
        assert len(llm_messages) == 3
        assert llm_messages[0] == {"role": "system", "content": "You are helpful."}
        assert llm_messages[1] == {"role": "user", "content": "Hello"}
        assert llm_messages[2] == {"role": "assistant", "content": "Hi!"}
    
    def test_to_llm_messages_with_limit(self):
        """Test limiting LLM messages."""
        history = ConversationHistory()
        
        history.add_message("system", "System prompt")
        for i in range(10):
            history.add_message("user", f"User {i}")
            history.add_message("assistant", f"Assistant {i}")
        
        # Limit to 5 messages, should keep system + last 4
        llm_messages = history.to_llm_messages(max_messages=5)
        
        assert len(llm_messages) == 5
        assert llm_messages[0]["role"] == "system"  # System preserved
    
    def test_max_messages_limit(self):
        """Test max messages limit trims old messages."""
        history = ConversationHistory(max_messages=5)
        
        history.add_message("system", "System")
        for i in range(10):
            history.add_message("user", f"User {i}")
        
        assert history.get_message_count() <= 5
        # System message should be preserved
        messages = history.get_messages()
        assert any(m["role"] == "system" for m in messages)
    
    def test_clear_messages(self):
        """Test clearing messages."""
        history = ConversationHistory()
        
        history.add_message("user", "Hello")
        history.add_message("assistant", "Hi")
        
        history.clear_messages()
        
        assert history.get_message_count() == 0
    
    def test_serialization(self):
        """Test to_dict and from_dict."""
        history = ConversationHistory(max_messages=100)
        
        history.add_message("user", "Hello")
        history.add_message("assistant", "Hi!")
        
        data = history.to_dict()
        restored = ConversationHistory.from_dict(data)
        
        assert restored.get_message_count() == 2
        assert restored.get_last_message()["content"] == "Hi!"


# =============================================================================
# STATE TRACKER TESTS
# =============================================================================

class TestStateTracker:
    """Tests for InMemoryStateTracker."""
    
    def test_set_and_get_state(self):
        """Test setting and getting state."""
        tracker = InMemoryStateTracker(session_id="test-session")
        
        tracker.set_state("current_node", "greeting")
        tracker.set_state("user_intent", "booking")
        
        assert tracker.get_state("current_node") == "greeting"
        assert tracker.get_state("user_intent") == "booking"
        assert tracker.get_state("nonexistent") is None
    
    def test_get_full_state(self):
        """Test getting full state."""
        tracker = InMemoryStateTracker(session_id="test-session")
        
        tracker.set_state("key1", "value1")
        tracker.set_state("key2", "value2")
        
        state = tracker.get_full_state()
        
        assert state == {"key1": "value1", "key2": "value2"}
    
    def test_save_checkpoint(self):
        """Test saving a checkpoint."""
        tracker = InMemoryStateTracker(session_id="test-session")
        
        tracker.set_state("current_node", "greeting")
        
        checkpoint = tracker.save_checkpoint(
            "checkpoint-1",
            {"node_status": "completed"},
            metadata={"description": "After greeting"}
        )
        
        assert checkpoint.id == "checkpoint-1"
        assert "node_status" in checkpoint.state
        assert "current_node" in checkpoint.state
    
    def test_get_checkpoint(self):
        """Test getting a checkpoint."""
        tracker = InMemoryStateTracker(session_id="test-session")
        
        tracker.save_checkpoint("cp-1", {"status": "done"})
        
        checkpoint = tracker.get_checkpoint("cp-1")
        
        assert checkpoint is not None
        assert checkpoint.id == "cp-1"
        assert checkpoint.state["status"] == "done"
    
    def test_get_latest_checkpoint(self):
        """Test getting latest checkpoint."""
        tracker = InMemoryStateTracker(session_id="test-session")
        
        tracker.save_checkpoint("cp-1", {"order": 1})
        tracker.save_checkpoint("cp-2", {"order": 2})
        tracker.save_checkpoint("cp-3", {"order": 3})
        
        latest = tracker.get_latest_checkpoint()
        
        assert latest is not None
        assert latest.id == "cp-3"
        assert latest.state["order"] == 3
    
    def test_list_checkpoints(self):
        """Test listing checkpoints."""
        tracker = InMemoryStateTracker(session_id="test-session")
        
        tracker.save_checkpoint("cp-1", {})
        tracker.save_checkpoint("cp-2", {})
        tracker.save_checkpoint("cp-3", {})
        
        checkpoints = tracker.list_checkpoints()
        
        assert len(checkpoints) == 3
        assert [cp.id for cp in checkpoints] == ["cp-1", "cp-2", "cp-3"]
    
    def test_delete_checkpoint(self):
        """Test deleting a checkpoint."""
        tracker = InMemoryStateTracker(session_id="test-session")
        
        tracker.save_checkpoint("cp-1", {})
        
        assert tracker.delete_checkpoint("cp-1") is True
        assert tracker.get_checkpoint("cp-1") is None
        assert tracker.delete_checkpoint("nonexistent") is False
    
    def test_max_checkpoints_limit(self):
        """Test max checkpoints limit."""
        tracker = InMemoryStateTracker(session_id="test-session", max_checkpoints=3)
        
        for i in range(5):
            tracker.save_checkpoint(f"cp-{i}", {"index": i})
        
        checkpoints = tracker.list_checkpoints()
        
        assert len(checkpoints) == 3
        # Oldest should be trimmed
        assert "cp-0" not in [cp.id for cp in checkpoints]
        assert "cp-1" not in [cp.id for cp in checkpoints]
    
    def test_create_snapshot(self):
        """Test creating a snapshot."""
        tracker = InMemoryStateTracker(session_id="test-session")
        
        tracker.set_state("key", "value")
        tracker.save_checkpoint("cp-1", {})
        
        snapshot = tracker.create_snapshot()
        
        assert snapshot.session_id == "test-session"
        assert "key" in snapshot.state
    
    def test_restore_from_snapshot(self):
        """Test restoring from snapshot."""
        tracker = InMemoryStateTracker(session_id="test-session")
        
        tracker.set_state("key", "original")
        snapshot = tracker.create_snapshot()
        
        tracker.set_state("key", "modified")
        tracker.set_state("new_key", "new_value")
        
        tracker.restore_from_snapshot(snapshot)
        
        assert tracker.get_state("key") == "original"


# =============================================================================
# WORKING MEMORY TESTS
# =============================================================================

class TestWorkingMemory:
    """Tests for WorkingMemory."""
    
    def test_create_working_memory(self):
        """Test creating working memory."""
        memory = WorkingMemory(session_id="test-session")
        
        assert memory.session_id == "test-session"
        assert memory.conversation is not None
        assert memory.state_tracker is not None
    
    def test_add_messages(self):
        """Test adding messages."""
        memory = WorkingMemory()
        
        memory.add_message("user", "Hello")
        memory.add_message("assistant", "Hi there!")
        
        history = memory.get_conversation_history()
        
        assert len(history) == 2
    
    def test_convenience_message_methods(self):
        """Test convenience methods for adding messages."""
        memory = WorkingMemory()
        
        memory.add_system_message("You are helpful.")
        memory.add_user_message("Hello")
        memory.add_assistant_message("Hi!")
        
        history = memory.get_conversation_history()
        
        assert len(history) == 3
        assert history[0]["role"] == "system"
        assert history[1]["role"] == "user"
        assert history[2]["role"] == "assistant"
    
    def test_get_last_messages(self):
        """Test getting last messages by role."""
        memory = WorkingMemory()
        
        memory.add_user_message("User message")
        memory.add_assistant_message("Assistant message")
        
        assert memory.get_last_user_message() == "User message"
        assert memory.get_last_assistant_message() == "Assistant message"
    
    def test_variables(self):
        """Test variable operations."""
        memory = WorkingMemory()
        
        memory.set_variable("service_name", "haircut")
        memory.set_variable("user_intent", "booking")
        
        assert memory.get_variable("service_name") == "haircut"
        assert memory.get_variable("nonexistent", "default") == "default"
        
        all_vars = memory.get_all_variables()
        assert "service_name" in all_vars
        assert "user_intent" in all_vars
    
    def test_update_variables(self):
        """Test updating multiple variables."""
        memory = WorkingMemory()
        
        memory.update_variables({
            "key1": "value1",
            "key2": "value2",
        })
        
        assert memory.get_variable("key1") == "value1"
        assert memory.get_variable("key2") == "value2"
    
    def test_delete_variable(self):
        """Test deleting a variable."""
        memory = WorkingMemory()
        
        memory.set_variable("key", "value")
        assert memory.delete_variable("key") is True
        assert memory.get_variable("key") is None
    
    def test_state_tracking(self):
        """Test state tracking."""
        memory = WorkingMemory()
        
        memory.set_state("current_node", "greeting")
        
        assert memory.get_state("current_node") == "greeting"
        
        state = memory.get_full_state()
        assert "current_node" in state
    
    def test_save_and_restore_checkpoint(self):
        """Test saving and restoring checkpoint."""
        memory = WorkingMemory()
        
        # Set up some state
        memory.add_user_message("Hello")
        memory.add_assistant_message("Hi!")
        memory.set_variable("service_name", "haircut")
        
        # Save checkpoint
        checkpoint = memory.save_checkpoint("after-greeting")
        
        # Modify state
        memory.add_user_message("Changed message")
        memory.set_variable("service_name", "coloring")
        
        # Restore
        success = memory.restore_from_checkpoint("after-greeting")
        
        assert success is True
        assert memory.get_last_user_message() == "Hello"
        assert memory.get_variable("service_name") == "haircut"
    
    def test_restore_nonexistent_checkpoint(self):
        """Test restoring from nonexistent checkpoint."""
        memory = WorkingMemory()
        
        success = memory.restore_from_checkpoint("nonexistent")
        
        assert success is False
    
    def test_list_checkpoints(self):
        """Test listing checkpoints."""
        memory = WorkingMemory()
        
        memory.save_checkpoint("cp-1")
        memory.save_checkpoint("cp-2")
        memory.save_checkpoint("cp-3")
        
        checkpoints = memory.list_checkpoints()
        
        assert len(checkpoints) == 3
    
    def test_clear(self):
        """Test clearing all memory."""
        memory = WorkingMemory()
        
        memory.add_message("user", "Hello")
        memory.set_variable("key", "value")
        memory.save_checkpoint("cp-1")
        
        memory.clear()
        
        assert len(memory.get_conversation_history()) == 0
        assert len(memory.get_all_variables()) == 0
        assert len(memory.list_checkpoints()) == 0
    
    def test_serialization(self):
        """Test to_dict and from_dict."""
        memory = WorkingMemory(session_id="test-session")
        
        memory.add_system_message("System prompt")
        memory.add_user_message("Hello")
        memory.add_assistant_message("Hi!")
        memory.set_variable("service", "haircut")
        memory.save_checkpoint("cp-1")
        
        # Serialize
        data = memory.to_dict()
        
        # Restore
        restored = WorkingMemory.from_dict(data)
        
        assert restored.session_id == "test-session"
        assert len(restored.get_conversation_history()) == 3
        assert restored.get_variable("service") == "haircut"
        assert len(restored.list_checkpoints()) == 1
    
    def test_workflow_recovery_scenario(self):
        """Test complete workflow recovery scenario."""
        # Simulate workflow execution
        memory = WorkingMemory(session_id="workflow-session")
        
        # Step 1: Greeting
        memory.add_user_message("Hi, I want to book an appointment")
        memory.add_assistant_message("Welcome! What service would you like?")
        memory.set_state("current_node", "greeting")
        memory.save_checkpoint("after-greeting")
        
        # Step 2: Service selection
        memory.add_user_message("I want a haircut")
        memory.add_assistant_message("Great choice! When would you like to come in?")
        memory.set_variable("service_name", "haircut")
        memory.set_state("current_node", "booking")
        memory.save_checkpoint("after-service-selection")
        
        # Simulate failure - memory would be lost
        # Instead, we serialize and restore
        data = memory.to_dict()
        
        # New process starts, restore memory
        recovered_memory = WorkingMemory.from_dict(data)
        
        # Verify recovery
        assert recovered_memory.session_id == "workflow-session"
        assert recovered_memory.get_variable("service_name") == "haircut"
        assert recovered_memory.get_state("current_node") == "booking"
        
        # Can continue from checkpoint
        recovered_memory.restore_from_checkpoint("after-service-selection")
        assert recovered_memory.get_last_user_message() == "I want a haircut"


# =============================================================================
# MEMORY FACTORY TESTS
# =============================================================================

class TestMemoryFactory:
    """Tests for MemoryFactory."""
    
    def test_create_working_memory(self):
        """Test creating working memory via factory."""
        memory = MemoryFactory.create_working_memory(
            session_id="factory-session",
            max_messages=50,
            max_checkpoints=10,
        )
        
        assert memory.session_id == "factory-session"
    
    def test_create_conversation_history(self):
        """Test creating conversation history via factory."""
        history = MemoryFactory.create_conversation_history(max_messages=100)
        
        history.add_message("user", "Test")
        assert history.get_message_count() == 1
    
    def test_create_state_tracker(self):
        """Test creating state tracker via factory."""
        tracker = MemoryFactory.create_state_tracker(
            session_id="tracker-session",
            max_checkpoints=5,
        )
        
        tracker.set_state("key", "value")
        assert tracker.get_state("key") == "value"
    
    def test_create_from_config_working(self):
        """Test creating from config - working memory."""
        memory = MemoryFactory.create_from_config({
            "type": "working",
            "session_id": "config-session",
            "max_messages": 100,
        })
        
        assert isinstance(memory, WorkingMemory)
        assert memory.session_id == "config-session"
    
    def test_create_from_config_conversation(self):
        """Test creating from config - conversation history."""
        history = MemoryFactory.create_from_config({
            "type": "conversation",
            "max_messages": 50,
        })
        
        assert isinstance(history, ConversationHistory)
    
    def test_create_from_config_state_tracker(self):
        """Test creating from config - state tracker."""
        tracker = MemoryFactory.create_from_config({
            "type": "state_tracker",
            "session_id": "tracker-session",
        })
        
        assert isinstance(tracker, InMemoryStateTracker)
    
    def test_create_from_config_invalid_type(self):
        """Test creating from config with invalid type."""
        with pytest.raises(ValueError):
            MemoryFactory.create_from_config({"type": "invalid"})
    
    def test_restore_working_memory(self):
        """Test restoring working memory."""
        original = WorkingMemory(session_id="original")
        original.add_user_message("Test")
        
        data = original.to_dict()
        restored = MemoryFactory.restore_working_memory(data)
        
        assert restored.session_id == "original"
        assert len(restored.get_conversation_history()) == 1


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestMemoryIntegration:
    """Integration tests for memory module."""
    
    def test_agent_memory_workflow(self):
        """Test memory workflow for an agent."""
        memory = WorkingMemory(session_id="agent-session")
        
        # Agent starts
        memory.add_system_message("You are a salon booking assistant.")
        
        # Conversation
        memory.add_user_message("I want to book a haircut")
        memory.set_variable("detected_intent", "booking")
        memory.set_variable("service", "haircut")
        
        memory.add_assistant_message("Great! When would you like to come in?")
        
        memory.add_user_message("Tomorrow at 2pm")
        memory.set_variable("date", "tomorrow")
        memory.set_variable("time", "2pm")
        
        # Agent needs to call LLM with full context
        llm_messages = memory.get_conversation_history()
        
        assert len(llm_messages) == 4  # system + 3 messages
        assert memory.get_variable("service") == "haircut"
    
    def test_workflow_state_recovery(self):
        """Test workflow state recovery after failure."""
        # Workflow execution
        memory = WorkingMemory(session_id="workflow-session")
        
        # Node 1: Greeting
        memory.add_user_message("Hello")
        memory.add_assistant_message("Welcome!")
        memory.set_state("current_node", "greeting")
        memory.set_state("node_status", "completed")
        memory.save_checkpoint("node-1-complete", metadata={
            "component_type": "node",
            "component_id": "greeting",
        })
        
        # Node 2: In progress when failure occurs
        memory.add_user_message("I want to book")
        memory.set_state("current_node", "booking")
        memory.set_state("node_status", "in_progress")
        
        # Simulate failure - serialize current state
        failure_state = memory.to_dict()
        
        # Recovery: restore and continue from last checkpoint
        recovered = WorkingMemory.from_dict(failure_state)
        
        # Can check current state
        assert recovered.get_state("node_status") == "in_progress"
        
        # Or restore to last known good state
        recovered.restore_from_checkpoint("node-1-complete")
        assert recovered.get_state("node_status") == "completed"
        assert recovered.get_state("current_node") == "greeting"
    
    def test_multi_agent_memory(self):
        """Test memory isolation between agents."""
        agent1_memory = WorkingMemory(session_id="agent-1")
        agent2_memory = WorkingMemory(session_id="agent-2")
        
        agent1_memory.set_variable("role", "greeter")
        agent2_memory.set_variable("role", "booker")
        
        assert agent1_memory.get_variable("role") == "greeter"
        assert agent2_memory.get_variable("role") == "booker"
        
        # They have independent state
        agent1_memory.add_user_message("Hello")
        
        assert len(agent1_memory.get_conversation_history()) == 1
        assert len(agent2_memory.get_conversation_history()) == 0


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

