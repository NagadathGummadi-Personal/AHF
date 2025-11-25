from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from pydantic import BaseModel, Field

# Local imports
from ..defaults import (
    DEFAULT_TOOL_VERSION,
    DEFAULT_TOOL_TIMEOUT_S,
    DEFAULT_RETURN_TYPE,
    DEFAULT_RETURN_TARGET,
    HTTP_DEFAULT_METHOD,
    DB_DEFAULT_DRIVER,
)
from ..constants import RETURNS, ARBITRARY_TYPES_ALLOWED, POPULATE_BY_NAME
from ..enum import ToolType, ToolReturnType, ToolReturnTarget
from .tool_parameters import ToolParameter
from .tool_config import RetryConfig, CircuitBreakerConfig, IdempotencyConfig

if TYPE_CHECKING:
    from ..runtimes.idempotency.idempotency_key_generator import IIdempotencyKeyGenerator

class ToolSpec(BaseModel):
    """
    Base class for tool specifications with common metadata.
    
    Attributes:
        id: Unique identifier for the tool
        version: Tool version string
        tool_name: Human-readable tool name
        description: Tool description
        tool_type: Type of tool (FUNCTION, HTTP, DB)
        parameters: List of tool parameters
        return_type: Type of return value (JSON, TEXT)
        return_target: Target for return value (HUMAN, LLM, AGENT, STEP)
        required: Whether tool is required
        owner: Tool owner identifier
        permissions: List of required permissions
        timeout_s: Execution timeout in seconds
        examples: Usage examples
        retry: Retry configuration
        circuit_breaker: Circuit breaker configuration
        idempotency: Idempotency configuration
        idempotency_key_generator: Custom key generator (optional)
        metrics_tags: Static tags for metrics
    """
    id: str
    version: str = DEFAULT_TOOL_VERSION
    tool_name: str
    description: str
    tool_type: ToolType
    parameters: List[ToolParameter]
    return_type: ToolReturnType = Field(default=DEFAULT_RETURN_TYPE, alias=RETURNS)
    return_target: ToolReturnTarget = DEFAULT_RETURN_TARGET
    required: bool = False
    owner: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)
    timeout_s: int = DEFAULT_TOOL_TIMEOUT_S
    examples: List[Dict[str, Any]] = Field(default_factory=list)

    # Advanced config
    retry: RetryConfig = Field(default_factory=RetryConfig)
    circuit_breaker: CircuitBreakerConfig = Field(default_factory=CircuitBreakerConfig)
    idempotency: IdempotencyConfig = Field(default_factory=IdempotencyConfig)
    
    # Pluggable policies (optional, defaults to None)
    idempotency_key_generator: Optional[Any] = None  # IIdempotencyKeyGenerator instance
    circuit_breaker_policy: Optional[Any] = None  # ICircuitBreakerPolicy instance
    retry_policy: Optional[Any] = None  # IRetryPolicy instance
    
    metrics_tags: Dict[str, str] = Field(default_factory=dict)  # static tags for metrics
    model_config = {
        ARBITRARY_TYPES_ALLOWED: True,
        POPULATE_BY_NAME: True
    }


class FunctionToolSpec(ToolSpec):
    """Tool specification for function-based tools"""
    tool_type: ToolType = Field(default=ToolType.FUNCTION)


class HttpToolSpec(ToolSpec):
    """Tool specification for HTTP-based tools"""
    tool_type: ToolType = Field(default=ToolType.HTTP)

    # HTTP-specific fields
    url: str
    method: str = HTTP_DEFAULT_METHOD  # GET, POST, PUT, DELETE, etc.
    headers: Optional[Dict[str, str]] = None
    query_params: Optional[Dict[str, str]] = None
    body: Optional[Dict[str, Any]] = None  # Only for non-GET requests


class DbToolSpec(ToolSpec):
    """
    Base specification for database-based tools.
    
    This is the base class for all database tool specifications. Provider-specific
    fields should be defined in subclasses (DynamoDbToolSpec, PostgreSqlToolSpec, etc.)
    
    Common Attributes:
        driver: Database driver/provider type ('dynamodb', 'postgresql', etc.)
        
    Subclasses:
        DynamoDbToolSpec: AWS DynamoDB configuration
        PostgreSqlToolSpec: PostgreSQL configuration
        MySqlToolSpec: MySQL configuration
        SqliteToolSpec: SQLite configuration
    """
    tool_type: ToolType = Field(default=ToolType.DB)
    driver: str = DB_DEFAULT_DRIVER  # dynamodb, postgresql, mysql, sqlite, etc.


class DynamoDbToolSpec(DbToolSpec):
    """
    Tool specification for AWS DynamoDB operations.
    
    Provider-specific configuration for DynamoDB tools. Configuration fields
    are at the spec level (not in parameters), keeping parameters for actual
    operation arguments.
    
    Configuration Fields:
        region: AWS region (e.g., 'us-west-2', 'eu-central-1')
        table_name: Default DynamoDB table name
        endpoint_url: Optional custom endpoint (for testing with LocalStack)
        aws_access_key_id: Optional AWS access key (prefer IAM roles)
        aws_secret_access_key: Optional AWS secret key (prefer IAM roles)
    
    Example:
        spec = DynamoDbToolSpec(
            id="user-orders-v1",
            tool_name="get_user_orders",
            description="Get user orders from DynamoDB",
            region="us-west-2",
            table_name="user-orders",
            parameters=[
                StringParameter(name="user_id", required=True),
                StringParameter(name="order_status", required=False)
            ]
        )
    
    Note:
        AWS credentials should preferably be configured via IAM roles or
        environment variables rather than hardcoded in the spec.
    """
    driver: str = Field(default="dynamodb")
    region: str = "us-west-2"
    table_name: str  # Required - the DynamoDB table name
    endpoint_url: Optional[str] = None  # For LocalStack/testing
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None


class PostgreSqlToolSpec(DbToolSpec):
    """
    Tool specification for PostgreSQL operations.
    
    Provider-specific configuration for PostgreSQL tools.
    
    Configuration Fields:
        host: Database host
        port: Database port (default: 5432)
        database: Database name
        username: Database username
        password: Database password
        connection_string: Optional full connection string (overrides individual fields)
        ssl_mode: SSL connection mode
        pool_size: Connection pool size
    
    Example:
        spec = PostgreSqlToolSpec(
            id="user-query-v1",
            tool_name="query_users",
            description="Query users from PostgreSQL",
            host="localhost",
            port=5432,
            database="myapp",
            username="app_user",
            password="secret",
            parameters=[
                StringParameter(name="query", required=True),
                ArrayParameter(name="params", required=False)
            ]
        )
    """
    driver: str = Field(default="postgresql")
    host: str = "localhost"
    port: int = 5432
    database: str
    username: str
    password: str
    connection_string: Optional[str] = None  # Overrides individual fields if provided
    ssl_mode: Optional[str] = None  # 'disable', 'allow', 'prefer', 'require'
    pool_size: int = 10


class MySqlToolSpec(DbToolSpec):
    """
    Tool specification for MySQL operations.
    
    Provider-specific configuration for MySQL tools.
    
    Configuration Fields:
        host: Database host
        port: Database port (default: 3306)
        database: Database name
        username: Database username
        password: Database password
        charset: Character set (default: 'utf8mb4')
        connection_string: Optional full connection string
    
    Example:
        spec = MySqlToolSpec(
            id="products-query-v1",
            tool_name="query_products",
            description="Query products from MySQL",
            host="localhost",
            port=3306,
            database="ecommerce",
            username="app_user",
            password="secret",
            charset="utf8mb4",
            parameters=[
                StringParameter(name="category", required=False),
                IntegerParameter(name="limit", required=False)
            ]
        )
    """
    driver: str = Field(default="mysql")
    host: str = "localhost"
    port: int = 3306
    database: str
    username: str
    password: str
    connection_string: Optional[str] = None
    charset: str = "utf8mb4"


class SqliteToolSpec(DbToolSpec):
    """
    Tool specification for SQLite operations.
    
    Provider-specific configuration for SQLite tools.
    
    Configuration Fields:
        database_path: Path to SQLite database file (or ':memory:' for in-memory)
        timeout: Connection timeout in seconds
        check_same_thread: Whether to check thread (default: False for async)
    
    Example:
        spec = SqliteToolSpec(
            id="local-cache-v1",
            tool_name="cache_query",
            description="Query local SQLite cache",
            database_path="/path/to/cache.db",
            parameters=[
                StringParameter(name="key", required=True)
            ]
        )
    """
    driver: str = Field(default="sqlite")
    database_path: str = ":memory:"  # Default to in-memory database
    timeout: float = 5.0
    check_same_thread: bool = False  # False for async usage