"""
Azure OpenAI Models.

Model-specific configurations and implementations for Azure OpenAI.
"""

from .gpt_4_1_mini import GPT_4_1_MiniMetadata, GPT_4_1_MiniLLM
from .registry import register_azure_models

__all__ = [
    "GPT_4_1_MiniMetadata",
    "GPT_4_1_MiniLLM",
    "register_azure_models",
]



