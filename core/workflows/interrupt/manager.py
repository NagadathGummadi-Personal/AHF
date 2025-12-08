"""
Interrupt Manager.

Manages interrupt signals and coordinates interrupt handling
across components.

Version: 1.0.0
"""

import asyncio
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING
from threading import Lock

from pydantic import BaseModel, Field

from .config import InterruptConfig, DEFAULT_INTERRUPT_CONFIG
from .state import InterruptState, StashedResponse, InterruptReason

if TYPE_CHECKING:
    from core.llms import ILLM


class InterruptSignal(BaseModel):
    """
    An interrupt signal.
    
    Attributes:
        reason: Reason for the interrupt
        source: Source of the interrupt (user, system, etc.)
        timestamp: When the signal was created
        priority: Signal priority (higher = more important)
        new_message: Optional new message from user
    """
    reason: InterruptReason = Field(
        default=InterruptReason.USER_INTERRUPT,
        description="Reason for the interrupt"
    )
    source: str = Field(
        default="user",
        description="Source of the interrupt"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the signal was created"
    )
    priority: int = Field(
        default=1,
        ge=0,
        description="Signal priority"
    )
    new_message: Optional[str] = Field(
        default=None,
        description="New message from user (if any)"
    )


class InterruptManager:
    """
    Manages interrupt signals and state for a component.
    
    The manager handles:
    - Receiving and processing interrupt signals
    - Stashing partial responses
    - Waiting for follow-up messages
    - Coordinating continuation with LLM
    
    Usage:
        manager = InterruptManager(config)
        
        # Check for interrupt during streaming
        async for chunk in stream:
            if manager.is_interrupted():
                manager.stash_partial_response(
                    content=accumulated,
                    component_type="llm",
                    component_id="gpt-4",
                )
                break
            yield chunk
        
        # After interrupt
        if manager.has_followup():
            context = await manager.create_continuation_context(llm)
    """
    
    def __init__(
        self,
        config: Optional[InterruptConfig] = None,
        component_id: str = "default",
        component_type: str = "unknown",
    ):
        """
        Initialize interrupt manager.
        
        Args:
            config: Interrupt configuration
            component_id: ID of the component being managed
            component_type: Type of component (llm, agent, node, workflow)
        """
        self.config = config or DEFAULT_INTERRUPT_CONFIG
        self.component_id = component_id
        self.component_type = component_type
        
        self._state = InterruptState()
        self._lock = Lock()
        self._signal_handlers: List[Callable[[InterruptSignal], None]] = []
        self._pending_signal: Optional[InterruptSignal] = None
        
        # Async event for waiting
        self._interrupt_event: Optional[asyncio.Event] = None
        self._followup_event: Optional[asyncio.Event] = None
    
    @property
    def state(self) -> InterruptState:
        """Get current interrupt state."""
        return self._state
    
    @property
    def is_enabled(self) -> bool:
        """Check if interrupts are enabled."""
        return self.config.enabled
    
    # =========================================================================
    # Signal Handling
    # =========================================================================
    
    def signal_interrupt(
        self,
        reason: InterruptReason = InterruptReason.USER_INTERRUPT,
        new_message: Optional[str] = None,
        source: str = "user",
        priority: int = 1,
    ):
        """
        Send an interrupt signal.
        
        Args:
            reason: Reason for interrupt
            new_message: Optional new message from user
            source: Source of interrupt
            priority: Signal priority
        """
        if not self.is_enabled:
            return
        
        signal = InterruptSignal(
            reason=reason,
            source=source,
            priority=priority,
            new_message=new_message,
        )
        
        with self._lock:
            self._pending_signal = signal
            self._state.set_interrupted(reason)
            
            # If there's a new message, record it
            if new_message:
                self._state.receive_followup(new_message)
        
        # Set event for async waiting
        if self._interrupt_event:
            self._interrupt_event.set()
        
        # Notify handlers
        for handler in self._signal_handlers:
            try:
                handler(signal)
            except Exception:
                pass  # Don't let handler errors stop interrupt
    
    def is_interrupted(self) -> bool:
        """Check if an interrupt signal has been received."""
        return self._state.is_interrupted
    
    def clear_interrupt(self):
        """Clear the interrupt state."""
        with self._lock:
            self._state.reset()
            self._pending_signal = None
        
        if self._interrupt_event:
            self._interrupt_event.clear()
    
    def add_signal_handler(self, handler: Callable[[InterruptSignal], None]):
        """Add a handler to be called on interrupt signals."""
        self._signal_handlers.append(handler)
    
    def remove_signal_handler(self, handler: Callable[[InterruptSignal], None]):
        """Remove a signal handler."""
        if handler in self._signal_handlers:
            self._signal_handlers.remove(handler)
    
    # =========================================================================
    # Response Stashing
    # =========================================================================
    
    def stash_partial_response(
        self,
        content: str,
        component_type: Optional[str] = None,
        component_id: Optional[str] = None,
        conversation_messages: Optional[List[Dict[str, Any]]] = None,
        last_user_message: Optional[str] = None,
        tokens_generated: int = 0,
        execution_progress: Optional[float] = None,
        pending_tool_call: Optional[Dict[str, Any]] = None,
        tool_results: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Stash a partial response for later continuation.
        
        Args:
            content: The partial response content
            component_type: Type of component
            component_id: ID of component
            conversation_messages: Conversation history
            last_user_message: Last user message
            tokens_generated: Tokens generated before interrupt
            execution_progress: Progress (0-1)
            pending_tool_call: Pending tool call
            tool_results: Collected tool results
            metadata: Additional metadata
        """
        if not self.config.stash_partial_response:
            return
        
        stashed = StashedResponse(
            content=content,
            component_type=component_type or self.component_type,
            component_id=component_id or self.component_id,
            interrupt_reason=self._state.interrupt_reason or InterruptReason.USER_INTERRUPT,
            last_user_message=last_user_message,
            conversation_messages=conversation_messages or [],
            tokens_generated=tokens_generated,
            execution_progress=execution_progress,
            pending_tool_call=pending_tool_call,
            tool_results=tool_results or [],
            metadata=metadata or {},
        )
        
        with self._lock:
            self._state.stashed_response = stashed
    
    def has_stashed_response(self) -> bool:
        """Check if there's a stashed response."""
        return self._state.has_stashed_response()
    
    def get_stashed_response(self) -> Optional[StashedResponse]:
        """Get the stashed response."""
        return self._state.stashed_response
    
    def clear_stashed_response(self):
        """Clear the stashed response."""
        with self._lock:
            self._state.stashed_response = None
    
    # =========================================================================
    # Follow-up Handling
    # =========================================================================
    
    async def wait_for_followup(self) -> bool:
        """
        Wait for a follow-up message after interrupt.
        
        Returns:
            True if follow-up received, False if timeout
        """
        if not self.is_enabled:
            return False
        
        timeout_ms = self.config.wait_for_followup_ms
        if timeout_ms <= 0:
            return False
        
        self._state.start_waiting_for_followup(timeout_ms)
        self._followup_event = asyncio.Event()
        
        try:
            await asyncio.wait_for(
                self._followup_event.wait(),
                timeout=timeout_ms / 1000.0
            )
            return True
        except asyncio.TimeoutError:
            self._state.waiting_for_followup = False
            return False
    
    def receive_message(self, message: str):
        """
        Receive a new message (potential follow-up).
        
        Args:
            message: The new message
        """
        with self._lock:
            if self._state.waiting_for_followup:
                self._state.receive_followup(message)
                
                if self._followup_event:
                    self._followup_event.set()
            else:
                # New message while not waiting = new interrupt
                self.signal_interrupt(
                    reason=InterruptReason.USER_INTERRUPT,
                    new_message=message,
                )
    
    def has_followup(self) -> bool:
        """Check if a follow-up message was received."""
        return self._state.followup_received
    
    def get_followup_message(self) -> Optional[str]:
        """Get the follow-up message."""
        return self._state.followup_message
    
    # =========================================================================
    # Continuation Context
    # =========================================================================
    
    def get_continuation_messages(
        self,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get messages for continuation including stashed response context.
        
        Args:
            conversation_history: Optional conversation history
            
        Returns:
            List of messages for continuation
        """
        messages = []
        
        # Add conversation history
        if self.config.include_conversation_history:
            history = conversation_history or []
            if self._state.stashed_response:
                history = history or self._state.stashed_response.conversation_messages
            
            # Limit history length
            max_messages = self.config.max_history_messages
            if len(history) > max_messages:
                history = history[-max_messages:]
            
            messages.extend(history)
        
        # Add continuation context
        if self._state.should_combine_with_followup():
            stashed = self._state.stashed_response
            followup = self._state.followup_message
            
            # Create continuation prompt
            continuation_prompt = self.config.continuation_prompt_template.format(
                stashed_response=stashed.content if stashed else "",
                new_message=followup or "",
            )
            
            messages.append({
                "role": "user",
                "content": continuation_prompt,
            })
        elif self._state.followup_message:
            # Just the follow-up, no stashed response
            messages.append({
                "role": "user",
                "content": self._state.followup_message,
            })
        
        return messages
    
    async def create_continuation_response(
        self,
        llm: 'ILLM',
        ctx: Any,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> Any:
        """
        Create a continuation response using LLM.
        
        Args:
            llm: LLM instance for generating response
            ctx: LLM context
            conversation_history: Optional conversation history
            **kwargs: Additional LLM parameters
            
        Returns:
            LLMResponse with continuation
        """
        if not self.config.auto_combine_responses:
            return None
        
        messages = self.get_continuation_messages(conversation_history)
        
        if not messages:
            return None
        
        # Generate continuation
        response = await llm.get_answer(messages, ctx, **kwargs)
        
        # Record continuation
        with self._lock:
            self._state.continuation_generated = True
            if hasattr(response, 'content'):
                self._state.continuation_content = str(response.content)
        
        return response
    
    # =========================================================================
    # Async Context Support
    # =========================================================================
    
    async def check_interrupt_async(self) -> bool:
        """
        Async check for interrupt (can be awaited in loops).
        
        Returns:
            True if interrupted
        """
        # Brief yield to allow interrupt signals to be processed
        await asyncio.sleep(0)
        return self.is_interrupted()
    
    def create_interruptable_iterator(self, iterator):
        """
        Wrap an async iterator to be interruptable.
        
        Args:
            iterator: Async iterator to wrap
            
        Yields:
            Items from iterator until interrupt
        """
        async def wrapper():
            accumulated = ""
            async for item in iterator:
                if self.is_interrupted():
                    # Stash accumulated content
                    if accumulated and hasattr(item, 'content'):
                        self.stash_partial_response(
                            content=accumulated,
                        )
                    break
                
                # Track accumulated content for stashing
                if hasattr(item, 'content'):
                    accumulated += item.content
                
                yield item
        
        return wrapper()
    
    # =========================================================================
    # Cleanup
    # =========================================================================
    
    def reset(self):
        """Reset the manager state."""
        with self._lock:
            self._state.reset()
            self._pending_signal = None
        
        if self._interrupt_event:
            self._interrupt_event.clear()
        if self._followup_event:
            self._followup_event.clear()


# Global interrupt managers (for singleton access)
_interrupt_managers: Dict[str, InterruptManager] = {}
_global_lock = Lock()


def get_interrupt_manager(
    component_id: str,
    component_type: str = "unknown",
    config: Optional[InterruptConfig] = None,
) -> InterruptManager:
    """
    Get or create an interrupt manager for a component.
    
    Args:
        component_id: Component identifier
        component_type: Type of component
        config: Optional configuration
        
    Returns:
        InterruptManager instance
    """
    key = f"{component_type}:{component_id}"
    
    with _global_lock:
        if key not in _interrupt_managers:
            _interrupt_managers[key] = InterruptManager(
                config=config,
                component_id=component_id,
                component_type=component_type,
            )
        return _interrupt_managers[key]


def clear_interrupt_managers():
    """Clear all interrupt managers."""
    with _global_lock:
        for manager in _interrupt_managers.values():
            manager.reset()
        _interrupt_managers.clear()

