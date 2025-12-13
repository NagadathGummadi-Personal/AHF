"""
Application Settings

Centralized settings with environment variable support.
Priority: Environment Variables > Dynamic Variables > Defaults

Usage:
    from air.config import get_settings
    
    settings = get_settings()
    url = settings.workflow_init_url
    
Version: 1.0.0
"""

import os
from functools import lru_cache
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

from .defaults import Defaults


class Settings(BaseSettings):
    """
    Application settings with automatic environment variable loading.
    
    Environment variables are automatically loaded with the prefix AHF_.
    Example: AHF_WORKFLOW_INIT_URL overrides workflow_init_url
    """
    
    # =========================================================================
    # API Endpoints
    # =========================================================================
    workflow_init_url: str = Field(
        default=Defaults.WORKFLOW_INIT_URL,
        description="URL for workflow initialization"
    )
    handover_url: str = Field(
        default=Defaults.HANDOVER_URL,
        description="URL for call handover"
    )
    service_info_url: str = Field(
        default=Defaults.SERVICE_INFO_URL,
        description="URL for service info retrieval"
    )
    pricing_info_url: str = Field(
        default=Defaults.PRICING_INFO_URL,
        description="URL for pricing info"
    )
    therapist_url: str = Field(
        default=Defaults.THERAPIST_URL,
        description="URL for therapist lookup"
    )
    kb_search_url: str = Field(
        default=Defaults.KB_SEARCH_URL,
        description="URL for knowledge base search"
    )
    
    # =========================================================================
    # Timeout Configuration
    # =========================================================================
    http_timeout_ms: int = Field(default=Defaults.HTTP_TIMEOUT_MS)
    llm_timeout_ms: int = Field(default=Defaults.LLM_TIMEOUT_MS)
    soft_timeout_ms: int = Field(default=Defaults.SOFT_TIMEOUT_MS)
    turn_timeout_ms: int = Field(default=Defaults.TURN_TIMEOUT_MS)
    interrupt_check_interval_ms: int = Field(default=Defaults.INTERRUPT_CHECK_INTERVAL_MS)
    
    # =========================================================================
    # Retry Configuration
    # =========================================================================
    max_retries: int = Field(default=Defaults.MAX_RETRIES)
    retry_delay_ms: int = Field(default=Defaults.RETRY_DELAY_MS)
    retry_backoff_multiplier: float = Field(default=Defaults.RETRY_BACKOFF_MULTIPLIER)
    
    # =========================================================================
    # Queue Configuration
    # =========================================================================
    task_queue_max_size: int = Field(default=Defaults.TASK_QUEUE_MAX_SIZE)
    
    # =========================================================================
    # Memory Configuration
    # =========================================================================
    max_conversation_messages: int = Field(default=Defaults.MAX_CONVERSATION_MESSAGES)
    max_state_snapshots: int = Field(default=Defaults.MAX_STATE_SNAPSHOTS)
    
    # =========================================================================
    # Agent Configuration
    # =========================================================================
    agent_max_iterations: int = Field(default=Defaults.AGENT_MAX_ITERATIONS)
    agent_temperature: float = Field(default=Defaults.AGENT_TEMPERATURE)
    agent_name: str = Field(default=Defaults.AGENT_NAME)
    
    # =========================================================================
    # LLM Configuration
    # =========================================================================
    llm_model: str = Field(default=Defaults.LLM_MODEL)
    llm_provider: str = Field(default=Defaults.LLM_PROVIDER)
    azure_endpoint: str = Field(default=Defaults.AZURE_ENDPOINT)
    azure_api_version: str = Field(default=Defaults.AZURE_API_VERSION)
    azure_api_key: Optional[str] = Field(default=None)
    
    # =========================================================================
    # Supported Languages
    # =========================================================================
    supported_languages: List[str] = Field(default=Defaults.SUPPORTED_LANGUAGES)
    
    model_config = {
        "env_prefix": "AHF_",
        "case_sensitive": False,
        "extra": "ignore",
    }
    
    def get_with_override(
        self,
        key: str,
        dynamic_vars: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Get a setting value with dynamic variable override support.
        
        Priority: Dynamic Variables > Settings > Defaults
        
        Args:
            key: Setting key (e.g., "agent_name")
            dynamic_vars: Dynamic variables from workflow init
            
        Returns:
            The setting value
        """
        # Check dynamic variables first
        if dynamic_vars and key in dynamic_vars:
            return dynamic_vars[key]
        
        # Fall back to settings
        return getattr(self, key, None)
    
    def to_dict(self) -> Dict[str, Any]:
        """Export settings to dictionary."""
        return self.model_dump()


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Settings are cached for performance. This is safe for Fargate/containers
    because settings are:
    - Loaded from environment variables at startup
    - Immutable (read-only)
    - Same for all requests in the container
    
    Call Settings() directly if you need a fresh instance.
    
    Returns:
        Settings instance
    """
    return Settings()


class DynamicConfig:
    """
    Runtime configuration that combines settings with dynamic variables.
    
    This class provides a unified interface for accessing configuration
    values that can come from multiple sources.
    """
    
    def __init__(
        self,
        settings: Optional[Settings] = None,
        dynamic_vars: Optional[Dict[str, Any]] = None,
    ):
        self._settings = settings or get_settings()
        self._dynamic_vars = dynamic_vars or {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value with fallback chain."""
        # 1. Check dynamic variables
        if key in self._dynamic_vars:
            return self._dynamic_vars[key]
        
        # 2. Check settings
        if hasattr(self._settings, key):
            return getattr(self._settings, key)
        
        # 3. Check defaults
        if hasattr(Defaults, key.upper()):
            return getattr(Defaults, key.upper())
        
        # 4. Return default
        return default
    
    def set_dynamic(self, key: str, value: Any) -> None:
        """Set a dynamic variable."""
        self._dynamic_vars[key] = value
    
    def update_dynamic(self, variables: Dict[str, Any]) -> None:
        """Update multiple dynamic variables."""
        self._dynamic_vars.update(variables)
    
    @property
    def dynamic_vars(self) -> Dict[str, Any]:
        """Get all dynamic variables."""
        return self._dynamic_vars.copy()
    
    def to_dict(self) -> Dict[str, Any]:
        """Export all configuration to dictionary."""
        result = self._settings.to_dict()
        result.update(self._dynamic_vars)
        return result

