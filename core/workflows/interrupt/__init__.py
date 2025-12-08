"""
Interrupt Handling Module for Workflows.

Provides interrupt capabilities for workflows, nodes, agents, LLMs, and tools.
When interrupted, the current response is stashed and the system waits for
a follow-up message to create a combined response.

Features:
- Interruptable flag on all components
- Stash partial responses for context
- Configurable wait time for follow-up messages
- LLM-based response combination using conversation history

Usage:
    from core.workflows.interrupt import (
        InterruptConfig,
        InterruptManager,
        InterruptState,
    )
    
    # Configure interrupts
    config = InterruptConfig(
        enabled=True,
        wait_for_followup_ms=500,
    )
    
    # Create manager
    manager = InterruptManager(config)
    
    # During execution
    async for chunk in llm.stream_answer(messages, ctx):
        if manager.is_interrupted():
            manager.stash_partial_response(accumulated_response)
            break
        yield chunk
    
    # After interrupt, if new message arrives
    if manager.has_stashed_response():
        combined_context = manager.get_continuation_context(
            new_message=user_message,
            conversation_history=messages,
        )
        # Continue with combined context

Version: 1.0.0
"""

from .config import (
    InterruptConfig,
    DEFAULT_INTERRUPT_CONFIG,
)
from .state import (
    InterruptState,
    StashedResponse,
    InterruptReason,
)
from .manager import (
    InterruptManager,
    InterruptSignal,
)
from .continuation import (
    ContinuationContext,
    create_continuation_prompt,
)

__all__ = [
    # Config
    "InterruptConfig",
    "DEFAULT_INTERRUPT_CONFIG",
    # State
    "InterruptState",
    "StashedResponse",
    "InterruptReason",
    # Manager
    "InterruptManager",
    "InterruptSignal",
    # Continuation
    "ContinuationContext",
    "create_continuation_prompt",
]

