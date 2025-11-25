"""
Observer Factory for Agents.

Provides factory methods for creating observer implementations.
"""

from typing import Dict, Type

from ...interfaces.agent_interfaces import IAgentObserver
from .noop_observer import NoOpObserver
from .logging_observer import LoggingObserver


class ObserverFactory:
    """
    Factory for creating agent observer implementations.
    
    Usage:
        observer = ObserverFactory.get_observer('logging')
        
        # Register custom observer
        ObserverFactory.register('custom', CustomObserver)
    """
    
    _observer_map: Dict[str, Type[IAgentObserver]] = {
        'noop': NoOpObserver,
        'logging': LoggingObserver,
        'default': NoOpObserver,
    }
    
    @classmethod
    def get_observer(cls, name: str) -> IAgentObserver:
        """
        Get an observer implementation by name.
        
        Args:
            name: Observer implementation name
            
        Returns:
            Observer instance
        """
        name_lower = name.lower()
        observer_class = cls._observer_map.get(name_lower)
        
        if not observer_class:
            raise ValueError(
                f"Unknown observer: {name}. Available: {list(cls._observer_map.keys())}"
            )
        
        return observer_class()
    
    @classmethod
    def register(cls, name: str, observer_class: Type[IAgentObserver]) -> None:
        """Register a custom observer implementation."""
        cls._observer_map[name.lower()] = observer_class
    
    @classmethod
    def list_available(cls) -> list:
        """List all registered observer implementations."""
        return list(cls._observer_map.keys())

