"""
Interrupt Handler

Manages workflow interrupts, response stashing, and context preservation.

Version: 1.0.0
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, Optional
import uuid

from pydantic import BaseModel, Field

from core.memory.interfaces import IInterruptHandler
from app.config import Defaults
from app.memory.session import VoiceAgentSession
from app.models.workflow_state import StashedResponse


class InterruptConfig(BaseModel):
    """Configuration for interrupt handling."""
    
    # Check interval for interrupt detection
    check_interval_ms: int = Field(default=Defaults.INTERRUPT_CHECK_INTERVAL_MS)
    
    # Whether to include stashed content in continuation
    include_stashed_in_continuation: bool = Field(default=True)
    
    # Maximum stash age before discarding
    max_stash_age_ms: int = Field(default=30000)
    
    # Auto-clear interrupt after handling
    auto_clear: bool = Field(default=True)


class InterruptHandler:
    """
    Handler for workflow interrupts.
    
    Responsibilities:
    - Detect user interrupts during response generation
    - Stash partial responses for context preservation
    - Provide continuation context after interrupt
    - Manage interrupt state lifecycle
    
    Design:
    - O(1) interrupt check via session.has_interrupt_sync()
    - Non-blocking stashing
    - Context preservation for natural conversation flow
    """
    
    def __init__(
        self,
        session: VoiceAgentSession,
        config: Optional[InterruptConfig] = None,
    ):
        self._session = session
        self._config = config or InterruptConfig()
        
        # Interrupt state
        self._is_interrupted = False
        self._interrupt_message: Optional[str] = None
        self._stashed_response: Optional[StashedResponse] = None
        
        # Tracking
        self._interrupt_count = 0
        self._last_interrupt_time: Optional[datetime] = None
    
    @property
    def is_interrupted(self) -> bool:
        """Check if currently interrupted."""
        return self._is_interrupted or self._session.is_interrupted()
    
    async def check_for_interrupt(self) -> bool:
        """
        Check for pending interrupts.
        
        This is an O(1) operation using the task queue.
        
        Returns:
            True if interrupt detected
        """
        # Check task queue for interrupt-priority tasks
        has_interrupt = self._session.has_interrupt_sync()
        
        if has_interrupt and not self._is_interrupted:
            self._is_interrupted = True
            self._last_interrupt_time = datetime.utcnow()
            self._interrupt_count += 1
        
        return has_interrupt
    
    async def trigger_interrupt(
        self,
        reason: str,
        user_message: Optional[str] = None,
    ) -> None:
        """
        Trigger an interrupt explicitly.
        
        Args:
            reason: Reason for interrupt
            user_message: User message that caused interrupt
        """
        self._is_interrupted = True
        self._interrupt_message = user_message or reason
        self._last_interrupt_time = datetime.utcnow()
        self._interrupt_count += 1
        
        # Update session state
        self._session.workflow_state.is_interrupted = True
        self._session.workflow_state.pending_interrupt = user_message
    
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
        stash_id = str(uuid.uuid4())[:8]
        
        self._stashed_response = StashedResponse(
            stash_id=stash_id,
            content=content,
            node_id=node_id or self._session.get_current_node(),
            interrupted_at=datetime.utcnow(),
            interrupt_message=self._interrupt_message,
            include_in_continuation=self._config.include_stashed_in_continuation,
        )
        
        # Also store in session for persistence
        self._session.stash_response(
            content=content,
            interrupt_message=self._interrupt_message or "User interrupted",
            node_id=node_id,
        )
        
        return stash_id
    
    async def get_stashed_response(self) -> Optional[Dict[str, Any]]:
        """Get the stashed response."""
        if self._stashed_response:
            return {
                "stash_id": self._stashed_response.stash_id,
                "content": self._stashed_response.content,
                "node_id": self._stashed_response.node_id,
                "interrupted_at": self._stashed_response.interrupted_at.isoformat(),
                "interrupt_message": self._stashed_response.interrupt_message,
            }
        return None
    
    async def get_continuation_context(self) -> Optional[str]:
        """
        Get context for continuing after interrupt.
        
        Returns a prompt addition that informs the agent about
        the interrupted response and user's new message.
        """
        if not self._stashed_response:
            return self._session.get_stashed_context()
        
        if not self._config.include_stashed_in_continuation:
            return None
        
        return self._stashed_response.get_continuation_context()
    
    async def clear_interrupt(self) -> Optional[Dict[str, Any]]:
        """
        Clear interrupt state.
        
        Returns:
            Stashed response if any
        """
        stashed = await self.get_stashed_response()
        
        self._is_interrupted = False
        self._interrupt_message = None
        self._stashed_response = None
        
        # Clear session state
        self._session.workflow_state.is_interrupted = False
        self._session.workflow_state.pending_interrupt = None
        self._session.workflow_state.stashed_response = None
        
        return stashed
    
    def create_interrupt_aware_generator(
        self,
        generator,
        on_interrupt: Optional[callable] = None,
    ):
        """
        Wrap a generator to be interrupt-aware.
        
        Checks for interrupts between each yield and
        handles stashing automatically.
        
        Args:
            generator: Async generator to wrap
            on_interrupt: Callback when interrupt detected
            
        Yields:
            Items from generator until interrupt
        """
        async def wrapped():
            accumulated_content = ""
            
            async for item in generator:
                # Check for interrupt
                if await self.check_for_interrupt():
                    # Stash accumulated content
                    if accumulated_content:
                        await self.stash_response(accumulated_content)
                    
                    # Call interrupt handler
                    if on_interrupt:
                        await on_interrupt(accumulated_content, self._interrupt_message)
                    
                    return
                
                # Accumulate content for potential stashing
                if isinstance(item, dict) and "chunk" in item:
                    accumulated_content += item["chunk"]
                elif isinstance(item, str):
                    accumulated_content += item
                
                yield item
        
        return wrapped()
    
    async def wait_for_interrupt(
        self,
        timeout_ms: Optional[int] = None,
    ) -> bool:
        """
        Wait for an interrupt to occur.
        
        Args:
            timeout_ms: Maximum time to wait
            
        Returns:
            True if interrupt occurred
        """
        timeout = (timeout_ms or 60000) / 1000
        start_time = asyncio.get_event_loop().time()
        
        while True:
            if await self.check_for_interrupt():
                return True
            
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= timeout:
                return False
            
            await asyncio.sleep(self._config.check_interval_ms / 1000)

