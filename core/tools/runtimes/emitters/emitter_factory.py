"""
Emitter Factory for Tools Specification System.

Provides a centralized way to create and register event emitter implementations by name.
"""

from typing import Dict

from ...interfaces.tool_interfaces import IToolEmitter
from .noop_emitter import NoOpEmitter

from ...constants import (
    NOOP,
    UNKNOWN_EMITTER_ERROR,
    COMMA,
    SPACE
)


class EmitterFactory:
    """
    Factory for creating event emitter instances.
    
    Built-in Emitter Implementations:
        - 'noop': NoOpEmitter - No event emission (for testing/development)
    
    Usage:
        # Get built-in emitter
        emitter = EmitterFactory.get_emitter('noop')
        
        # Register custom emitter implementation
        EmitterFactory.register('eventbridge', EventBridgeEmitter())
        emitter = EmitterFactory.get_emitter('eventbridge')
    """
    
    _emitters: Dict[str, IToolEmitter] = {
        NOOP: NoOpEmitter(),
    }
    
    @classmethod
    def get_emitter(cls, name: str = NOOP) -> IToolEmitter:
        """
        Get an emitter implementation by name.
        
        Args:
            name: Emitter implementation name ('noop', 'eventbridge', etc.)
            
        Returns:
            IToolEmitter instance
            
        Raises:
            ValueError: If emitter name is not registered
        """
        emitter = cls._emitters.get(name)
        
        if not emitter:
            available = (COMMA + SPACE).join(cls._emitters.keys())
            raise ValueError(
                UNKNOWN_EMITTER_ERROR.format(EMITTER_NAME=name, AVAILABLE_EMITTERS=available)
            )
        
        return emitter
    
    @classmethod
    def register(cls, name: str, emitter: IToolEmitter):
        """
        Register a custom emitter implementation.
        
        Args:
            name: Name to register the emitter under
            emitter: Emitter instance implementing IToolEmitter
        
        Example:
            class EventBridgeEmitter(IToolEmitter):
                async def emit(self, event_type: str, payload: Dict[str, Any]):
                    await eventbridge_client.put_events(...)
            
            EmitterFactory.register('eventbridge', EventBridgeEmitter())
        """
        cls._emitters[name] = emitter

