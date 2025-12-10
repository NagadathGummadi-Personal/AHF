"""
Tool Specification Models with UI Metadata.

This module defines the main tool specification models including
base ToolSpec and type-specific variants (Function, HTTP, DB).

Each field includes UI metadata for automatic Flutter form generation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

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
from .tool_config import (
    RetryConfig,
    CircuitBreakerConfig,
    IdempotencyConfig,
    InterruptionConfig,
    PreToolSpeechConfig,
    ExecutionConfig,
    DynamicVariableConfig,
)
from .ui_metadata import UIPresets, WidgetType, ui


class ToolSpec(BaseModel):
    """
    Base class for tool specifications with common metadata.
    
    This is the main model representing a tool definition. Type-specific
    fields are in FunctionToolSpec, HttpToolSpec, and DbToolSpec.
    """
    # Identity (Basic Info - Step 1)
    id: str = Field(
        json_schema_extra={"ui": UIPresets.text_input(
            display_name="Tool ID",
            placeholder="my-tool-v1",
            help_text="Unique identifier for the tool (auto-generated from name)",
            group="identity",
            order=0,
        )}
    )
    version: str = Field(
        default=DEFAULT_TOOL_VERSION,
        json_schema_extra={"ui": UIPresets.text_input(
            display_name="Version",
            placeholder="1.0.0",
            help_text="Tool version string (semver recommended)",
            group="identity",
            order=1,
        )}
    )
    tool_name: str = Field(
        json_schema_extra={"ui": UIPresets.text_input(
            display_name="Display Name",
            placeholder="My Tool",
            help_text="Human-readable tool name",
            group="identity",
            order=2,
        )}
    )
    description: str = Field(
        json_schema_extra={"ui": UIPresets.multiline_text(
            display_name="Description",
            placeholder="Describe what this tool does and when to use it...",
            help_text="Tool description (helps LLM understand when to use it)",
            group="identity",
            order=3,
        )}
    )
    tool_type: ToolType = Field(
        json_schema_extra={"ui": UIPresets.enum_dropdown(
            display_name="Tool Type",
            options=[
                {"value": "function", "label": "Function (Python)"},
                {"value": "http", "label": "HTTP (REST API)"},
                {"value": "db", "label": "Database (SQL/NoSQL)"},
            ],
            help_text="Type of tool implementation",
            group="identity",
            order=4,
        )}
    )
    
    # Parameters (Step 2)
    parameters: List[ToolParameter] = Field(
        default_factory=list,
        json_schema_extra={"ui": ui(
            display_name="Parameters",
            widget_type=WidgetType.ARRAY_EDITOR,
            item_label="Parameter {index}",
            help_text="Input parameters for this tool",
            group="parameters",
            order=0,
        )}
    )
    
    # Return Configuration
    return_type: ToolReturnType = Field(
        default=DEFAULT_RETURN_TYPE,
        alias=RETURNS,
        json_schema_extra={"ui": UIPresets.enum_dropdown(
            display_name="Return Type",
            options=[
                {"value": "json", "label": "JSON"},
                {"value": "text", "label": "Text"},
                {"value": "toon", "label": "TOON"},
            ],
            help_text="Format of tool output",
            group="return",
            order=0,
        )}
    )
    return_target: ToolReturnTarget = Field(
        default=DEFAULT_RETURN_TARGET,
        json_schema_extra={"ui": UIPresets.enum_dropdown(
            display_name="Return Target",
            options=[
                {"value": "llm", "label": "LLM (continue conversation)"},
                {"value": "human", "label": "Human (direct to user)"},
                {"value": "agent", "label": "Agent (for agent processing)"},
                {"value": "step", "label": "Step (workflow step output)"},
            ],
            help_text="Where to route tool output",
            group="return",
            order=1,
        )}
    )
    
    # Ownership and Permissions
    required: bool = Field(
        default=False,
        json_schema_extra={"ui": ui(
            display_name="Required Tool",
            widget_type=WidgetType.SWITCH,
            help_text="Whether this tool must be available for the agent",
            group="ownership",
            order=0,
        )}
    )
    owner: Optional[str] = Field(
        default=None,
        json_schema_extra={"ui": UIPresets.text_input(
            display_name="Owner",
            placeholder="team-name",
            help_text="Tool owner identifier",
            group="ownership",
            order=1,
        )}
    )
    permissions: List[str] = Field(
        default_factory=list,
        json_schema_extra={"ui": UIPresets.string_list(
            display_name="Required Permissions",
            item_label="Permission {index}",
            help_text="Permissions required to use this tool",
            group="ownership",
            order=2,
        )}
    )
    
    # Execution Settings
    timeout_s: int = Field(
        default=DEFAULT_TOOL_TIMEOUT_S,
        ge=1,
        le=300,
        json_schema_extra={"ui": UIPresets.count_slider(
            display_name="Timeout (seconds)",
            min_value=1,
            max_value=300,
            help_text="Maximum execution time before timeout",
            group="execution",
            order=0,
        )}
    )
    
    # Examples
    examples: List[Dict[str, Any]] = Field(
        default_factory=list,
        json_schema_extra={"ui": ui(
            display_name="Usage Examples",
            widget_type=WidgetType.ARRAY_EDITOR,
            item_label="Example {index}",
            help_text="Example inputs/outputs for documentation",
            group="examples",
            order=0,
        )}
    )

    # Advanced Configurations (collapsed sections)
    retry: RetryConfig = Field(
        default_factory=RetryConfig,
        json_schema_extra={"ui": ui(
            display_name="Retry Configuration",
            widget_type=WidgetType.OBJECT_EDITOR,
            help_text="Configure automatic retry behavior",
            group="advanced_retry",
            order=0,
        )}
    )
    circuit_breaker: CircuitBreakerConfig = Field(
        default_factory=CircuitBreakerConfig,
        json_schema_extra={"ui": ui(
            display_name="Circuit Breaker",
            widget_type=WidgetType.OBJECT_EDITOR,
            help_text="Configure circuit breaker pattern",
            group="advanced_circuit_breaker",
            order=1,
        )}
    )
    idempotency: IdempotencyConfig = Field(
        default_factory=IdempotencyConfig,
        json_schema_extra={"ui": ui(
            display_name="Idempotency",
            widget_type=WidgetType.OBJECT_EDITOR,
            help_text="Configure idempotency behavior",
            group="advanced_idempotency",
            order=2,
        )}
    )
    
    # Pluggable policies (not shown in UI - set programmatically)
    idempotency_key_generator: Optional[Any] = Field(
        default=None,
        json_schema_extra={"ui": ui(widget_type=WidgetType.HIDDEN)}
    )
    circuit_breaker_policy: Optional[Any] = Field(
        default=None,
        json_schema_extra={"ui": ui(widget_type=WidgetType.HIDDEN)}
    )
    retry_policy: Optional[Any] = Field(
        default=None,
        json_schema_extra={"ui": ui(widget_type=WidgetType.HIDDEN)}
    )
    
    # Metrics tags
    metrics_tags: Dict[str, str] = Field(
        default_factory=dict,
        json_schema_extra={"ui": UIPresets.key_value_pairs(
            display_name="Metrics Tags",
            help_text="Static tags for metrics/observability",
            group="advanced_metrics",
            order=0,
        )}
    )
    
    # Interruption control
    interruption: InterruptionConfig = Field(
        default_factory=InterruptionConfig,
        json_schema_extra={"ui": ui(
            display_name="Interruption Control",
            widget_type=WidgetType.OBJECT_EDITOR,
            help_text="Controls whether user input can interrupt tool execution",
            group="advanced_interruption",
            order=0,
        )}
    )
    
    # Pre-tool speech configuration
    pre_tool_speech: PreToolSpeechConfig = Field(
        default_factory=PreToolSpeechConfig,
        json_schema_extra={"ui": ui(
            display_name="Pre-Tool Speech",
            widget_type=WidgetType.OBJECT_EDITOR,
            help_text="Configuration for what agent says before executing tool",
            group="advanced_speech",
            order=0,
        )}
    )
    
    # Execution mode configuration
    execution: ExecutionConfig = Field(
        default_factory=ExecutionConfig,
        json_schema_extra={"ui": ui(
            display_name="Execution Mode",
            widget_type=WidgetType.OBJECT_EDITOR,
            help_text="Controls speech/execution timing",
            group="advanced_execution",
            order=0,
        )}
    )
    
    # Dynamic variable assignments from tool results
    dynamic_variables: DynamicVariableConfig = Field(
        default_factory=DynamicVariableConfig,
        json_schema_extra={"ui": ui(
            display_name="Dynamic Variables",
            widget_type=WidgetType.OBJECT_EDITOR,
            help_text="Configuration for updating variables based on tool results",
            group="advanced_dynamic_vars",
            order=0,
        )}
    )
    
    model_config = {
        ARBITRARY_TYPES_ALLOWED: True,
        POPULATE_BY_NAME: True
    }


class FunctionToolSpec(ToolSpec):
    """
    Tool specification for function-based tools.
    
    Includes Python code editor for the function implementation.
    """
    tool_type: ToolType = Field(
        default=ToolType.FUNCTION,
        json_schema_extra={"ui": ui(widget_type=WidgetType.HIDDEN)}
    )
    
    # Function-specific fields
    function_code: Optional[str] = Field(
        default=None,
        json_schema_extra={"ui": UIPresets.code_editor(
            display_name="Function Code",
            language="python",
            help_text="Python async function implementation",
            group="function",
            order=0,
        )}
    )


class HttpToolSpec(ToolSpec):
    """
    Tool specification for HTTP-based tools.
    
    Includes URL, method, headers, and body configuration.
    """
    tool_type: ToolType = Field(
        default=ToolType.HTTP,
        json_schema_extra={"ui": ui(widget_type=WidgetType.HIDDEN)}
    )

    # HTTP-specific fields
    url: str = Field(
        json_schema_extra={"ui": UIPresets.text_input(
            display_name="URL",
            placeholder="https://api.example.com/endpoint",
            help_text="API endpoint URL (supports {variable} substitution)",
            group="http",
            order=0,
        )}
    )
    method: str = Field(
        default=HTTP_DEFAULT_METHOD,
        json_schema_extra={"ui": UIPresets.enum_dropdown(
            display_name="HTTP Method",
            options=[
                {"value": "GET", "label": "GET"},
                {"value": "POST", "label": "POST"},
                {"value": "PUT", "label": "PUT"},
                {"value": "PATCH", "label": "PATCH"},
                {"value": "DELETE", "label": "DELETE"},
            ],
            help_text="HTTP request method",
            group="http",
            order=1,
        )}
    )
    headers: Optional[Dict[str, str]] = Field(
        default=None,
        json_schema_extra={"ui": UIPresets.key_value_pairs(
            display_name="Headers",
            help_text="HTTP headers (use ${VAR} for variable substitution)",
            group="http",
            order=2,
        )}
    )
    query_params: Optional[Dict[str, str]] = Field(
        default=None,
        json_schema_extra={"ui": UIPresets.key_value_pairs(
            display_name="Query Parameters",
            help_text="URL query parameters",
            group="http",
            order=3,
        )}
    )
    body: Optional[Dict[str, Any]] = Field(
        default=None,
        json_schema_extra={"ui": ui(
            display_name="Request Body",
            widget_type=WidgetType.CODE_EDITOR,
            language="json",
            visible_when="method != 'GET'",
            help_text="JSON request body template",
            group="http",
            order=4,
        )}
    )


class DbToolSpec(ToolSpec):
    """
    Base specification for database-based tools.
    
    Provider-specific fields are defined in subclasses.
    """
    tool_type: ToolType = Field(
        default=ToolType.DB,
        json_schema_extra={"ui": ui(widget_type=WidgetType.HIDDEN)}
    )
    driver: str = Field(
        default=DB_DEFAULT_DRIVER,
        json_schema_extra={"ui": UIPresets.enum_dropdown(
            display_name="Database Driver",
            options=[
                {"value": "postgresql", "label": "PostgreSQL"},
                {"value": "mysql", "label": "MySQL"},
                {"value": "sqlite", "label": "SQLite"},
                {"value": "dynamodb", "label": "DynamoDB"},
                {"value": "mongodb", "label": "MongoDB"},
                {"value": "mssql", "label": "SQL Server"},
            ],
            help_text="Database driver/provider",
            group="db",
            order=0,
        )}
    )


class DynamoDbToolSpec(DbToolSpec):
    """
    Tool specification for AWS DynamoDB operations.
    """
    driver: str = Field(
        default="dynamodb",
        json_schema_extra={"ui": ui(widget_type=WidgetType.HIDDEN)}
    )
    region: str = Field(
        default="us-west-2",
        json_schema_extra={"ui": UIPresets.enum_dropdown(
            display_name="AWS Region",
            options=[
                {"value": "us-east-1", "label": "US East (N. Virginia)"},
                {"value": "us-east-2", "label": "US East (Ohio)"},
                {"value": "us-west-1", "label": "US West (N. California)"},
                {"value": "us-west-2", "label": "US West (Oregon)"},
                {"value": "eu-west-1", "label": "EU (Ireland)"},
                {"value": "eu-central-1", "label": "EU (Frankfurt)"},
                {"value": "ap-southeast-1", "label": "Asia Pacific (Singapore)"},
                {"value": "ap-northeast-1", "label": "Asia Pacific (Tokyo)"},
            ],
            help_text="AWS region for DynamoDB",
            group="dynamodb",
            order=1,
        )}
    )
    table_name: str = Field(
        json_schema_extra={"ui": UIPresets.text_input(
            display_name="Table Name",
            placeholder="my-table",
            help_text="DynamoDB table name",
            group="dynamodb",
            order=2,
        )}
    )
    endpoint_url: Optional[str] = Field(
        default=None,
        json_schema_extra={"ui": UIPresets.text_input(
            display_name="Endpoint URL (Optional)",
            placeholder="http://localhost:8000",
            help_text="Custom endpoint for LocalStack/testing",
            group="dynamodb",
            order=3,
        )}
    )
    aws_access_key_id: Optional[str] = Field(
        default=None,
        json_schema_extra={"ui": UIPresets.text_input(
            display_name="AWS Access Key ID (Optional)",
            placeholder="Leave empty for IAM role",
            help_text="Prefer IAM roles over hardcoded credentials",
            group="dynamodb",
            order=4,
        )}
    )
    aws_secret_access_key: Optional[str] = Field(
        default=None,
        json_schema_extra={"ui": ui(
            display_name="AWS Secret Access Key",
            widget_type=WidgetType.TEXT,
            placeholder="Leave empty for IAM role",
            help_text="Prefer IAM roles over hardcoded credentials",
            group="dynamodb",
            order=5,
        )}
    )


class PostgreSqlToolSpec(DbToolSpec):
    """
    Tool specification for PostgreSQL operations.
    """
    driver: str = Field(
        default="postgresql",
        json_schema_extra={"ui": ui(widget_type=WidgetType.HIDDEN)}
    )
    host: str = Field(
        default="localhost",
        json_schema_extra={"ui": UIPresets.text_input(
            display_name="Host",
            placeholder="localhost",
            help_text="Database host",
            group="postgresql",
            order=1,
        )}
    )
    port: int = Field(
        default=5432,
        ge=1,
        le=65535,
        json_schema_extra={"ui": ui(
            display_name="Port",
            widget_type=WidgetType.NUMBER,
            min_value=1,
            max_value=65535,
            help_text="Database port (default: 5432)",
            group="postgresql",
            order=2,
        )}
    )
    database: str = Field(
        json_schema_extra={"ui": UIPresets.text_input(
            display_name="Database Name",
            placeholder="mydb",
            help_text="Database name",
            group="postgresql",
            order=3,
        )}
    )
    username: str = Field(
        json_schema_extra={"ui": UIPresets.text_input(
            display_name="Username",
            placeholder="postgres",
            help_text="Database username",
            group="postgresql",
            order=4,
        )}
    )
    password: str = Field(
        json_schema_extra={"ui": ui(
            display_name="Password",
            widget_type=WidgetType.TEXT,
            help_text="Database password",
            group="postgresql",
            order=5,
        )}
    )
    connection_string: Optional[str] = Field(
        default=None,
        json_schema_extra={"ui": UIPresets.text_input(
            display_name="Connection String (Optional)",
            placeholder="postgresql://user:pass@host:5432/db",
            help_text="Full connection string (overrides individual fields)",
            group="postgresql",
            order=6,
        )}
    )
    ssl_mode: Optional[str] = Field(
        default=None,
        json_schema_extra={"ui": UIPresets.enum_dropdown(
            display_name="SSL Mode",
            options=[
                {"value": "", "label": "Default"},
                {"value": "disable", "label": "Disable"},
                {"value": "allow", "label": "Allow"},
                {"value": "prefer", "label": "Prefer"},
                {"value": "require", "label": "Require"},
            ],
            help_text="SSL connection mode",
            group="postgresql",
            order=7,
        )}
    )
    pool_size: int = Field(
        default=10,
        ge=1,
        le=100,
        json_schema_extra={"ui": UIPresets.count_slider(
            display_name="Pool Size",
            min_value=1,
            max_value=100,
            help_text="Connection pool size",
            group="postgresql",
            order=8,
        )}
    )


class MySqlToolSpec(DbToolSpec):
    """
    Tool specification for MySQL operations.
    """
    driver: str = Field(
        default="mysql",
        json_schema_extra={"ui": ui(widget_type=WidgetType.HIDDEN)}
    )
    host: str = Field(
        default="localhost",
        json_schema_extra={"ui": UIPresets.text_input(
            display_name="Host",
            placeholder="localhost",
            help_text="Database host",
            group="mysql",
            order=1,
        )}
    )
    port: int = Field(
        default=3306,
        ge=1,
        le=65535,
        json_schema_extra={"ui": ui(
            display_name="Port",
            widget_type=WidgetType.NUMBER,
            min_value=1,
            max_value=65535,
            help_text="Database port (default: 3306)",
            group="mysql",
            order=2,
        )}
    )
    database: str = Field(
        json_schema_extra={"ui": UIPresets.text_input(
            display_name="Database Name",
            placeholder="mydb",
            help_text="Database name",
            group="mysql",
            order=3,
        )}
    )
    username: str = Field(
        json_schema_extra={"ui": UIPresets.text_input(
            display_name="Username",
            placeholder="root",
            help_text="Database username",
            group="mysql",
            order=4,
        )}
    )
    password: str = Field(
        json_schema_extra={"ui": ui(
            display_name="Password",
            widget_type=WidgetType.TEXT,
            help_text="Database password",
            group="mysql",
            order=5,
        )}
    )
    connection_string: Optional[str] = Field(
        default=None,
        json_schema_extra={"ui": UIPresets.text_input(
            display_name="Connection String (Optional)",
            placeholder="mysql://user:pass@host:3306/db",
            help_text="Full connection string (overrides individual fields)",
            group="mysql",
            order=6,
        )}
    )
    charset: str = Field(
        default="utf8mb4",
        json_schema_extra={"ui": UIPresets.text_input(
            display_name="Charset",
            placeholder="utf8mb4",
            help_text="Character set",
            group="mysql",
            order=7,
        )}
    )


class SqliteToolSpec(DbToolSpec):
    """
    Tool specification for SQLite operations.
    """
    driver: str = Field(
        default="sqlite",
        json_schema_extra={"ui": ui(widget_type=WidgetType.HIDDEN)}
    )
    database_path: str = Field(
        default=":memory:",
        json_schema_extra={"ui": UIPresets.text_input(
            display_name="Database Path",
            placeholder="/path/to/database.db",
            help_text="Path to SQLite database file (:memory: for in-memory)",
            group="sqlite",
            order=1,
        )}
    )
    timeout: float = Field(
        default=5.0,
        ge=0.1,
        le=60,
        json_schema_extra={"ui": UIPresets.duration_seconds(
            display_name="Connection Timeout",
            min_value=0.1,
            max_value=60,
            help_text="Connection timeout in seconds",
            group="sqlite",
            order=2,
        )}
    )
    check_same_thread: bool = Field(
        default=False,
        json_schema_extra={"ui": ui(
            display_name="Check Same Thread",
            widget_type=WidgetType.SWITCH,
            help_text="Enable thread safety check (disable for async)",
            group="sqlite",
            order=3,
        )}
    )
