"""
Real Tests for Prompt Evaluators.

Tests LLM evaluator with REAL Azure GPT-4.1-mini.
No mocks - uses actual LLM calls.

Requires:
- AZURE_OPENAI_API_KEY environment variable
- AZURE_OPENAI_ENDPOINT environment variable
"""

import pytest
import os
from core.promptregistry.evaluators import (
    LLMPromptEvaluator,
    HumanPromptEvaluator,
    CompositeEvaluator,
    EvaluationRequest,
    EvaluationResponse,
)


# Skip if no Azure credentials
pytestmark = pytest.mark.skipif(
    not os.getenv("AZURE_OPENAI_API_KEY"),
    reason="AZURE_OPENAI_API_KEY not set"
)


class TestLLMEvaluator:
    """Tests for LLM-as-judge evaluator with real Azure LLM."""
    
    @pytest.mark.asyncio
    async def test_evaluate_good_response(self, llm_evaluator):
        """Test evaluating a high-quality response."""
        request = EvaluationRequest(
            prompt_id="test-prompt-1",
            prompt_content="You are a helpful assistant. Answer the user's question clearly and concisely.",
            llm_response="I'd be happy to help! To answer your question about Python lists: you can add items using the append() method, like this: my_list.append('new_item'). This adds the item to the end of the list.",
            user_input="How do I add items to a Python list?",
        )
        
        response = await llm_evaluator.evaluate(request)
        
        assert response is not None
        assert response.prompt_id == "test-prompt-1"
        assert response.evaluator_type == "llm"
        
        # Should have scores
        assert response.scores is not None
        assert len(response.scores) > 0
        
        # Good response should score reasonably well
        if response.overall_score is not None:
            assert response.overall_score >= 0.0
            assert response.overall_score <= 1.0
        
        print(f"LLM Evaluation Scores: {response.scores}")
        print(f"Overall Score: {response.overall_score}")
        print(f"Feedback: {response.feedback}")
    
    @pytest.mark.asyncio
    async def test_evaluate_poor_response(self, llm_evaluator):
        """Test evaluating a low-quality response."""
        request = EvaluationRequest(
            prompt_id="test-prompt-2",
            prompt_content="You are a helpful coding assistant. Provide clear and accurate Python code examples.",
            llm_response="I dunno, try googling it or something.",
            user_input="How do I read a file in Python?",
        )
        
        response = await llm_evaluator.evaluate(request)
        
        assert response is not None
        assert response.evaluator_type == "llm"
        
        # Should have scores (may be lower)
        assert response.scores is not None
        
        print(f"Poor Response Scores: {response.scores}")
        print(f"Feedback: {response.feedback}")
    
    @pytest.mark.asyncio
    async def test_evaluate_with_expected_output(self, llm_evaluator):
        """Test evaluation with expected output comparison."""
        request = EvaluationRequest(
            prompt_id="test-prompt-3",
            prompt_content="Translate the following to French.",
            llm_response="Bonjour, comment allez-vous?",
            user_input="Hello, how are you?",
            expected_output="Bonjour, comment allez-vous?",
        )
        
        response = await llm_evaluator.evaluate(request)
        
        assert response is not None
        
        # When expected output matches, accuracy should be high
        if "accuracy" in response.scores:
            print(f"Accuracy with matching output: {response.scores['accuracy']}")
    
    @pytest.mark.asyncio
    async def test_evaluate_batch(self, llm_evaluator):
        """Test batch evaluation of multiple prompts."""
        requests = [
            EvaluationRequest(
                prompt_id=f"batch-{i}",
                prompt_content="You are a helpful assistant.",
                llm_response=f"Response {i}: I'm here to help!",
                user_input=f"Question {i}",
            )
            for i in range(3)
        ]
        
        responses = await llm_evaluator.evaluate_batch(requests)
        
        assert len(responses) == 3
        for i, response in enumerate(responses):
            assert response.prompt_id == f"batch-{i}"
            print(f"Batch {i} score: {response.overall_score}")
    
    @pytest.mark.asyncio
    async def test_evaluator_availability(self, llm_evaluator):
        """Test checking if evaluator is available."""
        is_available = await llm_evaluator.is_available()
        
        assert is_available == True


class TestHumanEvaluator:
    """Tests for human evaluation system (no real humans, testing the queue)."""
    
    @pytest.mark.asyncio
    async def test_submit_for_review(self, human_evaluator):
        """Test submitting a prompt for human review."""
        request = EvaluationRequest(
            prompt_id="human-test-1",
            prompt_content="You are a helpful assistant.",
            llm_response="I can help with that!",
        )
        
        task_id = await human_evaluator.submit_for_review(request, priority=2)
        
        assert task_id is not None
        
        # Should be in pending tasks
        pending = await human_evaluator.get_pending_tasks()
        assert len(pending) == 1
        assert pending[0].id == task_id
    
    @pytest.mark.asyncio
    async def test_submit_human_rating(self, human_evaluator):
        """Test submitting a human rating."""
        request = EvaluationRequest(
            prompt_id="human-test-2",
            prompt_content="Test prompt",
            llm_response="Test response",
        )
        
        task_id = await human_evaluator.submit_for_review(request)
        
        # Submit a rating
        response = await human_evaluator.submit_rating(
            task_id=task_id,
            reviewer_id="reviewer-1",
            scores={
                "relevance": 0.9,
                "coherence": 0.85,
                "helpfulness": 0.8,
            },
            feedback="Good response overall.",
            improvements=["Could be more concise"],
        )
        
        assert response is not None
        assert response.evaluator_type == "human"
        assert response.evaluator_id == "reviewer-1"
        assert response.scores["relevance"] == 0.9
    
    @pytest.mark.asyncio
    async def test_aggregated_response(self, human_evaluator):
        """Test aggregating multiple human reviews."""
        request = EvaluationRequest(
            prompt_id="human-test-3",
            prompt_content="Test prompt",
            llm_response="Test response",
        )
        
        task_id = await human_evaluator.submit_for_review(request)
        
        # Submit ratings from multiple reviewers
        await human_evaluator.submit_rating(
            task_id=task_id,
            reviewer_id="reviewer-1",
            scores={"relevance": 0.9, "coherence": 0.8},
        )
        
        await human_evaluator.submit_rating(
            task_id=task_id,
            reviewer_id="reviewer-2",
            scores={"relevance": 0.7, "coherence": 0.9},
        )
        
        # Get aggregated
        aggregated = await human_evaluator.get_aggregated_response(task_id)
        
        assert aggregated is not None
        # Average of 0.9 and 0.7 = 0.8
        assert aggregated.scores["relevance"] == 0.8
        # Average of 0.8 and 0.9 = 0.85
        assert aggregated.scores["coherence"] == 0.85
    
    @pytest.mark.asyncio
    async def test_queue_statistics(self, human_evaluator):
        """Test getting evaluation queue statistics."""
        # Submit some tasks
        for i in range(3):
            request = EvaluationRequest(
                prompt_id=f"stats-test-{i}",
                prompt_content="Test",
                llm_response="Response",
            )
            await human_evaluator.submit_for_review(request)
        
        stats = await human_evaluator.get_statistics()
        
        assert stats["pending"] >= 3
        assert stats["total_tasks"] >= 3


class TestCompositeEvaluator:
    """Tests for composite evaluator combining multiple evaluators."""
    
    @pytest.mark.asyncio
    async def test_composite_evaluation(self, composite_evaluator):
        """Test evaluation using composite (LLM only for automated test)."""
        request = EvaluationRequest(
            prompt_id="composite-test-1",
            prompt_content="You are a helpful coding assistant.",
            llm_response="Here's how to sort a list in Python: use the sorted() function or list.sort() method.",
            user_input="How do I sort a list?",
        )
        
        response = await composite_evaluator.evaluate(request)
        
        assert response is not None
        assert response.evaluator_type == "composite"
        assert "num_evaluators" in response.metadata
        
        print(f"Composite scores: {response.scores}")
        print(f"Evaluators used: {response.metadata.get('evaluator_types')}")
    
    @pytest.mark.asyncio
    async def test_composite_availability(self, composite_evaluator):
        """Test composite evaluator availability."""
        is_available = await composite_evaluator.is_available()
        
        # Should be available if at least one sub-evaluator is
        assert is_available == True

