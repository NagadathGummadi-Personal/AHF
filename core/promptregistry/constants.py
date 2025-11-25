"""
Constants for Prompt Registry Subsystem.
"""

# ============================================================================
# STORAGE
# ============================================================================

DEFAULT_STORAGE_PATH = ".prompts"
STORAGE_FORMAT_JSON = "json"
STORAGE_FORMAT_YAML = "yaml"
DEFAULT_STORAGE_FORMAT = STORAGE_FORMAT_JSON

# File extensions
JSON_EXTENSION = ".json"
YAML_EXTENSION = ".yaml"
YML_EXTENSION = ".yml"

# ============================================================================
# VERSIONING
# ============================================================================

DEFAULT_VERSION = "1.0.0"
LATEST_VERSION = "latest"
VERSION_SEPARATOR = "."

# ============================================================================
# PROMPT STRUCTURE
# ============================================================================

FIELD_LABEL = "label"
FIELD_CONTENT = "content"
FIELD_VERSION = "version"
FIELD_MODEL = "model"
FIELD_MODEL_TARGET = "model_target"
FIELD_TAGS = "tags"
FIELD_METRICS = "metrics"
FIELD_METADATA = "metadata"
FIELD_VERSIONS = "versions"
FIELD_CREATED_AT = "created_at"
FIELD_UPDATED_AT = "updated_at"
FIELD_STATUS = "status"
FIELD_CATEGORY = "category"

# Default model target
DEFAULT_MODEL = "default"

# ============================================================================
# METRIC NAMES
# ============================================================================

METRIC_ACCURACY = "accuracy"
METRIC_RELEVANCE = "relevance"
METRIC_FLUENCY = "fluency"
METRIC_CONSISTENCY = "consistency"
METRIC_LATENCY_MS = "latency_ms"
METRIC_TOKEN_COUNT = "token_count"
METRIC_USAGE_COUNT = "usage_count"
METRIC_SUCCESS_RATE = "success_rate"

# ============================================================================
# STATUS VALUES
# ============================================================================

STATUS_DRAFT = "draft"
STATUS_ACTIVE = "active"
STATUS_DEPRECATED = "deprecated"
STATUS_ARCHIVED = "archived"

# ============================================================================
# CATEGORY VALUES
# ============================================================================

CATEGORY_SYSTEM = "system"
CATEGORY_USER = "user"
CATEGORY_ASSISTANT = "assistant"
CATEGORY_FUNCTION = "function"
CATEGORY_TOOL = "tool"
CATEGORY_TEMPLATE = "template"
CATEGORY_EXAMPLE = "example"

# ============================================================================
# ERROR MESSAGES
# ============================================================================

ERROR_PROMPT_NOT_FOUND = "Prompt not found: {label}"
ERROR_VERSION_NOT_FOUND = "Version not found: {label}@{version}"
ERROR_INVALID_LABEL = "Invalid prompt label: {label}"
ERROR_INVALID_VERSION = "Invalid version format: {version}"
ERROR_STORAGE_ERROR = "Storage error: {error}"
ERROR_DUPLICATE_PROMPT = "Prompt already exists: {label}"

# ============================================================================
# LOG MESSAGES
# ============================================================================

LOG_PROMPT_SAVED = "Prompt saved: {label}@{version}"
LOG_PROMPT_LOADED = "Prompt loaded: {label}@{version}"
LOG_PROMPT_DELETED = "Prompt deleted: {label}"
LOG_METRICS_UPDATED = "Metrics updated: {prompt_id}"
LOG_VERSION_CREATED = "New version created: {label}@{version}"

# ============================================================================
# ENCODING
# ============================================================================

UTF_8 = "utf-8"

