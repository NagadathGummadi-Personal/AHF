"""
LLM Runtimes - Pluggable Components and Core Infrastructure.

This module provides:
1. Pluggable runtime components for LLM operations:
   - validators: Message and parameter validation
   - transformers: Parameter transformations
   - parsers: Response parsing
   - handlers: Structured output handling

2. Core infrastructure:
   - Model Registry: Registration and lookup of models
   - LLM Factory: Creating LLM instances

All components implement interfaces from llms.interfaces for easy swapping.
"""

# Pluggable Components
from .validators import BasicLLMValidator, NoOpLLMValidator, LLMValidatorFactory
from .transformers import (
    AzureGPT4Transformer,
    NoOpTransformer,
    TransformerFactory,
)
from .parsers import AzureResponseParser, NoOpResponseParser, ParserFactory
from .handlers import (
    BasicStructuredHandler,
    NoOpStructuredHandler,
    StructuredHandlerFactory,
)

# Core Infrastructure
from .model_registry import ModelRegistry, get_model_registry, reset_registry
from .llm_factory import LLMFactory

__all__ = [
    # Validators
    "BasicLLMValidator",
    "NoOpLLMValidator",
    "LLMValidatorFactory",
    # Transformers
    "AzureGPT4Transformer",
    "NoOpTransformer",
    "TransformerFactory",
    # Parsers
    "AzureResponseParser",
    "NoOpResponseParser",
    "ParserFactory",
    # Handlers
    "BasicStructuredHandler",
    "NoOpStructuredHandler",
    "StructuredHandlerFactory",
    # Core Infrastructure
    "ModelRegistry",
    "get_model_registry",
    "reset_registry",
    "LLMFactory",
]
