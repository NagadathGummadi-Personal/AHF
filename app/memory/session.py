"""
Voice Agent Session Memory

Unified session memory combining core.memory components with
voice agent-specific extensions.

Version: 1.0.0
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from core.memory import (
    DefaultWorkingMemory,
    IWorkingMemory,
    IStateTracker,
    IConversationMemory,
)
from core.workflows.interrupt import InterruptManager

from app.config import get_settings, Defaults
from app.models.task import Task, TaskPriority
from app.models.dynamic_variables import DynamicVariables
from app.models.workflow_state import WorkflowState, StepTracker, StashedResponse

from .task_queue import VoiceAgentTaskQueue
from .checkpointer import VoiceAgentCheckpointer


class VoiceAgentSession:
    """
    Unified session memory for voice agent workflow.
    
    Integrates:
    - core.memory.WorkingMemory for conversation and state
    - VoiceAgentTaskQueue for task management
    - VoiceAgentCheckpointer for lazy checkpointing
    - InterruptManager for interrupt handling
    
    This is the primary memory interface for nodes and edges.
    """
    
    def __init__(
        self,
        session_id: Optional[str] = None,
        settings: Optional[Any] = None,
    ):
        """
        Initialize session.
        
        Args:
            session_id: Unique session identifier
            settings: Application settings
        """
        self._session_id = session_id or str(uuid.uuid4())
        self._settings = settings or get_settings()
        
        # Core working memory (conversation, state, checkpoints)
        self._working_memory = DefaultWorkingMemory(
            session_id=self._session_id,
            max_messages=self._settings.max_conversation_messages,
            max_checkpoints=self._settings.max_checkpoints,
        )
        
        # Voice agent extensions
        self._task_queue = VoiceAgentTaskQueue(
            max_size=self._settings.task_queue_max_size,
            storage_path=f"{self._settings.checkpoint_storage_path}/tasks/{self._session_id}",
        )
        
        self._checkpointer = VoiceAgentCheckpointer(
            storage_path=f"{self._settings.checkpoint_storage_path}/sessions/{self._session_id}",
            wal_enabled=self._settings.checkpoint_wal_enabled,
        )
        
        # Dynamic variables
        self._dynamic_vars: Optional[DynamicVariables] = None
        
        # Workflow state tracking
        self._workflow_state = WorkflowState(session_id=self._session_id)
        self._step_tracker = StepTracker()
        
        # Interrupt handling
        self._interrupt_manager: Optional[InterruptManager] = None
        
        # Timestamps
        self._created_at = datetime.utcnow()
        self._started = False
    
    # =========================================================================
    # Properties
    # =========================================================================
    
    @property
    def session_id(self) -> str:
        """Get session ID."""
        return self._session_id
    
    @property
    def working_memory(self) -> IWorkingMemory:
        """Get core working memory."""
        return self._working_memory
    
    @property
    def conversation(self) -> IConversationMemory:
        """Get conversation memory."""
        return self._working_memory.conversation
    
    @property
    def state_tracker(self) -> IStateTracker:
        """Get state tracker."""
        return self._working_memory.state_tracker
    
    @property
    def task_queue(self) -> VoiceAgentTaskQueue:
        """Get task queue."""
        return self._task_queue
    
    @property
    def checkpointer(self) -> VoiceAgentCheckpointer:
        """Get checkpointer."""
        return self._checkpointer
    
    @property
    def workflow_state(self) -> WorkflowState:
        """Get workflow state."""
        return self._workflow_state
    
    @property
    def step_tracker(self) -> StepTracker:
        """Get step tracker."""
        return self._step_tracker
    
    @property
    def dynamic_vars(self) -> Optional[DynamicVariables]:
        """Get dynamic variables."""
        return self._dynamic_vars
    
    # =========================================================================
    # Lifecycle
    # =========================================================================
    
    async def start(self) -> None:
        """Start session (initialize background tasks)."""
        if self._started:
            return
        
        await self._checkpointer.start()
        await self._task_queue.recover()
        self._started = True
        self._workflow_state.started_at = datetime.utcnow()
    
    async def close(self) -> None:
        """Close session and persist state."""
        await self.save_checkpoint("session_close")
        await self._checkpointer.close()
        self._started = False
    
    # =========================================================================
    # Dynamic Variables
    # =========================================================================
    
    def set_dynamic_variables(self, variables: DynamicVariables) -> None:
        """Set all dynamic variables."""
        self._dynamic_vars = variables
        
        # Also store in working memory for serialization
        for key, value in variables.to_context_dict().items():
            self._working_memory.set_variable(f"dyn_{key}", value)
    
    def get_dynamic_variable(self, key: str, default: Any = None) -> Any:
        """Get a dynamic variable."""
        if self._dynamic_vars:
            return self._dynamic_vars.get(key, default)
        return default
    
    def update_dynamic_variable(self, key: str, value: Any) -> None:
        """Update a dynamic variable."""
        if self._dynamic_vars:
            self._dynamic_vars.set(key, value)
            self._working_memory.set_variable(f"dyn_{key}", value)
    
    # =========================================================================
    # Conversation (delegates to working memory)
    # =========================================================================
    
    def add_user_message(self, content: str, **metadata) -> str:
        """Add a user message."""
        return self._working_memory.add_message("user", content, metadata)
    
    def add_assistant_message(self, content: str, **metadata) -> str:
        """Add an assistant message."""
        return self._working_memory.add_message("assistant", content, metadata)
    
    def add_tool_message(
        self,
        content: str,
        tool_name: Optional[str] = None,
        **metadata,
    ) -> str:
        """Add a tool message."""
        if tool_name:
            metadata["tool_name"] = tool_name
        return self._working_memory.add_message("tool", content, metadata)
    
    def get_llm_messages(
        self,
        max_messages: Optional[int] = None,
    ) -> List[Dict[str, str]]:
        """Get conversation history for LLM."""
        return self._working_memory.get_conversation_history(max_messages)
    
    # =========================================================================
    # Task Management
    # =========================================================================
    
    async def create_task(
        self,
        intent: str,
        original_input: str = "",
        priority: TaskPriority = TaskPriority.NORMAL,
        **kwargs,
    ) -> Task:
        """Create and enqueue a new task."""
        task = Task(
            intent=intent,
            original_input=original_input,
            session_id=self._session_id,
            priority=priority,
            **kwargs,
        )
        await self._task_queue.enqueue(task)
        self._workflow_state.queue_task(task.task_id)
        return task
    
    async def get_current_task(self) -> Optional[Task]:
        """Get the current active task."""
        return await self._task_queue.get_current_task()
    
    async def start_task(self, task_id: str) -> Optional[Task]:
        """Start a task."""
        task = await self._task_queue.get_by_id(task_id)
        if task:
            task.start()
            await self._task_queue.update(task)
            self._workflow_state.current_task_id = task_id
            return task
        return None
    
    async def complete_task(self, task_id: str) -> Optional[Task]:
        """Complete a task."""
        task = await self._task_queue.get_by_id(task_id)
        if task:
            task.complete()
            await self._task_queue.update(task)
            self._workflow_state.complete_task(task_id)
            return task
        return None
    
    def has_pending_tasks_sync(self) -> bool:
        """O(1) check for pending tasks."""
        return self._task_queue.has_pending_sync()
    
    def has_interrupt_sync(self) -> bool:
        """O(1) check for interrupt tasks."""
        return self._task_queue.has_interrupt_sync()
    
    # =========================================================================
    # Workflow State
    # =========================================================================
    
    def move_to_node(self, node_id: str) -> None:
        """Move to a new workflow node."""
        self._workflow_state.move_to_node(node_id)
    
    def get_current_node(self) -> Optional[str]:
        """Get current node ID."""
        return self._workflow_state.current_node_id
    
    def set_workflow_variable(self, key: str, value: Any) -> None:
        """Set a workflow variable."""
        self._workflow_state.set_variable(key, value)
        self._working_memory.set_variable(key, value)
    
    def get_workflow_variable(self, key: str, default: Any = None) -> Any:
        """Get a workflow variable."""
        return self._workflow_state.get_variable(key, default)
    
    # =========================================================================
    # Step Tracking
    # =========================================================================
    
    def register_step(self, step_id: str) -> None:
        """Register a workflow step."""
        self._step_tracker.register_step(step_id)
    
    def start_step(self, step_id: str) -> None:
        """Start a step."""
        self._step_tracker.start_step(step_id)
    
    def complete_step(self, step_id: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Complete a step."""
        self._step_tracker.complete_step(step_id, data)
    
    def is_step_completed(self, step_id: str) -> bool:
        """Check if step is completed."""
        return self._step_tracker.is_step_completed(step_id)
    
    # =========================================================================
    # Interrupt Handling
    # =========================================================================
    
    def is_interrupted(self) -> bool:
        """Check if session is interrupted."""
        return self._workflow_state.is_interrupted
    
    def stash_response(
        self,
        content: str,
        interrupt_message: str,
        **kwargs,
    ) -> None:
        """Stash current response for interrupt."""
        self._workflow_state.stash_response(content, interrupt_message, **kwargs)
    
    def get_stashed_context(self) -> Optional[str]:
        """Get context from stashed response."""
        stashed = self._workflow_state.clear_interrupt()
        if stashed:
            return stashed.get_continuation_context()
        return None
    
    # =========================================================================
    # Checkpointing
    # =========================================================================
    
    async def save_checkpoint(
        self,
        checkpoint_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Save a checkpoint of current state."""
        cp_id = checkpoint_id or f"cp_{datetime.utcnow().timestamp()}"
        
        state_data = {
            "session_id": self._session_id,
            "working_memory": self._working_memory.to_dict(),
            "workflow_state": self._workflow_state.to_checkpoint_data(),
            "step_tracker": self._step_tracker.model_dump(mode="json"),
            "dynamic_vars": self._dynamic_vars.model_dump(mode="json") if self._dynamic_vars else None,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        return await self._checkpointer.save_checkpoint(cp_id, state_data, metadata)
    
    async def restore_from_checkpoint(self, checkpoint_id: str) -> bool:
        """Restore from checkpoint."""
        data = await self._checkpointer.get_checkpoint(checkpoint_id)
        if not data:
            return False
        
        try:
            # Restore working memory
            if "working_memory" in data:
                self._working_memory = DefaultWorkingMemory.from_dict(data["working_memory"])
            
            # Restore workflow state
            if "workflow_state" in data:
                self._workflow_state = WorkflowState.from_checkpoint_data(data["workflow_state"])
            
            # Restore step tracker
            if "step_tracker" in data:
                self._step_tracker = StepTracker(**data["step_tracker"])
            
            # Restore dynamic vars
            if data.get("dynamic_vars"):
                self._dynamic_vars = DynamicVariables(**data["dynamic_vars"])
            
            return True
        except Exception:
            return False
    
    # =========================================================================
    # Serialization
    # =========================================================================
    
    def to_dict(self) -> Dict[str, Any]:
        """Export session to dictionary."""
        return {
            "session_id": self._session_id,
            "working_memory": self._working_memory.to_dict(),
            "workflow_state": self._workflow_state.model_dump(mode="json"),
            "step_tracker": self._step_tracker.model_dump(mode="json"),
            "dynamic_vars": self._dynamic_vars.model_dump(mode="json") if self._dynamic_vars else None,
            "created_at": self._created_at.isoformat(),
        }


async def create_session(
    session_id: Optional[str] = None,
    **kwargs,
) -> VoiceAgentSession:
    """
    Create and initialize a session.
    
    This is the recommended way to create VoiceAgentSession
    as it properly initializes background tasks.
    """
    session = VoiceAgentSession(session_id=session_id, **kwargs)
    await session.start()
    return session

