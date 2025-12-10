"""
Checklist Factory for Agents.

Provides factory methods for creating checklist implementations.
"""

from typing import Dict, Type

from ...interfaces import IAgentChecklist
from ...constants import UNKNOWN_CHECKLIST_ERROR
from .basic_checklist import BasicChecklist


class ChecklistFactory:
    """
    Factory for creating agent checklist implementations.
    
    Usage:
        # Get built-in checklist
        checklist = ChecklistFactory.get_checklist('basic')
        
        # Register custom checklist
        ChecklistFactory.register('persistent', PersistentChecklist)
    """
    
    _checklist_map: Dict[str, Type[IAgentChecklist]] = {
        'basic': BasicChecklist,
        'default': BasicChecklist,
    }
    
    @classmethod
    def get_checklist(cls, name: str = 'basic') -> IAgentChecklist:
        """
        Get a checklist implementation by name.
        
        Args:
            name: Checklist implementation name
            
        Returns:
            Checklist instance
        """
        name_lower = name.lower()
        checklist_class = cls._checklist_map.get(name_lower)
        
        if not checklist_class:
            raise ValueError(
                UNKNOWN_CHECKLIST_ERROR.format(
                    CHECKLIST_NAME=name,
                    AVAILABLE_CHECKLISTS=list(cls._checklist_map.keys())
                )
            )
        
        return checklist_class()
    
    @classmethod
    def register(cls, name: str, checklist_class: Type[IAgentChecklist]) -> None:
        """Register a custom checklist implementation."""
        cls._checklist_map[name.lower()] = checklist_class
    
    @classmethod
    def unregister(cls, name: str) -> None:
        """Unregister a checklist implementation."""
        name_lower = name.lower()
        if name_lower in ('basic', 'default'):
            raise ValueError(f"Cannot unregister built-in checklist: {name}")
        cls._checklist_map.pop(name_lower, None)
    
    @classmethod
    def list_available(cls) -> list:
        """List all registered checklist implementations."""
        return list(cls._checklist_map.keys())



