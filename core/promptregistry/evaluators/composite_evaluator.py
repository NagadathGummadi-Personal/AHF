"""
Composite Prompt Evaluator.

Combines multiple evaluators for comprehensive prompt assessment.
"""

import asyncio
from typing import Any, Dict, List, Optional

from .interfaces import IPromptEvaluator, EvaluationRequest, EvaluationResponse


class CompositeEvaluator(IPromptEvaluator):
    """
    Combines multiple evaluators for comprehensive assessment.
    
    Can run evaluators in parallel and aggregate their results.
    
    Usage:
        composite = CompositeEvaluator([
            LLMPromptEvaluator(llm=judge_llm),
            RuleBasedEvaluator(),
        ])
        
        response = await composite.evaluate(request)
    """
    
    def __init__(
        self,
        evaluators: List[IPromptEvaluator],
        weights: Optional[Dict[str, float]] = None,
        parallel: bool = True,
    ):
        """
        Initialize composite evaluator.
        
        Args:
            evaluators: List of evaluators to use
            weights: Optional weights by evaluator type
            parallel: Run evaluators in parallel
        """
        self._evaluators = evaluators
        self._weights = weights or {}
        self._parallel = parallel
    
    @property
    def evaluator_type(self) -> str:
        return "composite"
    
    async def evaluate(
        self,
        request: EvaluationRequest,
    ) -> EvaluationResponse:
        """Run all evaluators and aggregate results."""
        if self._parallel:
            tasks = [e.evaluate(request) for e in self._evaluators]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
        else:
            responses = []
            for evaluator in self._evaluators:
                try:
                    resp = await evaluator.evaluate(request)
                    responses.append(resp)
                except Exception as e:
                    responses.append(e)
        
        # Filter out exceptions
        valid_responses = [
            r for r in responses
            if isinstance(r, EvaluationResponse)
        ]
        
        if not valid_responses:
            return EvaluationResponse(
                request_id=request.id,
                prompt_id=request.prompt_id,
                evaluator_type="composite",
                overall_score=0.0,
                feedback="All evaluators failed",
            )
        
        # Aggregate scores with weights
        aggregated_scores: Dict[str, float] = {}
        score_counts: Dict[str, int] = {}
        
        for response in valid_responses:
            weight = self._weights.get(response.evaluator_type, 1.0)
            
            for key, value in response.scores.items():
                if key not in aggregated_scores:
                    aggregated_scores[key] = 0.0
                    score_counts[key] = 0
                
                aggregated_scores[key] += value * weight
                score_counts[key] += 1
        
        # Normalize
        for key in aggregated_scores:
            if score_counts[key] > 0:
                aggregated_scores[key] /= score_counts[key]
        
        # Combine feedback
        all_feedback = [
            f"[{r.evaluator_type}] {r.feedback}"
            for r in valid_responses
            if r.feedback
        ]
        
        # Combine improvements
        all_improvements = []
        for r in valid_responses:
            all_improvements.extend(r.improvement_suggestions)
        unique_improvements = list(dict.fromkeys(all_improvements))
        
        return EvaluationResponse(
            request_id=request.id,
            prompt_id=request.prompt_id,
            evaluator_type="composite",
            scores=aggregated_scores,
            relevance=aggregated_scores.get("relevance"),
            coherence=aggregated_scores.get("coherence"),
            helpfulness=aggregated_scores.get("helpfulness"),
            safety=aggregated_scores.get("safety"),
            accuracy=aggregated_scores.get("accuracy"),
            feedback="\n".join(all_feedback) if all_feedback else None,
            improvement_suggestions=unique_improvements[:5],
            metadata={
                "num_evaluators": len(valid_responses),
                "evaluator_types": [r.evaluator_type for r in valid_responses],
                "weights": self._weights,
            }
        )
    
    async def evaluate_batch(
        self,
        requests: List[EvaluationRequest],
    ) -> List[EvaluationResponse]:
        """Evaluate multiple prompts."""
        tasks = [self.evaluate(req) for req in requests]
        return await asyncio.gather(*tasks)
    
    async def is_available(self) -> bool:
        """Check if at least one evaluator is available."""
        checks = await asyncio.gather(
            *[e.is_available() for e in self._evaluators]
        )
        return any(checks)
    
    def add_evaluator(
        self,
        evaluator: IPromptEvaluator,
        weight: float = 1.0,
    ) -> None:
        """Add an evaluator to the composite."""
        self._evaluators.append(evaluator)
        if weight != 1.0:
            self._weights[evaluator.evaluator_type] = weight
    
    def remove_evaluator(self, evaluator_type: str) -> bool:
        """Remove an evaluator by type."""
        original_len = len(self._evaluators)
        self._evaluators = [
            e for e in self._evaluators
            if e.evaluator_type != evaluator_type
        ]
        self._weights.pop(evaluator_type, None)
        return len(self._evaluators) < original_len

