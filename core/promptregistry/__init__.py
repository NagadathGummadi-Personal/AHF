"""
Prompt Registry Subsystem.

This module provides a centralized store for managing prompts, supporting
versioning, model-specific variations, environment-based deployment, and
comprehensive metrics tracking.

Features:
=========
- Version management for prompts (immutable versions)
- Model-specific prompt variations (different prompts per LLM)
- Environment-based deployment (prod, staging, dev, test) with fallback
- Dynamic variable substitution in templates
- LLM and human evaluation scores
- Runtime metrics tracking (latency, tokens, cost)
- Local file-based storage (JSON/YAML)
- Extensible storage backends

Usage:
======
    from core.promptregistry import (
        LocalPromptRegistry,
        PromptMetadata,
        PromptEnvironment,
        PromptType,
    )
    
    # Create registry
    registry = LocalPromptRegistry(storage_path=".prompts")
    
    # Save prompt with full metadata
    await registry.save_prompt(
        label="code_review",
        content="Review this {language} code for {review_type}...",
        metadata=PromptMetadata(
            model_target="gpt-4",
            environment=PromptEnvironment.PROD,
            prompt_type=PromptType.SYSTEM,
            tags=["code", "review"],
            llm_eval_score=0.95,
            human_eval_score=0.92
        )
    )
    
    # Get prompt with fallback and variable substitution
    result = await registry.get_prompt_with_fallback(
        "code_review",
        model="gpt-4",
        environment=PromptEnvironment.PROD,
        variables={"language": "Python", "review_type": "bugs"}
    )
    
    # Get required variables for a prompt
    variables = await registry.get_dynamic_variables("code_review")
    
    # Record runtime usage
    await registry.record_usage(
        prompt_id,
        latency_ms=150,
        prompt_tokens=100,
        completion_tokens=50,
        cost=0.001
    )
"""

from .constants import (
    DEFAULT_VERSION,
    DEFAULT_STORAGE_PATH,
    DEFAULT_ENVIRONMENT,
    STORAGE_FORMAT_JSON,
    STORAGE_FORMAT_YAML,
    # Agent prompt labels
    PROMPT_LABEL_REACT_AGENT,
    PROMPT_LABEL_GOAL_BASED_PLANNING,
    PROMPT_LABEL_GOAL_BASED_EXECUTION,
    PROMPT_LABEL_GOAL_BASED_FINAL,
    PROMPT_LABEL_HIERARCHICAL_MANAGER,
)

from .enum import (
    PromptStatus,
    PromptCategory,
    PromptEnvironment,
    PromptType,
)

from .interfaces import (
    IPromptRegistry,
    IPromptStorage,
    IPromptValidator,
    IPromptSecurity,
    ValidationResult,
    SecurityContext,
    AccessDecision,
)

from .spec import (
    PromptMetadata,
    PromptEntry,
    PromptVersion,
    PromptTemplate,
    PromptRetrievalResult,
    RuntimeMetrics,
)

from .runtimes import (
    LocalPromptRegistry,
    LocalFileStorage,
    PromptRegistryFactory,
    # Validators
    NoOpPromptValidator,
    BasicPromptValidator,
    PromptValidatorFactory,
    # Security
    NoOpPromptSecurity,
    RoleBasedPromptSecurity,
    PromptSecurityFactory,
)

from .defaults import (
    load_default_prompts,
    get_default_prompt_labels,
    initialize_default_prompts,
)

__all__ = [
    # Constants
    "DEFAULT_VERSION",
    "DEFAULT_STORAGE_PATH",
    "DEFAULT_ENVIRONMENT",
    "STORAGE_FORMAT_JSON",
    "STORAGE_FORMAT_YAML",
    # Agent prompt labels
    "PROMPT_LABEL_REACT_AGENT",
    "PROMPT_LABEL_GOAL_BASED_PLANNING",
    "PROMPT_LABEL_GOAL_BASED_EXECUTION",
    "PROMPT_LABEL_GOAL_BASED_FINAL",
    "PROMPT_LABEL_HIERARCHICAL_MANAGER",
    # Enums
    "PromptStatus",
    "PromptCategory",
    "PromptEnvironment",
    "PromptType",
    # Interfaces
    "IPromptRegistry",
    "IPromptStorage",
    "IPromptValidator",
    "IPromptSecurity",
    "ValidationResult",
    "SecurityContext",
    "AccessDecision",
    # Spec
    "PromptMetadata",
    "PromptEntry",
    "PromptVersion",
    "PromptTemplate",
    "PromptRetrievalResult",
    "RuntimeMetrics",
    # Runtimes
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
    # Defaults
    "load_default_prompts",
    "get_default_prompt_labels",
    "initialize_default_prompts",
]

