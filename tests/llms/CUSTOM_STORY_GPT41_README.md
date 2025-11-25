# Custom Story GPT-4.1 Mini Implementation

This demonstrates a custom GPT-4.1 Mini implementation with special business rules for story generation.

## Features

✅ **Custom Input Validation** - Rejects inputs containing the word "Nagadath"  
✅ **Fixed Max Tokens** - Forces all generations to use max_tokens=50  
✅ **Separate Text/Vision Tracking** - Tracks text and vision requests separately  
✅ **Complete Test Coverage** - 12 tests covering all scenarios  
✅ **Real Azure API Tests** - Optional tests with actual vision capabilities

## Custom Implementation: `StoryGPT41Mini`

```python
from tests.llms.test_custom_gpt41_mini_story import StoryGPT41Mini

# Create custom implementation
llm = StoryGPT41Mini(connector, metadata)

# Generates stories with max_tokens=50
response = await llm.get_answer(
    [{"role": "user", "content": "Write a fantasy story"}],
    ctx,
    max_tokens=1000  # Will be overridden to 50
)

# Vision-based story generation
vision_response = await llm.get_answer_with_vision(
    prompt="Write a story about this image",
    images=["https://example.com/nature.jpg"],
    ctx=ctx
)

# Validation: This will raise InputValidationError
try:
    await llm.get_answer(
        [{"role": "user", "content": "Story about Nagadath"}],
        ctx
    )
except InputValidationError as e:
    print(f"Rejected: {e.message}")
```

## Custom Rules

### 1. Input Validation
- **Rejects** any input containing the word "Nagadath"
- Works for both text and vision prompts
- Provides helpful error messages

### 2. Max Tokens Override
- **Always forces** max_tokens=50, regardless of user input
- Logs when overriding user's requested max_tokens
- Applies to all 4 generation methods

### 3. Request Tracking
- `text_request_count` - Counts text-only requests
- `vision_request_count` - Counts vision requests
- `rejected_count` - Counts rejected inputs

## Running Tests

### Unit Tests (Mock Connector)
```bash
# Run all tests
uv run pytest tests/llms/test_custom_gpt41_mini_story.py -v

# Run specific test category
uv run pytest tests/llms/test_custom_gpt41_mini_story.py -k "validation" -v
uv run pytest tests/llms/test_custom_gpt41_mini_story.py -k "streaming" -v
uv run pytest tests/llms/test_custom_gpt41_mini_story.py -k "vision" -v
```

### Real Azure API Tests

#### Setup Environment Variables
```bash
# Windows PowerShell
$env:AZURE_OPENAI_KEY="your-api-key"
$env:AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com"
$env:AZURE_OPENAI_DEPLOYMENT="gpt-4.1-mini"

# Linux/Mac
export AZURE_OPENAI_KEY="your-api-key"
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com"
export AZURE_OPENAI_DEPLOYMENT="gpt-4.1-mini"
```

#### Run Real Vision Tests
```bash
# Test 1: What does the LLM see in nature/animal images?
uv run pytest tests/llms/test_custom_gpt41_mini_story.py::test_real_vision_what_does_llm_see -v -s

# Test 2: Complete story workflow with validation
uv run pytest tests/llms/test_custom_gpt41_mini_story.py::test_real_story_generation_with_validation -v -s
```

## Test Coverage

### Text Generation (Non-Streaming)
- ✅ Normal text story generation
- ✅ Max tokens enforcement
- ✅ Request counting

### Text Generation (Streaming)
- ✅ Streaming text story generation
- ✅ Max tokens enforcement in streaming
- ✅ Request counting for streams

### Vision Generation (Non-Streaming)
- ✅ Vision-based story generation
- ✅ Max tokens enforcement with images
- ✅ Separate vision request counting

### Vision Generation (Streaming)
- ✅ Streaming with multimodal input
- ✅ Max tokens enforcement
- ✅ Request tracking

### Input Validation
- ✅ Rejects "Nagadath" in text input
- ✅ Rejects "Nagadath" in streaming input
- ✅ Rejects "Nagadath" in vision prompts
- ✅ Accepts normal input without forbidden words

### Max Tokens Enforcement
- ✅ Overrides user-specified max_tokens
- ✅ Applies to all 4 generation methods
- ✅ Logs when overriding

### Request Tracking
- ✅ Counts text vs vision requests separately
- ✅ Counts rejected requests
- ✅ Maintains accurate counts across methods

## Example Real Output

When running the vision test with real Azure API, you'll see:

```
================================================================================
TESTING: What does GPT-4.1 Mini see in nature/animal images?
================================================================================

────────────────────────────────────────────────────────────────────────────────
Image 1: Deer drinking water in river
URL: https://static.vecteezy.com/...deer-drinking-water...
────────────────────────────────────────────────────────────────────────────────

LLM Response:
In this serene image, a graceful deer stands at the edge of a tranquil river,
lowering its head to drink from the crystal-clear water. The forest surrounds
the scene with...

Tokens used: 32
Max tokens was forced to: 50

────────────────────────────────────────────────────────────────────────────────
Image 2: Deer family in sunlit forest
...
```

## Architecture Highlights

### Inheritance Chain
```
StoryGPT41Mini
  ↓ extends
GPT_4_1_MiniLLM
  ↓ extends  
AzureBaseLLM
  ↓ extends
BaseLLM (with get_answer_with_vision helper)
```

### Method Overrides
- `get_answer()` - Adds validation + max_tokens override
- `stream_answer()` - Adds validation + max_tokens override  
- `get_answer_with_vision()` - Adds validation + max_tokens override + tracking

### Validation Flow
1. User calls generation method
2. Custom validation checks for "Nagadath"
3. If found → raise `InputValidationError`
4. If clean → force max_tokens=50
5. Call parent implementation
6. Track request type

## Use Cases

This pattern is useful when you need:

1. **Content Filtering** - Block certain words/patterns
2. **Cost Control** - Force specific token limits
3. **Compliance** - Enforce business rules
4. **Monitoring** - Track different request types
5. **Custom Behavior** - Override defaults per use case

## Notes

- The mock connector returns realistic but fake responses
- Real tests require actual Azure credentials
- Max tokens override helps control API costs
- Validation prevents unwanted content generation
- Request tracking helps with analytics and monitoring

## Image Sources

Test images from: [Vecteezy Nature Animals Collection](https://www.vecteezy.com/free-photos/nature-animals)
- Deer drinking from river
- Deer family in sunlit forest  
- Monarch butterfly on flower
- Various wildlife and nature scenes

