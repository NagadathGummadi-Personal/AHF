"""
Workflow Specification Models Module.

This module defines all Pydantic models for workflow configuration,
execution context, and results.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Union

from pydantic import BaseModel, Field, field_validator

from ..enum import (
    NodeType,
    NodeState,
    EdgeType,
    WorkflowState,
    ConditionOperator,
    RoutingStrategy,
    DataTransformType,
    TriggerType,
    RetryStrategy,
    ExecutionMode,
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
    """Specification for a workflow node."""
    
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
    
    # Input/Output mappings
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


# =============================================================================
# EDGE MODELS
# =============================================================================


class EdgeSpec(BaseModel):
    """Specification for a workflow edge."""
    
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
    
    # Conditions
    conditions: List[ConditionSpec] = Field(
        default_factory=list,
        description="List of conditions (AND logic)"
    )
    condition_group: Optional[ConditionGroup] = Field(
        default=None,
        description="Complex condition group with AND/OR logic"
    )
    
    # Data transformation
    transform: Optional[TransformSpec] = Field(
        default=None,
        description="Data transformation to apply"
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
    """Complete specification for a workflow."""
    
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
    
    # Variables
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

