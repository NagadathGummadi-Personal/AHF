"""
Workflow Interfaces Module.

This module defines all the core interfaces (protocols) for the workflow system.
All interfaces are runtime checkable, allowing for duck typing and isinstance checks.
"""

from abc import abstractmethod
from typing import (
    Any,
    AsyncIterator,
    Callable,
    Dict,
    List,
    Optional,
    Protocol,
    Set,
    Tuple,
    TypeVar,
    Union,
    runtime_checkable,
)

from ..enum import (
    NodeType,
    NodeState,
    EdgeType,
    WorkflowState,
    ConditionOperator,
    RoutingStrategy,
    DataTransformType,
    TriggerType,
)

# Type variables for generic interfaces
T = TypeVar("T")
InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


# =============================================================================
# CONTEXT INTERFACES
# =============================================================================


@runtime_checkable
class IWorkflowContext(Protocol):
    """
    Interface for workflow execution context.
    
    The context holds all state and data needed during workflow execution,
    including variables, node outputs, and execution metadata.
    """
    
    @property
    @abstractmethod
    def workflow_id(self) -> str:
        """Get the workflow ID."""
        ...
    
    @property
    @abstractmethod
    def execution_id(self) -> str:
        """Get the unique execution ID for this run."""
        ...
    
    @property
    @abstractmethod
    def variables(self) -> Dict[str, Any]:
        """Get all context variables."""
        ...
    
    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """Get a variable from context."""
        ...
    
    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """Set a variable in context."""
        ...
    
    @abstractmethod
    def get_node_output(self, node_id: str) -> Optional[Any]:
        """Get the output of a previously executed node."""
        ...
    
    @abstractmethod
    def set_node_output(self, node_id: str, output: Any) -> None:
        """Store the output of a node execution."""
        ...
    
    @abstractmethod
    def get_node_state(self, node_id: str) -> Optional[NodeState]:
        """Get the execution state of a node."""
        ...
    
    @abstractmethod
    def set_node_state(self, node_id: str, state: NodeState) -> None:
        """Set the execution state of a node."""
        ...
    
    @abstractmethod
    def clone(self) -> "IWorkflowContext":
        """Create a copy of the context (useful for parallel execution)."""
        ...
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Serialize context to dictionary."""
        ...


@runtime_checkable
class IWorkflowStateManager(Protocol):
    """
    Interface for managing workflow execution state.
    
    Handles persistence and recovery of workflow state for features like
    pause/resume, checkpointing, and crash recovery.
    """
    
    @abstractmethod
    async def save_state(
        self,
        workflow_id: str,
        execution_id: str,
        state: WorkflowState,
        context: IWorkflowContext,
        current_node_id: Optional[str] = None,
    ) -> None:
        """Save workflow state for recovery."""
        ...
    
    @abstractmethod
    async def load_state(
        self,
        workflow_id: str,
        execution_id: str,
    ) -> Optional[Tuple[WorkflowState, IWorkflowContext, Optional[str]]]:
        """Load previously saved workflow state."""
        ...
    
    @abstractmethod
    async def delete_state(
        self,
        workflow_id: str,
        execution_id: str,
    ) -> None:
        """Delete saved workflow state."""
        ...
    
    @abstractmethod
    async def list_executions(
        self,
        workflow_id: str,
        state_filter: Optional[WorkflowState] = None,
    ) -> List[str]:
        """List all execution IDs for a workflow."""
        ...


# =============================================================================
# NODE INTERFACES
# =============================================================================


@runtime_checkable
class INode(Protocol):
    """
    Interface for workflow nodes.
    
    A node represents a single step or action in a workflow. Nodes can be
    agents, tools, decision points, or any custom processor.
    """
    
    @property
    @abstractmethod
    def id(self) -> str:
        """Get the unique node ID."""
        ...
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Get the human-readable node name."""
        ...
    
    @property
    @abstractmethod
    def node_type(self) -> NodeType:
        """Get the type of this node."""
        ...
    
    @property
    @abstractmethod
    def config(self) -> Dict[str, Any]:
        """Get the node configuration."""
        ...
    
    @property
    @abstractmethod
    def metadata(self) -> Dict[str, Any]:
        """Get node metadata (description, tags, etc.)."""
        ...
    
    @abstractmethod
    async def execute(
        self,
        input_data: Any,
        context: IWorkflowContext,
    ) -> Any:
        """
        Execute the node with given input and context.
        
        Args:
            input_data: Input data from previous node(s) or workflow input.
            context: Workflow execution context.
            
        Returns:
            The output of node execution.
        """
        ...
    
    @abstractmethod
    async def validate(self, context: IWorkflowContext) -> List[str]:
        """
        Validate node configuration.
        
        Args:
            context: Workflow execution context.
            
        Returns:
            List of validation error messages (empty if valid).
        """
        ...
    
    @abstractmethod
    def get_required_inputs(self) -> List[str]:
        """Get list of required input keys for this node."""
        ...
    
    @abstractmethod
    def get_output_schema(self) -> Optional[Dict[str, Any]]:
        """Get JSON schema for node output (if defined)."""
        ...
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Serialize node to dictionary."""
        ...


@runtime_checkable
class INodeExecutor(Protocol):
    """
    Interface for custom node executors.
    
    Allows plugging in custom execution logic for nodes.
    """
    
    @abstractmethod
    async def execute(
        self,
        node: INode,
        input_data: Any,
        context: IWorkflowContext,
    ) -> Any:
        """Execute a node with custom logic."""
        ...
    
    @abstractmethod
    def supports(self, node_type: NodeType) -> bool:
        """Check if this executor supports the given node type."""
        ...


@runtime_checkable
class INodeValidator(Protocol):
    """Interface for custom node validators."""
    
    @abstractmethod
    def validate(
        self,
        node: INode,
        context: IWorkflowContext,
    ) -> List[str]:
        """Validate a node, returning list of error messages."""
        ...
    
    @abstractmethod
    def supports(self, node_type: NodeType) -> bool:
        """Check if this validator supports the given node type."""
        ...


# =============================================================================
# EDGE INTERFACES
# =============================================================================


@runtime_checkable
class ICondition(Protocol):
    """
    Interface for edge conditions.
    
    Conditions determine whether an edge should be followed based on
    the current context and node outputs.
    """
    
    @property
    @abstractmethod
    def operator(self) -> ConditionOperator:
        """Get the condition operator."""
        ...
    
    @property
    @abstractmethod
    def field(self) -> str:
        """Get the field/variable to evaluate."""
        ...
    
    @property
    @abstractmethod
    def value(self) -> Any:
        """Get the comparison value."""
        ...
    
    @abstractmethod
    def evaluate(self, context: IWorkflowContext) -> bool:
        """Evaluate the condition against the context."""
        ...
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Serialize condition to dictionary."""
        ...


@runtime_checkable
class IConditionEvaluator(Protocol):
    """Interface for custom condition evaluation logic."""
    
    @abstractmethod
    def evaluate(
        self,
        condition: ICondition,
        context: IWorkflowContext,
    ) -> bool:
        """Evaluate a condition."""
        ...
    
    @abstractmethod
    def supports(self, operator: ConditionOperator) -> bool:
        """Check if this evaluator supports the given operator."""
        ...


@runtime_checkable
class IDataTransformer(Protocol):
    """
    Interface for data transformations between nodes.
    
    Transformers modify the output of one node before it becomes
    the input of the next node.
    """
    
    @property
    @abstractmethod
    def transform_type(self) -> DataTransformType:
        """Get the type of transformation."""
        ...
    
    @property
    @abstractmethod
    def config(self) -> Dict[str, Any]:
        """Get transformation configuration."""
        ...
    
    @abstractmethod
    async def transform(
        self,
        data: Any,
        context: IWorkflowContext,
    ) -> Any:
        """Transform the data."""
        ...
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Serialize transformer to dictionary."""
        ...


@runtime_checkable
class IEdge(Protocol):
    """
    Interface for workflow edges.
    
    An edge connects two nodes and can have conditions, transformations,
    and various behaviors like fallback or error handling.
    """
    
    @property
    @abstractmethod
    def id(self) -> str:
        """Get the unique edge ID."""
        ...
    
    @property
    @abstractmethod
    def source_id(self) -> str:
        """Get the source node ID."""
        ...
    
    @property
    @abstractmethod
    def target_id(self) -> str:
        """Get the target node ID."""
        ...
    
    @property
    @abstractmethod
    def edge_type(self) -> EdgeType:
        """Get the type of this edge."""
        ...
    
    @property
    @abstractmethod
    def conditions(self) -> List[ICondition]:
        """Get the conditions for this edge (AND logic)."""
        ...
    
    @property
    @abstractmethod
    def transformer(self) -> Optional[IDataTransformer]:
        """Get the data transformer for this edge (if any)."""
        ...
    
    @property
    @abstractmethod
    def priority(self) -> int:
        """Get the edge priority (higher = checked first)."""
        ...
    
    @property
    @abstractmethod
    def metadata(self) -> Dict[str, Any]:
        """Get edge metadata."""
        ...
    
    @abstractmethod
    def can_traverse(self, context: IWorkflowContext) -> bool:
        """Check if this edge can be traversed given current context."""
        ...
    
    @abstractmethod
    async def transform_data(
        self,
        data: Any,
        context: IWorkflowContext,
    ) -> Any:
        """Apply transformation to data passing through this edge."""
        ...
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Serialize edge to dictionary."""
        ...


# =============================================================================
# ROUTER INTERFACE
# =============================================================================


@runtime_checkable
class IRouter(Protocol):
    """
    Interface for workflow routing logic.
    
    The router determines which node(s) to execute next based on
    the current node, context, and available edges.
    """
    
    @property
    @abstractmethod
    def strategy(self) -> RoutingStrategy:
        """Get the routing strategy."""
        ...
    
    @abstractmethod
    async def get_next_nodes(
        self,
        current_node_id: str,
        context: IWorkflowContext,
        edges: List[IEdge],
    ) -> List[Tuple[str, Optional[IEdge]]]:
        """
        Determine the next node(s) to execute.
        
        Args:
            current_node_id: ID of the current node.
            context: Workflow execution context.
            edges: List of outgoing edges from current node.
            
        Returns:
            List of (target_node_id, edge) tuples for nodes to execute next.
            Edge can be None for direct routing.
        """
        ...
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Serialize router configuration to dictionary."""
        ...


# =============================================================================
# WORKFLOW INTERFACES
# =============================================================================


@runtime_checkable
class IWorkflow(Protocol):
    """
    Interface for workflows.
    
    A workflow is a directed graph of nodes connected by edges,
    representing a complete process or pipeline.
    """
    
    @property
    @abstractmethod
    def id(self) -> str:
        """Get the workflow ID."""
        ...
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Get the workflow name."""
        ...
    
    @property
    @abstractmethod
    def version(self) -> str:
        """Get the workflow version."""
        ...
    
    @property
    @abstractmethod
    def description(self) -> Optional[str]:
        """Get the workflow description."""
        ...
    
    @property
    @abstractmethod
    def nodes(self) -> Dict[str, INode]:
        """Get all nodes in the workflow."""
        ...
    
    @property
    @abstractmethod
    def edges(self) -> List[IEdge]:
        """Get all edges in the workflow."""
        ...
    
    @property
    @abstractmethod
    def start_node_id(self) -> str:
        """Get the ID of the start node."""
        ...
    
    @property
    @abstractmethod
    def end_node_ids(self) -> Set[str]:
        """Get the IDs of all end nodes."""
        ...
    
    @property
    @abstractmethod
    def router(self) -> IRouter:
        """Get the workflow router."""
        ...
    
    @property
    @abstractmethod
    def metadata(self) -> Dict[str, Any]:
        """Get workflow metadata."""
        ...
    
    @abstractmethod
    def get_node(self, node_id: str) -> Optional[INode]:
        """Get a node by ID."""
        ...
    
    @abstractmethod
    def get_outgoing_edges(self, node_id: str) -> List[IEdge]:
        """Get all outgoing edges from a node."""
        ...
    
    @abstractmethod
    def get_incoming_edges(self, node_id: str) -> List[IEdge]:
        """Get all incoming edges to a node."""
        ...
    
    @abstractmethod
    def validate(self) -> List[str]:
        """Validate the workflow structure."""
        ...
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Serialize workflow to dictionary."""
        ...


@runtime_checkable
class IWorkflowExecutor(Protocol):
    """
    Interface for workflow execution engines.
    
    The executor manages the lifecycle of workflow execution,
    including node orchestration, error handling, and state management.
    """
    
    @abstractmethod
    async def execute(
        self,
        workflow: IWorkflow,
        input_data: Any,
        context: Optional[IWorkflowContext] = None,
    ) -> Tuple[Any, IWorkflowContext]:
        """
        Execute a workflow to completion.
        
        Args:
            workflow: The workflow to execute.
            input_data: Initial input data.
            context: Optional pre-configured context.
            
        Returns:
            Tuple of (final_output, final_context).
        """
        ...
    
    @abstractmethod
    async def execute_streaming(
        self,
        workflow: IWorkflow,
        input_data: Any,
        context: Optional[IWorkflowContext] = None,
    ) -> AsyncIterator[Tuple[str, Any, IWorkflowContext]]:
        """
        Execute a workflow with streaming output.
        
        Yields:
            Tuples of (node_id, node_output, current_context).
        """
        ...
    
    @abstractmethod
    async def pause(self, execution_id: str) -> bool:
        """Pause a running workflow execution."""
        ...
    
    @abstractmethod
    async def resume(
        self,
        execution_id: str,
        input_data: Optional[Any] = None,
    ) -> Tuple[Any, IWorkflowContext]:
        """Resume a paused workflow execution."""
        ...
    
    @abstractmethod
    async def cancel(self, execution_id: str) -> bool:
        """Cancel a running workflow execution."""
        ...
    
    @abstractmethod
    async def get_status(self, execution_id: str) -> Optional[WorkflowState]:
        """Get the current status of a workflow execution."""
        ...


@runtime_checkable
class IWorkflowValidator(Protocol):
    """Interface for custom workflow validators."""
    
    @abstractmethod
    def validate(self, workflow: IWorkflow) -> List[str]:
        """Validate a workflow, returning list of error messages."""
        ...


# =============================================================================
# OBSERVER INTERFACES
# =============================================================================


@runtime_checkable
class INodeObserver(Protocol):
    """
    Interface for observing node execution events.
    
    Allows hooking into node lifecycle for logging, metrics, etc.
    """
    
    @abstractmethod
    async def on_node_start(
        self,
        node: INode,
        input_data: Any,
        context: IWorkflowContext,
    ) -> None:
        """Called before node execution starts."""
        ...
    
    @abstractmethod
    async def on_node_complete(
        self,
        node: INode,
        output: Any,
        context: IWorkflowContext,
        duration_ms: float,
    ) -> None:
        """Called after node execution completes."""
        ...
    
    @abstractmethod
    async def on_node_error(
        self,
        node: INode,
        error: Exception,
        context: IWorkflowContext,
    ) -> None:
        """Called when node execution fails."""
        ...
    
    @abstractmethod
    async def on_node_skip(
        self,
        node: INode,
        reason: str,
        context: IWorkflowContext,
    ) -> None:
        """Called when a node is skipped."""
        ...


@runtime_checkable
class IWorkflowObserver(Protocol):
    """
    Interface for observing workflow execution events.
    
    Allows hooking into workflow lifecycle for logging, metrics, etc.
    """
    
    @abstractmethod
    async def on_workflow_start(
        self,
        workflow: IWorkflow,
        input_data: Any,
        context: IWorkflowContext,
    ) -> None:
        """Called before workflow execution starts."""
        ...
    
    @abstractmethod
    async def on_workflow_complete(
        self,
        workflow: IWorkflow,
        output: Any,
        context: IWorkflowContext,
        duration_ms: float,
    ) -> None:
        """Called after workflow execution completes."""
        ...
    
    @abstractmethod
    async def on_workflow_error(
        self,
        workflow: IWorkflow,
        error: Exception,
        context: IWorkflowContext,
    ) -> None:
        """Called when workflow execution fails."""
        ...
    
    @abstractmethod
    async def on_workflow_pause(
        self,
        workflow: IWorkflow,
        context: IWorkflowContext,
    ) -> None:
        """Called when workflow is paused."""
        ...
    
    @abstractmethod
    async def on_workflow_resume(
        self,
        workflow: IWorkflow,
        context: IWorkflowContext,
    ) -> None:
        """Called when workflow is resumed."""
        ...
    
    @abstractmethod
    async def on_workflow_cancel(
        self,
        workflow: IWorkflow,
        context: IWorkflowContext,
    ) -> None:
        """Called when workflow is cancelled."""
        ...


# =============================================================================
# TRIGGER INTERFACES
# =============================================================================


@runtime_checkable
class ITrigger(Protocol):
    """
    Interface for workflow triggers.
    
    Triggers define how and when a workflow should be started.
    """
    
    @property
    @abstractmethod
    def id(self) -> str:
        """Get the trigger ID."""
        ...
    
    @property
    @abstractmethod
    def trigger_type(self) -> TriggerType:
        """Get the type of trigger."""
        ...
    
    @property
    @abstractmethod
    def config(self) -> Dict[str, Any]:
        """Get trigger configuration."""
        ...
    
    @abstractmethod
    async def is_active(self) -> bool:
        """Check if the trigger is currently active."""
        ...
    
    @abstractmethod
    async def activate(self) -> None:
        """Activate the trigger."""
        ...
    
    @abstractmethod
    async def deactivate(self) -> None:
        """Deactivate the trigger."""
        ...
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Serialize trigger to dictionary."""
        ...


@runtime_checkable
class ITriggerHandler(Protocol):
    """Interface for handling trigger events."""
    
    @abstractmethod
    async def handle(
        self,
        trigger: ITrigger,
        event_data: Any,
    ) -> Optional[Tuple[str, Any]]:
        """
        Handle a trigger event.
        
        Args:
            trigger: The trigger that fired.
            event_data: Data from the trigger event.
            
        Returns:
            Tuple of (workflow_id, input_data) to execute, or None to skip.
        """
        ...


# =============================================================================
# SERIALIZATION INTERFACES
# =============================================================================


@runtime_checkable
class INodeSerializer(Protocol):
    """Interface for custom node serialization."""
    
    @abstractmethod
    def serialize(self, node: INode) -> Dict[str, Any]:
        """Serialize a node to dictionary."""
        ...
    
    @abstractmethod
    def deserialize(self, data: Dict[str, Any]) -> INode:
        """Deserialize a node from dictionary."""
        ...
    
    @abstractmethod
    def supports(self, node_type: NodeType) -> bool:
        """Check if this serializer supports the given node type."""
        ...


@runtime_checkable
class IWorkflowSerializer(Protocol):
    """Interface for workflow serialization."""
    
    @abstractmethod
    def serialize(self, workflow: IWorkflow) -> Dict[str, Any]:
        """Serialize a workflow to dictionary."""
        ...
    
    @abstractmethod
    def deserialize(self, data: Dict[str, Any]) -> IWorkflow:
        """Deserialize a workflow from dictionary."""
        ...
    
    @abstractmethod
    def to_json(self, workflow: IWorkflow) -> str:
        """Serialize workflow to JSON string."""
        ...
    
    @abstractmethod
    def from_json(self, json_str: str) -> IWorkflow:
        """Deserialize workflow from JSON string."""
        ...

