"""
Human Prompt Evaluator.

Provides a queue-based system for human review of prompts.
Stores pending evaluations and aggregates human rankings.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional
from collections import defaultdict
import uuid

from pydantic import BaseModel, Field

from .interfaces import IPromptEvaluator, EvaluationRequest, EvaluationResponse
from core.metrics import EvaluationResult, EntityType, EvaluatorType


class HumanEvaluationTask(BaseModel):
    """A pending human evaluation task."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    request: EvaluationRequest
    status: str = Field(default="pending")  # pending, in_review, completed, cancelled
    assigned_to: Optional[str] = Field(default=None)
    priority: int = Field(default=1)  # 1 = normal, 2 = high, 3 = urgent
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(default=None)
    responses: List[EvaluationResponse] = Field(default_factory=list)


class HumanPromptEvaluator(IPromptEvaluator):
    """
    Human evaluation system for prompt quality assessment.
    
    Provides:
    - Queue for pending evaluations
    - Support for multiple human reviewers
    - Score aggregation across reviewers
    - Priority-based task assignment
    
    Usage:
        evaluator = HumanPromptEvaluator()
        
        # Submit for review
        task_id = await evaluator.submit_for_review(request)
        
        # Human reviews (via API/UI)
        await evaluator.submit_rating(task_id, reviewer_id, scores)
        
        # Get aggregated results
        response = await evaluator.get_aggregated_response(task_id)
    """
    
    def __init__(
        self,
        min_reviews: int = 1,
        aggregation_method: str = "average",
    ):
        """
        Initialize the human evaluator.
        
        Args:
            min_reviews: Minimum number of reviews before aggregation
            aggregation_method: How to aggregate scores (average, median)
        """
        self._min_reviews = min_reviews
        self._aggregation_method = aggregation_method
        
        # Task storage (in-memory, should be persisted for production)
        self._tasks: Dict[str, HumanEvaluationTask] = {}
        self._by_prompt: Dict[str, List[str]] = defaultdict(list)  # prompt_id -> task_ids
    
    @property
    def evaluator_type(self) -> str:
        return "human"
    
    async def submit_for_review(
        self,
        request: EvaluationRequest,
        priority: int = 1,
    ) -> str:
        """
        Submit a prompt for human review.
        
        Args:
            request: Evaluation request
            priority: Task priority (1=normal, 2=high, 3=urgent)
            
        Returns:
            Task ID for tracking
        """
        task = HumanEvaluationTask(
            request=request,
            priority=priority,
        )
        
        self._tasks[task.id] = task
        self._by_prompt[request.prompt_id].append(task.id)
        
        return task.id
    
    async def submit_rating(
        self,
        task_id: str,
        reviewer_id: str,
        scores: Dict[str, float],
        feedback: Optional[str] = None,
        improvements: Optional[List[str]] = None,
    ) -> EvaluationResponse:
        """
        Submit a human rating for a task.
        
        Args:
            task_id: Task ID
            reviewer_id: ID of the human reviewer
            scores: Score values by dimension
            feedback: Optional textual feedback
            improvements: Optional improvement suggestions
            
        Returns:
            The created evaluation response
        """
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")
        
        response = EvaluationResponse(
            request_id=task.request.id,
            prompt_id=task.request.prompt_id,
            evaluator_type="human",
            evaluator_id=reviewer_id,
            scores=scores,
            relevance=scores.get("relevance"),
            coherence=scores.get("coherence"),
            helpfulness=scores.get("helpfulness"),
            safety=scores.get("safety"),
            accuracy=scores.get("accuracy"),
            feedback=feedback,
            improvement_suggestions=improvements or [],
        )
        
        task.responses.append(response)
        
        # Check if we have enough reviews
        if len(task.responses) >= self._min_reviews:
            task.status = "completed"
            task.completed_at = datetime.utcnow()
        else:
            task.status = "in_review"
        
        return response
    
    async def get_pending_tasks(
        self,
        limit: Optional[int] = None,
        priority_min: Optional[int] = None,
    ) -> List[HumanEvaluationTask]:
        """
        Get pending evaluation tasks.
        
        Args:
            limit: Maximum tasks to return
            priority_min: Minimum priority filter
            
        Returns:
            List of pending tasks, sorted by priority and age
        """
        tasks = [
            t for t in self._tasks.values()
            if t.status == "pending"
        ]
        
        if priority_min:
            tasks = [t for t in tasks if t.priority >= priority_min]
        
        # Sort by priority (desc) then created_at (asc)
        tasks.sort(key=lambda t: (-t.priority, t.created_at))
        
        if limit:
            tasks = tasks[:limit]
        
        return tasks
    
    async def get_task(self, task_id: str) -> Optional[HumanEvaluationTask]:
        """Get a specific task."""
        return self._tasks.get(task_id)
    
    async def get_aggregated_response(
        self,
        task_id: str,
    ) -> Optional[EvaluationResponse]:
        """
        Get aggregated response from all human reviews.
        
        Args:
            task_id: Task ID
            
        Returns:
            Aggregated evaluation response or None if not enough reviews
        """
        task = self._tasks.get(task_id)
        if not task or not task.responses:
            return None
        
        # Aggregate scores
        all_scores: Dict[str, List[float]] = defaultdict(list)
        all_feedback: List[str] = []
        all_improvements: List[str] = []
        
        for response in task.responses:
            for key, value in response.scores.items():
                all_scores[key].append(value)
            if response.feedback:
                all_feedback.append(response.feedback)
            all_improvements.extend(response.improvement_suggestions)
        
        # Compute aggregates
        if self._aggregation_method == "median":
            aggregated_scores = {
                k: sorted(v)[len(v) // 2]
                for k, v in all_scores.items()
            }
        else:  # average
            aggregated_scores = {
                k: sum(v) / len(v)
                for k, v in all_scores.items()
            }
        
        # Deduplicate improvements
        unique_improvements = list(dict.fromkeys(all_improvements))
        
        return EvaluationResponse(
            request_id=task.request.id,
            prompt_id=task.request.prompt_id,
            evaluator_type="human",
            scores=aggregated_scores,
            relevance=aggregated_scores.get("relevance"),
            coherence=aggregated_scores.get("coherence"),
            helpfulness=aggregated_scores.get("helpfulness"),
            safety=aggregated_scores.get("safety"),
            accuracy=aggregated_scores.get("accuracy"),
            feedback=" | ".join(all_feedback) if all_feedback else None,
            improvement_suggestions=unique_improvements[:5],  # Top 5
            metadata={
                "num_reviewers": len(task.responses),
                "reviewer_ids": [r.evaluator_id for r in task.responses],
                "aggregation_method": self._aggregation_method,
            }
        )
    
    async def evaluate(
        self,
        request: EvaluationRequest,
    ) -> EvaluationResponse:
        """
        Submit for review and return placeholder response.
        
        Note: Human evaluation is asynchronous. This submits the request
        and returns a placeholder. Use get_aggregated_response() to get
        actual results after human review.
        """
        task_id = await self.submit_for_review(request)
        
        return EvaluationResponse(
            request_id=request.id,
            prompt_id=request.prompt_id,
            evaluator_type="human",
            feedback=f"Submitted for human review. Task ID: {task_id}",
            metadata={
                "task_id": task_id,
                "status": "pending",
            }
        )
    
    async def evaluate_batch(
        self,
        requests: List[EvaluationRequest],
    ) -> List[EvaluationResponse]:
        """Submit multiple prompts for human review."""
        return [await self.evaluate(req) for req in requests]
    
    async def is_available(self) -> bool:
        """Human evaluation is always available."""
        return True
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get evaluation queue statistics."""
        pending = sum(1 for t in self._tasks.values() if t.status == "pending")
        in_review = sum(1 for t in self._tasks.values() if t.status == "in_review")
        completed = sum(1 for t in self._tasks.values() if t.status == "completed")
        
        return {
            "total_tasks": len(self._tasks),
            "pending": pending,
            "in_review": in_review,
            "completed": completed,
            "completion_rate": completed / len(self._tasks) if self._tasks else 0,
        }

