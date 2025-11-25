"""
Prompt Registry Subsystem.

This module provides a centralized store for managing prompts, supporting
versioning, model-specific variations, and fine-tuning context.

Features:
=========
- Version management for prompts
- Model-specific prompt variations
- Performance metrics tracking
- Local file-based storage
- Extensible storage backends

Usage:
======
    from core.promptregistry import LocalPromptRegistry, PromptMetadata
    
    # Create registry
    registry = LocalPromptRegistry(storage_path=".prompts")
    
    # Save prompt
    await registry.save_prompt(
        label="code_review",
        content="Review this code for bugs and improvements...",
        metadata=PromptMetadata(
            model_target="gpt-4",
            tags=["code", "review"]
        )
    )
    
    # Get prompt (auto-selects version/model)
    prompt = await registry.get_prompt("code_review", model="gpt-4")
    
    # List versions
    versions = await registry.list_versions("code_review")
    
    # Update metrics after testing
    await registry.update_metrics(prompt_id, {"accuracy": 0.95})
"""

from .constants import (
    DEFAULT_VERSION,
    DEFAULT_STORAGE_PATH,
    STORAGE_FORMAT_JSON,
    STORAGE_FORMAT_YAML,
)

from .enum import (
    PromptStatus,
    PromptCategory,
)

from .interfaces import (
    IPromptRegistry,
    IPromptStorage,
)

from .spec import (
    PromptMetadata,
    PromptEntry,
    PromptVersion,
)

from .runtimes import (
    LocalPromptRegistry,
    LocalFileStorage,
    PromptRegistryFactory,
)

__all__ = [
    # Constants
    "DEFAULT_VERSION",
    "DEFAULT_STORAGE_PATH",
    "STORAGE_FORMAT_JSON",
    "STORAGE_FORMAT_YAML",
    # Enums
    "PromptStatus",
    "PromptCategory",
    # Interfaces
    "IPromptRegistry",
    "IPromptStorage",
    # Spec
    "PromptMetadata",
    "PromptEntry",
    "PromptVersion",
    # Runtimes
    "LocalPromptRegistry",
    "LocalFileStorage",
    "PromptRegistryFactory",
]

