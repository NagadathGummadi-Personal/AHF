"""
Base classes for LLM providers.

Defines abstract base classes for connectors, implementations, and metadata.
"""

from .connector import BaseConnector
from .implementation import BaseLLM
from .metadata import BaseMetadata

__all__ = [
    "BaseConnector",
    "BaseLLM",
    "BaseMetadata",
]



