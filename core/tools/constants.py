"""
Central constants for literals, error codes, event names, and logging formats.
"""

ERROR_TIMEOUT = "TIMEOUT"
ERROR_UNAVAILABLE = "UNAVAILABLE"
ERROR_TOOL = "TOOL_ERROR"
ERROR_MATH = "MATH_ERROR"
ERROR_UNAUTHORIZED = "UNAUTHORIZED"
ERROR_INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"
ERROR_UNAUTHORIZED_ROLE = "UNAUTHORIZED_ROLE"
ERROR_VALIDATION = "VALIDATION_ERROR"
ERROR_TOOL_NOT_FOUND = "TOOL_NOT_FOUND"
ERROR_INVALID_OPERATION = "INVALID_OPERATION"

# IDEMPOTENCY constants
IDEMPOTENCY_CACHE_PREFIX = "result"
SEPARATOR = "|"
COMMA = ","
SPACE = " "
SHA256_HASH_ALGORITHM = "sha256"
DEFAULT_IDEMPOTENCY_KEY_GENERATOR = "default"
FIELD_BASED_IDEMPOTENCY_KEY_GENERATOR = "field_based"
HASH_BASED_IDEMPOTENCY_KEY_GENERATOR = "hash_based"
CUSTOM_IDEMPOTENCY_KEY_GENERATOR = "custom"
KEY_FUNCTION_NOT_CALLABLE = "key_function must be callable"

UNKNOWN_IDEMPOTENCY_KEY_GENERATOR = "Unknown idempotency key generator: {GENERATOR_NAME}. Available: {AVAILABLE_GENERATORS}"

# Event/Metric Names
METRIC_TOOL_EXECUTION_STARTED = "tool.execution.started"
METRIC_TOOL_EXECUTION_SUCCESS = "tool.execution.success"
METRIC_TOOL_EXECUTION_FAILED = "tool.execution.failed"
METRIC_TOOL_EXECUTION_TIME = "tool.execution_time"
METRIC_ADDITION_SUCCESS = "addition.success"
METRIC_ADDITION_DURATION = "addition.duration"
METRIC_ADDITION_ERROR = "addition.error"

# Logging Messages (format strings)
LOG_STARTING_EXECUTION = "Starting tool execution"
LOG_PARAMETERS = "Tool parameters"
LOG_VALIDATING = "Validating parameters"
LOG_VALIDATION_PASSED = "Parameter validation passed"
LOG_VALIDATION_SKIPPED = "No validator available - skipping parameter validation"
LOG_AUTH_CHECK = "Checking authorization"
LOG_AUTH_PASSED = "Authorization passed"
LOG_AUTH_SKIPPED = "No security component available - skipping authorization"
LOG_EGRESS_CHECK = "Checking egress permissions"
LOG_EGRESS_PASSED = "Egress check passed"
LOG_EGRESS_SKIPPED = "No security component available - skipping egress check"
LOG_IDEMPOTENCY_CACHE_HIT = "Using cached result for idempotency"
LOG_EXECUTION_COMPLETED = "Tool execution completed"
LOG_EXECUTION_FAILED = "Tool execution failed"
LOG_HTTP_STARTING = "Starting HTTP tool execution"
LOG_HTTP_COMPLETED = "HTTP tool execution completed"
LOG_HTTP_FAILED = "HTTP tool execution failed"
LOG_DB_STARTING = "Starting database tool execution"
LOG_DB_COMPLETED = "Database tool execution completed"
LOG_DB_FAILED = "Database tool execution failed"

# Demo/Example event names
EVENT_EXECUTION_STARTED = "EXECUTION_STARTED"
EVENT_PARAMETER_EXTRACTION = "PARAMETER_EXTRACTION"
EVENT_TYPE_COERCION = "TYPE_COERCION"
EVENT_TYPE_COERCION_FAILED = "TYPE_COERCION_FAILED"
EVENT_SIMULATED_ERROR = "SIMULATED_ERROR"
EVENT_CALCULATION_STARTED = "CALCULATION_STARTED"
EVENT_CALCULATION_COMPLETED = "CALCULATION_COMPLETED"
EVENT_METRICS_RECORDED = "METRICS_RECORDED"
EVENT_TRACING_SPAN_CREATED = "TRACING_SPAN_CREATED"
EVENT_CACHE_OPERATION = "CACHE_OPERATION"
EVENT_EXECUTION_COMPLETED = "EXECUTION_COMPLETED"
EVENT_EXECUTION_ERROR = "EXECUTION_ERROR"

# Other constants
PARAMETER_TYPE_STRING = "string"
PARAMETER_TYPE_NUMBER = "number"
PARAMETER_TYPE_INTEGER = "integer"
PARAMETER_TYPE_BOOLEAN = "boolean"
PARAMETER_TYPE_BOOLEAN_TRUE = "true"
PARAMETER_TYPE_BOOLEAN_YES = "yes"
PARAMETER_TYPE_BOOLEAN_ON = "on"
PARAMETER_TYPE_BOOLEAN_1 = "1"
PARAMETER_TYPE_BOOLEAN_FALSE = "false"
PARAMETER_TYPE_BOOLEAN_NO = "no"
PARAMETER_TYPE_BOOLEAN_OFF = "off"
PARAMETER_TYPE_BOOLEAN_0 = "0"
PARAMETER_TYPE_ARRAY = "array"
PARAMETER_TYPE_OBJECT = "object"


# Derived collections
BOOLEAN_TRUE_STRINGS = (
    PARAMETER_TYPE_BOOLEAN_TRUE,
    PARAMETER_TYPE_BOOLEAN_1,
    PARAMETER_TYPE_BOOLEAN_YES,
    PARAMETER_TYPE_BOOLEAN_ON,
)
BOOLEAN_FALSE_STRINGS = (
    PARAMETER_TYPE_BOOLEAN_FALSE,
    PARAMETER_TYPE_BOOLEAN_0,
    PARAMETER_TYPE_BOOLEAN_NO,
    PARAMETER_TYPE_BOOLEAN_OFF,
)

# Python type mapping for parameter types
PARAMETER_PY_TYPES = {
    PARAMETER_TYPE_STRING: str,
    PARAMETER_TYPE_NUMBER: (int, float),
    PARAMETER_TYPE_INTEGER: int,
    PARAMETER_TYPE_BOOLEAN: bool,
    PARAMETER_TYPE_ARRAY: (list, tuple),
    PARAMETER_TYPE_OBJECT: dict,
}

# Error message format strings
MSG_UNKNOWN_PARAMETERS = "Unknown parameter(s): {params}"
MSG_MISSING_REQUIRED_PARAMETER = "Missing required parameter: {name}"
MSG_PARAMETER_FAILED_VALIDATION = "Parameter '{name}' failed validation"
MSG_UNAUTHORIZED_USER = "User {user_id} is not authorized to execute tool {tool_name}"
MSG_MISSING_REQUIRED_PERMISSIONS = "User {user_id} missing required permissions: {missing_perms}"
MSG_UNAUTHORIZED_ROLE = "User role {user_role} is not authorized to execute tool {tool_name}"
MSG_DIVISION_BY_ZERO = "Division by zero"
MSG_UNKNOWN_OPERATION = "Unknown operation: {operation}"

# Generic exception messages
EXC_HTTP_EXECUTION_NOT_IMPLEMENTED = "HTTP execution not implemented"
EXC_DB_EXECUTION_NOT_IMPLEMENTED = "DB execution not implemented"
EXC_CALCULATION_NOT_IMPLEMENTED = "Calculation for {name} not implemented"

# Encoding constants
UTF_8 = "utf-8"

# HTTP/DB/Tool execution status format strings
HTTP_EXECUTION_STATUS_COMPLETED = "HTTP tool {tool_name} execution completed: {method} to {url}"
HTTP_EXECUTION_STATUS_FAILED = "HTTP tool {tool_name} execution failed: {method} to {url}: {error}"
DB_EXECUTION_STATUS_COMPLETED = "Database tool {tool_name} execution completed: {rows_affected} rows"
DB_EXECUTION_STATUS_FAILED = "Database tool {tool_name} execution failed: {error}"
TOOL_EXECUTION_STATUS_COMPLETED = "Tool {tool_name} execution completed"
TOOL_EXECUTION_STATUS_FAILED = "Tool {tool_name} execution failed: {error}"

#Other
ENVIRONMENT = "ENVIRONMENT"
DEFAULT_ENVIRONMENT_STRING = "dev"
DEFAULT_VERSION_STRING = "1.0.0"
DB_DEFAULT_QUERY_STRING = "SELECT 1"
USER_ID = "user_id"
SESSION_ID = "session_id"
TOOL_NAME = "tool_name"
TRACE_ID = "trace_id"
HTTP_METHOD = "http_method"
HTTP_URL = "http_url"
DB_HOST = "db_host"
DB_PORT = "db_port"
DB_DATABASE = "db_database"
STATUS_CODE = "status_code"
RESPONSE = "response"
ARGS = "args"
METHOD = "method"
URL = "url"
ROWS_AFFECTED = "rows_affected"
QUERY = "query"
CONNECTION = "connection"
HOST = "host"
PORT = "port"
DATABASE = "database"
TOKENS_IN = "tokens_in"
TOKENS_OUT = "tokens_out"
COST_USD = "cost_usd"
ATTEMPTS = "attempts"
RETRIES = "retries"
CACHED_HIT = "cached_hit"
IDEMPOTENCY_REUSED = "idempotency_reused"
CIRCUIT_OPENED = "circuit_opened"
TIMEOUT = "timeout"
UNAVAILABLE = "unavailable"
TOOL_ERROR = "tool_error"
POST = "post"
DYNAMODB = "dynamodb"
TOOL_EXECUTION_TIME = "tool.execution_time"
TOOL_EXECUTIONS = "tool.executions"
STATUS = 'status'
SUCCESS = 'success'
TOOL = 'tool'
ERROR = 'error'
EXECUTION_FAILED = 'execution_failed'
HTTP = 'http'
DB = 'db'
ARBITRARY_TYPES_ALLOWED ='arbitrary_types_allowed'
RETURNS = 'returns'
POPULATE_BY_NAME = 'populate_by_name'
EMPTY_STRING = ''

#Enum constants
JSON = 'json'
TOON = 'toon'
TEXT = 'text'
HUMAN = 'human'
LLM = 'llm'
AGENT = 'agent'
STEP = 'step'
FUNCTION = 'function'
HTTP = 'http'
DB = 'db'
STRING = 'string'
NUMBER = 'number'
INTEGER = 'integer'
BOOLEAN = 'boolean'
ARRAY = 'array'
OBJECT = 'object'

#Policy constants
TIMEOUT = "timeout"
UNAVAILABLE = "unavailable"
NETWORK = "network"
RATE_LIMIT = "rate_limit"
TRANSIENT = "transient"

#Retry Policy constants
NONE = "none"
FIXED = "fixed"
EXPONENTIAL = "exponential"
UNKNOWN_RETRY_POLICY_ERROR = "Unknown retry policy: {POLICY_NAME}. Available: {AVAILABLE_POLICIES}"
RETRY_FUNC_NOT_CALLABLE_ERROR = "retry_func must be callable"

#Circuit Breaker Policy constants
STANDARD = "standard"
ADAPTIVE = "adaptive"
NOOP = "noop"
CIRCUIT_BREAKER_STATE_CLOSED = "closed"
CIRCUIT_BREAKER_STATE_OPEN = "open"
CIRCUIT_BREAKER_STATE_HALF_OPEN = "half_open"
UNKNOWN_CIRCUIT_BREAKER_POLICY_ERROR = "Unknown circuit breaker policy: {POLICY_NAME}. Available: {AVAILABLE_POLICIES}"
CIRCUIT_BREAKER_OPEN_ERROR = "Circuit breaker is open for {TOOL_NAME}"
UNKNOWN_DB_EXECUTOR_ERROR = "Unsupported database driver: {DRIVER}. Available drivers: {AVAILABLE_DRIVERS}"
FAILURES = 'failures'
SUCCESSES = 'successes'
RECENT_RESULTS = 'recent_results'
IS_OPEN = 'is_open'
OPENED_AT = 'opened_at'
CURRENT_THRESHOLD = 'current_threshold'

#Validator constants
BASIC = "basic"
UNKNOWN_VALIDATOR_ERROR = "Unknown validator: {VALIDATOR_NAME}. Available: {AVAILABLE_VALIDATORS}"

#Memory constants
UNKNOWN_MEMORY_ERROR = "Unknown memory implementation: {MEMORY_NAME}. Available: {AVAILABLE_MEMORIES}"

#Metrics constants
UNKNOWN_METRICS_ERROR = "Unknown metrics implementation: {METRICS_NAME}. Available: {AVAILABLE_METRICS}"

#Tracer constants
UNKNOWN_TRACER_ERROR = "Unknown tracer implementation: {TRACER_NAME}. Available: {AVAILABLE_TRACERS}"

#Limiter constants
UNKNOWN_LIMITER_ERROR = "Unknown limiter implementation: {LIMITER_NAME}. Available: {AVAILABLE_LIMITERS}"

#Emitter constants
UNKNOWN_EMITTER_ERROR = "Unknown emitter implementation: {EMITTER_NAME}. Available: {AVAILABLE_EMITTERS}"

#Security constants
UNKNOWN_SECURITY_ERROR = "Unknown security implementation: {SECURITY_NAME}. Available: {AVAILABLE_SECURITIES}"

#Policy constants
UNKNOWN_POLICY_ERROR = "Unknown policy implementation: {POLICY_NAME}. Available: {AVAILABLE_POLICIES}"

#Base DB Executor constants
TABLE_NAME = 'table_name'
DATABASE = 'database'
DRIVER = 'driver'
DB_NAME = 'db_name'
DB_OPERATION = 'db_operation'
DB_OPERATION_COMPLETED = 'db_operation_completed'
DB_OPERATION_FAILED = 'db_operation_failed'
DB_OPERATION_STARTED = 'db_operation_started'
DB_OPERATION_COMPLETED = 'db_operation_completed'
DB_OPERATION_FAILED = 'db_operation_failed'
DB_OPERATION_STARTED = 'db_operation_started'
DB_OPERATION_COMPLETED = 'db_operation_completed'
DB_OPERATION_FAILED = 'db_operation_failed'
DB_OPERATION_STARTED = 'db_operation_started'
DB='db'
IDEMPOTENCY_KEY='idempotency_key'
ROW_COUNT='row_count'
DEFAULT_REGION='us-west-2'
ENDPOINT_URL='endpoint_url'
REGION='region'