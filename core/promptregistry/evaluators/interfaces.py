"""
Interfaces for Prompt Evaluators.

Defines the protocol for prompt evaluation systems.
"""

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from datetime import datetime
from pydantic import BaseModel, Field
import uuid


class EvaluationRequest(BaseModel):
    """
    Request for prompt evaluation.
    
    Contains all information needed to evaluate a prompt's effectiveness.
    """
    
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Request ID"
    )
    prompt_id: str = Field(description="ID of the prompt being evaluated")
    prompt_label: Optional[str] = Field(
        default=None,
        description="Label of the prompt"
    )
    prompt_version: Optional[str] = Field(
        default=None,
        description="Version of the prompt"
    )
    prompt_content: str = Field(description="The rendered prompt content")
    llm_response: str = Field(description="The LLM's response to the prompt")
    user_input: Optional[str] = Field(
        default=None,
        description="Original user input (if applicable)"
    )
    expected_output: Optional[str] = Field(
        default=None,
        description="Expected/ideal output for comparison"
    )
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context for evaluation"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Request creation time"
    )


class EvaluationResponse(BaseModel):
    """
    Response from a prompt evaluation.
    
    Contains scores across multiple dimensions and optional feedback.
    """
    
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Response ID"
    )
    request_id: str = Field(description="ID of the evaluation request")
    prompt_id: str = Field(description="ID of the evaluated prompt")
    evaluator_type: str = Field(description="Type of evaluator (llm, human)")
    evaluator_id: Optional[str] = Field(
        default=None,
        description="ID of specific evaluator"
    )
    
    # Scores (0.0 to 1.0)
    scores: Dict[str, float] = Field(
        default_factory=dict,
        description="Scores by dimension"
    )
    
    # Standard score dimensions
    relevance: Optional[float] = Field(
        default=None,
        ge=0.0, le=1.0,
        description="How relevant the response is to the prompt"
    )
    coherence: Optional[float] = Field(
        default=None,
        ge=0.0, le=1.0,
        description="How coherent and well-structured the response is"
    )
    helpfulness: Optional[float] = Field(
        default=None,
        ge=0.0, le=1.0,
        description="How helpful the response is"
    )
    safety: Optional[float] = Field(
        default=None,
        ge=0.0, le=1.0,
        description="How safe/appropriate the response is"
    )
    accuracy: Optional[float] = Field(
        default=None,
        ge=0.0, le=1.0,
        description="How accurate the response is (if verifiable)"
    )
    
    # Aggregate score
    overall_score: Optional[float] = Field(
        default=None,
        ge=0.0, le=1.0,
        description="Overall quality score"
    )
    
    # Feedback
    feedback: Optional[str] = Field(
        default=None,
        description="Textual feedback or explanation"
    )
    improvement_suggestions: List[str] = Field(
        default_factory=list,
        description="Suggestions for improving the prompt"
    )
    
    # Metadata
    latency_ms: Optional[float] = Field(
        default=None,
        description="Evaluation latency in milliseconds"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Response creation time"
    )
    
    def model_post_init(self, __context: Any) -> None:
        """Populate scores dict from individual fields."""
        if self.relevance is not None:
            self.scores["relevance"] = self.relevance
        if self.coherence is not None:
            self.scores["coherence"] = self.coherence
        if self.helpfulness is not None:
            self.scores["helpfulness"] = self.helpfulness
        if self.safety is not None:
            self.scores["safety"] = self.safety
        if self.accuracy is not None:
            self.scores["accuracy"] = self.accuracy
        
        # Compute overall if not provided
        if self.overall_score is None and self.scores:
            self.overall_score = sum(self.scores.values()) / len(self.scores)


@runtime_checkable
class IPromptEvaluator(Protocol):
    """
    Interface for Prompt Evaluators.
    
    Evaluators assess prompt quality asynchronously.
    All implementations must be non-blocking to avoid
    interrupting the main voice application workflow.
    
    Example:
        evaluator = LLMPromptEvaluator(llm=judge_llm)
        
        response = await evaluator.evaluate(
            EvaluationRequest(
                prompt_id="prompt-123",
                prompt_content="You are...",
                llm_response="Sure, I can...",
            )
        )
        
        print(f"Overall score: {response.overall_score}")
    """
    
    @property
    def evaluator_type(self) -> str:
        """Return the type of this evaluator."""
        ...
    
    async def evaluate(
        self,
        request: EvaluationRequest,
    ) -> EvaluationResponse:
        """
        Evaluate a prompt's effectiveness.
        
        Args:
            request: Evaluation request with prompt and response
            
        Returns:
            EvaluationResponse with scores and feedback
        """
        ...
    
    async def evaluate_batch(
        self,
        requests: List[EvaluationRequest],
    ) -> List[EvaluationResponse]:
        """
        Evaluate multiple prompts in batch.
        
        Args:
            requests: List of evaluation requests
            
        Returns:
            List of evaluation responses
        """
        ...
    
    async def is_available(self) -> bool:
        """Check if the evaluator is available."""
        ...

