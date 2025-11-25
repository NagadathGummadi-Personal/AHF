"""
Structured Output Handler Factory.

Provides a centralized way to create and register handlers by name.
"""

from typing import Dict
from ...interfaces.llm_interfaces import IStructuredOutputHandler
from .basic_structured_handler import BasicStructuredHandler
from .noop_structured_handler import NoOpStructuredHandler


# Constants
BASIC = "basic"
NOOP = "noop"


class StructuredHandlerFactory:
    """
    Factory for creating structured output handler instances.
    
    Built-in Handlers:
        - 'basic': BasicStructuredHandler - Full validation with retries
        - 'noop': NoOpStructuredHandler - No validation (pass-through)
    
    Usage:
        # Get built-in handler
        handler = StructuredHandlerFactory.get_handler('basic')
        
        # Register custom handler
        StructuredHandlerFactory.register('my_custom', MyCustomHandler())
    """
    
    _handlers: Dict[str, IStructuredOutputHandler] = {
        BASIC: BasicStructuredHandler(),
        NOOP: NoOpStructuredHandler(),
    }
    
    @classmethod
    def get_handler(cls, name: str = BASIC) -> IStructuredOutputHandler:
        """
        Get a handler by name.
        
        Args:
            name: Handler name ('basic', 'noop', etc.)
            
        Returns:
            IStructuredOutputHandler instance
            
        Raises:
            ValueError: If handler name is not registered
        """
        handler = cls._handlers.get(name)
        
        if not handler:
            available = ", ".join(cls._handlers.keys())
            raise ValueError(
                f"Unknown handler: '{name}'. Available handlers: {available}"
            )
        
        return handler
    
    @classmethod
    def register(cls, name: str, handler: IStructuredOutputHandler) -> None:
        """
        Register a custom handler.
        
        Args:
            name: Name to register the handler under
            handler: Handler instance implementing IStructuredOutputHandler
        """
        cls._handlers[name] = handler
    
    @classmethod
    def list_handlers(cls) -> list:
        """
        List all registered handler names.
        
        Returns:
            List of handler names
        """
        return list(cls._handlers.keys())

