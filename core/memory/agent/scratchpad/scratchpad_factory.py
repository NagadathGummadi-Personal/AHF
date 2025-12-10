"""
Scratchpad Factory for Agents.

Provides factory methods for creating scratchpad implementations.
"""

from typing import Dict, Type

from ...interfaces import IAgentScratchpad
from ...constants import UNKNOWN_SCRATCHPAD_ERROR
from .basic_scratchpad import BasicScratchpad
from .structured_scratchpad import StructuredScratchpad


class ScratchpadFactory:
    """
    Factory for creating agent scratchpad implementations.
    
    Usage:
        # Get built-in scratchpad
        scratchpad = ScratchpadFactory.get_scratchpad('basic')
        scratchpad = ScratchpadFactory.get_scratchpad('structured')
        
        # Register custom scratchpad
        ScratchpadFactory.register('custom', CustomScratchpad)
    """
    
    _scratchpad_map: Dict[str, Type[IAgentScratchpad]] = {
        'basic': BasicScratchpad,
        'structured': StructuredScratchpad,
        'default': BasicScratchpad,
    }
    
    @classmethod
    def get_scratchpad(cls, name: str) -> IAgentScratchpad:
        """
        Get a scratchpad implementation by name.
        
        Args:
            name: Scratchpad implementation name
            
        Returns:
            Scratchpad instance
        """
        name_lower = name.lower()
        scratchpad_class = cls._scratchpad_map.get(name_lower)
        
        if not scratchpad_class:
            raise ValueError(
                UNKNOWN_SCRATCHPAD_ERROR.format(
                    SCRATCHPAD_NAME=name,
                    AVAILABLE_SCRATCHPADS=list(cls._scratchpad_map.keys())
                )
            )
        
        return scratchpad_class()
    
    @classmethod
    def register(cls, name: str, scratchpad_class: Type[IAgentScratchpad]) -> None:
        """Register a custom scratchpad implementation."""
        cls._scratchpad_map[name.lower()] = scratchpad_class
    
    @classmethod
    def unregister(cls, name: str) -> None:
        """Unregister a scratchpad implementation."""
        name_lower = name.lower()
        if name_lower in ('basic', 'structured', 'default'):
            raise ValueError(f"Cannot unregister built-in scratchpad: {name}")
        cls._scratchpad_map.pop(name_lower, None)
    
    @classmethod
    def list_available(cls) -> list:
        """List all registered scratchpad implementations."""
        return list(cls._scratchpad_map.keys())



