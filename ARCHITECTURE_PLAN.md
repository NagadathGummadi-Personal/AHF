# AHF Workflow Enhancement Architecture Plan

## Executive Summary

This document outlines a comprehensive plan to enhance the AHF workflow system with:
1. **Task Queue Manager** - Non-blocking user input handling
2. **Enhanced Checkpoints** - Zero-latency checkpoint system
3. **Intent Classification System** - Dedicated classifier layer
4. **Clarification Handler** - Systematic slot filling
5. **Service Match Resolution** - Multiple match handling
6. **Transaction Management** - Rollback/compensation patterns
7. **Handover System** - Human escalation
8. **Policy & Rate Limiting** - Safeguards layer

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

### ❌ What's Missing (From Your Agent Runtime Loop)
| Component | Priority | Impact |
|-----------|----------|--------|
| Task Queue Manager | 🔴 Critical | User input queuing without blocking |
| Intent/Slot Classifier | 🔴 Critical | Steps 2-3 of the flow |
| Clarification Flow | 🟠 High | Step 3 - missing slot handling |
| Flow Router | 🟠 High | Step 4 - intent to flow mapping |
| Service Match Handler | 🟠 High | Steps 6-7 - multiple match resolution |
| Transaction Manager | 🔴 Critical | Step 10 - rollback/compensation |
| Handover Manager | 🟠 High | Step 13 - human escalation |
| Policy Engine | 🟡 Medium | Step 15 - rate limits, restrictions |
| Deviation Handler | 🟠 High | Step 14 - mid-flow interruptions |

---

## Proposed Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AHF Enhanced Workflow Engine                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────┐    ┌──────────────────┐    ┌────────────────────────┐  │
│  │  TaskQueue     │───▶│ IntentClassifier │───▶│  ClarificationHandler  │  │
│  │  Manager       │    │ (Step 2)         │    │  (Step 3)              │  │
│  │  (Step 1)      │    │                  │    │                        │  │
│  └────────────────┘    └──────────────────┘    └────────────────────────┘  │
│         │                      │                         │                  │
│         ▼                      ▼                         ▼                  │
│  ┌────────────────┐    ┌──────────────────┐    ┌────────────────────────┐  │
│  │  FlowRouter    │◀───│ ToolInputAssmblr │◀───│  ServiceMatchHandler   │  │
│  │  (Step 4)      │    │ (Step 5)         │    │  (Steps 6-7)           │  │
│  └────────────────┘    └──────────────────┘    └────────────────────────┘  │
│         │                                                │                  │
│         ▼                                                ▼                  │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                    TransactionManager (Step 10)                     │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │    │
│  │  │  Checkpoint │  │  Rollback   │  │ Compensation│  │ Idempotent│  │    │
│  │  │  Handler    │  │  Handler    │  │   Actions   │  │   Keys    │  │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘  │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│         │                                                                   │
│         ▼                                                                   │
│  ┌────────────────┐    ┌──────────────────┐    ┌────────────────────────┐  │
│  │  PolicyEngine  │◀──▶│ HandoverManager  │◀──▶│  DeviationHandler      │  │
│  │  (Step 15)     │    │ (Step 13)        │    │  (Step 14)             │  │
│  └────────────────┘    └──────────────────┘    └────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Module 1: Task Queue Manager

### Purpose
Handle user input queuing without blocking workflow execution. This is critical for:
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
from typing import Protocol, Any, Optional
from enum import Enum

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
        """Add task to queue, returns task_id."""
        ...
    
    async def dequeue(self, workflow_id: str) -> Optional[ITask]:
        """Get next task for workflow (non-blocking)."""
        ...
    
    async def peek(self, workflow_id: str) -> Optional[ITask]:
        """View next task without removing."""
        ...
    
    async def has_pending(self, workflow_id: str) -> bool:
        """Check if workflow has pending tasks."""
        ...
    
    async def get_by_priority(
        self, 
        workflow_id: str, 
        min_priority: TaskPriority
    ) -> List[ITask]:
        """Get all tasks at or above priority."""
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

### Zero-Latency Design

The queue uses a **non-blocking observer pattern**:

```python
# core/workflows/taskqueue/manager.py
import asyncio
from collections import defaultdict
from typing import Dict, List, Optional, Callable, Awaitable
from heapq import heappush, heappop

class TaskQueueManager:
    """
    Zero-latency task queue manager.
    
    Design principles:
    1. Enqueueing is O(log n) - never blocks workflow
    2. Background processor handles persistence
    3. In-memory queue with optional persistence
    4. Priority-based processing with INTERRUPT > HIGH > NORMAL > LOW
    """
    
    def __init__(
        self,
        persist_enabled: bool = False,
        persist_interval_ms: int = 100,
    ):
        # Priority queues per workflow (heap-based)
        self._queues: Dict[str, List[tuple]] = defaultdict(list)
        self._task_map: Dict[str, Task] = {}  # Quick lookup
        self._sequence_counter: int = 0
        
        # Observers for new tasks
        self._observers: Dict[str, List[Callable[[Task], Awaitable[None]]]] = defaultdict(list)
        
        # Background persistence (optional, non-blocking)
        self._persist_enabled = persist_enabled
        self._dirty_tasks: List[str] = []
        self._persist_task: Optional[asyncio.Task] = None
        
    async def enqueue(
        self,
        task_type: str,
        payload: Any,
        priority: TaskPriority = TaskPriority.NORMAL,
        workflow_id: str = "default",
        session_id: str = "default",
        **kwargs,
    ) -> str:
        """
        Enqueue a task - O(log n), non-blocking.
        
        Priority order (heap uses negative for max-heap behavior):
        - INTERRUPT: -3
        - HIGH: -2  
        - NORMAL: -1
        - LOW: 0
        """
        self._sequence_counter += 1
        
        task = Task(
            task_type=task_type,
            payload=payload,
            priority=priority,
            workflow_id=workflow_id,
            session_id=session_id,
            sequence_number=self._sequence_counter,
            **kwargs,
        )
        
        # Heap entry: (priority_value, sequence_number, task_id)
        # Use negative priority for max-heap behavior (higher priority first)
        heap_entry = (-priority.value, self._sequence_counter, task.id)
        heappush(self._queues[workflow_id], heap_entry)
        self._task_map[task.id] = task
        
        # Mark for async persistence (non-blocking)
        if self._persist_enabled:
            self._dirty_tasks.append(task.id)
        
        # Notify observers (fire and forget)
        for observer in self._observers.get(workflow_id, []):
            asyncio.create_task(observer(task))
        
        return task.id
    
    async def dequeue(self, workflow_id: str) -> Optional[Task]:
        """Get and remove next task - O(log n)."""
        queue = self._queues.get(workflow_id)
        if not queue:
            return None
        
        _, _, task_id = heappop(queue)
        task = self._task_map.pop(task_id, None)
        
        if task:
            task.state = TaskState.PROCESSING
            task.processed_at = datetime.utcnow()
        
        return task
    
    def subscribe(
        self, 
        workflow_id: str, 
        callback: Callable[[Task], Awaitable[None]]
    ):
        """Subscribe to new tasks for a workflow."""
        self._observers[workflow_id].append(callback)
    
    async def check_for_interrupt(self, workflow_id: str) -> Optional[Task]:
        """
        Quick check for interrupt tasks - O(1).
        Used during streaming to detect user interrupts.
        """
        queue = self._queues.get(workflow_id)
        if not queue:
            return None
        
        # Peek at top of heap
        priority_val, _, task_id = queue[0]
        if priority_val == -TaskPriority.INTERRUPT.value:
            return self._task_map.get(task_id)
        return None
```

### Integration with Workflow

```python
# Example integration in WorkflowExecutionContext
class WorkflowExecutionContext(BaseModel):
    # ... existing fields ...
    
    # Task queue reference
    task_queue: Optional[Any] = Field(default=None, exclude=True)
    
    async def check_for_user_input(self) -> Optional[Task]:
        """Check for pending user input without blocking."""
        if self.task_queue:
            return await self.task_queue.peek(self.workflow_id)
        return None
    
    async def process_pending_interrupts(self) -> List[Task]:
        """Process any pending interrupt tasks."""
        if not self.task_queue:
            return []
        
        interrupts = await self.task_queue.get_by_priority(
            self.workflow_id,
            TaskPriority.INTERRUPT
        )
        return interrupts
```

---

## Module 2: Intent Classification System

### Purpose
Dedicated intent and slot extraction layer that runs before agent execution.
Maps to Steps 2-3 of your runtime loop.

### Directory Structure
```
core/workflows/
└── classification/
    ├── __init__.py
    ├── interfaces.py       # IClassifier, ISlotExtractor
    ├── models.py          # Intent, Slot, ClassificationResult
    ├── classifiers/
    │   ├── __init__.py
    │   ├── llm_classifier.py      # LLM-based classifier
    │   ├── pattern_classifier.py  # Regex/keyword-based
    │   └── hybrid_classifier.py   # Combined approach
    ├── extractors/
    │   ├── __init__.py
    │   ├── llm_extractor.py
    │   └── rule_extractor.py
    └── registry.py        # Intent/Slot registry
```

### Key Models

```python
# core/workflows/classification/models.py
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from enum import Enum

class IntentConfidence(Enum):
    HIGH = "high"      # > 0.85 confidence
    MEDIUM = "medium"  # 0.6 - 0.85
    LOW = "low"        # < 0.6
    UNKNOWN = "unknown"

class Intent(BaseModel):
    """Detected user intent."""
    name: str = Field(..., description="Intent identifier (e.g., 'book_service', 'cancel')")
    display_name: str = Field(default="", description="Human-readable name")
    confidence: float = Field(..., ge=0.0, le=1.0)
    confidence_level: IntentConfidence = Field(default=IntentConfidence.UNKNOWN)
    
    # Mapping to workflow
    target_flow: Optional[str] = Field(default=None, description="Workflow/flow ID to route to")
    target_node: Optional[str] = Field(default=None, description="Specific node to route to")
    
    # Required slots for this intent
    required_slots: List[str] = Field(default_factory=list)
    optional_slots: List[str] = Field(default_factory=list)

class Slot(BaseModel):
    """Extracted slot/entity value."""
    name: str = Field(..., description="Slot name (e.g., 'service_name', 'date')")
    value: Any = Field(..., description="Extracted value")
    raw_value: str = Field(default="", description="Original text")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    
    # Source tracking
    source: str = Field(default="user", description="Where this value came from")
    needs_confirmation: bool = Field(default=False)

class ClassificationResult(BaseModel):
    """Complete classification result."""
    intent: Intent
    slots: Dict[str, Slot] = Field(default_factory=dict)
    missing_required_slots: List[str] = Field(default_factory=list)
    
    # Clarification needs
    needs_clarification: bool = Field(default=False)
    clarification_reason: Optional[str] = Field(default=None)
    clarification_prompt: Optional[str] = Field(default=None)
    
    # Metadata
    raw_input: str = Field(default="")
    processing_time_ms: float = Field(default=0.0)
    
    def is_actionable(self) -> bool:
        """Check if we have enough info to proceed."""
        return (
            self.intent.confidence_level != IntentConfidence.LOW
            and len(self.missing_required_slots) == 0
        )
```

### Classifier Interface

```python
# core/workflows/classification/interfaces.py
from typing import Protocol, List, Dict, Any, Optional

class IIntentClassifier(Protocol):
    """Protocol for intent classification."""
    
    async def classify(
        self,
        user_input: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> ClassificationResult:
        """Classify user input into intent + slots."""
        ...
    
    def get_supported_intents(self) -> List[Intent]:
        """Get list of supported intents."""
        ...

class ISlotExtractor(Protocol):
    """Protocol for slot/entity extraction."""
    
    async def extract(
        self,
        user_input: str,
        target_slots: List[str],
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Slot]:
        """Extract specific slots from input."""
        ...
```

### LLM-Based Classifier

```python
# core/workflows/classification/classifiers/llm_classifier.py
class LLMIntentClassifier:
    """LLM-based intent classifier with zero-shot or few-shot learning."""
    
    def __init__(
        self,
        llm: Any,
        intent_registry: 'IntentRegistry',
        confidence_threshold: float = 0.6,
    ):
        self.llm = llm
        self.intent_registry = intent_registry
        self.confidence_threshold = confidence_threshold
    
    async def classify(
        self,
        user_input: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> ClassificationResult:
        """
        Classify using LLM with structured output.
        
        Uses a single LLM call to get:
        - Intent with confidence
        - All slots in one pass
        - Clarification needs
        """
        intents = self.intent_registry.get_all_intents()
        
        system_prompt = self._build_classification_prompt(intents)
        
        messages = [
            {"role": "system", "content": system_prompt},
        ]
        
        # Include conversation history for context
        if conversation_history:
            # Last 5 turns for context
            for msg in conversation_history[-10:]:
                messages.append(msg)
        
        messages.append({"role": "user", "content": user_input})
        
        # Use structured output for reliable parsing
        from core.llms import LLMContext
        response = await self.llm.get_answer(
            messages,
            LLMContext(),
            response_format={"type": "json_object"},
        )
        
        return self._parse_response(response.content, user_input)
    
    def _build_classification_prompt(self, intents: List[Intent]) -> str:
        """Build the classification system prompt."""
        intent_descriptions = "\n".join([
            f"- {i.name}: {i.display_name}. Required slots: {i.required_slots}"
            for i in intents
        ])
        
        return f"""You are an intent classifier for a salon booking system.

Available intents:
{intent_descriptions}

Analyze the user message and respond with JSON:
{{
    "intent": "intent_name",
    "confidence": 0.0-1.0,
    "slots": {{"slot_name": "value", ...}},
    "missing_slots": ["slot1", "slot2"],
    "needs_clarification": true/false,
    "clarification_prompt": "question to ask if needed"
}}

Rules:
1. If confidence < 0.6, set needs_clarification to true
2. List any required slots that couldn't be extracted in missing_slots
3. Generate a natural clarification_prompt if clarification is needed
"""
```

---

## Module 3: Clarification Handler

### Purpose
Systematic handling of missing slots and low-confidence classifications.
Implements Step 3 of your runtime loop.

### Directory Structure
```
core/workflows/
└── clarification/
    ├── __init__.py
    ├── interfaces.py
    ├── models.py
    ├── handler.py         # Main clarification logic
    └── strategies/
        ├── __init__.py
        ├── single_slot.py      # Ask for one slot at a time
        ├── batch_slot.py       # Ask for multiple slots
        └── confirmation.py     # Confirmation strategies
```

### Clarification Models

```python
# core/workflows/clarification/models.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum

class ClarificationState(Enum):
    NONE = "none"
    AWAITING_SLOT = "awaiting_slot"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    AWAITING_SELECTION = "awaiting_selection"
    MAX_RETRIES_EXCEEDED = "max_retries_exceeded"

class ClarificationRequest(BaseModel):
    """A request for clarification from the user."""
    id: str
    clarification_type: str  # "missing_slot", "low_confidence", "multiple_match", "confirmation"
    target_slots: List[str] = Field(default_factory=list)
    prompt: str = Field(..., description="The question to ask the user")
    
    # For selection clarifications
    options: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Tracking
    attempt_count: int = Field(default=0)
    max_attempts: int = Field(default=3)
    
    # Context
    original_input: str = Field(default="")
    partial_slots: Dict[str, Any] = Field(default_factory=dict)

class ClarificationContext(BaseModel):
    """Context for ongoing clarification flow."""
    state: ClarificationState = Field(default=ClarificationState.NONE)
    active_request: Optional[ClarificationRequest] = Field(default=None)
    history: List[ClarificationRequest] = Field(default_factory=list)
    
    # Accumulated slots from clarification
    collected_slots: Dict[str, Any] = Field(default_factory=dict)
    
    def needs_clarification(self) -> bool:
        return self.state not in (ClarificationState.NONE, ClarificationState.MAX_RETRIES_EXCEEDED)
```

### Clarification Handler

```python
# core/workflows/clarification/handler.py
class ClarificationHandler:
    """
    Handles the clarification flow for missing/ambiguous information.
    
    Strategies:
    1. Single-slot: Ask for one slot at a time (more natural)
    2. Batch: Ask for multiple slots in one turn (faster)
    3. Confirmation: Confirm extracted values before proceeding
    """
    
    def __init__(
        self,
        llm: Any,
        strategy: str = "single_slot",  # "single_slot", "batch", "adaptive"
        max_retries_per_slot: int = 3,
        total_max_retries: int = 10,
    ):
        self.llm = llm
        self.strategy = strategy
        self.max_retries_per_slot = max_retries_per_slot
        self.total_max_retries = total_max_retries
    
    async def create_clarification_request(
        self,
        classification: ClassificationResult,
        context: ClarificationContext,
    ) -> ClarificationRequest:
        """Create a clarification request based on what's missing."""
        
        if classification.intent.confidence_level == IntentConfidence.LOW:
            return await self._create_intent_clarification(classification, context)
        
        if classification.missing_required_slots:
            return await self._create_slot_clarification(
                classification.missing_required_slots,
                classification.intent,
                context,
            )
        
        return None
    
    async def _create_slot_clarification(
        self,
        missing_slots: List[str],
        intent: Intent,
        context: ClarificationContext,
    ) -> ClarificationRequest:
        """Create a natural-sounding slot clarification request."""
        
        if self.strategy == "single_slot":
            # Ask for most important slot first
            target_slot = missing_slots[0]
            prompt = await self._generate_slot_prompt(target_slot, intent, context)
            
            return ClarificationRequest(
                id=f"clarify-{target_slot}-{context.active_request.attempt_count if context.active_request else 0}",
                clarification_type="missing_slot",
                target_slots=[target_slot],
                prompt=prompt,
                partial_slots=context.collected_slots,
            )
        else:
            # Batch mode - ask for all at once
            prompt = await self._generate_batch_prompt(missing_slots, intent, context)
            
            return ClarificationRequest(
                id=f"clarify-batch-{len(context.history)}",
                clarification_type="missing_slot",
                target_slots=missing_slots,
                prompt=prompt,
                partial_slots=context.collected_slots,
            )
    
    async def _generate_slot_prompt(
        self,
        slot_name: str,
        intent: Intent,
        context: ClarificationContext,
    ) -> str:
        """Generate a natural prompt for a specific slot."""
        
        # Use LLM to generate natural prompt
        messages = [
            {
                "role": "system",
                "content": f"""Generate a natural, conversational question to ask the user for the '{slot_name}' value.
Context: User wants to {intent.display_name}.
Already collected: {context.collected_slots}
Keep it brief and friendly. Do not be robotic."""
            },
            {"role": "user", "content": f"Generate question for: {slot_name}"}
        ]
        
        from core.llms import LLMContext
        response = await self.llm.get_answer(messages, LLMContext())
        return response.content.strip()
    
    async def process_response(
        self,
        user_response: str,
        context: ClarificationContext,
    ) -> Dict[str, Any]:
        """Process user's response to a clarification request."""
        
        if not context.active_request:
            return {"success": False, "error": "No active clarification request"}
        
        # Extract slots from response
        from core.workflows.classification import LLMSlotExtractor
        extractor = LLMSlotExtractor(self.llm)
        
        extracted = await extractor.extract(
            user_response,
            context.active_request.target_slots,
        )
        
        # Update collected slots
        for slot_name, slot_value in extracted.items():
            context.collected_slots[slot_name] = slot_value.value
        
        # Check if we got what we needed
        still_missing = [
            s for s in context.active_request.target_slots
            if s not in context.collected_slots
        ]
        
        if still_missing:
            context.active_request.attempt_count += 1
            
            if context.active_request.attempt_count >= self.max_retries_per_slot:
                # Escalate to handover
                return {
                    "success": False,
                    "action": "handover",
                    "reason": f"Could not extract: {still_missing}",
                }
            
            return {
                "success": False,
                "action": "retry",
                "missing": still_missing,
            }
        
        return {
            "success": True,
            "slots": context.collected_slots,
        }
```

---

## Module 4: Service Match Handler

### Purpose
Handle multiple matches, no matches, and ambiguous matches from service lookups.
Implements Steps 6-7 of your runtime loop.

### Directory Structure
```
core/workflows/
└── matching/
    ├── __init__.py
    ├── interfaces.py
    ├── models.py
    ├── handlers/
    │   ├── __init__.py
    │   ├── single_match.py
    │   ├── multiple_match.py
    │   ├── no_match.py
    │   └── fuzzy_match.py
    └── resolution.py      # Resolution strategies
```

### Match Models

```python
# core/workflows/matching/models.py
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from enum import Enum

class MatchType(Enum):
    SINGLE = "single"           # Exact single match
    MULTIPLE = "multiple"       # Multiple matches found
    FUZZY = "fuzzy"            # Close but not exact match
    AMBIGUOUS = "ambiguous"    # Low confidence match
    NONE = "none"              # No match found

class MatchResult(BaseModel):
    """Result of a service/item match operation."""
    match_type: MatchType
    
    # For single/fuzzy matches
    match: Optional[Dict[str, Any]] = Field(default=None)
    confidence: float = Field(default=1.0)
    
    # For multiple matches
    matches: List[Dict[str, Any]] = Field(default_factory=list)
    
    # For user selection
    needs_selection: bool = Field(default=False)
    selection_prompt: Optional[str] = Field(default=None)
    selection_options: List[Dict[str, Any]] = Field(default_factory=list)
    
    # For no match
    suggestions: List[Dict[str, Any]] = Field(default_factory=list)
    suggestion_prompt: Optional[str] = Field(default=None)

class MatchContext(BaseModel):
    """Context for match resolution."""
    query: str = Field(..., description="Original search query")
    entity_type: str = Field(..., description="Type being searched: service, provider, etc.")
    
    # User preferences for disambiguation
    preferences: Dict[str, Any] = Field(default_factory=dict)
    
    # Previous selections in this session
    previous_selections: List[Dict[str, Any]] = Field(default_factory=list)
```

### Match Handler

```python
# core/workflows/matching/handlers/multiple_match.py
class MultipleMatchHandler:
    """
    Handle multiple match scenarios.
    
    Strategies:
    1. Auto-select if one is clearly preferred (user history, default)
    2. Present options to user with clear differentiators
    3. Use LLM to rank matches based on context
    """
    
    def __init__(
        self,
        llm: Any,
        auto_select_threshold: float = 0.9,
        max_options_to_show: int = 5,
    ):
        self.llm = llm
        self.auto_select_threshold = auto_select_threshold
        self.max_options_to_show = max_options_to_show
    
    async def handle(
        self,
        matches: List[Dict[str, Any]],
        context: MatchContext,
    ) -> MatchResult:
        """Handle multiple matches."""
        
        # Score matches based on context
        scored_matches = await self._score_matches(matches, context)
        
        # Check if top match is clearly preferred
        if scored_matches[0]["score"] >= self.auto_select_threshold:
            return MatchResult(
                match_type=MatchType.SINGLE,
                match=scored_matches[0]["item"],
                confidence=scored_matches[0]["score"],
            )
        
        # Need user selection
        selection_options = self._format_options(scored_matches[:self.max_options_to_show])
        selection_prompt = await self._generate_selection_prompt(selection_options, context)
        
        return MatchResult(
            match_type=MatchType.MULTIPLE,
            matches=[m["item"] for m in scored_matches],
            needs_selection=True,
            selection_prompt=selection_prompt,
            selection_options=selection_options,
        )
    
    async def _score_matches(
        self,
        matches: List[Dict[str, Any]],
        context: MatchContext,
    ) -> List[Dict[str, Any]]:
        """Score matches based on relevance and user preferences."""
        
        scored = []
        for match in matches:
            score = 1.0
            
            # Boost based on user preferences
            if context.preferences:
                for pref_key, pref_val in context.preferences.items():
                    if match.get(pref_key) == pref_val:
                        score += 0.2
            
            # Boost based on previous selections
            for prev in context.previous_selections:
                if prev.get("id") == match.get("id"):
                    score += 0.3
                    break
            
            scored.append({"item": match, "score": min(score, 1.0)})
        
        return sorted(scored, key=lambda x: x["score"], reverse=True)
    
    def _format_options(
        self,
        scored_matches: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Format matches for user selection display."""
        
        options = []
        for i, match in enumerate(scored_matches, 1):
            item = match["item"]
            options.append({
                "index": i,
                "id": item.get("id"),
                "name": item.get("name"),
                "description": item.get("description", ""),
                "price": item.get("price"),
                "duration": item.get("duration"),
                "attributes": {
                    k: v for k, v in item.items()
                    if k not in ("id", "name", "description", "price", "duration")
                },
            })
        
        return options
```

---

## Module 5: Transaction Manager

### Purpose
Handle transactional operations with proper rollback and compensation.
Implements Step 10 of your runtime loop. **Critical for zero-latency checkpointing.**

### Directory Structure
```
core/workflows/
└── transactions/
    ├── __init__.py
    ├── interfaces.py
    ├── models.py
    ├── manager.py              # Main transaction manager
    ├── checkpoints/
    │   ├── __init__.py
    │   ├── lazy_checkpoint.py  # Lazy async checkpointing
    │   ├── wal.py             # Write-ahead log for durability
    │   └── recovery.py        # Recovery from checkpoints
    └── compensation/
        ├── __init__.py
        ├── actions.py         # Compensation action registry
        └── executor.py        # Compensation executor
```

### Zero-Latency Checkpoint Design

```python
# core/workflows/transactions/checkpoints/lazy_checkpoint.py
import asyncio
from collections import deque
from typing import Dict, Any, Optional
from datetime import datetime
import json

class LazyCheckpointManager:
    """
    Zero-latency checkpoint manager using lazy async persistence.
    
    Design principles:
    1. Checkpoint creation is O(1) - just adds to in-memory queue
    2. Background worker persists checkpoints asynchronously
    3. WAL (Write-Ahead Log) for crash recovery
    4. Configurable persistence strategies:
       - IMMEDIATE: Persist before returning (slow but safe)
       - LAZY: Persist in background (fast, eventual consistency)
       - BATCHED: Batch multiple checkpoints (throughput optimized)
    """
    
    def __init__(
        self,
        storage_path: str = ".checkpoints",
        strategy: str = "lazy",  # "immediate", "lazy", "batched"
        batch_size: int = 10,
        batch_timeout_ms: int = 100,
        wal_enabled: bool = True,
    ):
        self.storage_path = storage_path
        self.strategy = strategy
        self.batch_size = batch_size
        self.batch_timeout_ms = batch_timeout_ms
        self.wal_enabled = wal_enabled
        
        # In-memory checkpoint cache
        self._checkpoints: Dict[str, Dict[str, Any]] = {}
        self._pending_persist: deque = deque()
        
        # WAL for durability
        self._wal = WriteAheadLog(storage_path) if wal_enabled else None
        
        # Background persistence task
        self._persist_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def create_checkpoint(
        self,
        workflow_id: str,
        checkpoint_id: str,
        state: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a checkpoint - O(1), non-blocking.
        
        Returns immediately, persistence happens in background.
        """
        checkpoint = {
            "id": checkpoint_id,
            "workflow_id": workflow_id,
            "state": state,
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat(),
        }
        
        # 1. Add to in-memory cache (O(1))
        key = f"{workflow_id}:{checkpoint_id}"
        self._checkpoints[key] = checkpoint
        
        # 2. Write to WAL if enabled (fast append-only)
        if self._wal:
            await self._wal.append(checkpoint)
        
        # 3. Queue for background persistence
        if self.strategy != "immediate":
            self._pending_persist.append(checkpoint)
            self._ensure_background_worker()
        else:
            await self._persist_checkpoint(checkpoint)
        
        return checkpoint_id
    
    async def get_checkpoint(
        self,
        workflow_id: str,
        checkpoint_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get a checkpoint - tries memory first, then storage."""
        key = f"{workflow_id}:{checkpoint_id}"
        
        # Try in-memory first (O(1))
        if key in self._checkpoints:
            return self._checkpoints[key]
        
        # Fall back to storage
        return await self._load_from_storage(workflow_id, checkpoint_id)
    
    async def restore_from_checkpoint(
        self,
        workflow_id: str,
        checkpoint_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Restore workflow state from a checkpoint."""
        checkpoint = await self.get_checkpoint(workflow_id, checkpoint_id)
        
        if checkpoint:
            return checkpoint["state"]
        
        return None
    
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
                while len(batch) < self.batch_size:
                    try:
                        checkpoint = await asyncio.wait_for(
                            asyncio.get_event_loop().run_in_executor(
                                None,
                                lambda: self._pending_persist.popleft() if self._pending_persist else None
                            ),
                            timeout=timeout
                        )
                        if checkpoint:
                            batch.append(checkpoint)
                        else:
                            break
                    except asyncio.TimeoutError:
                        break
                
                # Persist batch
                if batch:
                    await self._persist_batch(batch)
                    
            except Exception as e:
                # Log error but don't crash worker
                print(f"Checkpoint persistence error: {e}")
            
            # Small sleep to prevent tight loop
            await asyncio.sleep(0.01)
    
    async def _persist_batch(self, batch: List[Dict[str, Any]]):
        """Persist a batch of checkpoints to storage."""
        import aiofiles
        import os
        
        os.makedirs(self.storage_path, exist_ok=True)
        
        for checkpoint in batch:
            workflow_id = checkpoint["workflow_id"]
            checkpoint_id = checkpoint["id"]
            
            filepath = os.path.join(
                self.storage_path,
                workflow_id,
                f"{checkpoint_id}.json"
            )
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            async with aiofiles.open(filepath, 'w') as f:
                await f.write(json.dumps(checkpoint, indent=2))
```

### Transaction Manager

```python
# core/workflows/transactions/manager.py
class TransactionManager:
    """
    Manages transactional operations with rollback support.
    
    Features:
    1. Automatic checkpoint creation at transaction boundaries
    2. Compensation action registry for rollback
    3. Idempotency key support for safe retries
    4. Two-phase commit for distributed operations
    """
    
    def __init__(
        self,
        checkpoint_manager: LazyCheckpointManager,
        compensation_registry: 'CompensationRegistry',
    ):
        self.checkpoint_manager = checkpoint_manager
        self.compensation_registry = compensation_registry
        
        # Active transactions
        self._transactions: Dict[str, 'Transaction'] = {}
    
    async def begin_transaction(
        self,
        workflow_id: str,
        transaction_id: Optional[str] = None,
        auto_checkpoint: bool = True,
    ) -> 'Transaction':
        """Begin a new transaction."""
        import uuid
        
        tx_id = transaction_id or str(uuid.uuid4())
        
        # Create pre-transaction checkpoint
        if auto_checkpoint:
            await self.checkpoint_manager.create_checkpoint(
                workflow_id=workflow_id,
                checkpoint_id=f"pre-tx-{tx_id}",
                state={"transaction_id": tx_id, "phase": "pre"},
            )
        
        tx = Transaction(
            id=tx_id,
            workflow_id=workflow_id,
            checkpoint_manager=self.checkpoint_manager,
            compensation_registry=self.compensation_registry,
        )
        
        self._transactions[tx_id] = tx
        return tx
    
    async def rollback_to_checkpoint(
        self,
        workflow_id: str,
        checkpoint_id: str,
    ) -> Dict[str, Any]:
        """Rollback workflow to a specific checkpoint."""
        
        # Get checkpoint state
        state = await self.checkpoint_manager.restore_from_checkpoint(
            workflow_id,
            checkpoint_id,
        )
        
        if not state:
            raise ValueError(f"Checkpoint not found: {checkpoint_id}")
        
        # Execute compensation actions for operations after checkpoint
        # (handled by Transaction.rollback())
        
        return state


class Transaction:
    """A single transaction with rollback support."""
    
    def __init__(
        self,
        id: str,
        workflow_id: str,
        checkpoint_manager: LazyCheckpointManager,
        compensation_registry: 'CompensationRegistry',
    ):
        self.id = id
        self.workflow_id = workflow_id
        self.checkpoint_manager = checkpoint_manager
        self.compensation_registry = compensation_registry
        
        self._operations: List[Dict[str, Any]] = []
        self._state: str = "active"  # active, committed, rolled_back
    
    async def record_operation(
        self,
        operation_type: str,
        args: Dict[str, Any],
        result: Any,
        compensation_action: Optional[str] = None,
    ):
        """Record an operation for potential rollback."""
        self._operations.append({
            "type": operation_type,
            "args": args,
            "result": result,
            "compensation_action": compensation_action or f"compensate_{operation_type}",
            "timestamp": datetime.utcnow().isoformat(),
        })
    
    async def commit(self):
        """Commit the transaction."""
        # Create post-transaction checkpoint
        await self.checkpoint_manager.create_checkpoint(
            workflow_id=self.workflow_id,
            checkpoint_id=f"post-tx-{self.id}",
            state={
                "transaction_id": self.id,
                "phase": "committed",
                "operations": self._operations,
            },
        )
        
        self._state = "committed"
    
    async def rollback(self):
        """Rollback the transaction by executing compensation actions."""
        # Execute compensation actions in reverse order
        for op in reversed(self._operations):
            action = self.compensation_registry.get(op["compensation_action"])
            if action:
                try:
                    await action.execute(op["args"], op["result"])
                except Exception as e:
                    # Log but continue with other compensations
                    print(f"Compensation failed for {op['type']}: {e}")
        
        self._state = "rolled_back"
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.rollback()
        else:
            await self.commit()
```

---

## Module 6: Handover Manager

### Purpose
Handle escalation to human agents when AI cannot proceed.
Implements Step 13 of your runtime loop.

### Directory Structure
```
core/workflows/
└── handover/
    ├── __init__.py
    ├── interfaces.py
    ├── models.py
    ├── manager.py
    ├── triggers/
    │   ├── __init__.py
    │   ├── policy_trigger.py      # Policy violation
    │   ├── failure_trigger.py     # Repeated failures
    │   ├── explicit_trigger.py    # User request
    │   └── complexity_trigger.py  # Complex issue detection
    └── channels/
        ├── __init__.py
        ├── queue_channel.py       # Add to queue
        ├── live_transfer.py       # Live transfer
        └── callback_channel.py    # Schedule callback
```

### Handover Models

```python
# core/workflows/handover/models.py
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from enum import Enum
from datetime import datetime

class HandoverReason(Enum):
    POLICY_VIOLATION = "policy_violation"
    REPEATED_FAILURE = "repeated_failure"
    USER_REQUEST = "user_request"
    COMPLEXITY = "complexity"
    UNKNOWN_INTENT = "unknown_intent"
    SENSITIVE_TOPIC = "sensitive_topic"
    SYSTEM_ERROR = "system_error"

class HandoverPriority(Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

class HandoverChannel(Enum):
    QUEUE = "queue"              # Add to human agent queue
    LIVE_TRANSFER = "live"       # Immediate transfer
    CALLBACK = "callback"        # Schedule callback
    TICKET = "ticket"            # Create support ticket

class HandoverPayload(BaseModel):
    """Payload for handover to human agent."""
    
    id: str = Field(..., description="Handover ID")
    reason: HandoverReason
    priority: HandoverPriority = Field(default=HandoverPriority.NORMAL)
    channel: HandoverChannel = Field(default=HandoverChannel.QUEUE)
    
    # Context for human agent
    summary: str = Field(..., description="AI-generated summary of the conversation")
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list)
    last_user_message: str = Field(default="")
    
    # What was tried
    attempted_actions: List[Dict[str, Any]] = Field(default_factory=list)
    tool_results: List[Dict[str, Any]] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    
    # Customer info
    customer_id: Optional[str] = Field(default=None)
    customer_context: Dict[str, Any] = Field(default_factory=dict)
    
    # Workflow context
    workflow_id: str = Field(default="")
    current_node: str = Field(default="")
    workflow_state: Dict[str, Any] = Field(default_factory=dict)
    
    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    escalated_at: Optional[datetime] = Field(default=None)
```

### Handover Manager

```python
# core/workflows/handover/manager.py
class HandoverManager:
    """
    Manages handover to human agents.
    
    Features:
    1. Automatic trigger detection
    2. Context summarization for human agents
    3. Multiple handover channels
    4. Handover metrics tracking
    """
    
    def __init__(
        self,
        llm: Any,
        triggers: List['IHandoverTrigger'],
        channels: Dict[HandoverChannel, 'IHandoverChannel'],
        default_channel: HandoverChannel = HandoverChannel.QUEUE,
    ):
        self.llm = llm
        self.triggers = triggers
        self.channels = channels
        self.default_channel = default_channel
    
    async def should_handover(
        self,
        context: 'WorkflowExecutionContext',
    ) -> Optional[HandoverReason]:
        """Check if handover should be triggered."""
        for trigger in self.triggers:
            reason = await trigger.check(context)
            if reason:
                return reason
        return None
    
    async def initiate_handover(
        self,
        reason: HandoverReason,
        context: 'WorkflowExecutionContext',
        channel: Optional[HandoverChannel] = None,
        priority: Optional[HandoverPriority] = None,
    ) -> HandoverPayload:
        """Initiate handover to human agent."""
        
        # Generate summary for human agent
        summary = await self._generate_summary(context)
        
        # Determine priority based on reason
        if priority is None:
            priority = self._get_priority_for_reason(reason)
        
        # Create handover payload
        payload = HandoverPayload(
            id=f"handover-{context.execution_id}-{datetime.utcnow().timestamp()}",
            reason=reason,
            priority=priority,
            channel=channel or self.default_channel,
            summary=summary,
            conversation_history=self._get_conversation_history(context),
            last_user_message=self._get_last_user_message(context),
            attempted_actions=self._get_attempted_actions(context),
            workflow_id=context.workflow_id,
            current_node=context.current_node_id or "",
            workflow_state=context.variables,
        )
        
        # Execute handover through channel
        selected_channel = self.channels.get(payload.channel)
        if selected_channel:
            await selected_channel.execute(payload)
        
        return payload
    
    async def _generate_summary(
        self,
        context: 'WorkflowExecutionContext',
    ) -> str:
        """Generate a summary of the conversation for human agents."""
        
        conversation = self._get_conversation_history(context)
        
        messages = [
            {
                "role": "system",
                "content": """Summarize this customer conversation for a human agent taking over.
Include:
1. What the customer wants
2. What was tried by the AI
3. Why handover is needed
4. Any relevant context (preferences, issues)
Keep it concise but complete."""
            },
            {
                "role": "user",
                "content": f"Conversation:\n{json.dumps(conversation, indent=2)}"
            }
        ]
        
        from core.llms import LLMContext
        response = await self.llm.get_answer(messages, LLMContext())
        return response.content
    
    def _get_priority_for_reason(self, reason: HandoverReason) -> HandoverPriority:
        """Map handover reason to priority."""
        priority_map = {
            HandoverReason.POLICY_VIOLATION: HandoverPriority.HIGH,
            HandoverReason.USER_REQUEST: HandoverPriority.HIGH,
            HandoverReason.SYSTEM_ERROR: HandoverPriority.URGENT,
            HandoverReason.REPEATED_FAILURE: HandoverPriority.NORMAL,
            HandoverReason.COMPLEXITY: HandoverPriority.NORMAL,
            HandoverReason.UNKNOWN_INTENT: HandoverPriority.LOW,
            HandoverReason.SENSITIVE_TOPIC: HandoverPriority.HIGH,
        }
        return priority_map.get(reason, HandoverPriority.NORMAL)
```

---

## Module 7: Policy Engine

### Purpose
Enforce business rules, rate limits, and security policies.
Implements Step 15 of your runtime loop.

### Directory Structure
```
core/workflows/
└── policies/
    ├── __init__.py
    ├── interfaces.py
    ├── models.py
    ├── engine.py               # Main policy engine
    ├── rules/
    │   ├── __init__.py
    │   ├── rate_limit.py       # Rate limiting
    │   ├── content_filter.py   # Content filtering
    │   ├── access_control.py   # Access control
    │   └── business_rules.py   # Business rules
    └── registry.py             # Policy registry
```

### Policy Models

```python
# core/workflows/policies/models.py
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from enum import Enum

class PolicyResult(Enum):
    ALLOW = "allow"
    DENY = "deny"
    WARN = "warn"
    RATE_LIMIT = "rate_limit"
    HANDOVER = "handover"

class PolicyViolation(BaseModel):
    """A policy violation."""
    policy_id: str
    policy_name: str
    result: PolicyResult
    reason: str
    suggested_action: str = Field(default="")
    
    # For rate limiting
    retry_after_seconds: Optional[int] = Field(default=None)
    remaining_quota: Optional[int] = Field(default=None)

class PolicyEvaluationResult(BaseModel):
    """Result of evaluating all policies."""
    allowed: bool = Field(default=True)
    violations: List[PolicyViolation] = Field(default_factory=list)
    
    # Actions to take
    should_handover: bool = Field(default=False)
    handover_reason: Optional[str] = Field(default=None)
    
    # Response modification
    response_filter: Optional[str] = Field(default=None)
    warning_message: Optional[str] = Field(default=None)
```

### Policy Engine

```python
# core/workflows/policies/engine.py
class PolicyEngine:
    """
    Central policy enforcement engine.
    
    Evaluates policies at different points:
    1. Pre-execution: Before processing user input
    2. Pre-tool: Before calling external tools
    3. Post-response: Before sending response to user
    4. Rate limits: Continuous monitoring
    """
    
    def __init__(
        self,
        policies: List['IPolicy'],
        rate_limiter: 'IRateLimiter',
        content_filter: 'IContentFilter',
    ):
        self.policies = policies
        self.rate_limiter = rate_limiter
        self.content_filter = content_filter
    
    async def evaluate_pre_execution(
        self,
        user_input: str,
        context: 'WorkflowExecutionContext',
    ) -> PolicyEvaluationResult:
        """Evaluate policies before processing user input."""
        
        violations = []
        
        # Check rate limits
        rate_result = await self.rate_limiter.check(
            user_id=context.variables.get("user_id"),
            action="message",
        )
        if not rate_result.allowed:
            violations.append(PolicyViolation(
                policy_id="rate_limit",
                policy_name="Rate Limit",
                result=PolicyResult.RATE_LIMIT,
                reason=f"Rate limit exceeded: {rate_result.reason}",
                retry_after_seconds=rate_result.retry_after,
                remaining_quota=rate_result.remaining,
            ))
        
        # Check content filter
        filter_result = await self.content_filter.check(user_input)
        if filter_result.flagged:
            violations.append(PolicyViolation(
                policy_id="content_filter",
                policy_name="Content Filter",
                result=PolicyResult.DENY if filter_result.block else PolicyResult.WARN,
                reason=filter_result.reason,
                suggested_action="handover" if filter_result.handover else "",
            ))
        
        # Evaluate custom policies
        for policy in self.policies:
            result = await policy.evaluate(user_input, context)
            if result.result != PolicyResult.ALLOW:
                violations.append(result)
        
        return PolicyEvaluationResult(
            allowed=not any(v.result == PolicyResult.DENY for v in violations),
            violations=violations,
            should_handover=any(v.suggested_action == "handover" for v in violations),
        )
    
    async def evaluate_pre_tool(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        context: 'WorkflowExecutionContext',
    ) -> PolicyEvaluationResult:
        """Evaluate policies before tool execution."""
        
        violations = []
        
        # Check tool-specific rate limits
        rate_result = await self.rate_limiter.check(
            user_id=context.variables.get("user_id"),
            action=f"tool:{tool_name}",
        )
        if not rate_result.allowed:
            violations.append(PolicyViolation(
                policy_id="tool_rate_limit",
                policy_name="Tool Rate Limit",
                result=PolicyResult.RATE_LIMIT,
                reason=f"Tool rate limit exceeded for {tool_name}",
                retry_after_seconds=rate_result.retry_after,
            ))
        
        # Validate tool arguments against policies
        for policy in self.policies:
            if hasattr(policy, 'evaluate_tool'):
                result = await policy.evaluate_tool(tool_name, tool_args, context)
                if result.result != PolicyResult.ALLOW:
                    violations.append(result)
        
        return PolicyEvaluationResult(
            allowed=not any(v.result == PolicyResult.DENY for v in violations),
            violations=violations,
        )
```

---

## Module 8: Deviation Handler

### Purpose
Handle mid-flow interruptions and deviations gracefully.
Implements Step 14 of your runtime loop.

### Integration with Existing Interrupt System

This builds on your existing `core/workflows/interrupt/` module:

```python
# core/workflows/interrupt/deviation.py
class DeviationHandler:
    """
    Handle deviations from the current flow.
    
    Types of deviations:
    1. Topic change - User asks about something unrelated
    2. Clarification request - User asks for clarification
    3. Correction - User corrects previous input
    4. Abort - User wants to stop current flow
    5. Interrupt - User sends new message during processing
    """
    
    def __init__(
        self,
        llm: Any,
        clarification_handler: 'ClarificationHandler',
        interrupt_manager: 'InterruptManager',
    ):
        self.llm = llm
        self.clarification_handler = clarification_handler
        self.interrupt_manager = interrupt_manager
    
    async def detect_deviation(
        self,
        user_message: str,
        current_flow: str,
        context: 'WorkflowExecutionContext',
    ) -> Optional['Deviation']:
        """Detect if user message is a deviation from current flow."""
        
        messages = [
            {
                "role": "system",
                "content": f"""Analyze if the user's message is a deviation from the current flow.

Current flow: {current_flow}
Current context: {json.dumps(context.variables)}

Respond with JSON:
{{
    "is_deviation": true/false,
    "deviation_type": "topic_change" | "clarification" | "correction" | "abort" | "continuation",
    "confidence": 0.0-1.0,
    "should_pause_flow": true/false,
    "response_strategy": "answer_and_resume" | "switch_flow" | "ask_to_continue" | "abort"
}}"""
            },
            {"role": "user", "content": user_message}
        ]
        
        from core.llms import LLMContext
        response = await self.llm.get_answer(
            messages,
            LLMContext(),
            response_format={"type": "json_object"},
        )
        
        return self._parse_deviation(response.content)
    
    async def handle_deviation(
        self,
        deviation: 'Deviation',
        context: 'WorkflowExecutionContext',
    ) -> 'DeviationResponse':
        """Handle a detected deviation."""
        
        if deviation.deviation_type == "abort":
            return await self._handle_abort(context)
        
        if deviation.deviation_type == "clarification":
            return await self._handle_clarification(deviation, context)
        
        if deviation.deviation_type == "topic_change":
            if deviation.should_pause_flow:
                # Save current flow state for potential resume
                await self._pause_flow(context)
            return await self._handle_topic_change(deviation, context)
        
        if deviation.deviation_type == "correction":
            return await self._handle_correction(deviation, context)
        
        # Default: continue with current flow
        return DeviationResponse(
            action="continue",
            resume_flow=True,
        )
    
    async def _pause_flow(self, context: 'WorkflowExecutionContext'):
        """Pause current flow and save state for later resume."""
        
        from core.workflows.transactions import LazyCheckpointManager
        
        checkpoint_manager = context.get_checkpoint_manager()
        if checkpoint_manager:
            await checkpoint_manager.create_checkpoint(
                workflow_id=context.workflow_id,
                checkpoint_id=f"paused-{datetime.utcnow().timestamp()}",
                state={
                    "type": "paused",
                    "current_node": context.current_node_id,
                    "variables": context.variables,
                    "execution_path": context.execution_path,
                },
                metadata={"reason": "deviation_pause"},
            )
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1-2)
1. **Task Queue Manager** - Core queuing infrastructure
2. **Lazy Checkpoint System** - Zero-latency checkpointing
3. **Transaction Manager** - Basic transaction support

### Phase 2: Intelligence Layer (Week 3-4)
1. **Intent Classifier** - LLM-based classification
2. **Slot Extractor** - Entity extraction
3. **Clarification Handler** - Missing slot handling

### Phase 3: Resolution & Matching (Week 5)
1. **Service Match Handler** - Multiple match resolution
2. **Flow Router** - Intent to flow mapping
3. **Tool Input Assembler** - Variable preparation

### Phase 4: Safety & Escalation (Week 6)
1. **Policy Engine** - Rate limits, content filtering
2. **Handover Manager** - Human escalation
3. **Deviation Handler** - Mid-flow interruption handling

### Phase 5: Integration & Testing (Week 7-8)
1. **Integration with existing workflow engine**
2. **End-to-end testing with salon workflow**
3. **Performance benchmarking**
4. **Documentation**

---

## Performance Guarantees

### Zero-Latency Checkpointing
- Checkpoint creation: O(1) - in-memory only
- Background persistence: async, batched
- WAL for crash recovery

### Task Queue Performance
- Enqueue: O(log n)
- Dequeue: O(log n)
- Interrupt check: O(1)

### Memory Efficiency
- LRU cache for checkpoints
- Lazy loading of old checkpoints
- Configurable memory limits

---

## File Changes Summary

### New Directories
```
core/workflows/
├── taskqueue/           # NEW - Task queue manager
├── classification/      # NEW - Intent/slot classification
├── clarification/       # NEW - Clarification handling
├── matching/            # NEW - Service match resolution
├── transactions/        # NEW - Transaction & checkpoint management
├── handover/           # NEW - Human escalation
├── policies/           # NEW - Policy enforcement
└── interrupt/          # EXISTING - Enhanced with deviation handler
```

### Enhanced Existing Files
- `core/workflows/spec/workflow_models.py` - Add task_queue reference
- `core/workflows/interfaces/workflow_interfaces.py` - Add new protocols
- `core/memory/working_memory/default.py` - Integration with new checkpointing

---

## Next Steps

1. Review and approve this architecture plan
2. Prioritize modules based on immediate needs
3. Begin implementation with Phase 1 (Foundation)
4. Create test cases for each module (extend `test_salon_workflow.py`)

Would you like me to proceed with implementing any specific module first?


