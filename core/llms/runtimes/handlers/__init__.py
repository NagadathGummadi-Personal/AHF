"""
LLM Structured Output Handlers.

Provides pluggable handlers for structured output validation and retry logic.

Available handlers:
- BasicStructuredHandler: Full validation with retries
- NoOpStructuredHandler: Return raw content without validation

Usage:
    from core.llms.runtimes.handlers import StructuredHandlerFactory
    
    # Get specific handler
    handler = StructuredHandlerFactory.get_handler('basic')
"""

from .basic_structured_handler import BasicStructuredHandler
from .noop_structured_handler import NoOpStructuredHandler
from .structured_handler_factory import StructuredHandlerFactory

__all__ = [
    "BasicStructuredHandler",
    "NoOpStructuredHandler",
    "StructuredHandlerFactory",
]

