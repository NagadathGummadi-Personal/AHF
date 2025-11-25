"""
Centralized default values for the tools package.

These constants are used across spec models and implementations to
avoid scattering literal defaults and to make production tuning easier.
"""

from .enum import ToolReturnTarget, ToolReturnType
from .constants import (
    HTTP_EXECUTION_STATUS_COMPLETED,
    HTTP_EXECUTION_STATUS_FAILED,
    DB_EXECUTION_STATUS_FAILED,
    DEFAULT_VERSION_STRING,
    DEFAULT_ENVIRONMENT_STRING,
    DB_DEFAULT_QUERY_STRING,
    USER_ID,
    SESSION_ID,
    TOOL_NAME,
    TRACE_ID,
    HTTP_METHOD,
    HTTP_URL,
    DB_HOST,
    DB_PORT,
    DB_DATABASE,
    STATUS_CODE,
    RESPONSE,
    ARGS,
    METHOD,
    URL,
    ROWS_AFFECTED,
    QUERY,
    CONNECTION,
    HOST,
    PORT,
    DATABASE,
    TIMEOUT,
    UNAVAILABLE,
    TOOL_ERROR,
    POST,
    DYNAMODB,
)
# Re-export env-aware usage calculators


# ToolSpec defaults
DEFAULT_TOOL_VERSION = DEFAULT_VERSION_STRING
DEFAULT_TOOL_TIMEOUT_S = 30
DEFAULT_RETURN_TYPE = ToolReturnType.JSON
DEFAULT_RETURN_TARGET = ToolReturnTarget.STEP

# Environment defaults
DEFAULT_ENVIRONMENT = DEFAULT_ENVIRONMENT_STRING

# Dev-only mock response defaults
HTTP_DEFAULT_STATUS_CODE = 200
DB_DEFAULT_ROWS_AFFECTED = 1
DB_DEFAULT_QUERY = DB_DEFAULT_QUERY_STRING


# -------- Context data builders --------
def DEFAULT_TOOL_CONTEXT_DATA(spec, ctx):
    """Standard context dict for tool executions.
    
    Checks if fields are defined at spec level first, then falls back to ctx.
    """
    return {
        USER_ID: getattr(spec, 'user_id', None) or ctx.user_id,
        SESSION_ID: getattr(spec, 'session_id', None) or ctx.session_id,
        TOOL_NAME: spec.tool_name,
        TRACE_ID: getattr(spec, 'trace_id', None) or ctx.trace_id,
    }


def DEFAULT_HTTP_CONTEXT_DATA(spec, ctx):
    data = DEFAULT_TOOL_CONTEXT_DATA(spec, ctx)
    data.update({
        HTTP_METHOD: getattr(spec, METHOD, None),
        HTTP_URL: getattr(spec, URL, None),
    })
    return data


def DEFAULT_DB_CONTEXT_DATA(spec, ctx):
    data = DEFAULT_TOOL_CONTEXT_DATA(spec, ctx)
    # Handle both table_name (DynamoDB) and database (PostgreSQL, MySQL, etc.)
    db_name = getattr(spec, 'table_name', None) or getattr(spec, 'database', None)
    data.update({
        DB_HOST: getattr(spec, 'host', None),
        DB_PORT: getattr(spec, 'port', None),
        DB_DATABASE: db_name,
    })
    return data


# -------- Dev-only mock result builders --------
def HTTP_DEFAULT_SUCCESS_STATUS_RESPONSE(spec, args):
    return {
        STATUS_CODE: HTTP_DEFAULT_STATUS_CODE,
        RESPONSE: HTTP_EXECUTION_STATUS_COMPLETED.format(
            tool_name=spec.tool_name, method=spec.method, url=spec.url
        ),
        ARGS: args,
    }


def HTTP_DEFAULT_ERROR_STATUS_WARNING(spec, error: str) -> str:
    return HTTP_EXECUTION_STATUS_FAILED.format(
        tool_name=spec.tool_name, method=spec.method, url=spec.url, error=error
    )


def DB_DEFAULT_SUCCESS_RESULT_CONTENT(spec, args):
    # Handle both table_name (DynamoDB) and database (PostgreSQL, MySQL, etc.)
    db_name = getattr(spec, 'table_name', None) or getattr(spec, 'database', None)
    
    return {
        ROWS_AFFECTED: DB_DEFAULT_ROWS_AFFECTED,
        QUERY: args.get(QUERY, DB_DEFAULT_QUERY),
        CONNECTION: {
            HOST : getattr(spec, 'host', None),
            PORT: getattr(spec, 'port', None),
            DATABASE: db_name,
        },
    }


def DB_DEFAULT_ERROR_STATUS_WARNING(spec, error: str) -> str:
    return DB_EXECUTION_STATUS_FAILED.format(tool_name=spec.tool_name, error=error)


"""Re-export env-aware calculator functions from executors.usage_calculators."""

# Retry defaults
RETRY_DEFAULT_MAX_ATTEMPTS = 3
RETRY_DEFAULT_BASE_DELAY_S = 0.2
RETRY_DEFAULT_MAX_DELAY_S = 2.0
RETRY_DEFAULT_JITTER_S = 0.1

# Circuit breaker defaults
CB_DEFAULT_ENABLED = True
CB_DEFAULT_FAILURE_THRESHOLD = 5
CB_DEFAULT_RECOVERY_TIMEOUT_S = 30
CB_DEFAULT_HALF_OPEN_MAX_CALLS = 1
CB_DEFAULT_ERROR_CODES_TO_TRIP = [TIMEOUT, UNAVAILABLE, TOOL_ERROR]

# Idempotency defaults
IDEMPOTENCY_DEFAULT_ENABLED = True
IDEMPOTENCY_DEFAULT_TTL_S = 3600
IDEMPOTENCY_DEFAULT_PERSIST_RESULT = True
IDEMPOTENCY_DEFAULT_BYPASS_ON_MISSING_KEY = False

# HTTP/DB defaults
HTTP_DEFAULT_METHOD = POST
DB_DEFAULT_DRIVER = DYNAMODB


