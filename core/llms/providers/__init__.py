"""
LLM Providers.

This module contains provider-specific implementations organized by cloud provider.
Each provider has a shared connector, base implementation, and model-specific configurations.
"""

# Lazy imports to avoid import-time dependencies (e.g., aiohttp)
def create_azure_llm(*args, **kwargs):
    """Create Azure LLM instance. Lazy import to avoid aiohttp dependency at import time."""
    from .azure import create_azure_llm as _create_azure_llm
    return _create_azure_llm(*args, **kwargs)


def create_openai_llm(*args, **kwargs):
    """Create OpenAI LLM instance. Lazy import."""
    from .openai import create_openai_llm as _create_openai_llm
    return _create_openai_llm(*args, **kwargs)


__all__ = [
    "create_azure_llm",
    "create_openai_llm",
]

