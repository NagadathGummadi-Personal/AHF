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
- Dynamic variable substitution with {{var|default:value}} syntax
- Conditional prompt blocks with Python expressions
- Recursive variable replacement
- LLM and human evaluation system (async, non-blocking)
- Runtime metrics tracking (latency, tokens, cost)
- Local file-based storage (JSON/YAML) with async I/O
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
    
    # Save prompt with new {{variable}} syntax and conditionals
    await registry.save_prompt(
        label="greeting",
        content=\"\"\"{{#if is_new_user}}Welcome to our service, {{user_name|default:Guest}}!
{{#else}}Welcome back, {{user_name}}!{{#endif}}\"\"\",
        metadata=PromptMetadata(
            model_target="gpt-4",
            environment=PromptEnvironment.PROD,
            prompt_type=PromptType.SYSTEM,
        )
    )
    
    # Get prompt with fallback and variable substitution
    result = await registry.get_prompt_with_fallback(
        "greeting",
        model="gpt-4",
        environment=PromptEnvironment.PROD,
        variables={"user_name": "Alice", "is_new_user": True}
    )
    
    # Evaluate prompt quality (async, non-blocking)
    from core.promptregistry.evaluators import LLMPromptEvaluator
    evaluator = LLMPromptEvaluator()
    eval_result = await evaluator.evaluate(request)
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
    # Expression Engine
    SafeExpressionEvaluator,
    ExpressionError,
)

from .evaluators import (
    # Interfaces
    IPromptEvaluator,
    EvaluationRequest,
    EvaluationResponse,
    # Implementations
    LLMPromptEvaluator,
    HumanPromptEvaluator,
    CompositeEvaluator,
    # Factory
    PromptEvaluatorFactory,
    get_default_evaluator,
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
    # Expression Engine
    "SafeExpressionEvaluator",
    "ExpressionError",
    # Evaluators
    "IPromptEvaluator",
    "EvaluationRequest",
    "EvaluationResponse",
    "LLMPromptEvaluator",
    "HumanPromptEvaluator",
    "CompositeEvaluator",
    "PromptEvaluatorFactory",
    "get_default_evaluator",
    # Defaults
    "load_default_prompts",
    "get_default_prompt_labels",
    "initialize_default_prompts",
]

