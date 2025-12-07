"""
Integration-style test ensuring prompt registry works with an Azure-like LLM
while persisting versions to local storage and recording runtime metrics.

Tests the new pattern where LLMs record usage directly via set_prompt_registry()
and prompt_id in LLMContext, instead of using a separate PromptAwareLLM wrapper.
"""

import asyncio
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

import pytest

from core.promptregistry import (
    LocalPromptRegistry,
    PromptMetadata,
    PromptEnvironment,
    PromptType,
)
from core.llms.spec.llm_result import LLMResponse, LLMUsage
from core.llms.spec.llm_context import LLMContext
from core.llms.enum import FinishReason

if TYPE_CHECKING:
    from core.promptregistry.interfaces.prompt_registry_interfaces import IPromptRegistry


class TestAzureLLM:
    """
    Lightweight Azure-like LLM that returns static responses for testing.
    
    Includes prompt registry support (set_prompt_registry) to demonstrate
    the new pattern where LLMs record usage directly.
    """

    def __init__(
        self,
        config: Dict[str, Any],
        prompt_tokens: int = 32,
        completion_tokens: int = 18,
        latency_ms: int = 50,
    ):
        self.config = config
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.latency_ms = latency_ms
        self.call_history: List[Dict[str, Any]] = []
        self._prompt_registry: Optional['IPromptRegistry'] = None

    def set_prompt_registry(self, registry: 'IPromptRegistry') -> 'TestAzureLLM':
        """Set prompt registry for automatic usage tracking."""
        self._prompt_registry = registry
        return self

    async def get_answer(
        self,
        messages: List[Dict[str, Any]],
        ctx: LLMContext,
        **kwargs: Any,
    ) -> LLMResponse:
        start_time = time.time()
        success = True
        response = None
        
        try:
            await asyncio.sleep(self.latency_ms / 1000)
            self.call_history.append(
                {
                    "messages": messages,
                    "ctx": ctx,
                    "kwargs": kwargs,
                    "config": self.config,
                }
            )

            usage = LLMUsage(
                prompt_tokens=self.prompt_tokens,
                completion_tokens=self.completion_tokens,
                total_tokens=self.prompt_tokens + self.completion_tokens,
                duration_ms=self.latency_ms,
                cost_usd=0.0005,
            )

            response = LLMResponse(
                content="Azure mock response",
                role="assistant",
                finish_reason=FinishReason.STOP,
                usage=usage,
            )
            return response
            
        except Exception:
            success = False
            raise
            
        finally:
            # Record usage if registry is set and prompt_id is in context
            latency_ms = (time.time() - start_time) * 1000
            await self._record_prompt_usage(ctx, response, latency_ms, success)

    async def _record_prompt_usage(
        self,
        ctx: LLMContext,
        response: Optional[LLMResponse],
        latency_ms: float,
        success: bool = True
    ) -> None:
        """Record prompt usage metrics if registry is set and prompt_id is provided."""
        if not self._prompt_registry or not ctx.prompt_id:
            return
        
        try:
            prompt_tokens = 0
            completion_tokens = 0
            cost = 0.0
            
            if response and response.usage:
                prompt_tokens = response.usage.prompt_tokens or 0
                completion_tokens = response.usage.completion_tokens or 0
                cost = response.usage.cost_usd or 0.0
            
            await self._prompt_registry.record_usage(
                ctx.prompt_id,
                latency_ms=latency_ms,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cost=cost,
                success=success
            )
        except Exception:
            pass  # Don't fail the LLM call if metrics recording fails

    async def stream_answer(self, *args: Any, **kwargs: Any):
        raise NotImplementedError("Streaming not needed for this test.")


@pytest.fixture
def registry():
    # Use default storage handling from the registry (defaults to .prompts).
    return LocalPromptRegistry()


@pytest.fixture
def azure_config():
    return {
        "endpoint": "https://zeenie-sweden.openai.azure.com/",
        "deployment_name": "gpt-4.1-mini",
        "api_version": "2024-02-15-preview",
        "api_key": "test-azure-key",
        "timeout": 60,
    }


@pytest.fixture
def test_azure_llm(azure_config):
    return TestAzureLLM(config=azure_config)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_prompt_versions_and_metrics_with_azure_config(
    registry: LocalPromptRegistry,
    test_azure_llm: TestAzureLLM,
    azure_config: Dict[str, Any],
):
    label = "customer_reply_test"

    async def ensure_version(
        env: PromptEnvironment,
        content: str,
    ) -> str:
        """Get existing prompt id for env or create a new one."""
        if await registry.storage.exists(label):
            entry = await registry.get_prompt_entry(label)
            for version in reversed(entry.versions):
                if version.environment == env:
                    return version.metadata.id
        # Create if missing
        return await registry.save_prompt(
            label=label,
            content=content,
            metadata=PromptMetadata(
                model_target="azure-gpt-4.1-mini",
                environment=env,
                prompt_type=PromptType.SYSTEM,
                description=f"{env.value.capitalize()} prompt for customer replies",
            ),
        )

    prod_id = await ensure_version(
        PromptEnvironment.PROD,
        "PROD prompt: Provide a {tone} reply for {product}.",
    )
    staging_id = await ensure_version(
        PromptEnvironment.STAGING,
        "STAGING prompt: Dry-run {tone} reply for {product}.",
    )
    assert prod_id != staging_id

    # Storage file should exist with both versions
    storage_dir = Path(getattr(registry.storage, "storage_path", ".prompts"))
    storage_file = storage_dir / f"{label}.json"
    assert storage_file.exists()

    entry = await registry.get_prompt_entry(label)
    environments = {version.metadata.environment for version in entry.versions}
    assert PromptEnvironment.PROD in environments
    assert PromptEnvironment.STAGING in environments
    assert len(entry.versions) == 2

    # Retrieve staging version explicitly and ensure correct prompt id
    retrieved = await registry.get_prompt_with_fallback(
        label,
        environment=PromptEnvironment.STAGING,
        model="azure-gpt-4.1-mini",
        variables={"tone": "calm", "product": "AHF"},
    )
    assert "STAGING" in retrieved.content
    assert "calm" in retrieved.content
    assert "AHF" in retrieved.content
    assert retrieved.prompt_id == staging_id

    # Set prompt registry on the LLM for automatic metrics recording
    test_azure_llm.set_prompt_registry(registry)
    
    # Pass prompt_id in context - this is the new pattern
    ctx = LLMContext(request_id="azure-prompt-test", prompt_id=retrieved.prompt_id)

    # Snapshot metrics before calls to verify accumulation
    before_metrics = await registry.get_runtime_metrics(retrieved.prompt_id)

    # Call LLM directly - metrics are recorded automatically via prompt_id in context
    response = await test_azure_llm.get_answer(
        messages=[
            {"role": "system", "content": retrieved.content},
            {"role": "user", "content": "Handle a calm reply for the product."},
        ],
        ctx=ctx,
    )

    assert response.content == "Azure mock response"
    assert test_azure_llm.call_history  # ensure call happened
    assert (
        test_azure_llm.call_history[0]["config"]["deployment_name"]
        == azure_config["deployment_name"]
    )

    # Metrics should reflect accumulated usage (previous + this call)
    metrics = await registry.get_runtime_metrics(retrieved.prompt_id)
    usage = response.usage

    assert metrics.usage_count == before_metrics.usage_count + 1
    assert metrics.total_prompt_tokens == before_metrics.total_prompt_tokens + (usage.prompt_tokens or 0)
    assert metrics.total_completion_tokens == before_metrics.total_completion_tokens + (usage.completion_tokens or 0)
    assert metrics.total_tokens == before_metrics.total_tokens + (usage.total_tokens or 0)
    assert metrics.avg_tokens >= 0
    assert metrics.avg_latency_ms >= 0

    # Last values should match the most recent call
    assert metrics.last_prompt_tokens == usage.prompt_tokens
    assert metrics.last_completion_tokens == usage.completion_tokens
    assert metrics.last_total_tokens == usage.total_tokens
    assert metrics.last_cost == usage.cost_usd

    # Percentiles should be populated and within observed bounds
    assert metrics.p95_latency_ms is not None and metrics.p99_latency_ms is not None
    assert metrics.p95_total_tokens is not None and metrics.p99_total_tokens is not None
    assert metrics.p95_latency_ms <= max(metrics.latency_samples)
    assert metrics.p99_latency_ms <= max(metrics.latency_samples)
    assert metrics.p95_total_tokens <= max(metrics.total_tokens_samples)
    assert metrics.p99_total_tokens <= max(metrics.total_tokens_samples)
