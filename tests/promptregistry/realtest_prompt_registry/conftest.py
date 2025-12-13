"""
Pytest Configuration for Real Prompt Registry Tests.

Provides fixtures for Azure LLM, metrics store, and prompt registry.
All fixtures use REAL implementations, no mocks.
"""

import os
import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path

# Skip all tests if Azure credentials not set
pytestmark = pytest.mark.skipif(
    not os.getenv("AZURE_OPENAI_API_KEY"),
    reason="AZURE_OPENAI_API_KEY not set - set it to run real tests"
)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def azure_config():
    """Get Azure OpenAI configuration from environment."""
    return {
        "api_key": os.getenv("AZURE_OPENAI_API_KEY"),
        "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT", "https://your-resource.openai.azure.com/"),
        "deployment_name": os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4.1-mini"),
        "api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
    }


@pytest.fixture(scope="session")
def azure_llm(azure_config):
    """Create real Azure LLM instance."""
    from core.llms import LLMFactory
    
    llm = LLMFactory.create_llm(
        model_name=azure_config["deployment_name"],
        connector_config={
            "api_key": azure_config["api_key"],
            "endpoint": azure_config["endpoint"],
            "api_version": azure_config["api_version"],
        }
    )
    return llm


@pytest.fixture
def temp_storage_path():
    """Create temporary storage directory for tests."""
    path = tempfile.mkdtemp(prefix="ahf_test_prompts_")
    yield path
    # Cleanup after test
    shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def prompt_registry(temp_storage_path):
    """Create real LocalPromptRegistry with temporary storage."""
    from core.promptregistry import LocalPromptRegistry
    
    registry = LocalPromptRegistry(
        storage_path=temp_storage_path,
        format="json",
    )
    return registry


@pytest.fixture
async def metrics_store():
    """Create real in-memory metrics store."""
    from core.memory import InMemoryMetricsStore
    
    store = InMemoryMetricsStore()
    yield store
    await store.clear()


@pytest.fixture
def llm_evaluator(azure_llm):
    """Create real LLM evaluator with Azure LLM."""
    from core.promptregistry.evaluators import LLMPromptEvaluator
    
    return LLMPromptEvaluator(
        llm=azure_llm,
        timeout_seconds=60.0,
        max_retries=2,
    )


@pytest.fixture
def human_evaluator():
    """Create human evaluator for testing."""
    from core.promptregistry.evaluators import HumanPromptEvaluator
    
    return HumanPromptEvaluator(
        min_reviews=1,
        aggregation_method="average",
    )


@pytest.fixture
def composite_evaluator(llm_evaluator, human_evaluator):
    """Create composite evaluator with LLM and human."""
    from core.promptregistry.evaluators import CompositeEvaluator
    
    return CompositeEvaluator(
        evaluators=[llm_evaluator],  # Only LLM for automated tests
        weights={"llm": 1.0},
        parallel=True,
    )

