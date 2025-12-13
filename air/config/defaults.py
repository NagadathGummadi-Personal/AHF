"""
Default Configuration Values

These are fallback values when environment variables or dynamic variables are not provided.
All values can be overridden via:
1. Environment variables (highest priority)
2. Dynamic variables from WorkflowInit
3. These defaults (lowest priority)

Version: 1.0.0
"""

import os
from typing import Any, Dict, List, Optional


class Environment:
    """Environment detection and configuration."""
    
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    
    @classmethod
    def get_current(cls) -> str:
        """Get current environment from AHF_ENVIRONMENT or default to production."""
        return os.getenv("AHF_ENVIRONMENT", cls.PRODUCTION).lower()
    
    @classmethod
    def is_development(cls) -> bool:
        return cls.get_current() == cls.DEVELOPMENT
    
    @classmethod
    def is_staging(cls) -> bool:
        return cls.get_current() == cls.STAGING
    
    @classmethod
    def is_production(cls) -> bool:
        return cls.get_current() == cls.PRODUCTION


class ToolURLs:
    """
    Environment-aware tool URL configuration.
    
    URLs can be overridden via environment variables:
    - AHF_HANDOVER_URL
    - AHF_SERVICE_INFO_URL
    - AHF_PRICING_INFO_URL
    - AHF_THERAPIST_URL
    - AHF_KB_SEARCH_URL
    
    Usage:
        urls = ToolURLs()
        handover_url = urls.handover_url
    """
    
    # Production URLs (default)
    _PROD_URLS = {
        "handover": "https://voice-agent.zenoti.com/workflow/TransferCall",
        "service_info": "https://nu8kqsh6hj.execute-api.ap-south-1.amazonaws.com/workflow/GetServicesInfoByServiceCodes",
        "pricing_info": "https://voice-agent.zenoti.com/workflow/GetPricingInfo",
        "therapist": "https://voice-agent.zenoti.com/workflow/GetTherapistForService",
        "kb_search": "https://voice-agent.zenoti.com/workflow/KBSearch",
        "workflow_init": "https://voice-agent.zenoti.com/workflow/ElevenLabsClientInitialization",
    }
    
    # Development URLs (can be customized for local testing)
    _DEV_URLS = {
        "handover": "https://voice-agent.zenoti.com/workflow/TransferCall",
        "service_info": "https://nu8kqsh6hj.execute-api.ap-south-1.amazonaws.com/workflow/GetServicesInfoByServiceCodes",
        "pricing_info": "https://voice-agent.zenoti.com/workflow/GetPricingInfo",
        "therapist": "https://voice-agent.zenoti.com/workflow/GetTherapistForService",
        "kb_search": "https://voice-agent.zenoti.com/workflow/KBSearch",
        "workflow_init": "https://voice-agent.zenoti.com/workflow/ElevenLabsClientInitialization",
    }
    
    def __init__(self, environment: Optional[str] = None):
        """
        Initialize tool URLs for the given environment.
        
        Args:
            environment: Override environment (defaults to AHF_ENVIRONMENT)
        """
        self._environment = environment or Environment.get_current()
        self._base_urls = self._DEV_URLS if self._environment == Environment.DEVELOPMENT else self._PROD_URLS
    
    @property
    def environment(self) -> str:
        return self._environment
    
    @property
    def handover_url(self) -> str:
        return os.getenv("AHF_HANDOVER_URL", self._base_urls["handover"])
    
    @property
    def service_info_url(self) -> str:
        return os.getenv("AHF_SERVICE_INFO_URL", self._base_urls["service_info"])
    
    @property
    def pricing_info_url(self) -> str:
        return os.getenv("AHF_PRICING_INFO_URL", self._base_urls["pricing_info"])
    
    @property
    def therapist_url(self) -> str:
        return os.getenv("AHF_THERAPIST_URL", self._base_urls["therapist"])
    
    @property
    def kb_search_url(self) -> str:
        return os.getenv("AHF_KB_SEARCH_URL", self._base_urls["kb_search"])
    
    @property
    def workflow_init_url(self) -> str:
        return os.getenv("AHF_WORKFLOW_INIT_URL", self._base_urls["workflow_init"])
    
    def to_dict(self) -> Dict[str, str]:
        """Get all URLs as a dictionary."""
        return {
            "handover_url": self.handover_url,
            "service_info_url": self.service_info_url,
            "pricing_info_url": self.pricing_info_url,
            "therapist_url": self.therapist_url,
            "kb_search_url": self.kb_search_url,
            "workflow_init_url": self.workflow_init_url,
        }


# Singleton instance for convenient access
_tool_urls: Optional[ToolURLs] = None


def get_tool_urls() -> ToolURLs:
    """Get the singleton ToolURLs instance."""
    global _tool_urls
    if _tool_urls is None:
        _tool_urls = ToolURLs()
    return _tool_urls


class _DefaultsMeta(type):
    """
    Metaclass for Defaults to provide dynamic URL resolution.
    
    Allows Defaults.HANDOVER_URL to return environment-aware URLs
    while maintaining backward compatibility with class-level access.
    """
    
    @property
    def WORKFLOW_INIT_URL(cls) -> str:
        return get_tool_urls().workflow_init_url
    
    @property
    def HANDOVER_URL(cls) -> str:
        return get_tool_urls().handover_url
    
    @property
    def SERVICE_INFO_URL(cls) -> str:
        return get_tool_urls().service_info_url
    
    @property
    def PRICING_INFO_URL(cls) -> str:
        return get_tool_urls().pricing_info_url
    
    @property
    def THERAPIST_URL(cls) -> str:
        return get_tool_urls().therapist_url
    
    @property
    def KB_SEARCH_URL(cls) -> str:
        return get_tool_urls().kb_search_url


class Defaults(metaclass=_DefaultsMeta):
    """
    Default configuration values for the application.
    
    API Endpoints are resolved dynamically via ToolURLs for environment awareness.
    Access them as: Defaults.HANDOVER_URL, Defaults.SERVICE_INFO_URL, etc.
    """
    
    # =========================================================================
    # Timeout Configuration (milliseconds)
    # =========================================================================
    HTTP_TIMEOUT_MS = 30000
    LLM_TIMEOUT_MS = 60000
    SOFT_TIMEOUT_MS = 1500      # Time before generating engagement message
    TURN_TIMEOUT_MS = 2000      # Max silence before prompting user
    INTERRUPT_CHECK_INTERVAL_MS = 50
    
    # =========================================================================
    # Retry Configuration
    # =========================================================================
    MAX_RETRIES = 3
    RETRY_DELAY_MS = 1000
    RETRY_BACKOFF_MULTIPLIER = 2.0
    
    # =========================================================================
    # Queue Configuration (in-memory for low-latency)
    # =========================================================================
    TASK_QUEUE_MAX_SIZE = 100
    
    # =========================================================================
    # Memory Configuration
    # =========================================================================
    MAX_CONVERSATION_MESSAGES = 100
    MAX_STATE_SNAPSHOTS = 50  # For internal state tracking
    
    # =========================================================================
    # Agent Configuration
    # =========================================================================
    AGENT_MAX_ITERATIONS = 20
    AGENT_TEMPERATURE = 0.7
    AGENT_NAME = "AI Receptionist"
    
    # =========================================================================
    # LLM Configuration
    # =========================================================================
    LLM_MODEL = "gpt-4.1-mini"
    LLM_PROVIDER = "azure"
    AZURE_ENDPOINT = "https://zeenie-sweden.openai.azure.com/"
    AZURE_API_VERSION = "2024-02-15-preview"
    
    # =========================================================================
    # Supported Languages
    # =========================================================================
    SUPPORTED_LANGUAGES: List[str] = [
        "English", "Chinese", "French", "Spanish", "Czech", "Russian"
    ]
    
    # =========================================================================
    # First Message Templates
    # =========================================================================
    OUTSIDE_BUSINESS_NEW_USER_MESSAGE = (
        "Hey, you have reached outside business hours. I still can help you."
    )
    INSIDE_BUSINESS_NEW_USER_MESSAGE = (
        "Hey, how can I help you today?"
    )
    OUTSIDE_BUSINESS_EXISTING_USER_MESSAGE = (
        "Hey {guest_name}, you have reached outside business hours. I still can help you."
    )
    INSIDE_BUSINESS_EXISTING_USER_MESSAGE = (
        "Hey {guest_name}, how can I help you today?"
    )
    
    # =========================================================================
    # Workflow Node IDs
    # =========================================================================
    NODE_WORKFLOW_INIT = "workflow_init"
    NODE_FIRST_MESSAGE = "first_message_maker"
    NODE_GREETING_AGENT = "greeting_routing_agent"
    NODE_TRANSFORMATION = "transformation_tool"
    NODE_SERVICE_CHECK = "service_check_agent"
    NODE_SERVICE_INFO = "service_info_retrieval"
    NODE_GUIDELINES = "service_guidelines_agent"
    NODE_BOOKING = "booking_tool"
    NODE_FALLBACK = "fallback_agent"
    
    # =========================================================================
    # Task States
    # =========================================================================
    TASK_STATE_PENDING = "pending"
    TASK_STATE_IN_PROGRESS = "in_progress"
    TASK_STATE_COMPLETED = "completed"
    TASK_STATE_PAUSED = "paused"
    TASK_STATE_FAILED = "failed"
    
    # =========================================================================
    # Intent Types
    # =========================================================================
    INTENT_BOOK = "BOOK"
    INTENT_CANCEL = "CANCEL"
    INTENT_RESCHEDULE = "RESCHEDULE"
    INTENT_FAQ = "FAQ"
    INTENT_HANDOVER = "HANDOVER"
    INTENT_UNKNOWN = "UNKNOWN"
    
    @classmethod
    def get_all(cls) -> Dict[str, Any]:
        """Get all default values as a dictionary."""
        return {
            key: value for key, value in vars(cls).items()
            if not key.startswith("_") and not callable(value)
        }

