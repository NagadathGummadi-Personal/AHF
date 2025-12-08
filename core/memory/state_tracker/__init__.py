"""
State Tracker Module.

Provides base class and implementations for state tracking.
Extend BaseStateTracker to create custom state tracking for different workflows.

Version: 1.0.0
"""

from .base import BaseStateTracker
from .default import DefaultStateTracker, InMemoryStateTracker

__all__ = [
    "BaseStateTracker",
    "DefaultStateTracker",
    "InMemoryStateTracker",  # Alias for backward compatibility
]
