# LLM Subsystem - Architecture Decisions & Design Patterns

This document explains key architectural decisions made in the LLM subsystem.

## Table of Contents
1. [Why Two Types: ILLM vs BaseLLM](#illm-vs-basellm)
2. [Why AzureBaseLLM is Abstract](#azurebasellm-abstract)
3. [Text Output Validation](#text-output-validation)
4. [Multimodal I/O Design](#multimodal-design)
5. [Session Management](#session-management)
6. [Backup & Failover](#backup-failover)

---

## 1. Why Two Types: ILLM vs BaseLLM {#illm-vs-basellm}

### Question
> Why have both `ILLM` (Protocol) and `BaseLLM` (Abstract Base Class)?

### Answer

**`ILLM` - The Contract (Protocol)**
- **Structural typing** - Duck typing with type safety
- Defines **WHAT** the API must look like
- Only 2 required methods: `get_answer()`, `stream_answer()`
- Runtime checkable - can verify any object matches
- **No inheritance required**

```python
@runtime_checkable
class ILLM(Protocol):
    async def get_answer(self, messages, ctx, **kwargs) -> LLMResponse: ...
    async def stream_answer(self, messages, ctx, **kwargs) -> AsyncIterator[LLMStreamChunk]: ...
```

**`BaseLLM` - The Helper (Abstract Base Class)**
- **Nominal typing** - Must explicitly inherit
- Provides **HOW** with utility methods:
  - `_validate_messages()` - Input validation
  - `_merge_parameters()` - Parameter handling
  - `_estimate_tokens()` - Token estimation
  - `_validate_token_limits()` - Limit checking
  - `_check_text_output_support()` - Output validation
  - `get_answer_with_vision()` - Vision helper
  - Media output methods - Image/audio/video generation

### Why Both?

| Aspect | ILLM (Protocol) | BaseLLM (ABC) |
|--------|----------------|---------------|
| **Purpose** | Define contract | Provide helpers |
| **Inheritance** | Not required | Must inherit |
| **Methods** | 2 required | 2 abstract + 15+ utility |
| **Flexibility** | Maximum | Convenient |
| **Use Case** | Type hints, interfaces | Building implementations |

### Real Example

```python
# Works WITHOUT inheriting BaseLLM
class CompletelyCustomLLM:
    async def get_answer(self, ...): ...  # Matches ILLM Protocol
    async def stream_answer(self, ...): ...

# Works WITH inheriting BaseLLM
class StandardLLM(BaseLLM):
    async def get_answer(self, messages, ctx, **kwargs):
        self._validate_messages(messages)  # Free utility!
        self._validate_token_limits(messages)  # Free utility!
        # ... implementation
```

**Result:** Users can choose maximum flexibility (ILLM only) or maximum convenience (BaseLLM).

---

## 2. Why AzureBaseLLM is Abstract {#azurebasellm-abstract}

### Question
> Why is `AzureBaseLLM` abstract? Won't this cause problems?

### Answer - You Were Right! ✅

**Original Problem:**
If `AzureBaseLLM` provided complete implementations of `get_answer()` and `stream_answer()`, it would assume:
- ❌ All Azure models use identical parameters
- ❌ GPT-3.5, GPT-4, GPT-4.1, GPT-5 all work the same way
- ❌ No model-specific transformations needed
- ❌ Response formats never change

**Reality:**
- ✅ GPT-4.1 Mini: `max_tokens` → `max_completion_tokens` (transformation needed!)
- ✅ GPT-4.1 Mini: Temperature not supported (removal needed!)
- ✅ Different models may have different parameter ranges
- ✅ Future models may use different API formats

### Current Design (Correct!)

```python
class AzureBaseLLM(BaseLLM):
    """
    Provides HELPERS, not complete implementations.
    
    Helper Methods:
    - _parse_response() - Parse Azure response format
    - _stream_azure_response() - Handle Azure streaming
    - _build_azure_payload() - Build request payload
    - _map_finish_reason() - Map finish reasons
    
    Model implementations MUST implement:
    - get_answer() - With model-specific transformations
    - stream_answer() - With model-specific transformations
    """
    
    @abstractmethod
    async def get_answer(self, ...): pass  # Models MUST implement
    
    @abstractmethod
    async def stream_answer(self, ...): pass  # Models MUST implement
```

### Example: GPT-4.1 Mini Implementation

```python
class GPT_4_1_MiniLLM(AzureBaseLLM):
    async def get_answer(self, messages, ctx, **kwargs):
        # 1. Validate
        self._validate_messages(messages)
        
        # 2. MODEL-SPECIFIC transformation
        params = self._transform_parameters(kwargs)  # max_tokens → max_completion_tokens
        
        # 3. Use HELPER to build payload
        payload = self._build_azure_payload(messages, params)
        
        # 4. Make request
        response = await self.connector.request("chat/completions", payload)
        
        # 5. Use HELPER to parse
        return self._parse_response(response, start_time)
```

**Benefits:**
- ✅ Shared Azure logic in helpers (parsing, streaming)
- ✅ Model-specific logic in implementations (transformations)
- ✅ Easy to add new models (GPT-4o, GPT-3.5, etc.)
- ✅ Each model controls its own parameters

---

## 3. Text Output Validation {#text-output-validation}

### Question
> Should `get_answer()` and `stream_answer()` check if the model supports text output?

### Answer - Absolutely Yes! ✅

**Added:** `_check_text_output_support()` method in `BaseLLM`

```python
class BaseLLM(ABC):
    def _check_text_output_support(self) -> None:
        """Check if model supports text output."""
        if not self.metadata.supports_output_type(OutputMediaType.TEXT):
            raise UnsupportedOperationError(
                f"{self.metadata.model_name} does not support text output",
                hint="This model is for media generation only. Use get_image(), get_audio(), or get_video()."
            )
    
    @abstractmethod
    async def get_answer(self, messages, ctx, **kwargs):
        """Implementations should call self._check_text_output_support() first!"""
        pass
```

**Why This Matters:**

Imagine a future image-only model (like DALL-E):
```python
# DALL-E metadata
metadata = ModelMetadata(
    model_name="dall-e-3",
    supported_output_types={OutputMediaType.IMAGE}  # NO text output!
)

# Without validation
response = await dalle.get_answer(messages, ctx)  # ❌ Would fail mysteriously

# With validation
response = await dalle.get_answer(messages, ctx)
# ✅ Raises: UnsupportedOperationError: dall-e-3 does not support text output
#    Hint: Use get_image() instead
```

**Standard Pattern:**
```python
class AnyLLM(BaseLLM):
    async def get_answer(self, messages, ctx, **kwargs):
        # ALWAYS call this first!
        self._check_text_output_support()
        
        # ... rest of implementation
```

**Current Implementation:**
- ✅ GPT-4.1 Mini calls `_check_text_output_support()` ✅
- ✅ All media methods check output type ✅
- ✅ Provides clear, helpful error messages ✅

---

## 4. Multimodal I/O Design {#multimodal-design}

### Input (Multimodal Already Works!)

**Vision Input** - Standard OpenAI format:
```python
messages = [{
    "role": "user",
    "content": [
        {"type": "text", "text": "What's in this image?"},
        {"type": "image_url", "image_url": {"url": "https://..."}}
    ]
}]

# Or use convenience helper
response = await llm.get_answer_with_vision(
    prompt="What's in this image?",
    images=["https://example.com/img.jpg"],
    ctx=ctx
)
```

### Output (Media Generation - New!)

**Interface Design:**
```python
class BaseLLM(ABC):
    # Required (text output)
    async def get_answer(self, ...) -> LLMResponse: ...
    async def stream_answer(self, ...) -> AsyncIterator[LLMStreamChunk]: ...
    
    # Optional (media output - raises UnsupportedOperationError if not supported)
    async def get_image(self, ...) -> LLMImageResponse: ...
    async def stream_image(self, ...) -> AsyncIterator[LLMImageChunk]: ...
    async def get_audio(self, ...) -> LLMAudioResponse: ...
    async def stream_audio(self, ...) -> AsyncIterator[LLMAudioChunk]: ...
    async def get_video(self, ...) -> LLMVideoResponse: ...
    async def stream_video(self, ...) -> AsyncIterator[LLMVideoChunk]: ...
```

**Why Both Streaming and Non-Streaming?**

| Media Type | Streaming Useful? | Reason |
|------------|-------------------|--------|
| Image | Optional | Progressive rendering for large images |
| Audio | **YES** | Real-time TTS playback, music generation |
| Video | **YES** | Long videos need progressive download |

**Default Behavior (Text-Only Models):**
```python
# GPT-4.1 Mini (text-only)
llm.get_answer(...)  # ✅ Works
llm.stream_answer(...)  # ✅ Works
llm.get_image(...)  # ❌ Raises UnsupportedOperationError
llm.get_audio(...)  # ❌ Raises UnsupportedOperationError
llm.get_video(...)  # ❌ Raises UnsupportedOperationError
```

**Future Image Generation Model:**
```python
# DALL-E 3 (image generation)
class DALLE3(BaseLLM):
    async def get_answer(self, ...):
        # Check fails - no text output!
        self._check_text_output_support()  # Raises!
    
    async def get_image(self, ...):
        # Override to implement
        prompt = self._extract_prompt(messages)
        response = await self.connector.request("images/generations", {...})
        return LLMImageResponse(image_url=response["data"][0]["url"])
```

---

## 5. Session Management {#session-management}

### Question
> Why does the session matter in AzureConnector?

### Answer

**aiohttp.ClientSession** provides critical performance benefits:

### Performance Impact

| Scenario | Without Session | With Session |
|----------|----------------|--------------|
| First request | ~300ms | ~300ms |
| 10 subsequent requests | ~2.5 seconds | ~750ms |
| Connection overhead | Every request | Once |

**What Session Provides:**
1. ⚡ **Connection Pooling** - Reuses TCP connections (5-10x faster!)
2. 🔐 **Persistent Headers** - API key set once
3. 🔄 **HTTP/2 Support** - Request multiplexing
4. 🗑️ **Resource Management** - Proper cleanup

```python
class AzureConnector(BaseConnector):
    def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "api-key": self.api_key,  # Set once!
                    "Content-Type": "application/json"
                }
            )
        return self._session
    
    async def close(self) -> None:
        """Clean up resources."""
        if self._session and not self._session.closed:
            await self._session.close()
```

**Without session = New TCP connection + TLS handshake for EVERY request!**

---

## 6. Backup & Failover {#backup-failover}

### Design

**Minimal Configuration Needed:**
```python
config = {
    "api_key": "your-key",
    "endpoint": "https://eastus.openai.azure.com",
    "deployment_name": "gpt-4.1-mini",
    "backups": [
        {"endpoint": "https://westus.openai.azure.com"}
        # Inherits deployment_name and api_key!
    ]
}
```

**Automatic Failover:**
- ✅ Service Unavailable (503)
- ✅ Timeout Errors
- ✅ Connection Errors
- ❌ Authentication Errors (wrong credentials)
- ❌ Rate Limits (quota issue, not endpoint issue)

**Benefits:**
- Geographic redundancy
- Zero downtime
- Transparent to application code
- Minimal configuration overhead

---

## Architecture Summary

### Inheritance Hierarchy

```
ILLM (Protocol)                    # Contract: 2 methods required
  ↓ (duck typing)
BaseLLM (ABC)                      # Utilities: validation, tokens, media
  ↓ (inherits)
AzureBaseLLM (ABC)                 # Helpers: Azure parsing, streaming
  ↓ (inherits)
GPT_4_1_MiniLLM (Concrete)        # Implementation: transforms, calls API
```

### Flexibility Levels

```python
# Level 1: Maximum Flexibility (ILLM only)
class CustomLLM:  # No inheritance!
    async def get_answer(self, ...): ...
    async def stream_answer(self, ...): ...
# ✅ Matches ILLM protocol

# Level 2: Medium Flexibility (BaseLLM)
class CustomLLM(BaseLLM):
    async def get_answer(self, messages, ctx, **kwargs):
        self._validate_messages(messages)  # Utility from BaseLLM
        # ... custom logic

# Level 3: Azure Models (AzureBaseLLM)
class CustomAzureLLM(AzureBaseLLM):
    async def get_answer(self, messages, ctx, **kwargs):
        # ... model-specific transforms
        payload = self._build_azure_payload(messages, params)  # Helper!
        response = await self.connector.request(...)
        return self._parse_response(response, start_time)  # Helper!

# Level 4: Use existing implementation
llm = GPT_4_1_MiniLLM(connector, metadata)
```

### Key Principles

1. **Protocols Over Inheritance** - `ILLM` allows duck typing
2. **Helpers, Not Concrete Implementations** - Base classes provide utilities
3. **Model-Specific Implementations** - Each model controls its behavior
4. **Fail Fast with Clear Errors** - Check capabilities early
5. **Performance First** - Session reuse, connection pooling
6. **Resilience Built-In** - Backup endpoints, automatic failover

---

## Testing Strategy

### Unit Tests (Mocked)
```bash
uv run pytest tests/llms/test_custom_llm_implementations.py -v
uv run pytest tests/llms/test_custom_gpt41_mini_story.py -v
uv run pytest tests/llms/test_azure_backup_failover.py -v
```

### Integration Tests (Real API)
```bash
# Set credentials
$env:AZURE_OPENAI_KEY="..."
$env:AZURE_OPENAI_ENDPOINT="..."
$env:AZURE_OPENAI_DEPLOYMENT="..."

# Run
uv run pytest tests/llms/test_azure_integration.py -v
```

### All Tests
```bash
uv run pytest tests/llms/ -v
# Result: 61 passed, 6 skipped ✅
```

---

## Adding New Models

### Azure GPT-4o (Example)

```python
# 1. Create metadata
class GPT_4o_Metadata:
    NAME = "azure-gpt-4o"
    # ... capabilities, limits, costs

# 2. Create implementation
class GPT_4o_LLM(AzureBaseLLM):
    async def get_answer(self, messages, ctx, **kwargs):
        self._check_text_output_support()
        self._validate_messages(messages)
        
        # GPT-4o specific transformations
        params = self._merge_parameters(kwargs)
        # params = self._transform_parameters(params)  # If needed
        
        payload = self._build_azure_payload(messages, params)
        response = await self.connector.request("chat/completions", payload)
        return self._parse_response(response, time.time())
    
    async def stream_answer(self, messages, ctx, **kwargs):
        # Similar pattern
        ...

# 3. Register in factory
# In llm_factory.py:
if metadata.model_family == ModelFamily.AZURE_GPT_4O:
    return GPT_4o_LLM(connector=connector, metadata=metadata)
```

### Image Generation Model (DALL-E Example)

```python
class DALLE3(BaseLLM):
    # Text methods raise (image-only model)
    async def get_answer(self, ...):
        self._check_text_output_support()  # Raises!
    
    # Image methods implemented
    async def get_image(self, messages, ctx, **kwargs):
        prompt = self._extract_prompt(messages)
        response = await self.connector.request("images/generations", {
            "prompt": prompt,
            "size": kwargs.get("size", "1024x1024"),
            "quality": kwargs.get("quality", "standard")
        })
        
        return LLMImageResponse(
            image_url=response["data"][0]["url"],
            revised_prompt=response["data"][0].get("revised_prompt"),
            format="png",
            size=kwargs.get("size")
        )
```

---

## Best Practices

### DO ✅

1. **Call `_check_text_output_support()`** in text methods
2. **Call `_validate_token_limits()`** before API calls
3. **Inherit from provider base class** when available (AzureBaseLLM, OpenAIBaseLLM)
4. **Use helper methods** for common operations
5. **Add model-specific transformations** in model implementations
6. **Configure backup endpoints** for production systems
7. **Close connectors** when done: `await connector.close()`

### DON'T ❌

1. ❌ Instantiate abstract base classes directly
2. ❌ Implement everything in base classes
3. ❌ Skip validation checks
4. ❌ Forget to close sessions (resource leaks!)
5. ❌ Use same region for backup (no redundancy)
6. ❌ Assume all models work identically

---

## Decision Justifications

| Decision | Reason |
|----------|--------|
| Protocol + ABC | Flexibility + Convenience |
| Abstract AzureBaseLLM | Model-specific variations |
| Text output check | Prevent misuse of media-only models |
| Media methods in BaseLLM | Consistent API across all models |
| Vision helper in BaseLLM | Reusable across providers |
| Session management | Performance (10x faster) |
| Backup endpoints | High availability |
| Helpers not implementations | Flexibility for variations |

---

## Future Enhancements

1. **More Azure Models** - GPT-4o, GPT-3.5 Turbo, etc.
2. **OpenAI Provider** - Migrate to same pattern
3. **Bedrock Provider** - AWS models
4. **Image Generation** - DALL-E 3, Stable Diffusion
5. **Audio Generation** - TTS models
6. **Video Generation** - Sora
7. **Connection Pooling** - Advanced session management
8. **Load Balancing** - Smart endpoint selection
9. **Caching** - Response caching layer
10. **Metrics** - Request tracking, cost analysis

---

## References

- **ILLM Protocol**: `core/llms/interfaces/llm_interfaces.py`
- **BaseLLM**: `core/llms/providers/base/implementation.py`
- **AzureBaseLLM**: `core/llms/providers/azure/base_implementation.py`
- **GPT-4.1 Mini**: `core/llms/providers/azure/models/gpt_4_1_mini/`
- **Tests**: `tests/llms/`
- **Examples**: `core/llms/providers/EXAMPLE_USAGE.py`

---

**This architecture provides:**
- 🎯 Type safety through protocols
- 🔧 Convenience through base classes
- 🚀 Performance through session reuse
- 💪 Resilience through failover
- 📊 Clarity through abstraction layers
- ⚡ Flexibility through optional inheritance

