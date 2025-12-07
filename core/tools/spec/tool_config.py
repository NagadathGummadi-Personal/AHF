from typing import Any, Dict, List, Optional

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
    SPEECH_DEFAULT_MODE,
    SPEECH_DEFAULT_CONSTANT_MESSAGE,
    SPEECH_DEFAULT_RANDOM_MESSAGES,
    EXECUTION_DEFAULT_MODE,
    VARIABLE_ASSIGNMENT_DEFAULT_ENABLED,
)
from ..enum import (
    SpeechMode,
    ExecutionMode,
    VariableAssignmentOperator,
    SpeechContextScope,
    TransformExecutionMode,
)

class RetryConfig(BaseModel):
    """Configuration for retry behavior"""
    max_attempts: int = RETRY_DEFAULT_MAX_ATTEMPTS
    base_delay_s: float = RETRY_DEFAULT_BASE_DELAY_S
    max_delay_s: float = RETRY_DEFAULT_MAX_DELAY_S
    jitter_s: float = RETRY_DEFAULT_JITTER_S


class CircuitBreakerConfig(BaseModel):
    """Configuration for circuit breaker pattern"""
    enabled: bool = CB_DEFAULT_ENABLED
    failure_threshold: int = CB_DEFAULT_FAILURE_THRESHOLD  # consecutive failures to open
    recovery_timeout_s: int = CB_DEFAULT_RECOVERY_TIMEOUT_S  # OPEN -> HALF_OPEN after timeout
    half_open_max_calls: int = CB_DEFAULT_HALF_OPEN_MAX_CALLS  # allowed test calls in HALF_OPEN
    error_codes_to_trip: List[str] = Field(default_factory=lambda: CB_DEFAULT_ERROR_CODES_TO_TRIP)


class IdempotencyConfig(BaseModel):
    """Configuration for idempotency behavior"""
    enabled: bool = IDEMPOTENCY_DEFAULT_ENABLED
    key_fields: Optional[List[str]] = None  # if None, use all args
    ttl_s: Optional[int] = IDEMPOTENCY_DEFAULT_TTL_S
    persist_result: bool = IDEMPOTENCY_DEFAULT_PERSIST_RESULT  # store result for reuse
    bypass_on_missing_key: bool = IDEMPOTENCY_DEFAULT_BYPASS_ON_MISSING_KEY  # if key_fields missing, bypass idempotency


class InterruptionConfig(BaseModel):
    """
    Configuration for tool interruption behavior.
    
    Controls whether user inputs can interrupt tool execution.
    
    Attributes:
        disabled: If True, tool execution won't stop for any user inputs.
                  If False, tool execution will pause for user input validation.
    
    Example:
        # Tool that should not be interrupted (e.g., payment processing)
        InterruptionConfig(disabled=True)
        
        # Tool that can be interrupted for user confirmation
        InterruptionConfig(disabled=False)
    """
    disabled: bool = Field(
        default=INTERRUPTION_DEFAULT_DISABLED,
        description="If True, tool execution cannot be interrupted by user input"
    )


class PreToolSpeechConfig(BaseModel):
    """
    Configuration for pre-tool speech/announcement.
    
    Controls what the agent says before executing a tool.
    
    Attributes:
        enabled: Whether to speak before tool execution
        mode: Speech generation mode (auto, random, constant)
        constant_message: Fixed message for CONSTANT mode
        random_messages: List of messages to choose from for RANDOM mode
        
        # AUTO mode specific configuration
        context_scope: What context the LLM uses for generation
        llm_instruction: Custom instruction for LLM (required when context_scope=CUSTOM)
        include_tool_params: Whether to include tool parameters in context
        include_user_intent: Whether to include detected user intent
        max_tokens: Maximum tokens for generated speech
        temperature: LLM temperature for speech generation
        speech_style: Style guidance (e.g., "friendly", "professional", "concise")
    
    Example:
        # LLM generates contextual speech using full conversation context
        PreToolSpeechConfig(
            enabled=True,
            mode=SpeechMode.AUTO,
            context_scope=SpeechContextScope.FULL_CONTEXT,
            speech_style="friendly and concise"
        )
        
        # LLM generates based only on tool info (faster, less context)
        PreToolSpeechConfig(
            enabled=True,
            mode=SpeechMode.AUTO,
            context_scope=SpeechContextScope.TOOL_ONLY,
            include_tool_params=True
        )
        
        # Custom instruction for specific behavior
        PreToolSpeechConfig(
            enabled=True,
            mode=SpeechMode.AUTO,
            context_scope=SpeechContextScope.CUSTOM,
            llm_instruction="Generate a brief, reassuring message that we're looking up their reservation. Mention their name if available."
        )
        
        # Random selection from predefined messages
        PreToolSpeechConfig(
            enabled=True,
            mode=SpeechMode.RANDOM,
            random_messages=[
                "Let me check that for you...",
                "Looking that up now...",
                "One moment please..."
            ]
        )
        
        # Fixed constant message
        PreToolSpeechConfig(
            enabled=True,
            mode=SpeechMode.CONSTANT,
            constant_message="Processing your request..."
        )
        
        # No speech (LLM should not speak for this tool)
        PreToolSpeechConfig(enabled=False)
    """
    enabled: bool = Field(
        default=SPEECH_DEFAULT_ENABLED,
        description="Whether to speak before tool execution"
    )
    mode: SpeechMode = Field(
        default=SpeechMode.AUTO,
        description="Speech generation mode: auto (LLM generates), random (from list), constant (fixed)"
    )
    constant_message: str = Field(
        default=SPEECH_DEFAULT_CONSTANT_MESSAGE,
        description="Fixed message to use when mode is CONSTANT"
    )
    random_messages: List[str] = Field(
        default_factory=list,
        description="List of messages to randomly select from when mode is RANDOM"
    )
    
    # AUTO mode specific configuration
    context_scope: SpeechContextScope = Field(
        default=SpeechContextScope.TOOL_ONLY,
        description="What context the LLM uses when generating speech in AUTO mode"
    )
    llm_instruction: Optional[str] = Field(
        default=None,
        description="Custom instruction for LLM (required when context_scope=CUSTOM, optional otherwise)"
    )
    include_tool_params: bool = Field(
        default=True,
        description="Whether to include tool parameters in the context for AUTO mode"
    )
    include_user_intent: bool = Field(
        default=True,
        description="Whether to include detected user intent in the context"
    )
    max_tokens: int = Field(
        default=50,
        description="Maximum tokens for generated speech (keeps it concise)"
    )
    temperature: float = Field(
        default=0.7,
        description="LLM temperature for speech generation (higher = more creative)"
    )
    speech_style: Optional[str] = Field(
        default=None,
        description="Style guidance for speech (e.g., 'friendly', 'professional', 'concise')"
    )


class ExecutionConfig(BaseModel):
    """
    Configuration for tool execution behavior relative to speech.
    
    Controls whether to wait for speech to complete before executing
    the tool, or run both in parallel.
    
    Attributes:
        mode: Execution mode (sequential or parallel)
        speech_timeout_ms: Max time to wait for speech in sequential mode
    
    Example:
        # Wait for speech to complete, then execute tool
        ExecutionConfig(mode=ExecutionMode.SEQUENTIAL)
        
        # Execute speech and tool simultaneously
        ExecutionConfig(mode=ExecutionMode.PARALLEL)
    """
    mode: ExecutionMode = Field(
        default=ExecutionMode.SEQUENTIAL,
        description="Whether to wait for speech (sequential) or run in parallel"
    )
    speech_timeout_ms: Optional[int] = Field(
        default=None,
        description="Max time to wait for speech in sequential mode (ms)"
    )


class VariableAssignment(BaseModel):
    """
    Single variable assignment rule.
    
    Maps a field from tool result to a dynamic variable.
    
    Attributes:
        target_variable: Name of the dynamic variable to update
        source_field: JSONPath or dot-notation path to field in tool result
        operator: How to assign the value (set, set_if_exists, set_if_truthy, append, increment, transform)
        default_value: Default value if source field is not found
        transform_expr: Optional transformation expression (e.g., "bool(value)", "str(value)")
        transform_func: Optional callable for custom transformation
        transform_execution: Execution mode for transform function (sync, async, await)
        wait_for_transform: Whether to wait for async transform before returning tool result
    
    Example:
        # Set guest_id from result.data.guest_id
        VariableAssignment(
            target_variable="guest_id",
            source_field="data.guest_id",
            operator=VariableAssignmentOperator.SET
        )
        
        # Set is_new_guest to True if guest was created
        VariableAssignment(
            target_variable="is_new_guest_created",
            source_field="data.created",
            operator=VariableAssignmentOperator.SET_IF_TRUTHY,
            transform_expr="bool(value)"
        )
        
        # Use custom function to transform value
        VariableAssignment(
            target_variable="formatted_date",
            source_field="data.created_at",
            operator=VariableAssignmentOperator.TRANSFORM,
            transform_func=lambda value: datetime.fromisoformat(value).strftime("%B %d, %Y"),
            transform_execution=TransformExecutionMode.SYNC
        )
        
        # Async transform that doesn't block tool result
        VariableAssignment(
            target_variable="enriched_profile",
            source_field="data.user_id",
            operator=VariableAssignmentOperator.TRANSFORM,
            transform_func=fetch_user_profile,  # async function
            transform_execution=TransformExecutionMode.ASYNC
        )
        
        # Async transform that waits for completion before returning
        VariableAssignment(
            target_variable="validated_address",
            source_field="data.address",
            operator=VariableAssignmentOperator.TRANSFORM,
            transform_func=validate_and_normalize_address,  # async function
            transform_execution=TransformExecutionMode.AWAIT
        )
    """
    target_variable: str = Field(
        description="Name of the dynamic variable to update"
    )
    source_field: str = Field(
        description="Path to field in tool result (dot notation, e.g., 'data.guest_id')"
    )
    operator: VariableAssignmentOperator = Field(
        default=VariableAssignmentOperator.SET,
        description="Assignment operator"
    )
    default_value: Optional[Any] = Field(
        default=None,
        description="Default value if source field not found"
    )
    transform_expr: Optional[str] = Field(
        default=None,
        description="Simple transformation expression (e.g., 'bool(value)', 'str(value)', 'int(value)')"
    )
    transform_func: Optional[Any] = Field(
        default=None,
        description="Custom callable for complex transformations. Receives (value, context) and returns transformed value"
    )
    transform_execution: TransformExecutionMode = Field(
        default=TransformExecutionMode.SYNC,
        description="Execution mode for transform_func: sync (block), async (fire-and-forget), await (async but wait)"
    )
    
    model_config = {
        "arbitrary_types_allowed": True
    }


class DynamicVariableConfig(BaseModel):
    """
    Configuration for dynamic variable assignments from tool results.
    
    Allows updating conversation/session variables based on tool execution results.
    
    Attributes:
        enabled: Whether dynamic variable assignment is enabled
        assignments: List of variable assignment rules
        on_error: Behavior on assignment error ('ignore', 'log', 'raise')
    
    Example:
        DynamicVariableConfig(
            enabled=True,
            assignments=[
                VariableAssignment(
                    target_variable="guest_id",
                    source_field="data.guest_id",
                    operator=VariableAssignmentOperator.SET
                ),
                VariableAssignment(
                    target_variable="is_new_guest_created",
                    source_field="data.created",
                    operator=VariableAssignmentOperator.SET_IF_TRUTHY,
                    default_value=False
                ),
                VariableAssignment(
                    target_variable="reservation_count",
                    source_field="data.reservation_count",
                    operator=VariableAssignmentOperator.INCREMENT
                )
            ]
        )
    """
    enabled: bool = Field(
        default=VARIABLE_ASSIGNMENT_DEFAULT_ENABLED,
        description="Whether dynamic variable assignment is enabled"
    )
    assignments: List[VariableAssignment] = Field(
        default_factory=list,
        description="List of variable assignment rules"
    )
    on_error: str = Field(
        default="log",
        description="Behavior on assignment error: 'ignore', 'log', or 'raise'"
    )
