"""
Workflow Specification Models Module.

This module defines all Pydantic models for workflow configuration,
execution context, and results.

Key Models:
- IOSpec: Input/Output type specifications with formats
- TransitionVariable: Variables required for edge transitions
- NodeSpec: Enhanced node specification with I/O types
- EdgeSpec: Enhanced edge specification with transition conditions
- WorkflowSpec: Complete workflow specification
"""

import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set, Union

from pydantic import BaseModel, Field, field_validator

from ..enum import (
    NodeType,
    NodeState,
    EdgeType,
    WorkflowState,
    ConditionOperator,
    RoutingStrategy,
    DataTransformType,
    DataType,
    DataFormat,
    TriggerType,
    RetryStrategy,
    ExecutionMode,
    ConditionSourceType,
    VariableRequirement,
    IntentType,
)
from ..constants import (
    DEFAULT_MAX_WORKFLOW_ITERATIONS,
    DEFAULT_MAX_NODE_RETRIES,
    DEFAULT_NODE_TIMEOUT_SECONDS,
    DEFAULT_WORKFLOW_TIMEOUT_SECONDS,
    DEFAULT_RETRY_DELAY_SECONDS,
    NODE_ID_START,
    NODE_ID_END,
)


# =============================================================================
# CONDITION MODELS
# =============================================================================


class ConditionSpec(BaseModel):
    """Specification for a single condition."""
    
    field: str = Field(
        description="The field/variable path to evaluate (supports dot notation)"
    )
    operator: ConditionOperator = Field(
        default=ConditionOperator.EQUALS,
        description="The comparison operator"
    )
    value: Any = Field(
        default=None,
        description="The value to compare against (not needed for IS_EMPTY, IS_TRUE, etc.)"
    )
    negate: bool = Field(
        default=False,
        description="If True, negate the condition result"
    )
    
    model_config = {"extra": "allow"}


class ConditionGroup(BaseModel):
    """A group of conditions with logical operators."""
    
    conditions: List[Union[ConditionSpec, "ConditionGroup"]] = Field(
        default_factory=list,
        description="List of conditions or nested condition groups"
    )
    logic: str = Field(
        default="and",
        description="Logical operator: 'and' or 'or'"
    )
    
    @field_validator("logic")
    @classmethod
    def validate_logic(cls, v: str) -> str:
        if v.lower() not in ("and", "or"):
            raise ValueError("logic must be 'and' or 'or'")
        return v.lower()


# =============================================================================
# INPUT/OUTPUT SPECIFICATION MODELS
# =============================================================================


class IOFieldSpec(BaseModel):
    """Specification for a single input/output field."""
    
    name: str = Field(
        description="Field name"
    )
    data_type: DataType = Field(
        default=DataType.ANY,
        description="Data type of the field"
    )
    format: Optional[DataFormat] = Field(
        default=None,
        description="Data format (text, json, markdown, etc.)"
    )
    description: Optional[str] = Field(
        default=None,
        description="Human-readable description of the field"
    )
    required: bool = Field(
        default=False,
        description="Whether this field is required"
    )
    default: Any = Field(
        default=None,
        description="Default value if not provided"
    )
    json_schema: Optional[Dict[str, Any]] = Field(
        default=None,
        description="JSON Schema for complex validation"
    )
    examples: List[Any] = Field(
        default_factory=list,
        description="Example values for documentation"
    )
    
    model_config = {"extra": "allow"}


class IOSpec(BaseModel):
    """
    Input/Output specification for nodes and workflows.
    
    Defines the expected structure, types, and formats of data
    flowing into and out of nodes/workflows.
    """
    
    fields: List[IOFieldSpec] = Field(
        default_factory=list,
        description="List of field specifications"
    )
    format: DataFormat = Field(
        default=DataFormat.JSON,
        description="Overall data format"
    )
    json_schema: Optional[Dict[str, Any]] = Field(
        default=None,
        description="JSON Schema for the entire input/output"
    )
    description: Optional[str] = Field(
        default=None,
        description="Description of the input/output"
    )
    
    model_config = {"extra": "allow"}
    
    def get_required_fields(self) -> List[str]:
        """Get names of required fields."""
        return [f.name for f in self.fields if f.required]
    
    def get_field(self, name: str) -> Optional[IOFieldSpec]:
        """Get a field by name."""
        for field in self.fields:
            if field.name == name:
                return field
        return None
    
    def validate_data(self, data: Dict[str, Any]) -> List[str]:
        """Validate data against this spec, returning list of errors."""
        errors = []
        for field in self.fields:
            if field.required and field.name not in data:
                errors.append(f"Missing required field: {field.name}")
        return errors


# =============================================================================
# TRANSITION VARIABLE MODELS
# =============================================================================


class TransitionVariable(BaseModel):
    """
    Variable specification for edge transitions.
    
    Used to define what data must be extracted/available before
    transitioning to the next node. Supports prompting for missing
    required variables.
    """
    
    name: str = Field(
        description="Variable name"
    )
    data_type: DataType = Field(
        default=DataType.STRING,
        description="Expected data type"
    )
    requirement: VariableRequirement = Field(
        default=VariableRequirement.OPTIONAL,
        description="Whether this variable is required, optional, or conditional"
    )
    source: Optional[str] = Field(
        default=None,
        description="Source path to extract variable (e.g., '$output.service_name')"
    )
    description: Optional[str] = Field(
        default=None,
        description="Description of what this variable represents"
    )
    prompt_if_missing: Optional[str] = Field(
        default=None,
        description="Prompt to ask user if variable is missing and required"
    )
    extraction_instruction: Optional[str] = Field(
        default=None,
        description="LLM instruction for extracting this variable from conversation"
    )
    validation_regex: Optional[str] = Field(
        default=None,
        description="Regex pattern for validation"
    )
    allowed_values: Optional[List[Any]] = Field(
        default=None,
        description="List of allowed values (enum-like constraint)"
    )
    default: Any = Field(
        default=None,
        description="Default value if not provided and not required"
    )
    
    model_config = {"extra": "allow"}
    
    def is_required(self) -> bool:
        """Check if this variable is required."""
        return self.requirement == VariableRequirement.REQUIRED


class TransitionCondition(BaseModel):
    """
    Enhanced condition for edge transitions.
    
    Supports multiple condition sources including LLM classification,
    tool results, and context variables. Can be combined with required
    transition variables.
    """
    
    source_type: ConditionSourceType = Field(
        default=ConditionSourceType.CONTEXT,
        description="Source of the condition value"
    )
    field: str = Field(
        description="Field/path to evaluate"
    )
    operator: ConditionOperator = Field(
        default=ConditionOperator.EQUALS,
        description="Comparison operator"
    )
    value: Any = Field(
        default=None,
        description="Value to compare against"
    )
    
    # For LLM-based conditions
    llm_prompt: Optional[str] = Field(
        default=None,
        description="Prompt for LLM classification (used with LLM_CLASSIFICATION source)"
    )
    intent: Optional[IntentType] = Field(
        default=None,
        description="Expected intent type (for intent-based routing)"
    )
    
    # Negation
    negate: bool = Field(
        default=False,
        description="Negate the condition result"
    )
    
    model_config = {"extra": "allow"}


class TransitionSpec(BaseModel):
    """
    Complete specification for edge transitions.
    
    Combines conditions with required/optional variables and
    defines behavior when requirements aren't met.
    """
    
    conditions: List[TransitionCondition] = Field(
        default_factory=list,
        description="Conditions that must be met for transition"
    )
    variables: List[TransitionVariable] = Field(
        default_factory=list,
        description="Variables to extract/require for transition"
    )
    logic: str = Field(
        default="and",
        description="How to combine conditions: 'and' or 'or'"
    )
    on_missing_required: str = Field(
        default="prompt",
        description="Behavior when required variables missing: 'prompt', 'fail', 'skip'"
    )
    prompt_template: Optional[str] = Field(
        default=None,
        description="Template for prompting user for missing variables"
    )
    
    model_config = {"extra": "allow"}
    
    @field_validator("logic")
    @classmethod
    def validate_logic(cls, v: str) -> str:
        if v.lower() not in ("and", "or"):
            raise ValueError("logic must be 'and' or 'or'")
        return v.lower()
    
    @field_validator("on_missing_required")
    @classmethod
    def validate_on_missing(cls, v: str) -> str:
        if v.lower() not in ("prompt", "fail", "skip"):
            raise ValueError("on_missing_required must be 'prompt', 'fail', or 'skip'")
        return v.lower()
    
    def get_required_variables(self) -> List[TransitionVariable]:
        """Get all required transition variables."""
        return [v for v in self.variables if v.is_required()]
    
    def get_missing_required(self, data: Dict[str, Any]) -> List[TransitionVariable]:
        """Get required variables that are missing from data."""
        missing = []
        for var in self.get_required_variables():
            if var.name not in data or data.get(var.name) is None:
                missing.append(var)
        return missing
    
    def build_missing_prompt(self, missing_vars: List[TransitionVariable]) -> str:
        """Build a prompt to ask for missing required variables."""
        if self.prompt_template:
            return self.prompt_template.format(
                variables=", ".join(v.name for v in missing_vars)
            )
        
        prompts = []
        for var in missing_vars:
            if var.prompt_if_missing:
                prompts.append(var.prompt_if_missing)
            else:
                prompts.append(f"Please provide {var.name}" + 
                             (f" ({var.description})" if var.description else ""))
        
        return " ".join(prompts)


# =============================================================================
# TRANSFORM MODELS
# =============================================================================


class TransformSpec(BaseModel):
    """Specification for data transformation."""
    
    transform_type: DataTransformType = Field(
        default=DataTransformType.PASS_THROUGH,
        description="Type of transformation"
    )
    config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Transform-specific configuration"
    )
    
    # Common transform configs
    template: Optional[str] = Field(
        default=None,
        description="Template string for TEMPLATE transform type"
    )
    mapping: Optional[Dict[str, str]] = Field(
        default=None,
        description="Field mapping for MAP transform type"
    )
    expression: Optional[str] = Field(
        default=None,
        description="JMESPath/JSONPath/Python expression for expression-based transforms"
    )
    
    model_config = {"extra": "allow"}


# =============================================================================
# NODE MODELS
# =============================================================================


class RetryConfig(BaseModel):
    """Configuration for node retry behavior."""
    
    max_retries: int = Field(
        default=DEFAULT_MAX_NODE_RETRIES,
        ge=0,
        description="Maximum number of retries"
    )
    strategy: RetryStrategy = Field(
        default=RetryStrategy.EXPONENTIAL_BACKOFF,
        description="Retry delay strategy"
    )
    initial_delay_seconds: float = Field(
        default=DEFAULT_RETRY_DELAY_SECONDS,
        ge=0,
        description="Initial delay between retries"
    )
    max_delay_seconds: float = Field(
        default=60.0,
        ge=0,
        description="Maximum delay between retries"
    )
    multiplier: float = Field(
        default=2.0,
        ge=1.0,
        description="Multiplier for exponential/linear backoff"
    )
    retryable_errors: List[str] = Field(
        default_factory=list,
        description="List of error types to retry (empty = all errors)"
    )


class NodeInputMapping(BaseModel):
    """Mapping for node input from workflow context."""
    
    source: str = Field(
        description="Source path in context (e.g., '$input.query', '$node.prev.output')"
    )
    target: str = Field(
        description="Target key in node input"
    )
    default: Any = Field(
        default=None,
        description="Default value if source is not found"
    )
    required: bool = Field(
        default=False,
        description="If True, fail if source is not found and no default"
    )
    transform: Optional[TransformSpec] = Field(
        default=None,
        description="Optional transformation to apply"
    )


class NodeOutputMapping(BaseModel):
    """Mapping for storing node output to workflow context."""
    
    source: str = Field(
        default="$output",
        description="Source path in node output (e.g., '$output.result', '$output')"
    )
    target: str = Field(
        description="Target path in context to store the value"
    )
    transform: Optional[TransformSpec] = Field(
        default=None,
        description="Optional transformation to apply"
    )


class NodeSpec(BaseModel):
    """
    Specification for a workflow node.
    
    Enhanced with explicit input/output type specifications,
    supporting strong typing and validation.
    """
    
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique node identifier"
    )
    name: str = Field(
        description="Human-readable node name"
    )
    node_type: NodeType = Field(
        description="Type of node"
    )
    description: Optional[str] = Field(
        default=None,
        description="Node description"
    )
    
    # Node-specific configuration
    config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Node-type-specific configuration"
    )
    
    # Input/Output TYPE SPECIFICATIONS (new)
    input_spec: Optional[IOSpec] = Field(
        default=None,
        description="Specification for node input types and formats"
    )
    output_spec: Optional[IOSpec] = Field(
        default=None,
        description="Specification for node output types and formats"
    )
    
    # Input/Output mappings (legacy/compatibility)
    input_mappings: List[NodeInputMapping] = Field(
        default_factory=list,
        description="Mappings from context to node input"
    )
    output_mappings: List[NodeOutputMapping] = Field(
        default_factory=list,
        description="Mappings from node output to context"
    )
    
    # Execution configuration
    timeout_seconds: float = Field(
        default=DEFAULT_NODE_TIMEOUT_SECONDS,
        ge=0,
        description="Maximum execution time for this node"
    )
    retry_config: Optional[RetryConfig] = Field(
        default=None,
        description="Retry configuration for this node"
    )
    skip_on_error: bool = Field(
        default=False,
        description="If True, skip this node on error instead of failing workflow"
    )
    
    # Conditional execution
    run_if: Optional[ConditionGroup] = Field(
        default=None,
        description="Condition group - only run node if conditions are met"
    )
    
    # System prompt (for LLM/Agent nodes)
    system_prompt: Optional[str] = Field(
        default=None,
        description="System prompt for LLM/Agent nodes"
    )
    
    # Metadata
    tags: List[str] = Field(
        default_factory=list,
        description="Tags for categorization"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    
    # Position for visual editors
    position: Optional[Dict[str, float]] = Field(
        default=None,
        description="Node position for visual editing (x, y coordinates)"
    )
    
    model_config = {"extra": "allow"}
    
    def get_required_inputs(self) -> List[str]:
        """Get names of required input fields."""
        if self.input_spec:
            return self.input_spec.get_required_fields()
        return [m.target for m in self.input_mappings if m.required]
    
    def validate_input(self, data: Dict[str, Any]) -> List[str]:
        """Validate input data against spec."""
        if self.input_spec:
            return self.input_spec.validate_data(data)
        return []


# =============================================================================
# EDGE MODELS
# =============================================================================


class EdgeSpec(BaseModel):
    """
    Specification for a workflow edge.
    
    Enhanced with transition specifications that support:
    - Required/optional transition variables
    - LLM-based condition evaluation
    - Prompting for missing required data
    - Intent-based routing
    """
    
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique edge identifier"
    )
    source_id: str = Field(
        description="ID of the source node"
    )
    target_id: str = Field(
        description="ID of the target node"
    )
    edge_type: EdgeType = Field(
        default=EdgeType.DEFAULT,
        description="Type of edge"
    )
    
    # Legacy Conditions (for backward compatibility)
    conditions: List[ConditionSpec] = Field(
        default_factory=list,
        description="List of conditions (AND logic)"
    )
    condition_group: Optional[ConditionGroup] = Field(
        default=None,
        description="Complex condition group with AND/OR logic"
    )
    
    # Enhanced Transition Specification (new)
    transition_spec: Optional[TransitionSpec] = Field(
        default=None,
        description="Enhanced transition specification with variables and prompts"
    )
    
    # Intent-based routing
    intent: Optional[IntentType] = Field(
        default=None,
        description="Required intent type for this transition (for conversational flows)"
    )
    intent_confidence_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum confidence score for intent match"
    )
    
    # Data transformation
    transform: Optional[TransformSpec] = Field(
        default=None,
        description="Data transformation to apply"
    )
    
    # Variables to pass through this edge
    pass_through_variables: List[str] = Field(
        default_factory=list,
        description="Variable names to pass from source to target node"
    )
    
    # Priority and ordering
    priority: int = Field(
        default=0,
        description="Edge priority (higher = checked first)"
    )
    
    # Edge-specific settings
    label: Optional[str] = Field(
        default=None,
        description="Human-readable edge label"
    )
    description: Optional[str] = Field(
        default=None,
        description="Edge description"
    )
    
    # Metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    
    model_config = {"extra": "allow"}
    
    def has_required_variables(self) -> bool:
        """Check if this edge has required transition variables."""
        if not self.transition_spec:
            return False
        return len(self.transition_spec.get_required_variables()) > 0
    
    def get_missing_requirements(self, data: Dict[str, Any]) -> List[TransitionVariable]:
        """Get missing required variables from data."""
        if not self.transition_spec:
            return []
        return self.transition_spec.get_missing_required(data)


# =============================================================================
# TRIGGER MODELS
# =============================================================================


class ScheduleConfig(BaseModel):
    """Configuration for scheduled triggers."""
    
    cron: Optional[str] = Field(
        default=None,
        description="Cron expression for scheduling"
    )
    interval_seconds: Optional[int] = Field(
        default=None,
        ge=1,
        description="Interval in seconds between executions"
    )
    timezone: str = Field(
        default="UTC",
        description="Timezone for cron expression"
    )
    start_time: Optional[datetime] = Field(
        default=None,
        description="Start time for scheduled execution"
    )
    end_time: Optional[datetime] = Field(
        default=None,
        description="End time for scheduled execution"
    )


class WebhookConfig(BaseModel):
    """Configuration for webhook triggers."""
    
    path: str = Field(
        description="Webhook endpoint path"
    )
    methods: List[str] = Field(
        default=["POST"],
        description="Allowed HTTP methods"
    )
    auth_required: bool = Field(
        default=True,
        description="Whether authentication is required"
    )
    auth_type: Optional[str] = Field(
        default=None,
        description="Authentication type (api_key, bearer, basic, etc.)"
    )
    validate_payload: bool = Field(
        default=False,
        description="Whether to validate incoming payload"
    )
    payload_schema: Optional[Dict[str, Any]] = Field(
        default=None,
        description="JSON schema for payload validation"
    )


class TriggerSpec(BaseModel):
    """Specification for a workflow trigger."""
    
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique trigger identifier"
    )
    name: str = Field(
        description="Trigger name"
    )
    trigger_type: TriggerType = Field(
        description="Type of trigger"
    )
    enabled: bool = Field(
        default=True,
        description="Whether trigger is enabled"
    )
    
    # Trigger-type-specific config
    schedule_config: Optional[ScheduleConfig] = Field(
        default=None,
        description="Configuration for scheduled triggers"
    )
    webhook_config: Optional[WebhookConfig] = Field(
        default=None,
        description="Configuration for webhook triggers"
    )
    event_config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Configuration for event triggers"
    )
    
    # Input transformation
    input_transform: Optional[TransformSpec] = Field(
        default=None,
        description="Transform trigger payload to workflow input"
    )
    
    # Metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    
    model_config = {"extra": "allow"}


# =============================================================================
# WORKFLOW MODELS
# =============================================================================


class WorkflowVariable(BaseModel):
    """Definition of a workflow variable."""
    
    name: str = Field(
        description="Variable name"
    )
    type: str = Field(
        default="any",
        description="Variable type (string, number, boolean, object, array, any)"
    )
    default: Any = Field(
        default=None,
        description="Default value"
    )
    description: Optional[str] = Field(
        default=None,
        description="Variable description"
    )
    required: bool = Field(
        default=False,
        description="Whether variable is required in workflow input"
    )
    json_schema: Optional[Dict[str, Any]] = Field(
        default=None,
        description="JSON schema for validation"
    )


class WorkflowMetadata(BaseModel):
    """Metadata for a workflow."""
    
    author: Optional[str] = Field(
        default=None,
        description="Workflow author"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update timestamp"
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Workflow tags"
    )
    category: Optional[str] = Field(
        default=None,
        description="Workflow category"
    )
    documentation_url: Optional[str] = Field(
        default=None,
        description="Link to documentation"
    )
    icon: Optional[str] = Field(
        default=None,
        description="Workflow icon (emoji or URL)"
    )
    color: Optional[str] = Field(
        default=None,
        description="Workflow color for UI"
    )
    custom: Dict[str, Any] = Field(
        default_factory=dict,
        description="Custom metadata fields"
    )


class WorkflowSpec(BaseModel):
    """
    Complete specification for a workflow.
    
    Enhanced with:
    - Explicit input/output type specifications
    - Support for conversational/intent-based workflows
    - Nested workflow support (subworkflows)
    - Agent integration support
    """
    
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique workflow identifier"
    )
    name: str = Field(
        description="Workflow name"
    )
    version: str = Field(
        default="1.0.0",
        description="Workflow version (semver)"
    )
    description: Optional[str] = Field(
        default=None,
        description="Workflow description"
    )
    
    # Nodes and edges
    nodes: List[NodeSpec] = Field(
        default_factory=list,
        description="List of workflow nodes"
    )
    edges: List[EdgeSpec] = Field(
        default_factory=list,
        description="List of workflow edges"
    )
    
    # Start/End configuration
    start_node_id: Optional[str] = Field(
        default=None,
        description="ID of start node (auto-detected if not specified)"
    )
    end_node_ids: List[str] = Field(
        default_factory=list,
        description="IDs of end nodes (auto-detected if not specified)"
    )
    
    # INPUT/OUTPUT SPECIFICATIONS (new)
    input_spec: Optional[IOSpec] = Field(
        default=None,
        description="Specification for workflow input types and formats"
    )
    output_spec: Optional[IOSpec] = Field(
        default=None,
        description="Specification for workflow output types and formats"
    )
    
    # Legacy Variables (for backward compatibility)
    input_variables: List[WorkflowVariable] = Field(
        default_factory=list,
        description="Expected input variables"
    )
    output_variables: List[WorkflowVariable] = Field(
        default_factory=list,
        description="Output variable definitions"
    )
    
    # Triggers
    triggers: List[TriggerSpec] = Field(
        default_factory=list,
        description="Workflow triggers"
    )
    
    # Execution configuration
    max_iterations: int = Field(
        default=DEFAULT_MAX_WORKFLOW_ITERATIONS,
        ge=1,
        description="Maximum number of node executions"
    )
    timeout_seconds: float = Field(
        default=DEFAULT_WORKFLOW_TIMEOUT_SECONDS,
        ge=0,
        description="Maximum workflow execution time"
    )
    execution_mode: ExecutionMode = Field(
        default=ExecutionMode.SEQUENTIAL,
        description="Default execution mode"
    )
    routing_strategy: RoutingStrategy = Field(
        default=RoutingStrategy.FIRST_MATCH,
        description="Default routing strategy"
    )
    
    # Conversational/Intent-based configuration
    is_conversational: bool = Field(
        default=False,
        description="Whether this is a conversational workflow with turns"
    )
    conversation_context_key: str = Field(
        default="conversation_history",
        description="Context key for storing conversation history"
    )
    
    # Error handling
    error_handler_node_id: Optional[str] = Field(
        default=None,
        description="ID of global error handler node"
    )
    fail_fast: bool = Field(
        default=True,
        description="If True, stop on first error; if False, continue with other branches"
    )
    
    # State management
    enable_checkpointing: bool = Field(
        default=False,
        description="Enable state checkpointing for recovery"
    )
    checkpoint_interval: int = Field(
        default=5,
        ge=1,
        description="Checkpoint every N node executions"
    )
    
    # Metadata
    metadata: WorkflowMetadata = Field(
        default_factory=WorkflowMetadata,
        description="Workflow metadata"
    )
    
    model_config = {"extra": "allow"}
    
    @field_validator("nodes")
    @classmethod
    def validate_nodes(cls, v: List[NodeSpec]) -> List[NodeSpec]:
        # Ensure unique node IDs
        ids = [n.id for n in v]
        if len(ids) != len(set(ids)):
            raise ValueError("Node IDs must be unique")
        return v
    
    @field_validator("edges")
    @classmethod
    def validate_edges(cls, v: List[EdgeSpec]) -> List[EdgeSpec]:
        # Ensure unique edge IDs
        ids = [e.id for e in v]
        if len(ids) != len(set(ids)):
            raise ValueError("Edge IDs must be unique")
        return v
    
    def get_required_inputs(self) -> List[str]:
        """Get names of required input fields."""
        if self.input_spec:
            return self.input_spec.get_required_fields()
        return [v.name for v in self.input_variables if v.required]
    
    def validate_input(self, data: Dict[str, Any]) -> List[str]:
        """Validate input data against spec."""
        if self.input_spec:
            return self.input_spec.validate_data(data)
        errors = []
        for var in self.input_variables:
            if var.required and var.name not in data:
                errors.append(f"Missing required input: {var.name}")
        return errors
    
    def get_node(self, node_id: str) -> Optional[NodeSpec]:
        """Get a node spec by ID."""
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None
    
    def get_edges_from(self, node_id: str) -> List[EdgeSpec]:
        """Get all edges originating from a node."""
        return [e for e in self.edges if e.source_id == node_id]
    
    def get_edges_to(self, node_id: str) -> List[EdgeSpec]:
        """Get all edges targeting a node."""
        return [e for e in self.edges if e.target_id == node_id]


# =============================================================================
# CONTEXT MODELS
# =============================================================================


class NodeExecutionRecord(BaseModel):
    """Record of a single node execution."""
    
    node_id: str = Field(description="Node ID")
    state: NodeState = Field(description="Final node state")
    input_data: Any = Field(default=None, description="Input data")
    output_data: Any = Field(default=None, description="Output data")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(default=None)
    duration_ms: Optional[float] = Field(default=None)
    retry_count: int = Field(default=0)


class WorkflowExecutionRecord(BaseModel):
    """Record of a complete workflow execution."""
    
    workflow_id: str = Field(description="Workflow ID")
    execution_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique execution ID"
    )
    state: WorkflowState = Field(
        default=WorkflowState.IDLE,
        description="Current workflow state"
    )
    input_data: Any = Field(default=None, description="Workflow input")
    output_data: Any = Field(default=None, description="Workflow output")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(default=None)
    duration_ms: Optional[float] = Field(default=None)
    node_executions: List[NodeExecutionRecord] = Field(default_factory=list)
    current_node_id: Optional[str] = Field(default=None)
    iteration_count: int = Field(default=0)


class WorkflowContext(BaseModel):
    """
    Workflow execution context model.
    
    Implements the data structure for IWorkflowContext.
    """
    
    workflow_id: str = Field(description="Workflow ID")
    execution_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique execution ID"
    )
    
    # Variables storage
    variables: Dict[str, Any] = Field(
        default_factory=dict,
        description="Context variables"
    )
    
    # Node outputs storage
    node_outputs: Dict[str, Any] = Field(
        default_factory=dict,
        description="Outputs from each node"
    )
    
    # Node states
    node_states: Dict[str, NodeState] = Field(
        default_factory=dict,
        description="State of each node"
    )
    
    # Execution tracking
    execution_path: List[str] = Field(
        default_factory=list,
        description="Ordered list of executed node IDs"
    )
    
    # Input/Output
    input_data: Any = Field(default=None, description="Original workflow input")
    output_data: Any = Field(default=None, description="Final workflow output")
    
    # Metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Execution metadata"
    )
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = {"extra": "allow"}
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a variable from context."""
        return self.variables.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a variable in context."""
        self.variables[key] = value
        self.updated_at = datetime.utcnow()
    
    def get_node_output(self, node_id: str) -> Optional[Any]:
        """Get output from a node."""
        return self.node_outputs.get(node_id)
    
    def set_node_output(self, node_id: str, output: Any) -> None:
        """Set output for a node."""
        self.node_outputs[node_id] = output
        self.updated_at = datetime.utcnow()
    
    def get_node_state(self, node_id: str) -> Optional[NodeState]:
        """Get state of a node."""
        return self.node_states.get(node_id)
    
    def set_node_state(self, node_id: str, state: NodeState) -> None:
        """Set state for a node."""
        self.node_states[node_id] = state
        self.updated_at = datetime.utcnow()
    
    def clone(self) -> "WorkflowContext":
        """Create a copy of this context."""
        return WorkflowContext(
            workflow_id=self.workflow_id,
            execution_id=self.execution_id,
            variables=dict(self.variables),
            node_outputs=dict(self.node_outputs),
            node_states=dict(self.node_states),
            execution_path=list(self.execution_path),
            input_data=self.input_data,
            output_data=self.output_data,
            metadata=dict(self.metadata),
            created_at=self.created_at,
            updated_at=self.updated_at,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self.model_dump()


# =============================================================================
# RESULT MODELS
# =============================================================================


class NodeResult(BaseModel):
    """Result of a node execution."""
    
    node_id: str = Field(description="Node ID")
    success: bool = Field(description="Whether execution succeeded")
    output: Any = Field(default=None, description="Node output")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    state: NodeState = Field(description="Final node state")
    duration_ms: float = Field(description="Execution duration in milliseconds")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WorkflowResult(BaseModel):
    """Result of a workflow execution."""
    
    workflow_id: str = Field(description="Workflow ID")
    execution_id: str = Field(description="Execution ID")
    success: bool = Field(description="Whether workflow completed successfully")
    output: Any = Field(default=None, description="Final workflow output")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    state: WorkflowState = Field(description="Final workflow state")
    duration_ms: float = Field(description="Total execution duration in milliseconds")
    node_results: List[NodeResult] = Field(default_factory=list)
    context: WorkflowContext = Field(description="Final execution context")
    metadata: Dict[str, Any] = Field(default_factory=dict)

