"""
Runtime implementations for Prompt Registry.

All components are pluggable:
- Storage: LocalFileStorage (default), or any IPromptStorage implementation
- Validators: NoOpPromptValidator, BasicPromptValidator, or custom
- Security: NoOpPromptSecurity, RoleBasedPromptSecurity, or custom
- BasePromptRegistry: Abstract base class for creating custom registries

Note: LLM usage tracking is now handled directly in core/llms.
      Use llm.set_prompt_registry(registry) and pass prompt_id in LLMContext.
"""

from .base_registry import BasePromptRegistry
from .storage import (
    LocalPromptRegistry,
    LocalFileStorage,
)
from .registry_factory import PromptRegistryFactory

from .validators import (
    NoOpPromptValidator,
    BasicPromptValidator,
    PromptValidatorFactory,
)

from .security import (
    NoOpPromptSecurity,
    RoleBasedPromptSecurity,
    PromptSecurityFactory,
)

__all__ = [
    # Base
    "BasePromptRegistry",
    # Storage
    "LocalPromptRegistry",
    "LocalFileStorage",
    "PromptRegistryFactory",
    # Validators
    "NoOpPromptValidator",
    "BasicPromptValidator",
    "PromptValidatorFactory",
    # Security
    "NoOpPromptSecurity",
    "RoleBasedPromptSecurity",
    "PromptSecurityFactory",
]

