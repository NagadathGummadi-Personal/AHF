"""
Evaluator Factory.

Provides factory methods for creating prompt evaluators.
"""

from typing import Dict, List, Optional, Type, TYPE_CHECKING

from .interfaces import IPromptEvaluator
from .llm_evaluator import LLMPromptEvaluator
from .human_evaluator import HumanPromptEvaluator
from .composite_evaluator import CompositeEvaluator

if TYPE_CHECKING:
    from core.llms import ILLM


class PromptEvaluatorFactory:
    """
    Factory for creating prompt evaluators.
    
    Supports registration of custom evaluator implementations.
    
    Usage:
        # Create LLM evaluator
        evaluator = PromptEvaluatorFactory.create("llm", llm=judge_llm)
        
        # Create composite evaluator
        evaluator = PromptEvaluatorFactory.create_composite(
            ["llm", "human"],
            llm=judge_llm,
        )
    """
    
    _evaluators: Dict[str, Type[IPromptEvaluator]] = {
        "llm": LLMPromptEvaluator,
        "human": HumanPromptEvaluator,
        "composite": CompositeEvaluator,
    }
    
    @classmethod
    def register(
        cls,
        evaluator_type: str,
        evaluator_class: Type[IPromptEvaluator],
    ) -> None:
        """Register a custom evaluator implementation."""
        cls._evaluators[evaluator_type] = evaluator_class
    
    @classmethod
    def create(
        cls,
        evaluator_type: str,
        **kwargs,
    ) -> IPromptEvaluator:
        """
        Create an evaluator by type.
        
        Args:
            evaluator_type: Type of evaluator (llm, human, composite)
            **kwargs: Arguments passed to evaluator constructor
            
        Returns:
            IPromptEvaluator instance
        """
        evaluator_class = cls._evaluators.get(evaluator_type)
        if evaluator_class is None:
            raise ValueError(f"Unknown evaluator type: {evaluator_type}")
        
        return evaluator_class(**kwargs)
    
    @classmethod
    def create_llm_evaluator(
        cls,
        llm: Optional['ILLM'] = None,
        **kwargs,
    ) -> LLMPromptEvaluator:
        """Create an LLM-as-judge evaluator."""
        return LLMPromptEvaluator(llm=llm, **kwargs)
    
    @classmethod
    def create_human_evaluator(
        cls,
        **kwargs,
    ) -> HumanPromptEvaluator:
        """Create a human evaluator."""
        return HumanPromptEvaluator(**kwargs)
    
    @classmethod
    def create_composite(
        cls,
        evaluator_types: List[str],
        weights: Optional[Dict[str, float]] = None,
        **kwargs,
    ) -> CompositeEvaluator:
        """
        Create a composite evaluator with multiple sub-evaluators.
        
        Args:
            evaluator_types: List of evaluator types to include
            weights: Optional weights by evaluator type
            **kwargs: Arguments passed to sub-evaluators
            
        Returns:
            CompositeEvaluator instance
        """
        evaluators = []
        for etype in evaluator_types:
            if etype == "composite":
                continue  # Avoid recursive composites
            evaluator = cls.create(etype, **kwargs)
            evaluators.append(evaluator)
        
        return CompositeEvaluator(
            evaluators=evaluators,
            weights=weights,
        )
    
    @classmethod
    def list_types(cls) -> List[str]:
        """List available evaluator types."""
        return list(cls._evaluators.keys())


# Default evaluator instance
_default_evaluator: Optional[IPromptEvaluator] = None


async def get_default_evaluator(
    llm: Optional['ILLM'] = None,
) -> IPromptEvaluator:
    """
    Get the default evaluator instance.
    
    Creates an LLM evaluator if not already created.
    
    Args:
        llm: Optional LLM to use as judge
        
    Returns:
        IPromptEvaluator instance
    """
    global _default_evaluator
    
    if _default_evaluator is None:
        _default_evaluator = PromptEvaluatorFactory.create_llm_evaluator(llm=llm)
    
    return _default_evaluator

