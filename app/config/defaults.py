"""
Default Configuration Values

These are fallback values when environment variables or dynamic variables are not provided.
All values can be overridden via:
1. Environment variables (highest priority)
2. Dynamic variables from WorkflowInit
3. These defaults (lowest priority)

Version: 1.0.0
"""

from typing import Any, Dict, List


class Defaults:
    """Default configuration values for the application."""
    
    # =========================================================================
    # API Endpoints
    # =========================================================================
    WORKFLOW_INIT_URL = "https://voice-agent.zenoti.com/workflow/ElevenLabsClientInitialization"
    HANDOVER_URL = "https://voice-agent.zenoti.com/workflow/TransferCall"
    SERVICE_INFO_URL = "https://nu8kqsh6hj.execute-api.ap-south-1.amazonaws.com/workflow/GetServicesInfoByServiceCodes"
    PRICING_INFO_URL = "https://voice-agent.zenoti.com/workflow/GetPricingInfo"
    THERAPIST_URL = "https://voice-agent.zenoti.com/workflow/GetTherapistForService"
    KB_SEARCH_URL = "https://voice-agent.zenoti.com/workflow/KBSearch"
    
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
    # Queue Configuration
    # =========================================================================
    TASK_QUEUE_MAX_SIZE = 100
    TASK_QUEUE_PERSIST_INTERVAL_MS = 100
    
    # =========================================================================
    # Checkpoint Configuration
    # =========================================================================
    CHECKPOINT_STRATEGY = "lazy"  # "immediate", "lazy", "batched"
    CHECKPOINT_BATCH_SIZE = 10
    CHECKPOINT_BATCH_TIMEOUT_MS = 100
    CHECKPOINT_STORAGE_PATH = ".checkpoints"
    CHECKPOINT_WAL_ENABLED = True
    CHECKPOINT_CACHE_MAX_SIZE = 1000
    
    # =========================================================================
    # Memory Configuration
    # =========================================================================
    MAX_CONVERSATION_MESSAGES = 100
    MAX_CHECKPOINTS = 50
    
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

