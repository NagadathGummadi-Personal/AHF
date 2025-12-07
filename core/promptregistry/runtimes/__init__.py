"""
Runtime implementations for Prompt Registry.

All components are pluggable:
- Storage: LocalFileStorage (default), or any IPromptStorage implementation
- Validators: NoOpPromptValidator, BasicPromptValidator, or custom
- Security: NoOpPromptSecurity, RoleBasedPromptSecurity, or custom
- LLM Integration: PromptAwareLLM wrapper for automatic metrics tracking
"""

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

from .llm_integration import (
    PromptAwareLLM,
    call_with_prompt,
)

__all__ = [
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
    # LLM Integration
    "PromptAwareLLM",
    "call_with_prompt",
]

