"""
Full Integration Tests for Prompt Registry.

End-to-end tests using REAL Azure LLM and storage.
Tests the complete flow from prompt storage to evaluation.

Requires:
- AZURE_OPENAI_API_KEY environment variable
- AZURE_OPENAI_ENDPOINT environment variable
"""

import pytest
import os
from datetime import datetime

from core.promptregistry import (
    LocalPromptRegistry,
    PromptMetadata,
    PromptEnvironment,
    PromptType,
    PromptTemplate,
)
from core.promptregistry.evaluators import (
    LLMPromptEvaluator,
    EvaluationRequest,
    PromptEvaluatorFactory,
)
from core.memory import InMemoryMetricsStore, create_metrics_store
from core.llms import LLMFactory, LLMContext


# Skip if no Azure credentials
pytestmark = pytest.mark.skipif(
    not os.getenv("AZURE_OPENAI_API_KEY"),
    reason="AZURE_OPENAI_API_KEY not set"
)


class TestFullPromptWorkflow:
    """
    End-to-end tests for the complete prompt workflow:
    1. Create prompt with {{var|default:value}} syntax
    2. Store in registry
    3. Retrieve with variables
    4. Use with real LLM
    5. Evaluate response
    6. Store metrics
    7. Compare versions
    """
    
    @pytest.mark.asyncio
    async def test_complete_prompt_lifecycle(
        self,
        prompt_registry,
        azure_llm,
        llm_evaluator,
        metrics_store,
    ):
        """Test complete prompt lifecycle from creation to evaluation."""
        
        # 1. Create prompt with new syntax
        prompt_content = """You are {{role|default:a helpful assistant}}.
{{#if is_technical}}
Provide technical details and code examples.
{{#else}}
Keep explanations simple and non-technical.
{{#endif}}

User question: {{question}}"""
        
        # 2. Store in registry
        prompt_id = await prompt_registry.save_prompt(
            label="tech_support_v1",
            content=prompt_content,
            metadata=PromptMetadata(
                model_target="gpt-4",
                environment=PromptEnvironment.PROD,
                prompt_type=PromptType.SYSTEM,
                tags=["support", "technical"],
            )
        )
        
        assert prompt_id is not None
        print(f"Saved prompt with ID: {prompt_id}")
        
        # 3. Retrieve with variables (technical mode)
        result = await prompt_registry.get_prompt_with_fallback(
            "tech_support_v1",
            variables={
                "role": "a Python expert",
                "question": "How do I read a file in Python?"
            },
            context={"is_technical": True}
        )
        
        assert result is not None
        assert "Python expert" in result.content
        assert "technical details" in result.content
        print(f"Rendered prompt:\n{result.content[:200]}...")
        
        # 4. Use with real LLM
        messages = [
            {"role": "system", "content": result.content},
            {"role": "user", "content": "Show me how to read a text file."}
        ]
        
        ctx = LLMContext()
        llm_response = await azure_llm.get_answer(messages, ctx)
        
        assert llm_response is not None
        assert llm_response.content is not None
        print(f"LLM Response:\n{llm_response.content[:300]}...")
        
        # 5. Evaluate the response
        eval_request = EvaluationRequest(
            prompt_id=prompt_id,
            prompt_label="tech_support_v1",
            prompt_content=result.content,
            llm_response=llm_response.content,
            user_input="Show me how to read a text file.",
        )
        
        eval_response = await llm_evaluator.evaluate(eval_request)
        
        assert eval_response is not None
        assert eval_response.scores is not None
        print(f"Evaluation scores: {eval_response.scores}")
        print(f"Overall score: {eval_response.overall_score}")
        print(f"Feedback: {eval_response.feedback}")
        
        # 6. Store metrics
        await metrics_store.record(
            entity_id=prompt_id,
            entity_type="prompt",
            metric_type="evaluation",
            scores=eval_response.scores,
            metadata={
                "prompt_label": "tech_support_v1",
                "evaluator": "llm",
                "model": "gpt-4.1-mini",
            }
        )
        
        # 7. Verify metrics stored
        aggregated = await metrics_store.get_aggregated(prompt_id)
        
        assert aggregated["total_entries"] == 1
        print(f"Aggregated metrics: {aggregated}")
    
    @pytest.mark.asyncio
    async def test_version_comparison(
        self,
        prompt_registry,
        azure_llm,
        llm_evaluator,
        metrics_store,
    ):
        """Test comparing different prompt versions."""
        
        # Create version 1 - simple prompt
        v1_content = "You are a helpful assistant. Answer the user's question."
        
        v1_id = await prompt_registry.save_prompt(
            label="compare_prompt",
            content=v1_content,
            metadata=PromptMetadata(
                version="1.0.0",
                model_target="gpt-4",
                environment=PromptEnvironment.PROD,
            )
        )
        
        # Create version 2 - enhanced prompt
        v2_content = """You are an expert assistant specialized in providing clear, accurate answers.

Guidelines:
- Be concise but thorough
- Provide examples when helpful
- Cite sources if applicable

Answer the user's question thoughtfully."""
        
        v2_id = await prompt_registry.save_prompt(
            label="compare_prompt",
            content=v2_content,
            metadata=PromptMetadata(
                version="2.0.0",
                model_target="gpt-4",
                environment=PromptEnvironment.PROD,
            )
        )
        
        # Test question
        test_question = "What are the benefits of unit testing?"
        
        # Evaluate version 1
        v1_result = await prompt_registry.get_prompt_with_fallback(
            "compare_prompt",
            version="1.0.0"
        )
        
        messages = [
            {"role": "system", "content": v1_result.content},
            {"role": "user", "content": test_question}
        ]
        
        v1_response = await azure_llm.get_answer(messages, LLMContext())
        
        v1_eval = await llm_evaluator.evaluate(EvaluationRequest(
            prompt_id=v1_id,
            prompt_version="1.0.0",
            prompt_content=v1_result.content,
            llm_response=v1_response.content,
            user_input=test_question,
        ))
        
        await metrics_store.record(
            entity_id="compare_prompt",
            entity_type="prompt",
            metric_type="evaluation",
            scores=v1_eval.scores,
            metadata={"version": "1.0.0"}
        )
        
        # Evaluate version 2
        v2_result = await prompt_registry.get_prompt_with_fallback(
            "compare_prompt",
            version="2.0.0"
        )
        
        messages = [
            {"role": "system", "content": v2_result.content},
            {"role": "user", "content": test_question}
        ]
        
        v2_response = await azure_llm.get_answer(messages, LLMContext())
        
        v2_eval = await llm_evaluator.evaluate(EvaluationRequest(
            prompt_id=v2_id,
            prompt_version="2.0.0",
            prompt_content=v2_result.content,
            llm_response=v2_response.content,
            user_input=test_question,
        ))
        
        await metrics_store.record(
            entity_id="compare_prompt",
            entity_type="prompt",
            metric_type="evaluation",
            scores=v2_eval.scores,
            metadata={"version": "2.0.0"}
        )
        
        # Compare
        print("\n=== Version Comparison ===")
        print(f"V1 (simple) overall: {v1_eval.overall_score}")
        print(f"V2 (enhanced) overall: {v2_eval.overall_score}")
        print(f"V1 scores: {v1_eval.scores}")
        print(f"V2 scores: {v2_eval.scores}")
        
        # Get aggregated metrics
        aggregated = await metrics_store.get_aggregated("compare_prompt")
        print(f"Total evaluations: {aggregated['total_entries']}")
    
    @pytest.mark.asyncio
    async def test_conditional_prompt_with_llm(
        self,
        prompt_registry,
        azure_llm,
    ):
        """Test conditional prompts actually affect LLM behavior."""
        
        prompt_content = """{{#if is_formal}}
You are a professional business consultant. Use formal language.
{{#else}}
You are a friendly helper. Use casual, conversational language.
{{#endif}}

Help the user with their request."""
        
        await prompt_registry.save_prompt(
            label="tone_prompt",
            content=prompt_content,
            metadata=PromptMetadata(
                model_target="gpt-4",
                environment=PromptEnvironment.PROD,
            )
        )
        
        # Formal version
        formal_result = await prompt_registry.get_prompt_with_fallback(
            "tone_prompt",
            context={"is_formal": True}
        )
        
        formal_messages = [
            {"role": "system", "content": formal_result.content},
            {"role": "user", "content": "Introduce yourself briefly."}
        ]
        
        formal_response = await azure_llm.get_answer(formal_messages, LLMContext())
        
        # Casual version
        casual_result = await prompt_registry.get_prompt_with_fallback(
            "tone_prompt",
            context={"is_formal": False}
        )
        
        casual_messages = [
            {"role": "system", "content": casual_result.content},
            {"role": "user", "content": "Introduce yourself briefly."}
        ]
        
        casual_response = await azure_llm.get_answer(casual_messages, LLMContext())
        
        print("\n=== Tone Comparison ===")
        print(f"Formal prompt: {formal_result.content}")
        print(f"Formal response: {formal_response.content[:200]}...")
        print(f"\nCasual prompt: {casual_result.content}")
        print(f"Casual response: {casual_response.content[:200]}...")
        
        # Responses should be different due to different prompts
        assert formal_response.content != casual_response.content


class TestAsyncPerformance:
    """Tests for async performance - important for low-latency voice apps."""
    
    @pytest.mark.asyncio
    async def test_parallel_prompt_retrieval(self, prompt_registry):
        """Test parallel prompt retrieval performance."""
        import asyncio
        import time
        
        # Create multiple prompts
        for i in range(5):
            await prompt_registry.save_prompt(
                label=f"parallel_test_{i}",
                content=f"Prompt {{{{var_{i}}}}} content",
                metadata=PromptMetadata(
                    model_target="gpt-4",
                    environment=PromptEnvironment.PROD,
                )
            )
        
        # Sequential retrieval
        start = time.time()
        for i in range(5):
            await prompt_registry.get_prompt_with_fallback(f"parallel_test_{i}")
        sequential_time = time.time() - start
        
        # Parallel retrieval
        start = time.time()
        await asyncio.gather(*[
            prompt_registry.get_prompt_with_fallback(f"parallel_test_{i}")
            for i in range(5)
        ])
        parallel_time = time.time() - start
        
        print(f"\nSequential time: {sequential_time:.3f}s")
        print(f"Parallel time: {parallel_time:.3f}s")
        print(f"Speedup: {sequential_time / parallel_time:.2f}x")
    
    @pytest.mark.asyncio
    async def test_metrics_recording_performance(self, metrics_store):
        """Test metrics recording performance."""
        import asyncio
        import time
        
        # Sequential recording
        start = time.time()
        for i in range(100):
            await metrics_store.record(
                entity_id=f"perf_test_{i}",
                entity_type="prompt",
                metric_type="evaluation",
                scores={"relevance": 0.9},
            )
        sequential_time = time.time() - start
        
        # Parallel recording
        await metrics_store.clear()
        
        start = time.time()
        await asyncio.gather(*[
            metrics_store.record(
                entity_id=f"perf_test_{i}",
                entity_type="prompt",
                metric_type="evaluation",
                scores={"relevance": 0.9},
            )
            for i in range(100)
        ])
        parallel_time = time.time() - start
        
        print(f"\n100 metrics sequential: {sequential_time:.3f}s ({sequential_time*10:.1f}ms per record)")
        print(f"100 metrics parallel: {parallel_time:.3f}s ({parallel_time*10:.1f}ms per record)")

