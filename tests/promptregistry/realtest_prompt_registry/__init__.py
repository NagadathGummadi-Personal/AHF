"""
Real Integration Tests for Prompt Registry.

These tests use REAL Azure LLM (GPT-4.1-mini) and actual storage.
No mocks are used.

Requirements:
- Set environment variables before running:
  - AZURE_OPENAI_API_KEY
  - AZURE_OPENAI_ENDPOINT
  - AZURE_OPENAI_DEPLOYMENT_NAME (default: gpt-4.1-mini)

Run with:
    uv run pytest tests/promptregistry/realtest_prompt_registry/ -v

Version: 1.0.0
"""

