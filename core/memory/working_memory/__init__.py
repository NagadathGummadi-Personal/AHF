"""
Working Memory Module.

Provides base class and implementations for working memory.
Extend BaseWorkingMemory to create custom working memory for different workflows.

Version: 1.0.0
"""

from .base import BaseWorkingMemory
from .default import DefaultWorkingMemory, WorkingMemory

__all__ = [
    "BaseWorkingMemory",
    "DefaultWorkingMemory",
    "WorkingMemory",  # Alias for backward compatibility
]
