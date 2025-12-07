"""
Integration tests for Prompt Registry with LLM usage.

Tests end-to-end prompt lifecycle including:
- Saving prompts to registry
- Retrieving prompts with variable substitution
- Using prompts with an LLM
- Verifying runtime metrics are recorded
"""

import pytest
import tempfile
import shutil
import time
from typing import Any, Dict, List, AsyncIterator

from core.promptregistry import (
    LocalPromptRegistry,
    PromptMetadata,
    PromptEnvironment,
    PromptType,
)
from core.llms.spec.llm_result import LLMResponse, LLMUsage, LLMStreamChunk
from core.llms.spec.llm_context import LLMContext
from core.llms.enum import FinishReason


# ============================================================================
# MOCK LLM FOR TESTING
# ============================================================================

class MockLLM:
    """
    Mock LLM implementation for testing prompt metrics.
    
    Returns configurable responses with realistic usage statistics.
    Tracks all calls made to it for verification.
    """
    
    def __init__(
        self,
        default_response: str = "This is a mock response.",
        prompt_tokens: int = 50,
        completion_tokens: int = 30,
        latency_ms: int = 100,
        cost_usd: float = 0.001
    ):
        self.default_response = default_response
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.latency_ms = latency_ms
        self.cost_usd = cost_usd
        
        # Track calls for verification
        self.call_history: List[Dict[str, Any]] = []
    
    async def get_answer(
        self,
        messages: List[Dict[str, Any]],
        ctx: LLMContext,
        **kwargs: Any
    ) -> LLMResponse:
        """
        Return a mock LLM response with usage metrics.
        """
        # Simulate latency
        time.sleep(self.latency_ms / 1000)
        
        # Record the call
        self.call_history.append({
            "messages": messages,
            "ctx": ctx,
            "kwargs": kwargs,
            "timestamp": time.time()
        })
        
        # Create usage stats
        usage = LLMUsage(
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
            total_tokens=self.prompt_tokens + self.completion_tokens,
            duration_ms=self.latency_ms,
            cost_usd=self.cost_usd
        )
        
        # Return response
        return LLMResponse(
            content=self.default_response,
            role="assistant",
            finish_reason=FinishReason.STOP,
            usage=usage
        )
    
    async def stream_answer(
        self,
        messages: List[Dict[str, Any]],
        ctx: LLMContext,
        **kwargs: Any
    ) -> AsyncIterator[LLMStreamChunk]:
        """
        Stream a mock LLM response.
        """
        words = self.default_response.split()
        
        for i, word in enumerate(words):
            is_final = (i == len(words) - 1)
            usage = None
            
            if is_final:
                usage = LLMUsage(
                    prompt_tokens=self.prompt_tokens,
                    completion_tokens=self.completion_tokens,
                    total_tokens=self.prompt_tokens + self.completion_tokens,
                    duration_ms=self.latency_ms,
                    cost_usd=self.cost_usd
                )
            
            yield LLMStreamChunk(
                content=word + " ",
                role="assistant",
                is_final=is_final,
                finish_reason=FinishReason.STOP if is_final else None,
                usage=usage
            )
    
    def reset_history(self):
        """Clear call history."""
        self.call_history = []


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def temp_storage_path():
    """Create a temporary directory for storage."""
    path = tempfile.mkdtemp()
    yield path
    shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def registry(temp_storage_path):
    """Create LocalPromptRegistry instance."""
    return LocalPromptRegistry(storage_path=temp_storage_path)


@pytest.fixture
def mock_llm():
    """Create a mock LLM instance."""
    return MockLLM(
        default_response="Hello! I am here to help you with your task.",
        prompt_tokens=50,
        completion_tokens=25,
        latency_ms=150,
        cost_usd=0.0015
    )


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestPromptLLMIntegration:
    """Test prompt registry integration with LLM usage."""
    
    async def test_save_retrieve_and_use_prompt(self, registry, mock_llm):
        """
        Test complete flow: save prompt, retrieve it, use with LLM, verify metrics.
        """
        # 1. Save a prompt
        prompt_id = await registry.save_prompt(
            label="assistant_greeting",
            content="You are a helpful assistant named {name}. Help the user with {task}.",
            metadata=PromptMetadata(
                description="Assistant greeting prompt",
                model_target="gpt-4",
                environment=PromptEnvironment.PROD,
                prompt_type=PromptType.SYSTEM,
                tags=["greeting", "assistant"]
            )
        )
        
        assert prompt_id is not None
        
        # 2. Retrieve prompt with variables
        rendered_prompt = await registry.get_prompt(
            "assistant_greeting",
            variables={"name": "Claude", "task": "coding"}
        )
        
        assert "Claude" in rendered_prompt
        assert "coding" in rendered_prompt
        
        # 3. Use prompt with mock LLM
        messages = [
            {"role": "system", "content": rendered_prompt},
            {"role": "user", "content": "Hello, can you help me?"}
        ]
        
        ctx = LLMContext(request_id="test-123")
        response = await mock_llm.get_answer(messages, ctx)
        
        assert response.content is not None
        assert response.usage is not None
        assert response.usage.prompt_tokens == 50
        assert response.usage.completion_tokens == 25
        
        # 4. Record metrics to prompt registry
        await registry.record_usage(
            prompt_id,
            latency_ms=response.usage.duration_ms,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            cost=response.usage.cost_usd or 0.0,
            success=True
        )
        
        # 5. Verify metrics were recorded
        metrics = await registry.get_runtime_metrics(prompt_id)
        
        assert metrics.usage_count == 1
        assert metrics.total_latency_ms == 150.0
        assert metrics.avg_latency_ms == 150.0
        assert metrics.total_prompt_tokens == 50
        assert metrics.total_completion_tokens == 25
        assert metrics.total_tokens == 75
        assert metrics.success_rate == 1.0
    
    async def test_multiple_llm_calls_accumulate_metrics(self, registry, mock_llm):
        """
        Test that multiple LLM calls accumulate metrics correctly.
        """
        # Save a prompt
        prompt_id = await registry.save_prompt(
            label="multi_call_test",
            content="Process the following: {input}"
        )
        
        # Simulate multiple LLM calls
        for i in range(5):
            rendered = await registry.get_prompt(
                "multi_call_test",
                variables={"input": f"data_{i}"}
            )
            
            messages = [{"role": "user", "content": rendered}]
            ctx = LLMContext(request_id=f"test-{i}")
            
            response = await mock_llm.get_answer(messages, ctx)
            
            await registry.record_usage(
                prompt_id,
                latency_ms=response.usage.duration_ms,
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                cost=response.usage.cost_usd or 0.0,
                success=True
            )
        
        # Verify accumulated metrics
        metrics = await registry.get_runtime_metrics(prompt_id)
        
        assert metrics.usage_count == 5
        assert metrics.total_prompt_tokens == 250  # 50 * 5
        assert metrics.total_completion_tokens == 125  # 25 * 5
        assert metrics.total_tokens == 375
        assert metrics.avg_tokens == 75.0  # 375 / 5
        assert metrics.avg_latency_ms == 150.0
        assert metrics.success_rate == 1.0
    
    async def test_metrics_track_failures(self, registry, mock_llm):
        """
        Test that failures are tracked in metrics.
        """
        prompt_id = await registry.save_prompt(
            label="failure_test",
            content="Test prompt for failure tracking"
        )
        
        # Record successful calls
        await registry.record_usage(prompt_id, latency_ms=100, success=True)
        await registry.record_usage(prompt_id, latency_ms=100, success=True)
        
        # Record a failed call
        await registry.record_usage(prompt_id, latency_ms=50, success=False)
        
        # Verify metrics
        metrics = await registry.get_runtime_metrics(prompt_id)
        
        assert metrics.usage_count == 3
        assert metrics.error_count == 1
        assert abs(metrics.success_rate - 0.6667) < 0.01  # ~66.67%
    
    async def test_prompt_with_response_format(self, registry, mock_llm):
        """
        Test prompt with response format specification.
        """
        prompt_id = await registry.save_prompt(
            label="json_response_prompt",
            content="Return the following data as JSON: {data}",
            metadata=PromptMetadata(
                response_format={
                    "type": "json_object",
                    "schema": {
                        "name": {"type": "string"},
                        "value": {"type": "number"}
                    }
                }
            )
        )
        
        # Get prompt with fallback to check response format
        result = await registry.get_prompt_with_fallback(
            "json_response_prompt",
            variables={"data": "name=test, value=42"}
        )
        
        assert result.response_format is not None
        assert result.response_format["type"] == "json_object"
    
    async def test_environment_specific_prompts_with_llm(self, registry, mock_llm):
        """
        Test using environment-specific prompts with LLM.
        """
        # Save prod version
        prod_id = await registry.save_prompt(
            label="env_test",
            content="PRODUCTION: Process {task}",
            metadata=PromptMetadata(environment=PromptEnvironment.PROD)
        )
        
        # Save dev version with different content
        dev_id = await registry.save_prompt(
            label="env_test",
            content="DEVELOPMENT (debug enabled): Process {task}",
            metadata=PromptMetadata(environment=PromptEnvironment.DEV)
        )
        
        # Get prod version
        prod_prompt = await registry.get_prompt(
            "env_test",
            environment=PromptEnvironment.PROD,
            variables={"task": "user request"}
        )
        assert "PRODUCTION" in prod_prompt
        
        # Get dev version
        dev_prompt = await registry.get_prompt(
            "env_test",
            environment=PromptEnvironment.DEV,
            variables={"task": "user request"}
        )
        assert "DEVELOPMENT" in dev_prompt
        
        # Use both with LLM and record separate metrics
        ctx = LLMContext(request_id="test-env")
        
        # Prod call
        messages = [{"role": "system", "content": prod_prompt}]
        response = await mock_llm.get_answer(messages, ctx)
        await registry.record_usage(
            prod_id,
            latency_ms=response.usage.duration_ms,
            prompt_tokens=response.usage.prompt_tokens,
            success=True
        )
        
        # Dev call
        messages = [{"role": "system", "content": dev_prompt}]
        response = await mock_llm.get_answer(messages, ctx)
        await registry.record_usage(
            dev_id,
            latency_ms=response.usage.duration_ms,
            prompt_tokens=response.usage.prompt_tokens,
            success=True
        )
        
        # Verify both have metrics
        prod_metrics = await registry.get_runtime_metrics(prod_id)
        dev_metrics = await registry.get_runtime_metrics(dev_id)
        
        assert prod_metrics.usage_count == 1
        assert dev_metrics.usage_count == 1
    
    async def test_model_specific_prompts_with_llm(self, registry, mock_llm):
        """
        Test using model-specific prompts with LLM.
        """
        # Save default version
        default_id = await registry.save_prompt(
            label="model_test",
            content="Generic instruction for any model",
            metadata=PromptMetadata(model_target="default")
        )
        
        # Save GPT-4 optimized version
        gpt4_id = await registry.save_prompt(
            label="model_test",
            content="GPT-4 optimized: Think step by step and provide detailed analysis",
            metadata=PromptMetadata(model_target="gpt-4")
        )
        
        # Get for GPT-4
        gpt4_prompt = await registry.get_prompt("model_test", model="gpt-4")
        assert "GPT-4 optimized" in gpt4_prompt
        
        # Get for unknown model (should get latest or default)
        default_prompt = await registry.get_prompt("model_test", model="unknown-model")
        # Should fallback to some version
        assert default_prompt is not None
        
        # Use with LLM
        ctx = LLMContext(request_id="test-model")
        messages = [{"role": "system", "content": gpt4_prompt}]
        response = await mock_llm.get_answer(messages, ctx)
        
        await registry.record_usage(
            gpt4_id,
            latency_ms=response.usage.duration_ms,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            cost=response.usage.cost_usd or 0.0,
            success=True
        )
        
        metrics = await registry.get_runtime_metrics(gpt4_id)
        assert metrics.usage_count == 1
    
    async def test_eval_scores_with_usage_metrics(self, registry, mock_llm):
        """
        Test combining eval scores with runtime usage metrics.
        """
        prompt_id = await registry.save_prompt(
            label="eval_test",
            content="A well-crafted prompt for evaluation"
        )
        
        # Simulate multiple LLM uses
        for _ in range(3):
            await registry.record_usage(
                prompt_id,
                latency_ms=100,
                prompt_tokens=40,
                completion_tokens=20,
                success=True
            )
        
        # Update eval scores based on observed quality
        await registry.update_eval_scores(
            prompt_id,
            llm_eval_score=0.92,
            human_eval_score=0.88
        )
        
        # Verify both eval scores and runtime metrics exist
        entry = await registry.get_prompt_entry("eval_test")
        version = entry.versions[-1]
        
        # Check eval scores
        assert version.metadata.llm_eval_score == 0.92
        assert version.metadata.human_eval_score == 0.88
        
        # Check runtime metrics
        assert version.metadata.runtime_metrics.usage_count == 3
        assert version.metadata.runtime_metrics.total_tokens == 180  # (40+20) * 3


@pytest.mark.integration
@pytest.mark.asyncio
class TestMockLLM:
    """Test the MockLLM implementation itself."""
    
    async def test_mock_llm_returns_response(self, mock_llm):
        """Test MockLLM returns a valid response."""
        ctx = LLMContext(request_id="test-1")
        messages = [{"role": "user", "content": "Hello"}]
        
        response = await mock_llm.get_answer(messages, ctx)
        
        assert response.content is not None
        assert response.role == "assistant"
        assert response.usage is not None
    
    async def test_mock_llm_tracks_calls(self, mock_llm):
        """Test MockLLM tracks call history."""
        ctx = LLMContext(request_id="test-2")
        
        await mock_llm.get_answer([{"role": "user", "content": "First"}], ctx)
        await mock_llm.get_answer([{"role": "user", "content": "Second"}], ctx)
        
        assert len(mock_llm.call_history) == 2
        assert mock_llm.call_history[0]["messages"][0]["content"] == "First"
        assert mock_llm.call_history[1]["messages"][0]["content"] == "Second"
    
    async def test_mock_llm_reset_history(self, mock_llm):
        """Test MockLLM can reset call history."""
        ctx = LLMContext(request_id="test-3")
        
        await mock_llm.get_answer([{"role": "user", "content": "Test"}], ctx)
        assert len(mock_llm.call_history) == 1
        
        mock_llm.reset_history()
        assert len(mock_llm.call_history) == 0
    
    async def test_mock_llm_usage_stats(self, mock_llm):
        """Test MockLLM returns correct usage stats."""
        ctx = LLMContext(request_id="test-4")
        
        response = await mock_llm.get_answer([{"role": "user", "content": "Test"}], ctx)
        
        assert response.usage.prompt_tokens == 50
        assert response.usage.completion_tokens == 25
        assert response.usage.total_tokens == 75
        assert response.usage.duration_ms == 150
        assert response.usage.cost_usd == 0.0015


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
