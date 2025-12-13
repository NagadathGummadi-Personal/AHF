"""
Timeout Management

Handles soft timeouts and engagement messages.

Version: 1.0.0
"""

import asyncio
from datetime import datetime
from typing import Any, Callable, Optional

from air.config import Defaults


class TimeoutManager:
    """
    Manages various timeouts for conversation flow.
    
    Timeouts:
    - Soft timeout: Time before generating engagement message
    - Turn timeout: Max silence before prompting user
    - Response timeout: Max time for agent response
    """
    
    def __init__(
        self,
        soft_timeout_ms: int = Defaults.SOFT_TIMEOUT_MS,
        turn_timeout_ms: int = Defaults.TURN_TIMEOUT_MS,
    ):
        self._soft_timeout_ms = soft_timeout_ms
        self._turn_timeout_ms = turn_timeout_ms
        
        # Active timers
        self._soft_timer: Optional[asyncio.Task] = None
        self._turn_timer: Optional[asyncio.Task] = None
        
        # Callbacks
        self._on_soft_timeout: Optional[Callable] = None
        self._on_turn_timeout: Optional[Callable] = None
        
        # State
        self._is_waiting = False
        self._last_activity = datetime.utcnow()
    
    def set_soft_timeout_callback(self, callback: Callable) -> None:
        """Set callback for soft timeout."""
        self._on_soft_timeout = callback
    
    def set_turn_timeout_callback(self, callback: Callable) -> None:
        """Set callback for turn timeout."""
        self._on_turn_timeout = callback
    
    async def start_waiting(self) -> None:
        """Start waiting for user input (activates timeouts)."""
        self._is_waiting = True
        self._last_activity = datetime.utcnow()
        
        # Start soft timeout
        if self._soft_timer:
            self._soft_timer.cancel()
        
        self._soft_timer = asyncio.create_task(self._soft_timeout_task())
        
        # Start turn timeout
        if self._turn_timer:
            self._turn_timer.cancel()
        
        self._turn_timer = asyncio.create_task(self._turn_timeout_task())
    
    async def stop_waiting(self) -> None:
        """Stop waiting (user responded or workflow moved on)."""
        self._is_waiting = False
        
        if self._soft_timer:
            self._soft_timer.cancel()
            self._soft_timer = None
        
        if self._turn_timer:
            self._turn_timer.cancel()
            self._turn_timer = None
    
    def reset_activity(self) -> None:
        """Reset activity timestamp (e.g., when user starts speaking)."""
        self._last_activity = datetime.utcnow()
    
    async def _soft_timeout_task(self) -> None:
        """Task that handles soft timeout."""
        try:
            await asyncio.sleep(self._soft_timeout_ms / 1000)
            
            if self._is_waiting and self._on_soft_timeout:
                await self._on_soft_timeout()
        except asyncio.CancelledError:
            pass
    
    async def _turn_timeout_task(self) -> None:
        """Task that handles turn timeout."""
        try:
            await asyncio.sleep(self._turn_timeout_ms / 1000)
            
            if self._is_waiting and self._on_turn_timeout:
                await self._on_turn_timeout()
        except asyncio.CancelledError:
            pass


class SoftTimeoutHandler:
    """
    Handler for soft timeouts.
    
    Generates engagement messages to keep user engaged
    during processing.
    """
    
    # Default engagement messages
    ENGAGEMENT_MESSAGES = [
        "Just a moment...",
        "Let me check that for you...",
        "One second please...",
        "I'm looking that up...",
    ]
    
    def __init__(
        self,
        custom_messages: Optional[list] = None,
    ):
        self._messages = custom_messages or self.ENGAGEMENT_MESSAGES
        self._message_index = 0
    
    def get_engagement_message(self) -> str:
        """Get the next engagement message."""
        message = self._messages[self._message_index % len(self._messages)]
        self._message_index += 1
        return message
    
    async def create_engagement_response(self) -> dict:
        """Create an engagement response for the user."""
        return {
            "type": "engagement",
            "message": self.get_engagement_message(),
            "timestamp": datetime.utcnow().isoformat(),
        }

