"""
Base Task Queue Implementation.

Abstract base class for task queue implementations.

Version: 1.0.0
"""

from abc import ABC, abstractmethod
import asyncio
import heapq
from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar

from ..interfaces import ITask, ITaskQueue


T = TypeVar("T", bound=ITask)


class BaseTaskQueue(ABC, Generic[T]):
    """
    Abstract base class for task queues.
    
    Provides common functionality for task queueing with
    priority-based ordering and O(1) pending checks.
    
    Extend this class to create custom task queue implementations
    (e.g., Redis-backed, persistent, distributed).
    
    Example:
        class RedisTaskQueue(BaseTaskQueue[MyTask]):
            def __init__(self, redis_client):
                super().__init__()
                self.redis = redis_client
            
            async def _persist_task(self, task):
                await self.redis.hset("tasks", task.task_id, task.to_dict())
    """
    
    def __init__(
        self,
        max_size: int = 100,
    ):
        """
        Initialize task queue.
        
        Args:
            max_size: Maximum queue size
        """
        self._max_size = max_size
        self._lock = asyncio.Lock()
        
        # Task storage - subclasses may override
        self._tasks: Dict[str, T] = {}
        
        # Priority heap for ordering
        self._heap: List[tuple] = []  # (priority, timestamp, task_id)
        
        # O(1) counters
        self._pending_count = 0
    
    # =========================================================================
    # Abstract Methods - Must be implemented by subclasses
    # =========================================================================
    
    @abstractmethod
    async def _persist_task(self, task: T) -> None:
        """Persist a task (for durable queues)."""
        ...
    
    @abstractmethod
    async def _remove_persisted_task(self, task_id: str) -> None:
        """Remove a persisted task."""
        ...
    
    @abstractmethod
    async def _load_tasks(self) -> List[T]:
        """Load all persisted tasks (for recovery)."""
        ...
    
    # =========================================================================
    # ITaskQueue Implementation
    # =========================================================================
    
    async def enqueue(self, task: T) -> str:
        """Add a task to the queue."""
        async with self._lock:
            # Check capacity
            if len(self._tasks) >= self._max_size:
                await self._cleanup_completed()
            
            # Store task
            self._tasks[task.task_id] = task
            
            # Add to heap if pending
            if self._is_pending_state(task.state):
                heapq.heappush(
                    self._heap,
                    (-task.priority, datetime.utcnow().timestamp(), task.task_id)
                )
                self._pending_count += 1
            
            # Persist
            await self._persist_task(task)
            
            return task.task_id
    
    async def dequeue(self) -> Optional[T]:
        """Remove and return highest priority task."""
        async with self._lock:
            while self._heap:
                _, _, task_id = heapq.heappop(self._heap)
                task = self._tasks.get(task_id)
                
                if task and self._is_pending_state(task.state):
                    self._pending_count = max(0, self._pending_count - 1)
                    return task
            
            return None
    
    async def peek(self) -> Optional[T]:
        """Return highest priority task without removing."""
        async with self._lock:
            for _, _, task_id in sorted(self._heap):
                task = self._tasks.get(task_id)
                if task and self._is_pending_state(task.state):
                    return task
            return None
    
    async def get_by_id(self, task_id: str) -> Optional[T]:
        """Get a task by ID."""
        async with self._lock:
            return self._tasks.get(task_id)
    
    async def update(self, task: T) -> None:
        """Update an existing task."""
        async with self._lock:
            old_task = self._tasks.get(task.task_id)
            
            if old_task:
                # Update pending count if state changed
                was_pending = self._is_pending_state(old_task.state)
                is_pending = self._is_pending_state(task.state)
                
                if was_pending and not is_pending:
                    self._pending_count = max(0, self._pending_count - 1)
                elif not was_pending and is_pending:
                    self._pending_count += 1
                    heapq.heappush(
                        self._heap,
                        (-task.priority, datetime.utcnow().timestamp(), task.task_id)
                    )
            
            self._tasks[task.task_id] = task
            await self._persist_task(task)
    
    async def remove(self, task_id: str) -> bool:
        """Remove a task by ID."""
        async with self._lock:
            task = self._tasks.pop(task_id, None)
            if task:
                if self._is_pending_state(task.state):
                    self._pending_count = max(0, self._pending_count - 1)
                await self._remove_persisted_task(task_id)
                return True
            return False
    
    def has_pending_sync(self) -> bool:
        """Synchronous O(1) check for pending tasks."""
        return self._pending_count > 0
    
    async def has_pending(self) -> bool:
        """Check if there are pending tasks."""
        return self._pending_count > 0
    
    async def get_pending_count(self) -> int:
        """Get count of pending tasks."""
        return self._pending_count
    
    async def get_all_pending(self) -> List[T]:
        """Get all pending tasks in priority order."""
        async with self._lock:
            pending = [
                self._tasks[task_id]
                for _, _, task_id in sorted(self._heap)
                if task_id in self._tasks
                and self._is_pending_state(self._tasks[task_id].state)
            ]
            return pending
    
    async def clear(self) -> None:
        """Clear all tasks."""
        async with self._lock:
            for task_id in list(self._tasks.keys()):
                await self._remove_persisted_task(task_id)
            
            self._tasks.clear()
            self._heap.clear()
            self._pending_count = 0
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def _is_pending_state(self, state: str) -> bool:
        """Check if state is a pending state."""
        return state in ("pending", "in_progress")
    
    async def _cleanup_completed(self) -> None:
        """Remove completed tasks to make room."""
        completed = [
            task_id for task_id, task in self._tasks.items()
            if task.state in ("completed", "failed", "cancelled")
        ]
        for task_id in completed[:10]:
            await self.remove(task_id)
    
    async def recover(self) -> None:
        """Recover tasks from persistence."""
        tasks = await self._load_tasks()
        for task in tasks:
            self._tasks[task.task_id] = task
            if self._is_pending_state(task.state):
                heapq.heappush(
                    self._heap,
                    (-task.priority, datetime.utcnow().timestamp(), task.task_id)
                )
                self._pending_count += 1

