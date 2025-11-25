"""
Interfaces for LLM Subsystem.

Exports all protocol interfaces for pluggable components.
"""

from .llm_interfaces import (
    ILLM,
    ILLMValidator,
    IParameterTransformer,
    IResponseParser,
    IStructuredOutputHandler,
    IPayloadBuilder,
    IConnector,
    IModelRegistry,
    Messages,
    Parameters,
)

__all__ = [
    # Core LLM interface
    "ILLM",
    # Pluggable component interfaces
    "ILLMValidator",
    "IParameterTransformer",
    "IResponseParser",
    "IStructuredOutputHandler",
    "IPayloadBuilder",
    # Infrastructure interfaces
    "IConnector",
    "IModelRegistry",
    # Type aliases
    "Messages",
    "Parameters",
]
