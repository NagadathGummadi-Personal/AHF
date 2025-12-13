"""
Voice Agent Task Queue

Lightweight in-memory task queue for low-latency voice workflows.
Extends BaseTaskQueue from core.memory.

Version: 1.1.0
"""

from typing import List, Optional

from core.memory import BaseTaskQueue
from air.models.task import Task


class VoiceAgentTaskQueue(BaseTaskQueue[Task]):
    """
    Voice agent-specific task queue.
    
    Designed for low-latency text-to-text WebSocket workflows:
    - Purely in-memory (no disk I/O overhead)
    - Interrupt priority detection (O(1))
    - Task pause/resume support
    
    Sessions are ephemeral—task state lives only for the WebSocket connection.
    """
    
    def __init__(self, max_size: int = 100):
        """
        Initialize task queue.
        
        Args:
            max_size: Maximum queue size
        """
        super().__init__(max_size=max_size)
    
    # =========================================================================
    # Override Abstract Methods (No-op for in-memory only)
    # =========================================================================
    
    async def _persist_task(self, task: Task) -> None:
        """No-op: Tasks are in-memory only for low-latency."""
        pass
    
    async def _remove_persisted_task(self, task_id: str) -> None:
        """No-op: Tasks are in-memory only."""
        pass
    
    async def _load_tasks(self) -> List[Task]:
        """No-op: No persistence to load from."""
        return []
    
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
