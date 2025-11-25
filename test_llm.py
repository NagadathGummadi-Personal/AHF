#!/usr/bin/env python3

# Test dynamic variables functionality directly without full imports
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.llms.configs import AzureOpenAIConfig, BedrockConfig, GeminiConfig
from core.llms.enums import LLMProvider

# Test configuration creation
azure_config = AzureOpenAIConfig(
    provider=LLMProvider.AZURE_OPENAI,
    model_name="gpt-4",
    api_key="test",
    endpoint="https://test.openai.azure.com/",
    deployment_name="test-deployment",
)
print("Azure configuration created successfully!")

bedrock_config = BedrockConfig(
    provider=LLMProvider.BEDROCK,
    model_name="anthropic.claude-3-sonnet-20240229-v1:0",
    api_key="test",
    region="us-east-1",
)
print("Bedrock configuration created successfully!")

gemini_config = GeminiConfig(
    provider=LLMProvider.GEMINI,
    model_name="gemini-pro",
    api_key="test",
    project_id="test-project",
)
print("Gemini configuration created successfully!")

# Test provider listing
providers = LLMFactory.get_supported_providers()
print(f"Available providers: {[p.value for p in providers]}")

# Test LLM creation (will fail due to missing dependencies)
print("Trying to create Azure LLM (will fail due to missing openai library)...")
try:
    llm = LLMFactory.create_llm(azure_config)
    print("LLM created successfully!")
except Exception as e:
    print(f"Expected error: {type(e).__name__}: {e}")

# Test dynamic variables functionality
print("Testing dynamic variables functionality...")
azure_config_with_vars = AzureOpenAIConfig(
    provider=LLMProvider.AZURE_OPENAI,
    model_name="gpt-4",
    api_key="test",
    endpoint="https://test.openai.azure.com/",
    deployment_name="test-deployment",
    prompt="Hello {{name}}, you are {{role}} and your age is {{age}}.",
    dynamic_variables={"name": "Alice", "role": "developer", "age": 30},
)

# Test that the configuration was created successfully
assert azure_config_with_vars.dynamic_variables is not None
assert azure_config_with_vars.dynamic_variables["name"] == "Alice"
assert azure_config_with_vars.dynamic_variables["role"] == "developer"
assert azure_config_with_vars.dynamic_variables["age"] == 30

# Test that variables are not replaced during config creation (should happen during LLM usage)
assert "{{name}}" in azure_config_with_vars.prompt
assert "{{role}}" in azure_config_with_vars.prompt
assert "{{age}}" in azure_config_with_vars.prompt

print("Dynamic variables configuration test passed!")

# Test config with no dynamic variables
azure_config_no_vars = AzureOpenAIConfig(
    provider=LLMProvider.AZURE_OPENAI,
    model_name="gpt-4",
    api_key="test",
    endpoint="https://test.openai.azure.com/",
    deployment_name="test-deployment",
    prompt="Simple prompt without variables.",
)

assert azure_config_no_vars.dynamic_variables is None
print("Configuration without dynamic variables test passed!")

# Test config with partial dynamic variables (some variables missing)
azure_config_partial_vars = AzureOpenAIConfig(
    provider=LLMProvider.AZURE_OPENAI,
    model_name="gpt-4",
    api_key="test",
    endpoint="https://test.openai.azure.com/",
    deployment_name="test-deployment",
    prompt="Hello {{name}}, you are {{role}}. {{missing_var}} should remain unchanged.",
    dynamic_variables={"name": "Bob", "role": "manager"},
)

assert azure_config_partial_vars.dynamic_variables is not None
assert "{{missing_var}}" in azure_config_partial_vars.prompt  # Should remain unchanged
assert "{{name}}" not in azure_config_partial_vars.prompt  # Should be replaced
assert "{{role}}" not in azure_config_partial_vars.prompt  # Should be replaced

print("Partial dynamic variables test passed!")

print("All tests completed successfully!")
