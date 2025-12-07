"""
LLM Integration Utilities for Prompt Registry.

Provides helper functions and classes for integrating prompts with LLM calls,
including automatic metrics recording.
"""

import time
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from functools import wraps

if TYPE_CHECKING:
    from ..interfaces.prompt_registry_interfaces import IPromptRegistry
    from ...llms.interfaces.llm_interfaces import ILLM
    from ...llms.spec.llm_context import LLMContext
    from ...llms.spec.llm_result import LLMResponse


class PromptAwareLLM:
    """
    Wrapper that automatically records prompt metrics for LLM calls.
    
    Wraps an existing LLM implementation and records usage metrics
    to the prompt registry after each call.
    
    Usage:
        registry = LocalPromptRegistry(storage_path=".prompts")
        llm = GPT4LLM(...)
        
        # Wrap the LLM
        tracked_llm = PromptAwareLLM(llm, registry)
        
        # Get and use a prompt
        result = await registry.get_prompt_with_fallback(
            "greeting",
            variables={"name": "Assistant"}
        )
        
        # Make LLM call with automatic metrics tracking
        response = await tracked_llm.get_answer(
            messages=[{"role": "system", "content": result.content}],
            ctx=ctx,
            prompt_id=result.prompt_id  # Pass prompt_id for tracking
        )
        # Metrics are automatically recorded!
    """
    
    def __init__(
        self,
        llm: 'ILLM',
        registry: 'IPromptRegistry',
        record_on_failure: bool = True
    ):
        """
        Initialize the prompt-aware LLM wrapper.
        
        Args:
            llm: The underlying LLM implementation
            registry: Prompt registry for metrics recording
            record_on_failure: Whether to record metrics on failed calls
        """
        self.llm = llm
        self.registry = registry
        self.record_on_failure = record_on_failure
    
    async def get_answer(
        self,
        messages: List[Dict[str, Any]],
        ctx: 'LLMContext',
        prompt_id: Optional[str] = None,
        **kwargs: Any
    ) -> 'LLMResponse':
        """
        Call the LLM and optionally record prompt metrics.
        
        Args:
            messages: Messages to send to LLM
            ctx: LLM context
            prompt_id: Optional prompt ID for metrics tracking
            **kwargs: Additional LLM parameters
            
        Returns:
            LLM response
        """
        start_time = time.time()
        success = True
        response = None
        
        try:
            response = await self.llm.get_answer(messages, ctx, **kwargs)
            return response
            
        except Exception as e:
            success = False
            raise
            
        finally:
            latency_ms = (time.time() - start_time) * 1000
            
            if prompt_id and (success or self.record_on_failure):
                await self._record_metrics(
                    prompt_id=prompt_id,
                    latency_ms=latency_ms,
                    response=response,
                    success=success
                )
    
    async def _record_metrics(
        self,
        prompt_id: str,
        latency_ms: float,
        response: Optional['LLMResponse'],
        success: bool
    ) -> None:
        """Record metrics to the prompt registry."""
        try:
            prompt_tokens = 0
            completion_tokens = 0
            cost = 0.0
            
            if response and hasattr(response, 'usage') and response.usage:
                prompt_tokens = response.usage.prompt_tokens or 0
                completion_tokens = response.usage.completion_tokens or 0
                cost = response.usage.cost_usd or 0.0
            
            await self.registry.record_usage(
                prompt_id,
                latency_ms=latency_ms,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cost=cost,
                success=success
            )
        except Exception:
            # Don't fail the LLM call if metrics recording fails
            pass


async def call_with_prompt(
    llm: 'ILLM',
    registry: 'IPromptRegistry',
    prompt_label: str,
    user_message: str,
    ctx: 'LLMContext',
    variables: Optional[Dict[str, Any]] = None,
    system_message: bool = True,
    **llm_kwargs: Any
) -> tuple['LLMResponse', str]:
    """
    Convenience function to call LLM with a registered prompt.
    
    Retrieves a prompt from the registry, renders it with variables,
    calls the LLM, and records usage metrics.
    
    Args:
        llm: LLM implementation
        registry: Prompt registry
        prompt_label: Label of the prompt to use
        user_message: User message to send
        ctx: LLM context
        variables: Variables to substitute in prompt
        system_message: Whether prompt is a system message (default True)
        **llm_kwargs: Additional LLM parameters
        
    Returns:
        Tuple of (LLMResponse, prompt_id)
        
    Usage:
        response, prompt_id = await call_with_prompt(
            llm=my_llm,
            registry=my_registry,
            prompt_label="code_review",
            user_message="Review this code: ...",
            ctx=ctx,
            variables={"language": "Python"}
        )
    """
    # Get prompt with fallback
    result = await registry.get_prompt_with_fallback(
        prompt_label,
        variables=variables
    )
    
    # Build messages
    messages = []
    if system_message:
        messages.append({"role": "system", "content": result.content})
    else:
        messages.append({"role": "user", "content": result.content})
    
    if user_message:
        messages.append({"role": "user", "content": user_message})
    
    # Call LLM with tracking
    start_time = time.time()
    success = True
    response = None
    
    try:
        response = await llm.get_answer(messages, ctx, **llm_kwargs)
        return response, result.prompt_id
        
    except Exception as e:
        success = False
        raise
        
    finally:
        latency_ms = (time.time() - start_time) * 1000
        
        prompt_tokens = 0
        completion_tokens = 0
        cost = 0.0
        
        if response and hasattr(response, 'usage') and response.usage:
            prompt_tokens = response.usage.prompt_tokens or 0
            completion_tokens = response.usage.completion_tokens or 0
            cost = response.usage.cost_usd or 0.0
        
        try:
            await registry.record_usage(
                result.prompt_id,
                latency_ms=latency_ms,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cost=cost,
                success=success
            )
        except Exception:
            pass  # Don't fail if metrics recording fails


__all__ = [
    "PromptAwareLLM",
    "call_with_prompt",
]
