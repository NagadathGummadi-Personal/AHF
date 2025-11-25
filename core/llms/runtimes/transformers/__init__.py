"""
LLM Parameter Transformers.

Provides pluggable transformers for converting standard parameters
to model-specific formats.

Available transformers:
- AzureGPT4Transformer: For GPT-4.x models (max_tokens → max_completion_tokens)
- NoOpTransformer: No transformation (pass-through)

Usage:
    from core.llms.runtimes.transformers import TransformerFactory
    
    # Get default transformer
    transformer = TransformerFactory.get_transformer()
    
    # Get specific transformer
    transformer = TransformerFactory.get_transformer('azure_gpt4')
"""

from .azure_gpt4_transformer import AzureGPT4Transformer
from .noop_transformer import NoOpTransformer
from .transformer_factory import TransformerFactory

__all__ = [
    "AzureGPT4Transformer",
    "NoOpTransformer",
    "TransformerFactory",
]

