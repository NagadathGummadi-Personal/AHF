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
- Dynamic variable substitution: {variable_name}
- Conditional prompt loading: {# if condition #}...{# endif #}
- LLM and human evaluation scores
- Runtime metrics tracking (latency, tokens, cost)
- Local file-based storage (JSON/YAML)
- Extensible storage backends

Conditional Syntax:
==================
    - {# if condition #}...{# endif #}
    - {# if condition #}...{# else #}...{# endif #}
    - {# if condition #}...{# elif condition #}...{# else #}...{# endif #}

Condition Types:
    - Boolean: {# if is_premium #}
    - Negation: {# if not is_active #}
    - Comparison: {# if age >= 18 #}
    - Equality: {# if status == 'active' #}
    - Membership: {# if 'admin' in roles #}
    - Logical: {# if is_active and is_verified #}

Usage:
======
    from core.promptregistry import (
        LocalPromptRegistry,
        PromptMetadata,
        PromptEnvironment,
        PromptType,
        ConditionalProcessor,
        process_conditionals,
    )
    
    # Create registry
    registry = LocalPromptRegistry(storage_path=".prompts")
    
    # Save prompt with conditionals and variables
    await registry.save_prompt(
        label="greeting",
        content='''
        {# if is_formal #}
        Good day, {name}. How may I assist you today?
        {# else #}
        Hey {name}! What's up?
        {# endif #}
        ''',
        metadata=PromptMetadata(
            model_target="gpt-4",
            environment=PromptEnvironment.PROD,
            prompt_type=PromptType.SYSTEM,
        )
    )
    
    # Get prompt - conditionals and variables are processed automatically
    result = await registry.get_prompt(
        "greeting",
        variables={"is_formal": True, "name": "Dr. Smith"}
    )
    # Output: "Good day, Dr. Smith. How may I assist you today?"
    
    # Direct conditional processing
    template = "{# if is_premium #}Premium{# else #}Free{# endif #}"
    result = process_conditionals(template, {"is_premium": True})
    # Output: "Premium"
    
    # Get required variables for a prompt
    variables = await registry.get_dynamic_variables("greeting")
    
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
    # Conditional Processing
    ConditionalProcessor,
    process_conditionals,
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
    # Conditional Processing
    "ConditionalProcessor",
    "process_conditionals",
    # Defaults
    "load_default_prompts",
    "get_default_prompt_labels",
    "initialize_default_prompts",
]

