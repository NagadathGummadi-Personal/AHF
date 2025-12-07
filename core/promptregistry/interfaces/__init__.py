"""
Interfaces for Prompt Registry Subsystem.

All components are designed to be pluggable:
- IPromptRegistry: Main registry interface
- IPromptStorage: Storage backend interface
- IPromptValidator: Validation interface
- IPromptSecurity: Security/access control interface
"""

from .prompt_registry_interfaces import (
    IPromptRegistry,
    IPromptStorage,
    IPromptValidator,
    IPromptSecurity,
    ValidationResult,
    SecurityContext,
    AccessDecision,
)

__all__ = [
    # Registry interfaces
    "IPromptRegistry",
    "IPromptStorage",
    # Validation interfaces
    "IPromptValidator",
    "ValidationResult",
    # Security interfaces
    "IPromptSecurity",
    "SecurityContext",
    "AccessDecision",
]

