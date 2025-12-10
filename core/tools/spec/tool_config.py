"""
Tool Configuration Models with UI Metadata.

This module defines configuration models for tool behavior including
retry, circuit breaker, idempotency, speech, and dynamic variable configs.

Each field includes UI metadata for automatic Flutter form generation.
"""

from typing import Any, List, Optional

from pydantic import BaseModel, Field
from ..defaults import (
    RETRY_DEFAULT_MAX_ATTEMPTS,
    RETRY_DEFAULT_BASE_DELAY_S,
    RETRY_DEFAULT_MAX_DELAY_S,
    RETRY_DEFAULT_JITTER_S,
    CB_DEFAULT_ENABLED,
    CB_DEFAULT_FAILURE_THRESHOLD,
    CB_DEFAULT_RECOVERY_TIMEOUT_S,
    CB_DEFAULT_HALF_OPEN_MAX_CALLS,
    CB_DEFAULT_ERROR_CODES_TO_TRIP,
    IDEMPOTENCY_DEFAULT_ENABLED,
    IDEMPOTENCY_DEFAULT_TTL_S,
    IDEMPOTENCY_DEFAULT_PERSIST_RESULT,
    IDEMPOTENCY_DEFAULT_BYPASS_ON_MISSING_KEY,
    INTERRUPTION_DEFAULT_DISABLED,
    SPEECH_DEFAULT_ENABLED,
    SPEECH_DEFAULT_CONSTANT_MESSAGE,
    VARIABLE_ASSIGNMENT_DEFAULT_ENABLED,
)
from ..enum import (
    SpeechMode,
    ExecutionMode,
    VariableAssignmentOperator,
    SpeechContextScope,
    TransformExecutionMode,
)
from .ui_metadata import UIPresets, WidgetType, ui


class RetryConfig(BaseModel):
    """
    Configuration for retry behavior.
    
    Controls automatic retry on transient failures with exponential backoff.
    """
    enabled: bool = Field(
        default=False,
        json_schema_extra={"ui": UIPresets.enabled_switch(
            display_name="Enable Retries",
            help_text="Automatically retry on transient failures",
            group="retry",
            order=0,
        )}
    )
    max_attempts: int = Field(
        default=RETRY_DEFAULT_MAX_ATTEMPTS,
        ge=1,
        le=10,
        json_schema_extra={"ui": UIPresets.count_slider(
            display_name="Max Retry Attempts",
            min_value=1,
            max_value=10,
            visible_when="enabled == true",
            help_text="Maximum number of retry attempts before giving up",
            group="retry",
            order=1,
        )}
    )
    base_delay_s: float = Field(
        default=RETRY_DEFAULT_BASE_DELAY_S,
        ge=0.1,
        le=60,
        json_schema_extra={"ui": UIPresets.duration_seconds(
            display_name="Base Delay",
            min_value=0.1,
            max_value=60,
            visible_when="enabled == true",
            help_text="Initial delay between retries (seconds)",
            group="retry",
            order=2,
        )}
    )
    max_delay_s: float = Field(
        default=RETRY_DEFAULT_MAX_DELAY_S,
        ge=1,
        le=300,
        json_schema_extra={"ui": UIPresets.duration_seconds(
            display_name="Max Delay",
            min_value=1,
            max_value=300,
            visible_when="enabled == true",
            help_text="Maximum delay between retries with exponential backoff",
            group="retry",
            order=3,
        )}
    )
    jitter_s: float = Field(
        default=RETRY_DEFAULT_JITTER_S,
        ge=0,
        le=10,
        json_schema_extra={"ui": UIPresets.duration_seconds(
            display_name="Jitter",
            min_value=0,
            max_value=10,
            visible_when="enabled == true",
            help_text="Random jitter added to delay to prevent thundering herd",
            group="retry",
            order=4,
        )}
    )


class CircuitBreakerConfig(BaseModel):
    """
    Configuration for circuit breaker pattern.
    
    Protects against cascading failures by failing fast when a service is unhealthy.
    """
    enabled: bool = Field(
        default=CB_DEFAULT_ENABLED,
        json_schema_extra={"ui": UIPresets.enabled_switch(
            display_name="Enable Circuit Breaker",
            help_text="Fail fast when service is unhealthy to prevent cascading failures",
            group="circuit_breaker",
            order=0,
        )}
    )
    failure_threshold: int = Field(
        default=CB_DEFAULT_FAILURE_THRESHOLD,
        ge=1,
        le=20,
        json_schema_extra={"ui": UIPresets.count_slider(
            display_name="Failure Threshold",
            min_value=1,
            max_value=20,
            visible_when="enabled == true",
            help_text="Consecutive failures before opening the circuit",
            group="circuit_breaker",
            order=1,
        )}
    )
    recovery_timeout_s: int = Field(
        default=CB_DEFAULT_RECOVERY_TIMEOUT_S,
        ge=5,
        le=600,
        json_schema_extra={"ui": ui(
            display_name="Recovery Timeout",
            widget_type=WidgetType.NUMBER,
            min_value=5,
            max_value=600,
            step=5,
            visible_when="enabled == true",
            help_text="Seconds to wait before attempting recovery (OPEN → HALF_OPEN)",
            group="circuit_breaker",
            order=2,
        )}
    )
    half_open_max_calls: int = Field(
        default=CB_DEFAULT_HALF_OPEN_MAX_CALLS,
        ge=1,
        le=10,
        json_schema_extra={"ui": UIPresets.count_slider(
            display_name="Half-Open Max Calls",
            min_value=1,
            max_value=10,
            visible_when="enabled == true",
            help_text="Number of test calls allowed in HALF_OPEN state",
            group="circuit_breaker",
            order=3,
        )}
    )
    error_codes_to_trip: List[str] = Field(
        default_factory=lambda: CB_DEFAULT_ERROR_CODES_TO_TRIP,
        json_schema_extra={"ui": UIPresets.string_list(
            display_name="Error Codes to Trip",
            item_label="Error Code {index}",
            visible_when="enabled == true",
            help_text="Error codes that should trip the circuit breaker",
            group="circuit_breaker",
            order=4,
        )}
    )


class IdempotencyConfig(BaseModel):
    """
    Configuration for idempotency behavior.
    
    Prevents duplicate executions and enables result caching.
    """
    enabled: bool = Field(
        default=IDEMPOTENCY_DEFAULT_ENABLED,
        json_schema_extra={"ui": UIPresets.enabled_switch(
            display_name="Enable Idempotency",
            help_text="Cache and guard against repeated executions using key fields",
            group="idempotency",
            order=0,
        )}
    )
    key_fields: Optional[List[str]] = Field(
        default=None,
        json_schema_extra={"ui": UIPresets.string_list(
            display_name="Key Fields",
            item_label="Field {index}",
            visible_when="enabled == true",
            help_text="Fields to use for idempotency key (empty = all args)",
            group="idempotency",
            order=1,
        )}
    )
    ttl_s: Optional[int] = Field(
        default=IDEMPOTENCY_DEFAULT_TTL_S,
        ge=60,
        le=86400,
        json_schema_extra={"ui": ui(
            display_name="TTL (seconds)",
            widget_type=WidgetType.NUMBER,
            min_value=60,
            max_value=86400,
            step=60,
            visible_when="enabled == true",
            help_text="Time-to-live for cached results",
            group="idempotency",
            order=2,
        )}
    )
    persist_result: bool = Field(
        default=IDEMPOTENCY_DEFAULT_PERSIST_RESULT,
        json_schema_extra={"ui": ui(
            display_name="Persist Result",
            widget_type=WidgetType.SWITCH,
            visible_when="enabled == true",
            help_text="Store result for reuse on duplicate calls",
            group="idempotency",
            order=3,
        )}
    )
    bypass_on_missing_key: bool = Field(
        default=IDEMPOTENCY_DEFAULT_BYPASS_ON_MISSING_KEY,
        json_schema_extra={"ui": ui(
            display_name="Bypass on Missing Key",
            widget_type=WidgetType.SWITCH,
            visible_when="enabled == true",
            help_text="Skip idempotency check if key fields are missing",
            group="idempotency",
            order=4,
        )}
    )


class InterruptionConfig(BaseModel):
    """
    Configuration for tool interruption behavior.
    
    Controls whether user inputs can interrupt tool execution.
    """
    disabled: bool = Field(
        default=INTERRUPTION_DEFAULT_DISABLED,
        json_schema_extra={"ui": ui(
            display_name="Disable Interruption",
            widget_type=WidgetType.SWITCH,
            help_text="If enabled, tool execution cannot be interrupted by user input",
            group="interruption",
            order=0,
        )}
    )


class PreToolSpeechConfig(BaseModel):
    """
    Configuration for pre-tool speech/announcement.
    
    Controls what the agent says before executing a tool.
    """
    enabled: bool = Field(
        default=SPEECH_DEFAULT_ENABLED,
        json_schema_extra={"ui": UIPresets.enabled_switch(
            display_name="Enable Pre-Tool Speech",
            help_text="Whether to speak/announce before tool execution",
            group="speech",
            order=0,
        )}
    )
    mode: SpeechMode = Field(
        default=SpeechMode.AUTO,
        json_schema_extra={"ui": UIPresets.enum_dropdown(
            display_name="Speech Mode",
            options=[
                {"value": "auto", "label": "Auto (LLM generates)"},
                {"value": "random", "label": "Random (from list)"},
                {"value": "constant", "label": "Constant (fixed message)"},
            ],
            visible_when="enabled == true",
            help_text="How to generate the pre-tool speech",
            group="speech",
            order=1,
        )}
    )
    constant_message: str = Field(
        default=SPEECH_DEFAULT_CONSTANT_MESSAGE,
        json_schema_extra={"ui": UIPresets.text_input(
            display_name="Constant Message",
            placeholder="Processing your request...",
            visible_when="enabled == true && mode == 'constant'",
            help_text="Fixed message to use when mode is CONSTANT",
            group="speech",
            order=2,
        )}
    )
    random_messages: List[str] = Field(
        default_factory=list,
        json_schema_extra={"ui": UIPresets.string_list(
            display_name="Random Messages",
            item_label="Message {index}",
            visible_when="enabled == true && mode == 'random'",
            help_text="List of messages to randomly select from",
            group="speech",
            order=3,
        )}
    )
    
    # AUTO mode specific configuration
    context_scope: SpeechContextScope = Field(
        default=SpeechContextScope.TOOL_ONLY,
        json_schema_extra={"ui": UIPresets.enum_dropdown(
            display_name="Context Scope",
            options=[
                {"value": "full_context", "label": "Full Context"},
                {"value": "tool_only", "label": "Tool Only"},
                {"value": "last_message", "label": "Last Message"},
                {"value": "custom", "label": "Custom Instruction"},
            ],
            visible_when="enabled == true && mode == 'auto'",
            help_text="What context the LLM uses when generating speech",
            group="speech_auto",
            order=4,
        )}
    )
    llm_instruction: Optional[str] = Field(
        default=None,
        json_schema_extra={"ui": UIPresets.multiline_text(
            display_name="Custom LLM Instruction",
            placeholder="Generate a brief message that...",
            visible_when="enabled == true && mode == 'auto' && context_scope == 'custom'",
            help_text="Custom instruction for LLM (required when context_scope=CUSTOM)",
            group="speech_auto",
            order=5,
        )}
    )
    include_tool_params: bool = Field(
        default=True,
        json_schema_extra={"ui": ui(
            display_name="Include Tool Parameters",
            widget_type=WidgetType.SWITCH,
            visible_when="enabled == true && mode == 'auto'",
            help_text="Include tool parameters in context for speech generation",
            group="speech_auto",
            order=6,
        )}
    )
    include_user_intent: bool = Field(
        default=True,
        json_schema_extra={"ui": ui(
            display_name="Include User Intent",
            widget_type=WidgetType.SWITCH,
            visible_when="enabled == true && mode == 'auto'",
            help_text="Include detected user intent in context",
            group="speech_auto",
            order=7,
        )}
    )
    max_tokens: int = Field(
        default=50,
        ge=10,
        le=200,
        json_schema_extra={"ui": UIPresets.count_slider(
            display_name="Max Tokens",
            min_value=10,
            max_value=200,
            visible_when="enabled == true && mode == 'auto'",
            help_text="Maximum tokens for generated speech",
            group="speech_auto",
            order=8,
        )}
    )
    temperature: float = Field(
        default=0.7,
        ge=0,
        le=2,
        json_schema_extra={"ui": ui(
            display_name="Temperature",
            widget_type=WidgetType.SLIDER,
            min_value=0,
            max_value=2,
            step=0.1,
            visible_when="enabled == true && mode == 'auto'",
            help_text="LLM temperature (higher = more creative)",
            group="speech_auto",
            order=9,
        )}
    )
    speech_style: Optional[str] = Field(
        default=None,
        json_schema_extra={"ui": UIPresets.text_input(
            display_name="Speech Style",
            placeholder="friendly, professional, concise",
            visible_when="enabled == true && mode == 'auto'",
            help_text="Style guidance for speech generation",
            group="speech_auto",
            order=10,
        )}
    )


class ExecutionConfig(BaseModel):
    """
    Configuration for tool execution behavior relative to speech.
    
    Controls whether to wait for speech to complete before executing
    the tool, or run both in parallel.
    """
    mode: ExecutionMode = Field(
        default=ExecutionMode.SEQUENTIAL,
        json_schema_extra={"ui": UIPresets.enum_dropdown(
            display_name="Execution Mode",
            options=[
                {"value": "sequential", "label": "Sequential (speech then execute)"},
                {"value": "parallel", "label": "Parallel (speech and execute together)"},
            ],
            help_text="Whether to wait for speech (sequential) or run in parallel",
            group="execution",
            order=0,
        )}
    )
    speech_timeout_ms: Optional[int] = Field(
        default=None,
        ge=100,
        le=10000,
        json_schema_extra={"ui": ui(
            display_name="Speech Timeout (ms)",
            widget_type=WidgetType.NUMBER,
            min_value=100,
            max_value=10000,
            step=100,
            visible_when="mode == 'sequential'",
            help_text="Max time to wait for speech in sequential mode",
            group="execution",
            order=1,
        )}
    )


class VariableAssignment(BaseModel):
    """
    Single variable assignment rule.
    
    Maps a field from tool result to a dynamic variable.
    """
    target_variable: str = Field(
        json_schema_extra={"ui": UIPresets.text_input(
            display_name="Target Variable",
            placeholder="guest_id",
            help_text="Name of the dynamic variable to update",
            group="assignment",
            order=0,
        )}
    )
    source_field: str = Field(
        json_schema_extra={"ui": UIPresets.text_input(
            display_name="Source Field",
            placeholder="data.guest_id",
            help_text="Path to field in tool result (dot notation)",
            group="assignment",
            order=1,
        )}
    )
    operator: VariableAssignmentOperator = Field(
        default=VariableAssignmentOperator.SET,
        json_schema_extra={"ui": UIPresets.enum_dropdown(
            display_name="Operator",
            options=[
                {"value": "set", "label": "Set (always)"},
                {"value": "set_if_exists", "label": "Set if Exists"},
                {"value": "set_if_truthy", "label": "Set if Truthy"},
                {"value": "append", "label": "Append to List"},
                {"value": "increment", "label": "Increment Number"},
                {"value": "transform", "label": "Transform with Function"},
            ],
            help_text="How to assign the value",
            group="assignment",
            order=2,
        )}
    )
    default_value: Optional[Any] = Field(
        default=None,
        json_schema_extra={"ui": UIPresets.text_input(
            display_name="Default Value",
            placeholder="null",
            help_text="Default value if source field not found",
            group="assignment",
            order=3,
        )}
    )
    transform_expr: Optional[str] = Field(
        default=None,
        json_schema_extra={"ui": UIPresets.text_input(
            display_name="Transform Expression",
            placeholder="bool(value)",
            visible_when="operator == 'transform'",
            help_text="Simple transformation expression (e.g., 'bool(value)', 'str(value)')",
            group="assignment",
            order=4,
        )}
    )
    transform_func: Optional[Any] = Field(
        default=None,
        json_schema_extra={"ui": ui(
            display_name="Transform Function",
            widget_type=WidgetType.HIDDEN,
            help_text="Custom callable for complex transformations (set programmatically)",
        )}
    )
    transform_execution: TransformExecutionMode = Field(
        default=TransformExecutionMode.SYNC,
        json_schema_extra={"ui": UIPresets.enum_dropdown(
            display_name="Transform Execution",
            options=[
                {"value": "sync", "label": "Sync (block)"},
                {"value": "async", "label": "Async (fire-and-forget)"},
                {"value": "await", "label": "Await (async but wait)"},
            ],
            visible_when="operator == 'transform'",
            help_text="Execution mode for transform_func",
            group="assignment",
            order=5,
        )}
    )
    
    model_config = {
        "arbitrary_types_allowed": True
    }


class DynamicVariableConfig(BaseModel):
    """
    Configuration for dynamic variable assignments from tool results.
    
    Allows updating conversation/session variables based on tool execution results.
    """
    enabled: bool = Field(
        default=VARIABLE_ASSIGNMENT_DEFAULT_ENABLED,
        json_schema_extra={"ui": UIPresets.enabled_switch(
            display_name="Enable Dynamic Variables",
            help_text="Update conversation/session variables based on tool results",
            group="dynamic_vars",
            order=0,
        )}
    )
    assignments: List[VariableAssignment] = Field(
        default_factory=list,
        json_schema_extra={"ui": ui(
            display_name="Variable Assignments",
            widget_type=WidgetType.ARRAY_EDITOR,
            item_label="Assignment {index}",
            visible_when="enabled == true",
            help_text="List of variable assignment rules",
            group="dynamic_vars",
            order=1,
        )}
    )
    on_error: str = Field(
        default="log",
        json_schema_extra={"ui": UIPresets.enum_dropdown(
            display_name="On Error",
            options=[
                {"value": "ignore", "label": "Ignore"},
                {"value": "log", "label": "Log Warning"},
                {"value": "raise", "label": "Raise Exception"},
            ],
            visible_when="enabled == true",
            help_text="Behavior on assignment error",
            group="dynamic_vars",
            order=2,
        )}
    )
