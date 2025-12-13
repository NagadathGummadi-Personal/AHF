"""
Prompt Evaluators for quality assessment.

Provides async evaluators for measuring prompt quality using:
- LLM-as-judge evaluation (automated)
- Human evaluation (manual ranking)
- Composite evaluation (combining multiple evaluators)

All evaluators run asynchronously and do not block the main workflow.

Usage:
    from core.promptregistry.evaluators import (
        LLMPromptEvaluator,
        HumanPromptEvaluator,
        CompositeEvaluator,
    )
    
    # LLM evaluation
    evaluator = LLMPromptEvaluator(llm=judge_llm)
    result = await evaluator.evaluate(
        prompt_id="prompt-123",
        prompt_content="You are a helpful assistant...",
        llm_response="Sure, I can help with that.",
    )
    
    # Human evaluation (queue-based)
    human_evaluator = HumanPromptEvaluator(store=metrics_store)
    await human_evaluator.submit_for_review(
        prompt_id="prompt-123",
        prompt_content="...",
        llm_response="...",
    )

Version: 1.0.0
"""

from .interfaces import (
    IPromptEvaluator,
    EvaluationRequest,
    EvaluationResponse,
)

from .llm_evaluator import LLMPromptEvaluator
from .human_evaluator import HumanPromptEvaluator
from .composite_evaluator import CompositeEvaluator
from .evaluator_factory import (
    PromptEvaluatorFactory,
    get_default_evaluator,
)

__all__ = [
    # Interfaces
    "IPromptEvaluator",
    "EvaluationRequest",
    "EvaluationResponse",
    # Implementations
    "LLMPromptEvaluator",
    "HumanPromptEvaluator",
    "CompositeEvaluator",
    # Factory
    "PromptEvaluatorFactory",
    "get_default_evaluator",
]

