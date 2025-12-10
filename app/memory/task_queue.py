"""
Voice Agent Task Queue

Custom task queue implementation for the voice agent workflow.
Extends BaseTaskQueue from core.memory.

Version: 1.0.0
"""

from typing import Any, Dict, List, Optional
import json
from pathlib import Path

from core.memory import BaseTaskQueue, ITask
from app.models.task import Task


class VoiceAgentTaskQueue(BaseTaskQueue[Task]):
    """
    Voice agent-specific task queue.
    
    Extends BaseTaskQueue with:
    - Local file persistence for development
    - Interrupt priority detection
    - Task pause/resume support
    
    In production, override _persist_task etc. for Redis/database.
    """
    
    def __init__(
        self,
        max_size: int = 100,
        storage_path: Optional[str] = None,
    ):
        """
        Initialize task queue.
        
        Args:
            max_size: Maximum queue size
            storage_path: Path for local persistence (None for in-memory only)
        """
        super().__init__(max_size=max_size)
        
        self._storage_path = Path(storage_path) if storage_path else None
        if self._storage_path:
            self._storage_path.mkdir(parents=True, exist_ok=True)
    
    # =========================================================================
    # Override Abstract Methods
    # =========================================================================
    
    async def _persist_task(self, task: Task) -> None:
        """Persist task to local file."""
        if not self._storage_path:
            return
        
        task_file = self._storage_path / f"{task.task_id}.json"
        try:
            with open(task_file, "w") as f:
                json.dump(task.model_dump(mode="json"), f)
        except Exception:
            pass  # Log in production
    
    async def _remove_persisted_task(self, task_id: str) -> None:
        """Remove persisted task file."""
        if not self._storage_path:
            return
        
        task_file = self._storage_path / f"{task_id}.json"
        if task_file.exists():
            task_file.unlink()
    
    async def _load_tasks(self) -> List[Task]:
        """Load all persisted tasks."""
        if not self._storage_path:
            return []
        
        tasks = []
        for task_file in self._storage_path.glob("*.json"):
            try:
                with open(task_file, "r") as f:
                    data = json.load(f)
                    tasks.append(Task(**data))
            except Exception:
                pass  # Log in production
        
        return tasks
    
    # =========================================================================
    # Voice Agent Specific Methods
    # =========================================================================
    
    def has_interrupt_sync(self) -> bool:
        """
        Synchronous O(1) check for interrupt priority tasks.
        
        Returns:
            True if there are interrupt priority tasks
        """
        # Check if any task has interrupt priority (3)
        for task in self._tasks.values():
            if task.priority.value == 3 and self._is_pending_state(task.state):
                return True
        return False
    
    async def pause_task(
        self,
        task_id: str,
        reason: Optional[str] = None,
    ) -> bool:
        """
        Pause a task for later resumption.
        
        Args:
            task_id: Task to pause
            reason: Reason for pausing
            
        Returns:
            True if paused
        """
        async with self._lock:
            task = self._tasks.get(task_id)
            if task and task.state == "in_progress":
                task.pause(reason=reason)
                await self._persist_task(task)
                self._pending_count = max(0, self._pending_count - 1)
                return True
            return False
    
    async def resume_task(self, task_id: str) -> bool:
        """
        Resume a paused task.
        
        Args:
            task_id: Task to resume
            
        Returns:
            True if resumed
        """
        async with self._lock:
            task = self._tasks.get(task_id)
            if task and task.state == "paused":
                task.resume()
                await self._persist_task(task)
                self._pending_count += 1
                return True
            return False
    
    async def get_current_task(self) -> Optional[Task]:
        """Get the currently active (in_progress) task."""
        async with self._lock:
            for task in self._tasks.values():
                if task.state == "in_progress":
                    return task
            return None
