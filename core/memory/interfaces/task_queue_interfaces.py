"""
Task Queue Interfaces.

Defines protocols for task queue management used by workflows.
A task represents a discrete unit of work (e.g., user request, sub-task).

Version: 1.0.0
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


@runtime_checkable
class ITask(Protocol):
    """
    Protocol for a task/work item.
    
    A task represents a discrete unit of work that can be
    queued, prioritized, and processed.
    """
    
    @property
    def task_id(self) -> str:
        """Unique task identifier."""
        ...
    
    @property
    def priority(self) -> int:
        """Task priority (higher = more urgent)."""
        ...
    
    @property
    def state(self) -> str:
        """Task state (pending, in_progress, completed, etc.)."""
        ...
    
    def to_dict(self) -> Dict[str, Any]:
        """Export task to dictionary."""
        ...


@runtime_checkable
class ITaskQueue(Protocol):
    """
    Protocol for task queue management.
    
    Provides priority-based task queuing with O(1) interrupt detection.
    Used by workflows to manage user requests and sub-tasks.
    
    Key Requirements:
    - O(1) has_pending() for interrupt detection
    - Priority-based ordering
    - Task lookup by ID
    """
    
    async def enqueue(self, task: ITask) -> str:
        """
        Add a task to the queue.
        
        Args:
            task: Task to enqueue
            
        Returns:
            Task ID
        """
        ...
    
    async def dequeue(self) -> Optional[ITask]:
        """
        Remove and return the highest priority task.
        
        Returns:
            Task or None if queue is empty
        """
        ...
    
    async def peek(self) -> Optional[ITask]:
        """
        Return highest priority task without removing it.
        
        Returns:
            Task or None if queue is empty
        """
        ...
    
    async def get_by_id(self, task_id: str) -> Optional[ITask]:
        """
        Get a task by ID.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Task or None if not found
        """
        ...
    
    async def update(self, task: ITask) -> None:
        """
        Update an existing task.
        
        Args:
            task: Task with updated values
        """
        ...
    
    async def remove(self, task_id: str) -> bool:
        """
        Remove a task by ID.
        
        Args:
            task_id: Task identifier
            
        Returns:
            True if removed, False if not found
        """
        ...
    
    def has_pending_sync(self) -> bool:
        """
        Synchronous O(1) check for pending tasks.
        
        Used for interrupt detection without async overhead.
        
        Returns:
            True if there are pending tasks
        """
        ...
    
    async def has_pending(self) -> bool:
        """
        Check if there are pending tasks.
        
        Returns:
            True if there are pending tasks
        """
        ...
    
    async def get_pending_count(self) -> int:
        """
        Get count of pending tasks.
        
        Returns:
            Number of pending tasks
        """
        ...
    
    async def get_all_pending(self) -> List[ITask]:
        """
        Get all pending tasks in priority order.
        
        Returns:
            List of pending tasks
        """
        ...
    
    async def clear(self) -> None:
        """Clear all tasks from queue."""
        ...


@runtime_checkable
class ICheckpointer(Protocol):
    """
    Protocol for workflow checkpointing.
    
    Supports lazy checkpointing with Write-Ahead Log (WAL)
    for minimal latency impact.
    
    Design Goals:
    - save_checkpoint() returns immediately (O(1))
    - Persistence happens asynchronously
    - Recovery from WAL on startup
    """
    
    async def save_checkpoint(
        self,
        checkpoint_id: str,
        state: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Save a checkpoint.
        
        This should return immediately for lazy checkpointing.
        Actual persistence may happen asynchronously.
        
        Args:
            checkpoint_id: Unique checkpoint identifier
            state: State data to checkpoint
            metadata: Optional metadata
            
        Returns:
            Checkpoint ID
        """
        ...
    
    async def get_checkpoint(
        self,
        checkpoint_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get a checkpoint by ID.
        
        Args:
            checkpoint_id: Checkpoint identifier
            
        Returns:
            Checkpoint data or None if not found
        """
        ...
    
    async def get_latest_checkpoint(self) -> Optional[Dict[str, Any]]:
        """
        Get the most recent checkpoint.
        
        Returns:
            Latest checkpoint data or None
        """
        ...
    
    async def list_checkpoints(
        self,
        limit: Optional[int] = None,
    ) -> List[str]:
        """
        List checkpoint IDs in order (newest first).
        
        Args:
            limit: Maximum checkpoints to return
            
        Returns:
            List of checkpoint IDs
        """
        ...
    
    async def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """
        Delete a checkpoint.
        
        Args:
            checkpoint_id: Checkpoint identifier
            
        Returns:
            True if deleted
        """
        ...
    
    async def flush(self) -> None:
        """
        Force flush any pending writes to storage.
        
        Use this to ensure all checkpoints are persisted
        before shutdown.
        """
        ...
    
    async def close(self) -> None:
        """
        Close the checkpointer.
        
        Flushes pending writes and releases resources.
        """
        ...


@runtime_checkable
class IInterruptHandler(Protocol):
    """
    Protocol for interrupt handling.
    
    Manages workflow interrupts, response stashing,
    and context preservation.
    """
    
    async def trigger_interrupt(
        self,
        reason: str,
        user_message: Optional[str] = None,
    ) -> None:
        """
        Trigger an interrupt.
        
        Args:
            reason: Reason for interrupt
            user_message: User message that caused interrupt
        """
        ...
    
    async def stash_response(
        self,
        content: str,
        node_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Stash a partial response during interrupt.
        
        Args:
            content: Partial response content
            node_id: Node that was generating response
            metadata: Additional metadata
            
        Returns:
            Stash ID
        """
        ...
    
    async def get_stashed_response(self) -> Optional[Dict[str, Any]]:
        """
        Get the stashed response.
        
        Returns:
            Stashed response data or None
        """
        ...
    
    async def clear_interrupt(self) -> Optional[Dict[str, Any]]:
        """
        Clear interrupt state.
        
        Returns:
            Stashed response if any
        """
        ...
    
    def is_interrupted(self) -> bool:
        """
        Check if currently interrupted.
        
        Returns:
            True if in interrupt state
        """
        ...

