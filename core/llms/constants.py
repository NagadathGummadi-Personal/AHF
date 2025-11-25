"""
Constants for LLM Subsystem.

This module defines all constants used throughout the LLM subsystem including
log messages, configuration keys, defaults, and limits.
"""

# ============================================================================
# ENCODING & FORMAT
# ============================================================================

UTF_8 = "utf-8"
JSON_CONTENT_TYPE = "application/json"
TEXT_CONTENT_TYPE = "text/plain"

# ============================================================================
# LOG MESSAGES
# ============================================================================

# Connection & initialization
LOG_CONNECTOR_INITIALIZING = "Initializing LLM connector"
LOG_CONNECTOR_CONNECTED = "LLM connector connected successfully"
LOG_CONNECTOR_DISCONNECTED = "LLM connector disconnected"
LOG_CONNECTOR_CONNECTION_FAILED = "LLM connector connection failed"
LOG_CONNECTOR_TESTING = "Testing LLM connector connection"
LOG_CONNECTOR_TEST_SUCCESS = "LLM connector test successful"
LOG_CONNECTOR_TEST_FAILED = "LLM connector test failed"

# Request lifecycle
LOG_LLM_REQUEST_STARTING = "Starting LLM request"
LOG_LLM_REQUEST_COMPLETED = "LLM request completed successfully"
LOG_LLM_REQUEST_FAILED = "LLM request failed"
LOG_LLM_STREAMING_STARTED = "LLM streaming started"
LOG_LLM_STREAMING_CHUNK = "Received LLM streaming chunk"
LOG_LLM_STREAMING_COMPLETED = "LLM streaming completed"
LOG_LLM_STREAMING_FAILED = "LLM streaming failed"

# Validation
LOG_VALIDATING_INPUT = "Validating LLM input"
LOG_VALIDATION_PASSED = "LLM input validation passed"
LOG_VALIDATION_FAILED = "LLM input validation failed"
LOG_VALIDATING_PARAMETERS = "Validating LLM parameters"
LOG_PARAMETER_VALIDATION_PASSED = "LLM parameter validation passed"
LOG_PARAMETER_VALIDATION_FAILED = "LLM parameter validation failed"

# Token management
LOG_ESTIMATING_TOKENS = "Estimating token count"
LOG_TOKEN_LIMIT_EXCEEDED = "Token limit exceeded"
LOG_TOKEN_LIMIT_WARNING = "Approaching token limit"

# Model registry
LOG_REGISTERING_MODEL = "Registering model in registry"
LOG_MODEL_REGISTERED = "Model registered successfully"
LOG_MODEL_LOOKUP = "Looking up model in registry"
LOG_MODEL_NOT_FOUND = "Model not found in registry"
LOG_REGISTRY_INITIALIZING = "Initializing model registry"

# Cost & usage
LOG_CALCULATING_COST = "Calculating LLM usage cost"
LOG_COST_CALCULATED = "LLM cost calculated"
LOG_USAGE_TRACKED = "LLM usage tracked"

# ============================================================================
# ERROR MESSAGES
# ============================================================================

ERROR_INVALID_INPUT = "Invalid input provided to LLM"
ERROR_UNSUPPORTED_INPUT_TYPE = "Unsupported input media type: {input_type}"
ERROR_UNSUPPORTED_OUTPUT_TYPE = "Unsupported output media type: {output_type}"
ERROR_MODEL_NOT_FOUND = "Model not found: {model_name}"
ERROR_PROVIDER_NOT_AVAILABLE = "Provider not available: {provider}"
ERROR_CONNECTION_FAILED = "Connection to provider failed: {provider}"
ERROR_AUTHENTICATION_FAILED = "Authentication failed for provider: {provider}"
ERROR_RATE_LIMIT_EXCEEDED = "Rate limit exceeded for provider: {provider}"
ERROR_QUOTA_EXCEEDED = "Quota exceeded for model: {model_name}"
ERROR_INVALID_RESPONSE = "Invalid response from provider: {provider}"
ERROR_JSON_PARSE_FAILED = "Failed to parse JSON response"
ERROR_TOKEN_LIMIT_EXCEEDED = "Token limit exceeded: {tokens} > {limit}"
ERROR_INVALID_PARAMETER = "Invalid parameter: {parameter}"
ERROR_MISSING_PARAMETER = "Missing required parameter: {parameter}"
ERROR_TIMEOUT = "Request timed out after {timeout}s"
ERROR_SERVICE_UNAVAILABLE = "Service unavailable: {provider}"

# ============================================================================
# CONFIGURATION KEYS
# ============================================================================

# Connector configuration
CONFIG_PROVIDER = "provider"
CONFIG_API_KEY = "api_key"
CONFIG_API_KEY_ENV = "api_key_env"
CONFIG_ENDPOINT = "endpoint"
CONFIG_REGION = "region"
CONFIG_DEPLOYMENT_NAME = "deployment_name"
CONFIG_API_VERSION = "api_version"
CONFIG_TIMEOUT = "timeout"
CONFIG_MAX_RETRIES = "max_retries"
CONFIG_RETRY_DELAY = "retry_delay"

# Model configuration
CONFIG_MODEL_NAME = "model_name"
CONFIG_MAX_TOKENS = "max_tokens"
CONFIG_TEMPERATURE = "temperature"
CONFIG_TOP_P = "top_p"
CONFIG_FREQUENCY_PENALTY = "frequency_penalty"
CONFIG_PRESENCE_PENALTY = "presence_penalty"
CONFIG_STOP_SEQUENCES = "stop"
CONFIG_STREAM = "stream"

# ============================================================================
# DEFAULT VALUES
# ============================================================================

# Connection defaults
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY_SECONDS = 1
DEFAULT_BACKOFF_FACTOR = 2

# Parameter defaults
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 4096
DEFAULT_TOP_P = 1.0
DEFAULT_FREQUENCY_PENALTY = 0.0
DEFAULT_PRESENCE_PENALTY = 0.0

# Token limits (conservative estimates)
DEFAULT_MAX_CONTEXT_LENGTH = 8192
DEFAULT_MAX_INPUT_TOKENS = 4096
DEFAULT_MAX_OUTPUT_TOKENS = 4096

# Streaming
DEFAULT_STREAM_BUFFER_SIZE = 1024
DEFAULT_STREAM_TIMEOUT = 60

# ============================================================================
# STANDARD PARAMETER NAMES (OpenAI-style)
# ============================================================================

PARAM_MAX_TOKENS = "max_tokens"
PARAM_MAX_COMPLETION_TOKENS = "max_completion_tokens"  # New parameter name for GPT-4o/4.1
PARAM_TEMPERATURE = "temperature"
PARAM_TOP_P = "top_p"
PARAM_FREQUENCY_PENALTY = "frequency_penalty"
PARAM_PRESENCE_PENALTY = "presence_penalty"
PARAM_STOP = "stop"
PARAM_STREAM = "stream"
PARAM_N = "n"
PARAM_LOGPROBS = "logprobs"
PARAM_ECHO = "echo"
PARAM_BEST_OF = "best_of"
PARAM_LOGIT_BIAS = "logit_bias"
PARAM_USER = "user"

# ============================================================================
# API REQUIREMENT KEYS
# ============================================================================

API_REQ_USES_MODEL_ID = "uses_model_id"
API_REQ_USES_DEPLOYMENT_NAME = "uses_deployment_name"
API_REQ_REQUIRES_API_KEY = "requires_api_key"
API_REQ_REQUIRES_ENDPOINT = "requires_endpoint"
API_REQ_REQUIRES_API_VERSION = "requires_api_version"
API_REQ_REQUIRES_REGION = "requires_region"
API_REQ_SUPPORTS_STREAMING = "supports_streaming"
API_REQ_BODY_FORMAT = "body_format"

# ============================================================================
# METADATA KEYS
# ============================================================================

META_MODEL_NAME = "model_name"
META_PROVIDER = "provider"
META_MODEL_FAMILY = "model_family"
META_REQUEST_ID = "request_id"
META_TIMESTAMP = "timestamp"
META_DURATION_MS = "duration_ms"
META_INPUT_TOKENS = "input_tokens"
META_OUTPUT_TOKENS = "output_tokens"
META_TOTAL_TOKENS = "total_tokens"
META_FINISH_REASON = "finish_reason"
META_COST_USD = "cost_usd"

# Additional metadata keys
META_MODEL = "model"
META_ID = "id"
META_DEPLOYMENT = "deployment"
META_ERROR = "error"

# ============================================================================
# CONTEXT FIELD KEYS
# ============================================================================

CONTEXT_REQUEST_ID = "request_id"
CONTEXT_USER_ID = "user_id"
CONTEXT_SESSION_ID = "session_id"
CONTEXT_TENANT_ID = "tenant_id"
CONTEXT_TRACE_ID = "trace_id"
CONTEXT_LOCALE = "locale"
CONTEXT_TIMEZONE = "timezone"
CONTEXT_METADATA = "metadata"
CONTEXT_CONFIG = "config"

# Default context values
DEFAULT_LOCALE = "en-US"
DEFAULT_TIMEZONE = "UTC"

# Context prefixes
PREFIX_REQUEST = "req-"
PREFIX_TEST_USER = "test-user"
PREFIX_TEST_SESSION = "test-session"
PREFIX_TEST_TENANT = "test-tenant"

# Context test values
TEST_ENVIRONMENT_KEY = "environment"
TEST_ENVIRONMENT_VALUE = "test"

# ============================================================================
# MESSAGE FIELD KEYS
# ============================================================================

MESSAGE_FIELD_ROLE = "role"
MESSAGE_FIELD_CONTENT = "content"

# ============================================================================
# STREAM CONSTANTS
# ============================================================================

STREAM_DATA_PREFIX = "data: "
STREAM_DATA_PREFIX_LENGTH = 6
STREAM_DONE_TOKEN = "[DONE]"
STREAM_PARAM_TRUE = "stream"

# ============================================================================
# COMMON ERROR MESSAGES
# ============================================================================

ERROR_MSG_EMPTY_MESSAGES = "Messages list cannot be empty"
ERROR_MSG_MESSAGE_NOT_DICT = "Message {i} must be a dictionary"
ERROR_MSG_MISSING_ROLE = "Message {i} missing 'role' field"
ERROR_MSG_MISSING_CONTENT = "Message {i} missing 'content' field"
ERROR_MSG_REQUEST_FAILED_ALL_RETRIES = "Request failed after all retries"
ERROR_MSG_RESPONSE_MISSING_CHOICES = "Response missing choices"
ERROR_MSG_FAILED_PARSE_RESPONSE = "Failed to parse {provider} response: {error}"

# ============================================================================
# METRIC NAMES
# ============================================================================

METRIC_LLM_CALLS = "llm.calls"
METRIC_LLM_ERRORS = "llm.errors"
METRIC_LLM_LATENCY = "llm.latency"
METRIC_LLM_TOKENS_INPUT = "llm.tokens.input"
METRIC_LLM_TOKENS_OUTPUT = "llm.tokens.output"
METRIC_LLM_COST = "llm.cost"

# ============================================================================
# LIMITS & CONSTRAINTS
# ============================================================================

# Token estimation (rough heuristics)
CHARS_PER_TOKEN_ESTIMATE = 4
TOKENS_PER_MESSAGE_OVERHEAD = 4  # Approximate per-message formatting tokens

# Retry limits
MAX_RETRY_ATTEMPTS = 5
MIN_RETRY_DELAY_MS = 100
MAX_RETRY_DELAY_MS = 32000

# Rate limiting
RATE_LIMIT_WINDOW_SECONDS = 60
DEFAULT_REQUESTS_PER_MINUTE = 60

# ============================================================================
# API FIELD NAMES (Provider-specific mappings source)
# ============================================================================

# OpenAI/Azure field names
OPENAI_FIELD_MESSAGES = "messages"
OPENAI_FIELD_MODEL = "model"
OPENAI_FIELD_MAX_TOKENS = "max_tokens"
OPENAI_FIELD_TEMPERATURE = "temperature"
OPENAI_FIELD_TOP_P = "top_p"
OPENAI_FIELD_FREQUENCY_PENALTY = "frequency_penalty"
OPENAI_FIELD_PRESENCE_PENALTY = "presence_penalty"
OPENAI_FIELD_STOP = "stop"
OPENAI_FIELD_STREAM = "stream"
OPENAI_FIELD_FUNCTIONS = "functions"
OPENAI_FIELD_FUNCTION_CALL = "function_call"
OPENAI_FIELD_TOOLS = "tools"
OPENAI_FIELD_TOOL_CHOICE = "tool_choice"

# Response field names
RESPONSE_FIELD_CHOICES = "choices"
RESPONSE_FIELD_MESSAGE = "message"
RESPONSE_FIELD_CONTENT = "content"
RESPONSE_FIELD_ROLE = "role"
RESPONSE_FIELD_FINISH_REASON = "finish_reason"
RESPONSE_FIELD_USAGE = "usage"
RESPONSE_FIELD_PROMPT_TOKENS = "prompt_tokens"
RESPONSE_FIELD_COMPLETION_TOKENS = "completion_tokens"
RESPONSE_FIELD_TOTAL_TOKENS = "total_tokens"

# Stream response fields
STREAM_FIELD_DELTA = "delta"
STREAM_FIELD_CONTENT = "content"
STREAM_FIELD_ROLE = "role"

# ============================================================================
# CONTENT FILTERS & SAFETY
# ============================================================================

CONTENT_FILTER_HATE = "hate"
CONTENT_FILTER_VIOLENCE = "violence"
CONTENT_FILTER_SEXUAL = "sexual"
CONTENT_FILTER_SELF_HARM = "self_harm"

# ============================================================================
# REGISTRY KEYS
# ============================================================================

REGISTRY_KEY_MODELS = "models"
REGISTRY_KEY_PROVIDERS = "providers"
REGISTRY_KEY_FAMILIES = "families"

# ============================================================================
# ENVIRONMENT VARIABLE NAMES
# ============================================================================

ENV_OPENAI_API_KEY = "OPENAI_API_KEY"
ENV_AZURE_OPENAI_KEY = "AZURE_OPENAI_KEY"
ENV_AZURE_OPENAI_ENDPOINT = "AZURE_OPENAI_ENDPOINT"
ENV_AZURE_OPENAI_DEPLOYMENT = "AZURE_OPENAI_DEPLOYMENT"
ENV_AZURE_OPENAI_API_VERSION = "AZURE_OPENAI_API_VERSION"

# ============================================================================
# ENUM VALUES (Provider Identifiers)
# ============================================================================

PROVIDER_AZURE = "azure"
PROVIDER_OPENAI = "openai"
PROVIDER_BEDROCK = "bedrock"
PROVIDER_GEMINI = "gemini"
PROVIDER_ANTHROPIC = "anthropic"

# ============================================================================
# ENUM VALUES (Model Families)
# ============================================================================

MODEL_FAMILY_GPT_4 = "gpt-4"
MODEL_FAMILY_GPT_4_1_MINI = "gpt-4.1-mini"
MODEL_FAMILY_AZURE_GPT_4 = "azure-gpt-4"
MODEL_FAMILY_AZURE_GPT_4_1_MINI = "azure-gpt-4.1-mini"

# ============================================================================
# MODEL NAMES
# ============================================================================

# OpenAI Models
MODEL_NAME_GPT_4O = "gpt-4o"
MODEL_NAME_GPT_4_TURBO = "gpt-4-turbo"
MODEL_NAME_GPT_35_TURBO = "gpt-3.5-turbo"

# Azure Models
MODEL_NAME_AZURE_GPT_4O = "azure-gpt-4o"
MODEL_NAME_AZURE_GPT_4_TURBO = "azure-gpt-4-turbo"
MODEL_NAME_AZURE_GPT_35_TURBO = "azure-gpt-3.5-turbo"
MODEL_NAME_AZURE_GPT_41_MINI = "azure-gpt-4.1-mini"

# ============================================================================
# MODEL DISPLAY NAMES
# ============================================================================

DISPLAY_NAME_GPT_4O = "GPT-4o"
DISPLAY_NAME_GPT_4_TURBO = "GPT-4 Turbo"
DISPLAY_NAME_GPT_35_TURBO = "GPT-3.5 Turbo"
DISPLAY_NAME_AZURE_GPT_4O = "Azure GPT-4o"
DISPLAY_NAME_AZURE_GPT_4_TURBO = "Azure GPT-4 Turbo"
DISPLAY_NAME_AZURE_GPT_35_TURBO = "Azure GPT-3.5 Turbo"
DISPLAY_NAME_AZURE_GPT_41_MINI = "Azure GPT-4.1 Mini"

# ============================================================================
# ENUM VALUES (Media Types)
# ============================================================================

MEDIA_TYPE_TEXT = "text"
MEDIA_TYPE_IMAGE = "image"
MEDIA_TYPE_AUDIO = "audio"
MEDIA_TYPE_VIDEO = "video"
MEDIA_TYPE_MULTIMODAL = "multimodal"

# ============================================================================
# ENUM VALUES (Output Format Types for TEXT media)
# ============================================================================

OUTPUT_FORMAT_TEXT = "text"
OUTPUT_FORMAT_JSON = "json"
OUTPUT_FORMAT_TOON = "toon"

# ============================================================================
# ENUM VALUES (Message Roles)
# ============================================================================

ROLE_SYSTEM = "system"
ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"
ROLE_FUNCTION = "function"
ROLE_TOOL = "tool"

# Default role for responses
DEFAULT_RESPONSE_ROLE = ROLE_ASSISTANT

# ============================================================================
# ENUM VALUES (Capabilities)
# ============================================================================

CAPABILITY_STREAMING = "streaming"
CAPABILITY_FUNCTION_CALLING = "function_calling"
CAPABILITY_VISION = "vision"
CAPABILITY_JSON_MODE = "json_mode"
CAPABILITY_TOOL_USE = "tool_use"
CAPABILITY_SYSTEM_MESSAGE = "system_message"
CAPABILITY_MULTI_TURN = "multi_turn"
CAPABILITY_CONTEXT_CACHING = "context_caching"
CAPABILITY_PARALLEL_FUNCTION_CALLING = "parallel_function_calling"

# ============================================================================
# ENUM VALUES (LLM Types)
# ============================================================================

LLM_TYPE_CHAT = "chat"
LLM_TYPE_COMPLETION = "completion"
LLM_TYPE_INSTRUCTION = "instruction"
LLM_TYPE_EMBEDDING = "embedding"
LLM_TYPE_CODE = "code"

# ============================================================================
# ENUM VALUES (Stream Event Types)
# ============================================================================

STREAM_EVENT_START = "start"
STREAM_EVENT_CONTENT = "content"
STREAM_EVENT_FUNCTION_CALL = "function_call"
STREAM_EVENT_TOOL_USE = "tool_use"
STREAM_EVENT_END = "end"
STREAM_EVENT_ERROR = "error"
STREAM_EVENT_METADATA = "metadata"

# ============================================================================
# ENUM VALUES (Finish Reasons)
# ============================================================================

FINISH_REASON_STOP = "stop"
FINISH_REASON_LENGTH = "length"
FINISH_REASON_CONTENT_FILTER = "content_filter"
FINISH_REASON_FUNCTION_CALL = "function_call"
FINISH_REASON_ERROR = "error"
FINISH_REASON_TIMEOUT = "timeout"

# ============================================================================
# CONFIGURATION CATEGORIES
# ============================================================================

CONFIG_CATEGORY_PARAMETERS = "parameters"
CONFIG_CATEGORY_CONNECTOR = "connector"

# ============================================================================
# ERROR CATEGORIES
# ============================================================================

ERROR_CATEGORY_AUTHENTICATION = "authentication"
ERROR_CATEGORY_RATE_LIMIT = "rate_limit"
ERROR_CATEGORY_TIMEOUT = "timeout"
ERROR_CATEGORY_QUOTA = "quota"
ERROR_CATEGORY_SERVICE_UNAVAILABLE = "service_unavailable"
ERROR_CATEGORY_VALIDATION = "validation"
ERROR_CATEGORY_TOKEN_LIMIT = "token_limit"
ERROR_CATEGORY_CONTENT_FILTER = "content_filter"
ERROR_CATEGORY_STREAMING = "streaming"
ERROR_CATEGORY_LLM_ERROR = "llm_error"
ERROR_CATEGORY_UNKNOWN = "unknown"

# ============================================================================
# LLM Defaults
# ============================================================================

TIMEOUT = "timeout"
MAX_RETRIES = "max_retries"
RETRY_DELAY = "retry_delay"
DEFAULT_TEMPERATURE = "default_temperature"
DEFAULT_MAX_TOKENS = "default_max_tokens"
DEFAULT_TOP_P = "default_top_p"
DEFAULT_FREQUENCY_PENALTY = "default_frequency_penalty"
DEFAULT_PRESENCE_PENALTY = "default_presence_penalty"
DEFAULT_N = "default_n"
DEFAULT_API_VERSION = "default_api_version"
DEFAULT_TIMEOUT = "default_timeout"
DEFAULT_MAX_RETRIES = "default_max_retries"
DEFAULT_RETRY_DELAY = "default_retry_delay"
DEFAULT_BACKOFF_FACTOR = "default_backoff_factor"
MESSAGE_COUNT = "message_count"
ESTIMATED_TOKENS = "estimated_tokens"
PROMPT_TOKENS = "prompt_tokens"
COMPLETION_TOKENS = "completion_tokens"
TOTAL_TOKENS = "total_tokens"
PARAMETERS = "parameters"
CONNECTOR = "connector"
ROLE = "role"
CONTENT = "content"
OPENAI_DEFAULT_TEMPERATURE = "temperature"
OPENAI_DEFAULT_MAX_TOKENS = "max_tokens"
OPENAI_DEFAULT_TOP_P = "top_p"
OPENAI_DEFAULT_FREQUENCY_PENALTY = "frequency_penalty"
OPENAI_DEFAULT_PRESENCE_PENALTY = "presence_penalty"
OPENAI_DEFAULT_N = "n"
OPENAI_DEFAULT_API_VERSION = None
OPENAI_DEFAULT_TIMEOUT = "timeout"
OPENAI_DEFAULT_MAX_RETRIES = "max_retries"
OPENAI_DEFAULT_RETRY_DELAY = "retry_delay"
AZURE_DEFAULT_TEMPERATURE = "temperature"
AZURE_DEFAULT_MAX_TOKENS = "max_tokens"
AZURE_DEFAULT_TOP_P = "top_p"
AZURE_DEFAULT_FREQUENCY_PENALTY = "frequency_penalty"
AZURE_DEFAULT_PRESENCE_PENALTY = "presence_penalty"
AZURE_DEFAULT_API_VERSION = "2024-02-15-preview"
AZURE_DEFAULT_TIMEOUT = "timeout"
AZURE_DEFAULT_MAX_RETRIES = "max_retries"
AZURE_DEFAULT_RETRY_DELAY = "retry_delay"
AZURE_DEFAULT_API_VERSION_2024_02_15_PREVIEW = "2024-02-15-preview"
OPENAI_CONNECTOR_DEFAULTS = "connector"
AZURE_CONNECTOR_DEFAULTS = "connector"

# ============================================================================
# METADATA KEYS
# ============================================================================

UNIQUE_MODEL_IDENTIFIER = "unique model identifier"
PROVIDER_HOSTING_THE_MODEL = "provider hosting the model"
MODEL_FAMILY_GROUPING = "model_family_grouping"
HUMAN_READABLE_NAME = "human readable name"
TYPE_OF_LLM = "type of llm"
INPUT_MEDIA_TYPES_SUPPORTED = "input media types supported"
OUTPUT_MEDIA_TYPES_SUPPORTED = "output media types supported"
STREAMING_SUPPORT = "streaming support"
FUNCTION_CALLING_SUPPORT = "function calling support"
VISION_SUPPORT = "vision support"
JSON_MODE_SUPPORT = "JSON mode support"
PARALLEL_FUNCTION_CALLING_SUPPORT = "parallel function calling support"
MAXIMUM_CONTEXT_WINDOW_IN_TOKENS = "maximum context window in tokens"
MAXIMUM_OUTPUT_TOKENS = "maximum output tokens"
MAXIMUM_INPUT_TOKENS = "maximum input tokens"
MAPS_STANDARD_PARAMETER_NAMES_TO_PROVIDER_SPECIFIC_NAMES = "maps standard parameter names to provider specific names"
DEFAULT_PARAMETER_VALUES = "default parameter values"
VALID_PARAMETER_RANGES_FOR_THIS_MODEL = "Valid parameter ranges for this model"
SET_OF_PARAMETER_NAMES_SUPPORTED_BY_THIS_MODEL = "Set of parameter names supported by this model"
PROVIDER_SPECIFIC_API_REQUIREMENTS = "provider specific api requirements"
OPTIONAL_FUNCTION_NAME_TO_CONVERT_RESPONSES = "Optional function name to convert responses"
COST_PER_1000_INPUT_TOKENS_IN_USD = "Cost per 1000 input tokens in USD"
COST_PER_1000_OUTPUT_TOKENS_IN_USD = "Cost per 1000 output tokens in USD"
WHETHER_MODEL_IS_DEPRECATED = "Whether model is deprecated"
DEPRECATION_DATE_ISO_FORMAT = "Deprecation date (ISO format)"
RECOMMENDED_REPLACEMENT = "Recommended replacement"

ARBITRARY_TYPES_ALLOWED = "arbitrary_types_allowed"
USE_ENUM_VALUES = "use_enum_values"
JSON_SCHEMA_EXTRA = "json_schema_extra"
EXAMPLES = "examples"
MODEL_NAME = "model_name"
PROVIDER = "provider"
MODEL_FAMILY = "model_family"
DISPLAY_NAME = "display_name"
SUPPORTED_INPUT_TYPES = "supported_input_types"
SUPPORTED_OUTPUT_TYPES = "supported_output_types"
SUPPORTS_STREAMING = "supports_streaming"
SUPPORTS_FUNCTION_CALLING = "supports_function_calling"
SUPPORTS_PARALLEL_FUNCTION_CALLING = "supports_parallel_function_calling"
SUPPORTS_VISION = "supports_vision"
SUPPORTS_JSON_MODE = "supports_json_mode"


# ============================================================================
# ENUM VALUES (Model Display Names)
# ============================================================================

DISPLAY_NAME_GPT_4 = "GPT-4"
DISPLAY_NAME_GPT_4_1_MINI = "GPT-4.1 Mini"
DISPLAY_NAME_AZURE_GPT_4 = "Azure GPT-4"
DISPLAY_NAME_AZURE_GPT_4_1_MINI = "Azure GPT-4.1 Mini"

# ============================================================================
# DEFAULT CONTEXT DATA GENERATORS (similar to tools)
# ============================================================================

def DEFAULT_LLM_CONTEXT_DATA(model_name: str, provider: str) -> dict:
    """Generate default context data for LLM logging."""
    return {
        META_MODEL_NAME: model_name,
        META_PROVIDER: provider,
    }


def LLM_ERROR_MESSAGE(error_type: str, details: str) -> str:
    """Format LLM error message."""
    return f"LLM Error [{error_type}]: {details}"

