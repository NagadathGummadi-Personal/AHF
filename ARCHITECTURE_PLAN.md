# AHF Workflow Enhancement Architecture Plan

## Executive Summary

This document outlines the plan to enhance the AHF workflow system with **core infrastructure** components:

1. **Task Queue Manager** - Non-blocking user input handling & interrupt detection
2. **Transaction Manager + Lazy Checkpoints** - Zero-latency checkpointing & rollback

> **Note:** The following are implemented as **agent/tool nodes** within workflows (not infrastructure):
> - Intent/Slot Classification
> - Clarification Flow
> - Service Match Handler
> - Flow Router
> - Policy Engine
> - Handover Manager
> - Deviation Handler

The design prioritizes **zero additional latency** by using async queues, background processing, and lazy persistence.

---

## Current State Analysis

### ✅ What You Have
| Component | Status | Location |
|-----------|--------|----------|
| Workflow Nodes/Edges | ✅ Complete | `core/workflows/spec/` |
| Agent Execution | ✅ Complete | `core/agents/` |
| LLM Conditions | ✅ Complete | `core/workflows/spec/edge_models.py` |
| Pass-Through Fields | ✅ Complete | `EdgeSpec.extract_pass_through_fields()` |
| Working Memory | ✅ Complete | `core/memory/working_memory/` |
| Basic Checkpoints | ✅ Complete | `WorkingMemory.save_checkpoint()` |
| Interrupt Handling | ✅ Basic | `core/workflows/interrupt/` |
| Metrics Logging | ✅ Complete | `utils/logging/` |

### ❌ Infrastructure Gaps
| Component | Priority | Impact |
|-----------|----------|--------|
| Task Queue Manager | 🔴 Critical | User input queuing without blocking |
| Lazy Checkpoint System | 🔴 Critical | Zero-latency checkpointing |
| Transaction Manager | 🔴 Critical | Rollback/compensation support |

---

## Proposed Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       AHF Core Infrastructure Layer                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                        TaskQueueManager                                 │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────────┐  │ │
│  │  │  Priority   │  │  Observer   │  │  Interrupt  │  │   Background  │  │ │
│  │  │    Heap     │  │   Pattern   │  │    Check    │  │   Processor   │  │ │
│  │  │   O(log n)  │  │             │  │    O(1)     │  │               │  │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────────┘  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                    │                                         │
│                                    ▼                                         │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                       TransactionManager                                │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────────┐  │ │
│  │  │    Lazy     │  │   Write-    │  │  Rollback   │  │  Compensation │  │ │
│  │  │ Checkpoint  │  │   Ahead     │  │   Handler   │  │    Actions    │  │ │
│  │  │    O(1)     │  │    Log      │  │             │  │               │  │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────────┘  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Workflow Execution Layer (Existing)                     │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  Nodes (Agent/Tool)  │  Edges (Conditions)  │  Working Memory           ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
│  Agent/Tool Nodes handle: Intent Classification, Clarification,             │
│  Service Matching, Policy, Handover, Deviation - via workflow configuration │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Module 1: Task Queue Manager

### Purpose
Handle user input queuing without blocking workflow execution. Critical for:
- Processing multiple user messages during long operations
- Handling interrupts gracefully
- Enabling "fire and forget" user input

### Directory Structure
```
core/workflows/
└── taskqueue/
    ├── __init__.py
    ├── interfaces.py       # ITaskQueue, ITask protocols
    ├── models.py          # Task, TaskState, TaskPriority models
    ├── manager.py         # TaskQueueManager implementation
    ├── processors.py      # Task processors
    └── storage/
        ├── __init__.py
        ├── memory.py      # In-memory queue (default)
        └── redis.py       # Redis-backed queue (optional)
```

### Key Interfaces

```python
# core/workflows/taskqueue/interfaces.py
from typing import Protocol, Any, Optional, List
from enum import Enum
from datetime import datetime

class TaskPriority(Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    INTERRUPT = 3  # User interrupt - highest priority

class TaskState(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ITask(Protocol):
    """Protocol for a queued task."""
    id: str
    task_type: str  # "user_message", "tool_result", "interrupt"
    payload: Any
    priority: TaskPriority
    state: TaskState
    created_at: datetime
    workflow_id: str
    session_id: str

class ITaskQueue(Protocol):
    """Protocol for task queue operations."""
    
    async def enqueue(
        self,
        task_type: str,
        payload: Any,
        priority: TaskPriority = TaskPriority.NORMAL,
        workflow_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> str:
        """Add task to queue, returns task_id. O(log n)"""
        ...
    
    async def dequeue(self, workflow_id: str) -> Optional[ITask]:
        """Get next task for workflow (non-blocking). O(log n)"""
        ...
    
    async def peek(self, workflow_id: str) -> Optional[ITask]:
        """View next task without removing. O(1)"""
        ...
    
    async def has_pending(self, workflow_id: str) -> bool:
        """Check if workflow has pending tasks. O(1)"""
        ...
    
    async def check_for_interrupt(self, workflow_id: str) -> Optional[ITask]:
        """Quick check for interrupt tasks. O(1)"""
        ...
    
    async def get_by_priority(
        self, 
        workflow_id: str, 
        min_priority: TaskPriority
    ) -> List[ITask]:
        """Get all tasks at or above priority."""
        ...
    
    def subscribe(
        self,
        workflow_id: str,
        callback: Callable[[ITask], Awaitable[None]]
    ) -> None:
        """Subscribe to new tasks for a workflow."""
        ...
```

### Task Model

```python
# core/workflows/taskqueue/models.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any, Dict, Optional
import uuid

class Task(BaseModel):
    """A queued task for workflow processing."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_type: str = Field(..., description="Type: user_message, tool_result, interrupt, clarification_response")
    payload: Any = Field(..., description="Task payload (message, result, etc.)")
    priority: TaskPriority = Field(default=TaskPriority.NORMAL)
    state: TaskState = Field(default=TaskState.PENDING)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = Field(default=None)
    
    # Context
    workflow_id: str = Field(..., description="Associated workflow")
    session_id: str = Field(..., description="User session")
    node_id: Optional[str] = Field(default=None, description="Current node when created")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    retry_count: int = Field(default=0)
    max_retries: int = Field(default=3)
    
    # Ordering
    sequence_number: int = Field(default=0, description="Order within same priority")
```

### TaskQueueManager Implementation

```python
# core/workflows/taskqueue/manager.py
import asyncio
from collections import defaultdict
from typing import Dict, List, Optional, Callable, Awaitable, Any
from heapq import heappush, heappop
from datetime import datetime
from threading import Lock

from .interfaces import ITaskQueue, TaskPriority, TaskState
from .models import Task


class TaskQueueManager(ITaskQueue):
    """
    Zero-latency task queue manager.
    
    Design principles:
    1. Enqueueing is O(log n) - never blocks workflow
    2. Background processor handles persistence
    3. In-memory queue with optional persistence
    4. Priority-based processing with INTERRUPT > HIGH > NORMAL > LOW
    
    Usage:
        queue = TaskQueueManager()
        
        # Enqueue user message
        task_id = await queue.enqueue(
            task_type="user_message",
            payload={"content": "Book a haircut"},
            workflow_id="salon-workflow",
            session_id="user-123",
        )
        
        # Check for interrupts during streaming (O(1))
        async for chunk in llm.stream(...):
            if await queue.check_for_interrupt(workflow_id):
                break
            yield chunk
        
        # Process next task
        task = await queue.dequeue(workflow_id)
    """
    
    def __init__(
        self,
        persist_enabled: bool = False,
        persist_interval_ms: int = 100,
        max_queue_size: int = 10000,
    ):
        # Priority queues per workflow (heap-based)
        self._queues: Dict[str, List[tuple]] = defaultdict(list)
        self._task_map: Dict[str, Task] = {}  # Quick lookup by task_id
        self._sequence_counter: int = 0
        self._lock = Lock()
        
        # Observers for new tasks (fire-and-forget notifications)
        self._observers: Dict[str, List[Callable[[Task], Awaitable[None]]]] = defaultdict(list)
        
        # Background persistence (optional, non-blocking)
        self._persist_enabled = persist_enabled
        self._persist_interval_ms = persist_interval_ms
        self._dirty_tasks: List[str] = []
        self._persist_task: Optional[asyncio.Task] = None
        
        # Limits
        self._max_queue_size = max_queue_size
        
    async def enqueue(
        self,
        task_type: str,
        payload: Any,
        priority: TaskPriority = TaskPriority.NORMAL,
        workflow_id: str = "default",
        session_id: str = "default",
        node_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Enqueue a task - O(log n), non-blocking.
        
        Priority order (heap uses negative for max-heap behavior):
        - INTERRUPT: -3 (processed first)
        - HIGH: -2  
        - NORMAL: -1
        - LOW: 0
        """
        with self._lock:
            self._sequence_counter += 1
            seq = self._sequence_counter
        
        task = Task(
            task_type=task_type,
            payload=payload,
            priority=priority,
            workflow_id=workflow_id,
            session_id=session_id,
            node_id=node_id,
            sequence_number=seq,
            metadata=metadata or {},
        )
        
        # Heap entry: (priority_value, sequence_number, task_id)
        # Use negative priority for max-heap behavior (higher priority first)
        # Sequence number ensures FIFO within same priority
        heap_entry = (-priority.value, seq, task.id)
        
        with self._lock:
            heappush(self._queues[workflow_id], heap_entry)
            self._task_map[task.id] = task
        
        # Mark for async persistence (non-blocking)
        if self._persist_enabled:
            self._dirty_tasks.append(task.id)
            self._ensure_background_worker()
        
        # Notify observers (fire and forget - don't await)
        for observer in self._observers.get(workflow_id, []):
            asyncio.create_task(self._safe_notify(observer, task))
        
        return task.id
    
    async def _safe_notify(self, observer: Callable, task: Task):
        """Safely notify observer without blocking or crashing."""
        try:
            await observer(task)
        except Exception:
            pass  # Don't let observer errors affect queue
    
    async def dequeue(self, workflow_id: str) -> Optional[Task]:
        """Get and remove next task - O(log n)."""
        with self._lock:
            queue = self._queues.get(workflow_id)
            if not queue:
                return None
            
            _, _, task_id = heappop(queue)
            task = self._task_map.pop(task_id, None)
        
        if task:
            task.state = TaskState.PROCESSING
            task.processed_at = datetime.utcnow()
        
        return task
    
    async def peek(self, workflow_id: str) -> Optional[Task]:
        """View next task without removing - O(1)."""
        with self._lock:
            queue = self._queues.get(workflow_id)
            if not queue:
                return None
            
            _, _, task_id = queue[0]
            return self._task_map.get(task_id)
    
    async def has_pending(self, workflow_id: str) -> bool:
        """Check if workflow has pending tasks - O(1)."""
        with self._lock:
            queue = self._queues.get(workflow_id)
            return bool(queue and len(queue) > 0)
    
    async def check_for_interrupt(self, workflow_id: str) -> Optional[Task]:
        """
        Quick check for interrupt tasks - O(1).
        
        This is the key method for zero-latency interrupt detection.
        Call this during streaming to detect user interrupts.
        
        Example:
            async for chunk in llm.stream(...):
                interrupt = await queue.check_for_interrupt(workflow_id)
                if interrupt:
                    # Handle interrupt
                    manager.stash_partial_response(accumulated)
                    break
                yield chunk
        """
        with self._lock:
            queue = self._queues.get(workflow_id)
            if not queue:
                return None
            
            # Peek at top of heap
            priority_val, _, task_id = queue[0]
            
            # Check if it's an interrupt (priority -3)
            if priority_val == -TaskPriority.INTERRUPT.value:
                return self._task_map.get(task_id)
        
        return None
    
    async def get_by_priority(
        self, 
        workflow_id: str, 
        min_priority: TaskPriority
    ) -> List[Task]:
        """Get all tasks at or above specified priority."""
        with self._lock:
            queue = self._queues.get(workflow_id, [])
            tasks = []
            
            for priority_val, _, task_id in queue:
                # Remember: we use negative values, so higher priority = more negative
                if -priority_val >= min_priority.value:
                    task = self._task_map.get(task_id)
                    if task:
                        tasks.append(task)
            
            return tasks
    
    def subscribe(
        self, 
        workflow_id: str, 
        callback: Callable[[Task], Awaitable[None]]
    ) -> None:
        """Subscribe to new tasks for a workflow."""
        self._observers[workflow_id].append(callback)
    
    def unsubscribe(
        self,
        workflow_id: str,
        callback: Callable[[Task], Awaitable[None]]
    ) -> None:
        """Unsubscribe from workflow tasks."""
        if callback in self._observers.get(workflow_id, []):
            self._observers[workflow_id].remove(callback)
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending task."""
        with self._lock:
            task = self._task_map.get(task_id)
            if task and task.state == TaskState.PENDING:
                task.state = TaskState.CANCELLED
                return True
        return False
    
    async def clear_workflow(self, workflow_id: str) -> int:
        """Clear all pending tasks for a workflow. Returns count cleared."""
        with self._lock:
            queue = self._queues.get(workflow_id, [])
            count = len(queue)
            
            # Remove from task map
            for _, _, task_id in queue:
                self._task_map.pop(task_id, None)
            
            # Clear queue
            self._queues[workflow_id] = []
            
            return count
    
    def get_queue_size(self, workflow_id: str) -> int:
        """Get current queue size for a workflow."""
        with self._lock:
            return len(self._queues.get(workflow_id, []))
    
    def get_total_size(self) -> int:
        """Get total tasks across all workflows."""
        with self._lock:
            return sum(len(q) for q in self._queues.values())
    
    # =========================================================================
    # Background Persistence (Optional)
    # =========================================================================
    
    def _ensure_background_worker(self):
        """Ensure background persistence worker is running."""
        if self._persist_task is None or self._persist_task.done():
            self._persist_task = asyncio.create_task(self._background_persist())
    
    async def _background_persist(self):
        """Background worker for lazy task persistence."""
        while self._dirty_tasks:
            await asyncio.sleep(self._persist_interval_ms / 1000.0)
            
            # Collect dirty tasks
            with self._lock:
                to_persist = self._dirty_tasks.copy()
                self._dirty_tasks.clear()
            
            # Persist (implement based on storage backend)
            for task_id in to_persist:
                task = self._task_map.get(task_id)
                if task:
                    await self._persist_task_to_storage(task)
    
    async def _persist_task_to_storage(self, task: Task):
        """Persist a task to storage backend. Override for custom storage."""
        pass  # Default: no persistence
```

### Integration with WorkflowExecutionContext

```python
# Add to core/workflows/spec/workflow_models.py

class WorkflowExecutionContext(BaseModel):
    # ... existing fields ...
    
    # Task queue reference (set at runtime)
    _task_queue: Optional[Any] = PrivateAttr(default=None)
    
    def set_task_queue(self, queue: 'ITaskQueue') -> None:
        """Set the task queue for this execution context."""
        self._task_queue = queue
    
    async def check_for_user_input(self) -> Optional['Task']:
        """Check for pending user input without blocking."""
        if self._task_queue:
            return await self._task_queue.peek(self.workflow_id)
        return None
    
    async def check_for_interrupt(self) -> Optional['Task']:
        """Check for interrupt tasks - O(1)."""
        if self._task_queue:
            return await self._task_queue.check_for_interrupt(self.workflow_id)
        return None
    
    async def enqueue_user_message(self, message: str, **kwargs) -> str:
        """Enqueue a user message for processing."""
        if self._task_queue:
            return await self._task_queue.enqueue(
                task_type="user_message",
                payload={"content": message},
                workflow_id=self.workflow_id,
                **kwargs
            )
        raise RuntimeError("Task queue not configured")
    
    async def enqueue_interrupt(self, message: str, **kwargs) -> str:
        """Enqueue an interrupt (highest priority)."""
        if self._task_queue:
            return await self._task_queue.enqueue(
                task_type="interrupt",
                payload={"content": message},
                priority=TaskPriority.INTERRUPT,
                workflow_id=self.workflow_id,
                **kwargs
            )
        raise RuntimeError("Task queue not configured")
```

---

## Module 2: Transaction Manager + Lazy Checkpoints

### Purpose
Handle transactional operations with proper rollback and **zero-latency checkpointing**.

Key features:
- Checkpoint creation is O(1) - in-memory only
- Background persistence (lazy, batched)
- WAL (Write-Ahead Log) for crash recovery
- Compensation actions for rollback

### Directory Structure
```
core/workflows/
└── transactions/
    ├── __init__.py
    ├── interfaces.py           # ICheckpointManager, ITransaction
    ├── models.py              # Checkpoint, CompensationAction
    ├── manager.py             # TransactionManager
    ├── checkpoints/
    │   ├── __init__.py
    │   ├── lazy_checkpoint.py  # LazyCheckpointManager
    │   ├── wal.py             # Write-ahead log
    │   └── recovery.py        # Recovery utilities
    └── compensation/
        ├── __init__.py
        ├── registry.py        # CompensationRegistry
        └── actions.py         # Built-in compensation actions
```

### Checkpoint Interfaces

```python
# core/workflows/transactions/interfaces.py
from typing import Protocol, Dict, Any, Optional, List
from datetime import datetime


class ICheckpointManager(Protocol):
    """Protocol for checkpoint management."""
    
    async def create_checkpoint(
        self,
        workflow_id: str,
        checkpoint_id: str,
        state: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create a checkpoint - O(1), non-blocking."""
        ...
    
    async def get_checkpoint(
        self,
        workflow_id: str,
        checkpoint_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get a checkpoint by ID."""
        ...
    
    async def get_latest_checkpoint(
        self,
        workflow_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get the most recent checkpoint for a workflow."""
        ...
    
    async def list_checkpoints(
        self,
        workflow_id: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """List checkpoints for a workflow."""
        ...
    
    async def delete_checkpoint(
        self,
        workflow_id: str,
        checkpoint_id: str,
    ) -> bool:
        """Delete a checkpoint."""
        ...
    
    async def restore_from_checkpoint(
        self,
        workflow_id: str,
        checkpoint_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Restore state from a checkpoint."""
        ...


class ITransaction(Protocol):
    """Protocol for a transaction."""
    
    id: str
    workflow_id: str
    state: str  # "active", "committed", "rolled_back"
    
    async def record_operation(
        self,
        operation_type: str,
        args: Dict[str, Any],
        result: Any,
        compensation_action: Optional[str] = None,
    ) -> None:
        """Record an operation for potential rollback."""
        ...
    
    async def commit(self) -> None:
        """Commit the transaction."""
        ...
    
    async def rollback(self) -> None:
        """Rollback the transaction."""
        ...


class ICompensationAction(Protocol):
    """Protocol for compensation actions."""
    
    name: str
    
    async def execute(
        self,
        args: Dict[str, Any],
        result: Any,
    ) -> None:
        """Execute the compensation action."""
        ...
```

### Checkpoint Models

```python
# core/workflows/transactions/models.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Dict, Any, Optional, List
import uuid


class Checkpoint(BaseModel):
    """A workflow checkpoint."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id: str = Field(..., description="Associated workflow")
    
    # State
    state: Dict[str, Any] = Field(..., description="Captured state")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Tracking
    node_id: Optional[str] = Field(default=None, description="Node at checkpoint time")
    execution_path: List[str] = Field(default_factory=list)
    
    # Persistence status
    persisted: bool = Field(default=False)
    persisted_at: Optional[datetime] = Field(default=None)


class Operation(BaseModel):
    """A recorded operation for transaction rollback."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    operation_type: str = Field(..., description="Type of operation")
    args: Dict[str, Any] = Field(default_factory=dict)
    result: Any = Field(default=None)
    compensation_action: str = Field(..., description="Action to undo this operation")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Transaction(BaseModel):
    """A transaction with rollback support."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id: str = Field(..., description="Associated workflow")
    
    # State
    state: str = Field(default="active")  # active, committed, rolled_back
    operations: List[Operation] = Field(default_factory=list)
    
    # Checkpoints
    pre_checkpoint_id: Optional[str] = Field(default=None)
    post_checkpoint_id: Optional[str] = Field(default=None)
    
    # Timing
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(default=None)
```

### LazyCheckpointManager Implementation

```python
# core/workflows/transactions/checkpoints/lazy_checkpoint.py
import asyncio
from collections import deque, OrderedDict
from typing import Dict, Any, Optional, List
from datetime import datetime
from threading import Lock
import json
import os

from ..models import Checkpoint
from ..interfaces import ICheckpointManager


class LazyCheckpointManager(ICheckpointManager):
    """
    Zero-latency checkpoint manager using lazy async persistence.
    
    Design principles:
    1. Checkpoint creation is O(1) - just adds to in-memory cache
    2. Background worker persists checkpoints asynchronously
    3. WAL (Write-Ahead Log) for crash recovery (optional)
    4. LRU cache with configurable size limit
    
    Persistence strategies:
    - IMMEDIATE: Persist before returning (slow but safe)
    - LAZY: Persist in background (fast, eventual consistency)
    - BATCHED: Batch multiple checkpoints (throughput optimized)
    
    Usage:
        manager = LazyCheckpointManager(
            storage_path=".checkpoints",
            strategy="lazy",
        )
        
        # Create checkpoint - returns immediately (O(1))
        await manager.create_checkpoint(
            workflow_id="salon-workflow",
            checkpoint_id="booking-step-1",
            state={"service": "haircut", "date": "2024-01-15"},
        )
        
        # Restore from checkpoint
        state = await manager.restore_from_checkpoint(
            workflow_id="salon-workflow",
            checkpoint_id="booking-step-1",
        )
    """
    
    def __init__(
        self,
        storage_path: str = ".checkpoints",
        strategy: str = "lazy",  # "immediate", "lazy", "batched"
        batch_size: int = 10,
        batch_timeout_ms: int = 100,
        wal_enabled: bool = True,
        cache_max_size: int = 1000,
    ):
        self.storage_path = storage_path
        self.strategy = strategy
        self.batch_size = batch_size
        self.batch_timeout_ms = batch_timeout_ms
        self.wal_enabled = wal_enabled
        self.cache_max_size = cache_max_size
        
        # In-memory checkpoint cache (LRU)
        self._cache: OrderedDict[str, Checkpoint] = OrderedDict()
        self._lock = Lock()
        
        # Pending persistence queue
        self._pending_persist: deque = deque()
        
        # WAL for durability
        self._wal: Optional['WriteAheadLog'] = None
        if wal_enabled:
            self._wal = WriteAheadLog(storage_path)
        
        # Background persistence task
        self._persist_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Per-workflow latest checkpoint tracking
        self._latest: Dict[str, str] = {}  # workflow_id -> checkpoint_id
    
    async def create_checkpoint(
        self,
        workflow_id: str,
        checkpoint_id: str,
        state: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a checkpoint - O(1), non-blocking.
        
        Returns immediately. Persistence happens in background.
        """
        checkpoint = Checkpoint(
            id=checkpoint_id,
            workflow_id=workflow_id,
            state=state,
            metadata=metadata or {},
        )
        
        key = f"{workflow_id}:{checkpoint_id}"
        
        with self._lock:
            # Add to cache (O(1))
            self._cache[key] = checkpoint
            self._cache.move_to_end(key)  # LRU: move to end
            
            # Evict if over limit
            while len(self._cache) > self.cache_max_size:
                self._cache.popitem(last=False)  # Remove oldest
            
            # Track latest
            self._latest[workflow_id] = checkpoint_id
        
        # Write to WAL if enabled (fast append-only)
        if self._wal:
            await self._wal.append(checkpoint)
        
        # Queue for background persistence
        if self.strategy == "immediate":
            await self._persist_checkpoint(checkpoint)
        else:
            self._pending_persist.append(checkpoint)
            self._ensure_background_worker()
        
        return checkpoint_id
    
    async def get_checkpoint(
        self,
        workflow_id: str,
        checkpoint_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get a checkpoint - tries memory first, then storage."""
        key = f"{workflow_id}:{checkpoint_id}"
        
        # Try in-memory cache first (O(1))
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)  # LRU: update access
                checkpoint = self._cache[key]
                return checkpoint.model_dump()
        
        # Fall back to storage
        return await self._load_from_storage(workflow_id, checkpoint_id)
    
    async def get_latest_checkpoint(
        self,
        workflow_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get the most recent checkpoint for a workflow."""
        with self._lock:
            checkpoint_id = self._latest.get(workflow_id)
        
        if checkpoint_id:
            return await self.get_checkpoint(workflow_id, checkpoint_id)
        
        # Try loading from storage
        return await self._load_latest_from_storage(workflow_id)
    
    async def list_checkpoints(
        self,
        workflow_id: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """List checkpoints for a workflow."""
        checkpoints = []
        
        with self._lock:
            for key, checkpoint in self._cache.items():
                if checkpoint.workflow_id == workflow_id:
                    checkpoints.append(checkpoint.model_dump())
        
        # Sort by created_at descending
        checkpoints.sort(key=lambda c: c["created_at"], reverse=True)
        return checkpoints[:limit]
    
    async def delete_checkpoint(
        self,
        workflow_id: str,
        checkpoint_id: str,
    ) -> bool:
        """Delete a checkpoint."""
        key = f"{workflow_id}:{checkpoint_id}"
        
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
        
        # Also delete from storage
        return await self._delete_from_storage(workflow_id, checkpoint_id)
    
    async def restore_from_checkpoint(
        self,
        workflow_id: str,
        checkpoint_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Restore state from a checkpoint."""
        checkpoint_data = await self.get_checkpoint(workflow_id, checkpoint_id)
        
        if checkpoint_data:
            return checkpoint_data.get("state")
        
        return None
    
    # =========================================================================
    # Background Persistence
    # =========================================================================
    
    def _ensure_background_worker(self):
        """Ensure background persistence worker is running."""
        if not self._running:
            self._running = True
            self._persist_task = asyncio.create_task(self._background_persist())
    
    async def _background_persist(self):
        """Background worker for lazy checkpoint persistence."""
        while self._running or self._pending_persist:
            batch = []
            
            try:
                # Collect batch
                timeout = self.batch_timeout_ms / 1000.0
                deadline = asyncio.get_event_loop().time() + timeout
                
                while len(batch) < self.batch_size:
                    remaining = deadline - asyncio.get_event_loop().time()
                    if remaining <= 0:
                        break
                    
                    try:
                        if self._pending_persist:
                            checkpoint = self._pending_persist.popleft()
                            batch.append(checkpoint)
                        else:
                            await asyncio.sleep(0.01)
                    except IndexError:
                        break
                
                # Persist batch
                if batch:
                    await self._persist_batch(batch)
                    
            except Exception as e:
                # Log error but don't crash worker
                print(f"Checkpoint persistence error: {e}")
            
            # Small sleep to prevent tight loop
            await asyncio.sleep(0.01)
        
        self._running = False
    
    async def _persist_batch(self, batch: List[Checkpoint]):
        """Persist a batch of checkpoints to storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        for checkpoint in batch:
            await self._persist_checkpoint(checkpoint)
    
    async def _persist_checkpoint(self, checkpoint: Checkpoint):
        """Persist a single checkpoint to storage."""
        workflow_dir = os.path.join(self.storage_path, checkpoint.workflow_id)
        os.makedirs(workflow_dir, exist_ok=True)
        
        filepath = os.path.join(workflow_dir, f"{checkpoint.id}.json")
        
        # Use aiofiles if available, otherwise sync
        try:
            import aiofiles
            async with aiofiles.open(filepath, 'w') as f:
                await f.write(json.dumps(checkpoint.model_dump(), indent=2, default=str))
        except ImportError:
            with open(filepath, 'w') as f:
                json.dump(checkpoint.model_dump(), f, indent=2, default=str)
        
        checkpoint.persisted = True
        checkpoint.persisted_at = datetime.utcnow()
    
    async def _load_from_storage(
        self,
        workflow_id: str,
        checkpoint_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Load a checkpoint from storage."""
        filepath = os.path.join(
            self.storage_path, workflow_id, f"{checkpoint_id}.json"
        )
        
        if not os.path.exists(filepath):
            return None
        
        try:
            import aiofiles
            async with aiofiles.open(filepath, 'r') as f:
                content = await f.read()
                return json.loads(content)
        except ImportError:
            with open(filepath, 'r') as f:
                return json.load(f)
    
    async def _load_latest_from_storage(
        self,
        workflow_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Load the latest checkpoint from storage."""
        workflow_dir = os.path.join(self.storage_path, workflow_id)
        
        if not os.path.exists(workflow_dir):
            return None
        
        # Find most recent file
        files = [f for f in os.listdir(workflow_dir) if f.endswith('.json')]
        if not files:
            return None
        
        # Sort by modification time
        files.sort(
            key=lambda f: os.path.getmtime(os.path.join(workflow_dir, f)),
            reverse=True
        )
        
        checkpoint_id = files[0].replace('.json', '')
        return await self._load_from_storage(workflow_id, checkpoint_id)
    
    async def _delete_from_storage(
        self,
        workflow_id: str,
        checkpoint_id: str,
    ) -> bool:
        """Delete a checkpoint from storage."""
        filepath = os.path.join(
            self.storage_path, workflow_id, f"{checkpoint_id}.json"
        )
        
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
        
        return False
    
    # =========================================================================
    # Cleanup
    # =========================================================================
    
    async def flush(self):
        """Flush all pending checkpoints to storage."""
        while self._pending_persist:
            checkpoint = self._pending_persist.popleft()
            await self._persist_checkpoint(checkpoint)
    
    async def shutdown(self):
        """Shutdown the manager, flushing pending writes."""
        self._running = False
        await self.flush()
        
        if self._persist_task:
            self._persist_task.cancel()
            try:
                await self._persist_task
            except asyncio.CancelledError:
                pass


class WriteAheadLog:
    """
    Write-Ahead Log for checkpoint durability.
    
    Provides crash recovery by logging checkpoint data before
    acknowledging the write. Recovery replays the log to restore
    any checkpoints that weren't persisted.
    """
    
    def __init__(self, storage_path: str):
        self.storage_path = storage_path
        self.wal_path = os.path.join(storage_path, "wal.log")
        self._lock = Lock()
    
    async def append(self, checkpoint: Checkpoint):
        """Append a checkpoint entry to the WAL."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "checkpoint": checkpoint.model_dump(),
        }
        
        with self._lock:
            with open(self.wal_path, 'a') as f:
                f.write(json.dumps(entry, default=str) + "\n")
    
    async def recover(self) -> List[Checkpoint]:
        """Recover checkpoints from the WAL."""
        if not os.path.exists(self.wal_path):
            return []
        
        checkpoints = []
        
        with open(self.wal_path, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    checkpoint = Checkpoint(**entry["checkpoint"])
                    checkpoints.append(checkpoint)
                except Exception:
                    continue  # Skip corrupted entries
        
        return checkpoints
    
    async def truncate(self):
        """Truncate the WAL after successful recovery/persistence."""
        if os.path.exists(self.wal_path):
            os.remove(self.wal_path)
```

### TransactionManager Implementation

```python
# core/workflows/transactions/manager.py
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

from .models import Transaction, Operation
from .checkpoints.lazy_checkpoint import LazyCheckpointManager
from .compensation.registry import CompensationRegistry


class TransactionManager:
    """
    Manages transactional operations with rollback support.
    
    Features:
    1. Automatic checkpoint creation at transaction boundaries
    2. Compensation action registry for rollback
    3. Idempotency key support for safe retries
    
    Usage:
        tx_manager = TransactionManager(checkpoint_manager, compensation_registry)
        
        # Using context manager (auto commit/rollback)
        async with await tx_manager.begin(workflow_id) as tx:
            result = await some_tool.execute(args)
            await tx.record_operation("book_slot", args, result)
            
            result2 = await another_tool.execute(args2)
            await tx.record_operation("send_confirmation", args2, result2)
        
        # Manual control
        tx = await tx_manager.begin(workflow_id)
        try:
            result = await some_tool.execute(args)
            await tx.record_operation("book_slot", args, result)
            await tx.commit()
        except Exception:
            await tx.rollback()
            raise
    """
    
    def __init__(
        self,
        checkpoint_manager: LazyCheckpointManager,
        compensation_registry: Optional[CompensationRegistry] = None,
        auto_checkpoint: bool = True,
    ):
        self.checkpoint_manager = checkpoint_manager
        self.compensation_registry = compensation_registry or CompensationRegistry()
        self.auto_checkpoint = auto_checkpoint
        
        # Active transactions
        self._transactions: Dict[str, 'TransactionContext'] = {}
    
    async def begin(
        self,
        workflow_id: str,
        transaction_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> 'TransactionContext':
        """
        Begin a new transaction.
        
        Args:
            workflow_id: Workflow this transaction belongs to
            transaction_id: Optional custom transaction ID
            idempotency_key: Optional key for idempotent retries
        
        Returns:
            TransactionContext that can be used as context manager
        """
        tx_id = transaction_id or str(uuid.uuid4())
        
        # Check for idempotent replay
        if idempotency_key:
            existing = await self._check_idempotency(idempotency_key)
            if existing:
                return existing
        
        # Create pre-transaction checkpoint
        pre_checkpoint_id = None
        if self.auto_checkpoint:
            pre_checkpoint_id = f"pre-tx-{tx_id}"
            await self.checkpoint_manager.create_checkpoint(
                workflow_id=workflow_id,
                checkpoint_id=pre_checkpoint_id,
                state={"transaction_id": tx_id, "phase": "pre"},
                metadata={"idempotency_key": idempotency_key},
            )
        
        # Create transaction context
        tx = TransactionContext(
            id=tx_id,
            workflow_id=workflow_id,
            checkpoint_manager=self.checkpoint_manager,
            compensation_registry=self.compensation_registry,
            pre_checkpoint_id=pre_checkpoint_id,
            idempotency_key=idempotency_key,
        )
        
        self._transactions[tx_id] = tx
        return tx
    
    async def rollback_to_checkpoint(
        self,
        workflow_id: str,
        checkpoint_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Rollback workflow to a specific checkpoint."""
        state = await self.checkpoint_manager.restore_from_checkpoint(
            workflow_id,
            checkpoint_id,
        )
        
        if not state:
            raise ValueError(f"Checkpoint not found: {checkpoint_id}")
        
        return state
    
    async def _check_idempotency(
        self,
        idempotency_key: str,
    ) -> Optional['TransactionContext']:
        """Check if this is an idempotent replay."""
        # Check for completed transaction with this key
        for tx in self._transactions.values():
            if tx.idempotency_key == idempotency_key and tx.state == "committed":
                return tx
        return None
    
    def get_transaction(self, transaction_id: str) -> Optional['TransactionContext']:
        """Get an active transaction by ID."""
        return self._transactions.get(transaction_id)


class TransactionContext:
    """
    A transaction context with rollback support.
    
    Can be used as an async context manager for automatic commit/rollback.
    """
    
    def __init__(
        self,
        id: str,
        workflow_id: str,
        checkpoint_manager: LazyCheckpointManager,
        compensation_registry: CompensationRegistry,
        pre_checkpoint_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ):
        self.id = id
        self.workflow_id = workflow_id
        self.checkpoint_manager = checkpoint_manager
        self.compensation_registry = compensation_registry
        self.pre_checkpoint_id = pre_checkpoint_id
        self.idempotency_key = idempotency_key
        
        self._operations: List[Operation] = []
        self.state: str = "active"
        self.started_at = datetime.utcnow()
        self.completed_at: Optional[datetime] = None
    
    async def record_operation(
        self,
        operation_type: str,
        args: Dict[str, Any],
        result: Any,
        compensation_action: Optional[str] = None,
    ) -> None:
        """
        Record an operation for potential rollback.
        
        Args:
            operation_type: Type of operation (e.g., "book_slot", "charge_payment")
            args: Arguments passed to the operation
            result: Result of the operation
            compensation_action: Name of compensation action to undo this operation
                                (defaults to "compensate_{operation_type}")
        """
        if self.state != "active":
            raise RuntimeError(f"Cannot record operation: transaction is {self.state}")
        
        operation = Operation(
            operation_type=operation_type,
            args=args,
            result=result,
            compensation_action=compensation_action or f"compensate_{operation_type}",
        )
        
        self._operations.append(operation)
    
    async def commit(self) -> None:
        """Commit the transaction."""
        if self.state != "active":
            raise RuntimeError(f"Cannot commit: transaction is {self.state}")
        
        # Create post-transaction checkpoint
        await self.checkpoint_manager.create_checkpoint(
            workflow_id=self.workflow_id,
            checkpoint_id=f"post-tx-{self.id}",
            state={
                "transaction_id": self.id,
                "phase": "committed",
                "operations": [op.model_dump() for op in self._operations],
            },
            metadata={"idempotency_key": self.idempotency_key},
        )
        
        self.state = "committed"
        self.completed_at = datetime.utcnow()
    
    async def rollback(self) -> None:
        """Rollback the transaction by executing compensation actions."""
        if self.state != "active":
            raise RuntimeError(f"Cannot rollback: transaction is {self.state}")
        
        errors = []
        
        # Execute compensation actions in reverse order
        for op in reversed(self._operations):
            action = self.compensation_registry.get(op.compensation_action)
            
            if action:
                try:
                    await action.execute(op.args, op.result)
                except Exception as e:
                    # Log but continue with other compensations
                    errors.append(f"{op.operation_type}: {e}")
        
        self.state = "rolled_back"
        self.completed_at = datetime.utcnow()
        
        if errors:
            # Log compensation errors
            print(f"Rollback completed with errors: {errors}")
    
    async def __aenter__(self) -> 'TransactionContext':
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.rollback()
        else:
            await self.commit()
        return False  # Don't suppress exceptions
```

### Compensation Registry

```python
# core/workflows/transactions/compensation/registry.py
from typing import Dict, Any, Optional, Callable, Awaitable


class CompensationAction:
    """A compensation action that can undo an operation."""
    
    def __init__(
        self,
        name: str,
        handler: Callable[[Dict[str, Any], Any], Awaitable[None]],
    ):
        self.name = name
        self.handler = handler
    
    async def execute(self, args: Dict[str, Any], result: Any) -> None:
        """Execute the compensation action."""
        await self.handler(args, result)


class CompensationRegistry:
    """
    Registry of compensation actions for transaction rollback.
    
    Usage:
        registry = CompensationRegistry()
        
        # Register a compensation action
        @registry.register("compensate_book_slot")
        async def compensate_book_slot(args: dict, result: any):
            await booking_service.cancel(result["booking_id"])
        
        # Or register inline
        registry.add(
            "compensate_send_email",
            lambda args, result: email_service.mark_cancelled(result["email_id"])
        )
    """
    
    def __init__(self):
        self._actions: Dict[str, CompensationAction] = {}
    
    def register(self, name: str):
        """Decorator to register a compensation action."""
        def decorator(func: Callable[[Dict[str, Any], Any], Awaitable[None]]):
            self._actions[name] = CompensationAction(name, func)
            return func
        return decorator
    
    def add(
        self,
        name: str,
        handler: Callable[[Dict[str, Any], Any], Awaitable[None]],
    ) -> None:
        """Add a compensation action to the registry."""
        self._actions[name] = CompensationAction(name, handler)
    
    def get(self, name: str) -> Optional[CompensationAction]:
        """Get a compensation action by name."""
        return self._actions.get(name)
    
    def list_actions(self) -> list:
        """List all registered action names."""
        return list(self._actions.keys())
```

---

## Integration Example

### Using Task Queue + Transactions in Workflow Execution

```python
# Example usage in workflow execution
from core.workflows.taskqueue import TaskQueueManager, TaskPriority
from core.workflows.transactions import TransactionManager, LazyCheckpointManager


async def execute_workflow_with_infrastructure(
    workflow: WorkflowSpec,
    initial_input: str,
    session_id: str,
):
    """Execute workflow with task queue and transaction support."""
    
    # Initialize infrastructure
    task_queue = TaskQueueManager()
    checkpoint_manager = LazyCheckpointManager(
        storage_path=".checkpoints",
        strategy="lazy",
    )
    tx_manager = TransactionManager(checkpoint_manager)
    
    # Create execution context
    context = WorkflowExecutionContext(
        workflow_id=workflow.id,
        execution_id=str(uuid.uuid4()),
    )
    context.set_task_queue(task_queue)
    
    # Enqueue initial input
    await task_queue.enqueue(
        task_type="user_message",
        payload={"content": initial_input},
        workflow_id=workflow.id,
        session_id=session_id,
    )
    
    # Main processing loop
    current_node = workflow.start_node_id
    
    while current_node:
        node = workflow.get_node(current_node)
        
        # Get next task
        task = await task_queue.dequeue(workflow.id)
        if not task:
            break
        
        # Begin transaction for this node
        async with await tx_manager.begin(workflow.id) as tx:
            # Execute node (agent or tool)
            result = await execute_node(node, task.payload, context)
            
            # Record operation for rollback
            await tx.record_operation(
                operation_type=f"node_{node.id}",
                args={"input": task.payload},
                result=result,
            )
        
        # Check for interrupts during long operations
        interrupt = await task_queue.check_for_interrupt(workflow.id)
        if interrupt:
            # Handle interrupt
            await handle_interrupt(interrupt, context, checkpoint_manager)
            continue
        
        # Get next nodes based on edge conditions
        next_nodes = workflow.get_next_nodes(current_node, context.get_context_for_conditions())
        current_node = next_nodes[0] if next_nodes else None
    
    # Cleanup
    await checkpoint_manager.shutdown()
    
    return context


async def handle_interrupt(
    interrupt: Task,
    context: WorkflowExecutionContext,
    checkpoint_manager: LazyCheckpointManager,
):
    """Handle a user interrupt."""
    
    # Save current state
    await checkpoint_manager.create_checkpoint(
        workflow_id=context.workflow_id,
        checkpoint_id=f"interrupt-{datetime.utcnow().timestamp()}",
        state={
            "current_node": context.current_node_id,
            "variables": context.variables,
            "interrupt_message": interrupt.payload.get("content"),
        },
    )
    
    # Process interrupt message
    # (This would typically re-route to appropriate node)
    pass
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1-2)
1. **Task Queue Manager**
   - Core queue with heap-based priority
   - Observer pattern for notifications
   - Interrupt detection (O(1))
   
2. **Lazy Checkpoint System**
   - In-memory cache with LRU eviction
   - Background persistence worker
   - WAL for durability

3. **Transaction Manager**
   - Begin/Commit/Rollback
   - Compensation action registry
   - Context manager support

### Phase 2: Integration (Week 3)
1. **WorkflowExecutionContext integration**
2. **Interrupt handling integration**
3. **Unit tests for all modules**

### Phase 3: Testing & Optimization (Week 4)
1. **Integration tests with salon workflow**
2. **Performance benchmarking**
3. **Memory optimization**

---

## Performance Guarantees

| Operation | Complexity | Notes |
|-----------|------------|-------|
| Task enqueue | O(log n) | Heap-based priority queue |
| Task dequeue | O(log n) | Heap extraction |
| Interrupt check | O(1) | Peek at heap top |
| Checkpoint create | O(1) | In-memory only |
| Checkpoint get | O(1) | Cache hit |
| Checkpoint persist | Async | Background worker |

### Memory Efficiency
- LRU cache for checkpoints (configurable max size)
- Lazy loading of old checkpoints from storage
- Periodic cleanup of old checkpoints

---

## File Changes Summary

### New Directories
```
core/workflows/
├── taskqueue/           # NEW - Task queue manager
│   ├── __init__.py
│   ├── interfaces.py
│   ├── models.py
│   ├── manager.py
│   └── storage/
│       ├── memory.py
│       └── redis.py     # Optional
└── transactions/        # NEW - Transaction & checkpoint management
    ├── __init__.py
    ├── interfaces.py
    ├── models.py
    ├── manager.py
    ├── checkpoints/
    │   ├── lazy_checkpoint.py
    │   ├── wal.py
    │   └── recovery.py
    └── compensation/
        ├── registry.py
        └── actions.py
```

### Enhanced Existing Files
- `core/workflows/spec/workflow_models.py` - Add task_queue to context
- `core/workflows/__init__.py` - Export new modules

---

## Next Steps

1. **Review and approve this focused plan**
2. **Implement Task Queue Manager**
3. **Implement Lazy Checkpoint + Transaction Manager**
4. **Add tests to `test_salon_workflow.py`**
5. **Integration with existing workflow execution**

Would you like me to proceed with implementing these two core infrastructure modules?
