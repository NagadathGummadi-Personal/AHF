"""
Default values and configurations for LLM Subsystem.

This module provides default values, configuration helpers, and
standard defaults for LLM operations.
"""

from typing import Dict, Any, Optional
from .enum import LLMProvider, MessageRole
from .constants import (
    DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_MAX_RETRIES,
    DEFAULT_RETRY_DELAY_SECONDS,
    META_MODEL_NAME,
    META_PROVIDER,
    CONFIG_CATEGORY_PARAMETERS,
    TIMEOUT,
    MAX_RETRIES,
    RETRY_DELAY,
    OPENAI_DEFAULT_TEMPERATURE,
    OPENAI_DEFAULT_MAX_TOKENS,
    OPENAI_DEFAULT_TOP_P,
    OPENAI_DEFAULT_FREQUENCY_PENALTY,
    OPENAI_DEFAULT_PRESENCE_PENALTY,
    OPENAI_DEFAULT_N,
    OPENAI_DEFAULT_API_VERSION,
    OPENAI_DEFAULT_TIMEOUT,
    OPENAI_DEFAULT_MAX_RETRIES,
    OPENAI_DEFAULT_RETRY_DELAY,
    AZURE_DEFAULT_TEMPERATURE,
    AZURE_DEFAULT_MAX_TOKENS,
    AZURE_DEFAULT_TOP_P,
    AZURE_DEFAULT_FREQUENCY_PENALTY,
    AZURE_DEFAULT_PRESENCE_PENALTY,
    AZURE_DEFAULT_API_VERSION,
    AZURE_DEFAULT_TIMEOUT,
    AZURE_DEFAULT_MAX_RETRIES,
    AZURE_DEFAULT_RETRY_DELAY,
    AZURE_DEFAULT_API_VERSION_2024_02_15_PREVIEW,
    MESSAGE_COUNT,
    ESTIMATED_TOKENS,
    PARAMETERS,
    CONNECTOR,
    ROLE,
    CONTENT,
)


# ============================================================================
# DEFAULT CONNECTOR CONFIG
# ============================================================================

DEFAULT_CONNECTOR_CONFIG = {
    TIMEOUT: DEFAULT_TIMEOUT_SECONDS,
    MAX_RETRIES: DEFAULT_MAX_RETRIES,
    RETRY_DELAY: DEFAULT_RETRY_DELAY_SECONDS,
}


# ============================================================================
# OPENAI DEFAULTS
# ============================================================================

OPENAI_DEFAULT_PARAMETERS = {
    OPENAI_DEFAULT_TEMPERATURE: 0.7,
    OPENAI_DEFAULT_MAX_TOKENS: 4096,
    OPENAI_DEFAULT_TOP_P: 1.0,
    OPENAI_DEFAULT_FREQUENCY_PENALTY: 0.0,
    OPENAI_DEFAULT_PRESENCE_PENALTY: 0.0,
    OPENAI_DEFAULT_N: 1,
}


OPENAI_CONNECTOR_DEFAULTS = {
    OPENAI_DEFAULT_API_VERSION: None,
    OPENAI_DEFAULT_TIMEOUT: 30,
    OPENAI_DEFAULT_MAX_RETRIES: 3,
    OPENAI_DEFAULT_RETRY_DELAY: 1,
}


# ============================================================================
# AZURE OPENAI DEFAULTS
# ============================================================================

AZURE_DEFAULT_PARAMETERS = {
    AZURE_DEFAULT_TEMPERATURE: 0.7,
    AZURE_DEFAULT_MAX_TOKENS: 4096,
    AZURE_DEFAULT_TOP_P: 1.0,
    AZURE_DEFAULT_FREQUENCY_PENALTY: 0.0,
    AZURE_DEFAULT_PRESENCE_PENALTY: 0.0,
}


AZURE_CONNECTOR_DEFAULTS = {
    AZURE_DEFAULT_API_VERSION: AZURE_DEFAULT_API_VERSION_2024_02_15_PREVIEW,
    AZURE_DEFAULT_TIMEOUT: 30,
    AZURE_DEFAULT_MAX_RETRIES: 3,
    AZURE_DEFAULT_RETRY_DELAY: 1,
}


# ============================================================================
# MESSAGE TEMPLATES
# ============================================================================

def create_system_message(content: str) -> Dict[str, str]:
    """
    Create a standard system message.
    
    Args:
        content: System message content
        
    Returns:
        Formatted system message dict
        
    Example:
        system_msg = create_system_message("You are a helpful assistant.")
    """
    return {
        ROLE: MessageRole.SYSTEM.value,
        CONTENT : content
    }


def create_user_message(content: str) -> Dict[str, str]:
    """
    Create a standard user message.
    
    Args:
        content: User message content
        
    Returns:
        Formatted user message dict
        
    Example:
        user_msg = create_user_message("Hello, how are you?")
    """
    return {
        ROLE : MessageRole.USER.value,
        CONTENT : content
    }


def create_assistant_message(content: str) -> Dict[str, str]:
    """
    Create a standard assistant message.
    
    Args:
        content: Assistant message content
        
    Returns:
        Formatted assistant message dict
        
    Example:
        assistant_msg = create_assistant_message("I'm doing well, thank you!")
    """
    return {
        ROLE : MessageRole.ASSISTANT.value,
        CONTENT : content
    }


# ============================================================================
# CONTEXT DATA GENERATORS
# ============================================================================

def DEFAULT_LLM_CONTEXT_DATA(model_name: str, provider: str, **kwargs) -> Dict[str, Any]:
    """
    Generate default context data for LLM logging and tracking.
    
    Args:
        model_name: Name of the model
        provider: Provider identifier
        **kwargs: Additional context fields
        
    Returns:
        Dictionary with context data
        
    Example:
        context = DEFAULT_LLM_CONTEXT_DATA(
            "gpt-4",
            "openai",
            request_id="req-123"
        )
    """
    context = {
        META_MODEL_NAME: model_name,
        META_PROVIDER: provider,
    }
    context.update(kwargs)
    return context


def LLM_REQUEST_CONTEXT(
    model_name: str,
    provider: str,
    message_count: int,
    estimated_tokens: Optional[int] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Generate context data for LLM request tracking.
    
    Args:
        model_name: Name of the model
        provider: Provider identifier
        message_count: Number of messages in request
        estimated_tokens: Estimated input tokens
        **kwargs: Additional context fields
        
    Returns:
        Dictionary with request context
        
    Example:
        context = LLM_REQUEST_CONTEXT(
            "gpt-4",
            "openai",
            message_count=3,
            estimated_tokens=150
        )
    """
    context = DEFAULT_LLM_CONTEXT_DATA(model_name, provider)
    context.update({
        MESSAGE_COUNT : message_count,
        ESTIMATED_TOKENS : estimated_tokens,
    })
    context.update(kwargs)
    return context


# ============================================================================
# PARAMETER HELPERS
# ============================================================================

def merge_parameters(
    user_params: Dict[str, Any],
    defaults: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Merge user parameters with defaults.
    
    User parameters take precedence over defaults.
    
    Args:
        user_params: User-provided parameters
        defaults: Default parameters
        
    Returns:
        Merged parameters
        
    Example:
        params = merge_parameters(
            {"temperature": 0.5},
            DEFAULT_LLM_PARAMETERS
        )
    """
    merged = defaults.copy()
    merged.update({k: v for k, v in user_params.items() if v is not None})
    return merged


def filter_none_values(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove None values from parameters dictionary.
    
    Args:
        params: Parameters dictionary
        
    Returns:
        Filtered parameters
        
    Example:
        params = filter_none_values({
            "temperature": 0.7,
            "max_tokens": None,
            "top_p": 1.0
        })
        # Returns: {"temperature": 0.7, "top_p": 1.0}
    """
    return {k: v for k, v in params.items() if v is not None}

# ============================================================================
# PROVIDER-SPECIFIC DEFAULTS
# ============================================================================

PROVIDER_DEFAULTS = {
    LLMProvider.OPENAI: {
        PARAMETERS : OPENAI_DEFAULT_PARAMETERS,
        CONNECTOR : OPENAI_CONNECTOR_DEFAULTS,
    },
    LLMProvider.AZURE: {
        PARAMETERS : AZURE_DEFAULT_PARAMETERS,
        CONNECTOR : AZURE_CONNECTOR_DEFAULTS,
    },
}


def get_provider_defaults(provider: LLMProvider, category: str = CONFIG_CATEGORY_PARAMETERS) -> Dict[str, Any]:
    """
    Get default values for a specific provider.
    
    Args:
        provider: Provider identifier
        category: Category of defaults (CONFIG_CATEGORY_PARAMETERS or CONFIG_CATEGORY_CONNECTOR)
        
    Returns:
        Provider-specific defaults
        
    Example:
        defaults = get_provider_defaults(LLMProvider.AZURE, "parameters")
    """
    provider_config = PROVIDER_DEFAULTS.get(provider, {})
    return provider_config.get(category, {}).copy()
