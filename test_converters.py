#!/usr/bin/env python3

from core.llms.models import get_model_capabilities
from core.llms.constants import AZURE_OPENAI_GPT_4O
from core.llms.converters import convert_to_azure_openai_request

# Test model capabilities
caps = get_model_capabilities(AZURE_OPENAI_GPT_4O)
print(f'Model capabilities for {AZURE_OPENAI_GPT_4O}:')
print(f'  Supports vision: {caps.supports_vision}')
print(f'  Supports JSON mode: {caps.supports_json_mode}')

# Test request conversion
messages = [{'role': 'user', 'content': 'Hello, world!'}]
request = convert_to_azure_openai_request(
    messages,
    AZURE_OPENAI_GPT_4O,
    temperature=0.8,
    max_tokens=100,
    json_mode=True
)

print(f'Converted request has {len(request)} parameters')
print(f'Model: {request.get("model", "not set")}')
print(f'Temperature: {request.get("temperature", "not set")}')
print('Test completed successfully!')
