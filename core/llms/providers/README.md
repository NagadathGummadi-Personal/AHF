

# LLM Providers

Provider-centric organization for LLM implementations. Each provider has a shared connector, base implementation, and model-specific configurations.

## Structure

```
providers/
├── base/                           # Base classes
│   ├── connector.py               # BaseConnector
│   ├── implementation.py          # BaseLLM
│   └── metadata.py                # BaseMetadata
├── azure/
│   ├── __init__.py                # Factory: create_azure_llm()
│   ├── connector.py               # AzureConnector (shared for ALL Azure models)
│   ├── base_implementation.py    # AzureBaseLLM (shared logic)
│   └── models/
│       └── gpt41_mini/
│           ├── __init__.py
│           ├── metadata.py        # GPT41MiniMetadata
│           └── implementation.py  # GPT41MiniLLM (model-specific)
└── openai/
    ├── __init__.py
    ├── connector.py
    ├── base_implementation.py
    └── models/
        └── ...
```

## Key Concepts

### 1. **Shared Connector per Provider**
- One connector serves ALL models from a provider
- Azure API is the same for GPT-4.1 Mini, GPT-4o, GPT-3.5 Turbo
- Connectors handle low-level API communication

```python
# All Azure models use the same connector
connector = AzureConnector(config)
```

### 2. **Shared Base Implementation**
- Common logic for all models from a provider
- Handles request/response formatting, streaming, error handling
- Models override only when they have specific needs

```python
class AzureBaseLLM:
    """Works for most Azure models."""
    async def get_answer(self, messages, ctx, **kwargs):
        # Common logic
        ...
```

### 3. **Model-Specific Metadata** (Always Required)
- Capabilities, parameters, costs, limits
- Validation rules
- No API logic, just configuration

```python
class GPT41MiniMetadata:
    NAME = "azure-gpt-4.1-mini"
    MAX_TOKENS = 16384
    COST_PER_1K_INPUT = 0.00015
    SUPPORTED_PARAMS = {PARAM_MAX_TOKENS, ...}
```

### 4. **Model-Specific Implementation** (Optional)
- Only when model needs custom behavior
- Overrides base implementation methods
- Example: GPT-4.1 Mini transforms `max_tokens` → `max_completion_tokens`

```python
class GPT41MiniLLM(AzureBaseLLM):
    """Only overrides what's different."""
    
    def _transform_parameters(self, params):
        # GPT-4.1 specific transformation
        ...
```

## Usage

### Simple Creation

```python
from core.llms.providers.azure import create_azure_llm

llm = create_azure_llm(
    "gpt-4.1-mini",
    api_key="your-key",
    endpoint="https://your-resource.openai.azure.com",
    deployment_name="gpt-4.1-mini"
)

response = await llm.get_answer(
    messages=[{"role": "user", "content": "Hello!"}],
    ctx=context,
    max_tokens=100
)
```

### Using Environment Variables

```python
import os

os.environ['AZURE_OPENAI_KEY'] = 'your-key'
os.environ['AZURE_OPENAI_ENDPOINT'] = 'https://your-resource.openai.azure.com'
os.environ['AZURE_OPENAI_DEPLOYMENT'] = 'gpt-4.1-mini'

# Automatically uses environment variables
llm = create_azure_llm("gpt-4.1-mini")
```

### Model-Specific Features

```python
# GPT-4.1 Mini has vision support
llm = create_azure_llm("gpt-4.1-mini", ...)

response = await llm.generate_with_vision(
    "What's in this image?",
    images=["https://example.com/image.jpg"],
    context=ctx,
    max_tokens=500
)
```

## Adding New Models

### 1. Simple Model (Uses Base Implementation)

For models with standard behavior, just add metadata:

```python
# providers/azure/models/gpt35_turbo/metadata.py
class GPT35TurboMetadata:
    NAME = "azure-gpt-3.5-turbo"
    MAX_TOKENS = 4096
    SUPPORTED_PARAMS = {...}
    # ... other config
```

Update factory:
```python
# providers/azure/__init__.py
elif model_name == "gpt-3.5-turbo":
    return AzureBaseLLM(
        connector=connector,
        metadata=GPT35TurboMetadata
    )
```

### 2. Complex Model (Needs Custom Implementation)

For models with special behavior:

1. Create model directory: `providers/azure/models/gpt4o/`
2. Add `metadata.py` with configuration
3. Add `implementation.py` with custom logic:

```python
# providers/azure/models/gpt4o/implementation.py
class GPT4oLLM(AzureBaseLLM):
    """Custom behavior for GPT-4o."""
    
    def _transform_parameters(self, params):
        # GPT-4o specific transformations
        ...
    
    async def some_special_method(self, ...):
        # GPT-4o specific feature
        ...
```

4. Update factory to use custom implementation

## Benefits

### ✅ No Redundancy
- **One connector per provider** - Not one per model
- **One base implementation per provider** - Shared logic
- **Only metadata for simple models** - No duplicate code

### ✅ Clear Organization
- Everything for Azure is under `providers/azure/`
- Easy to find: Want GPT-4.1 Mini config? Go to `azure/models/gpt41_mini/`
- Natural grouping by provider

### ✅ Easy to Extend
- Simple model? Just add metadata file
- Complex model? Add metadata + implementation
- New provider? Copy provider template

### ✅ Maintainable
- Change Azure API logic once in `AzureConnector`
- Update common behavior once in `AzureBaseLLM`
- Model-specific changes isolated to model folder

## Migration from Old Structure

### Old Structure (❌ Redundant)
```
runtimes/
├── connectors/
│   ├── azure_connector.py         # Shared
│   └── openai_connector.py
├── implementations/
│   ├── azure_llm.py               # Shared
│   └── openai_llm.py
└── model_registries/
    ├── azure_gpt41_mini.py        # Just metadata
    ├── azure_gpt4o.py
    └── ...
```

### New Structure (✅ Organized)
```
providers/
├── azure/
│   ├── connector.py               # Same: shared connector
│   ├── base_implementation.py    # Same: shared implementation
│   └── models/
│       ├── gpt41_mini/            # Combined: metadata + custom impl
│       └── gpt4o/
└── openai/
    └── ...
```

## Testing

Each level can be tested independently:

```python
# Test connector
connector = AzureConnector(config)
response = await connector.request("POST", "/chat/completions", data)

# Test metadata
GPT41MiniMetadata.validate_params({"max_tokens": 100})

# Test implementation
llm = GPT41MiniLLM(connector, GPT41MiniMetadata)
response = await llm.get_answer(messages, ctx)
```

## FAQs

**Q: Why not one connector per model?**  
A: Azure API is identical for all models. One connector serves all.

**Q: When do I need a custom implementation?**  
A: Only when the model has special parameter mappings, unique features, or different behavior from the base.

**Q: Can I still use the old structure?**  
A: The old files in `runtimes/` still exist for backward compatibility, but new development should use `providers/`.

**Q: How do I know what parameters a model supports?**  
A: Check the model's metadata: `GPT41MiniMetadata.SUPPORTED_PARAMS`

