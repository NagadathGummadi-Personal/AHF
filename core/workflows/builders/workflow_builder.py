"""
Workflow Builder

Fluent builder for creating complete workflows.

Version: 1.0.0
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..spec.node_models import NodeSpec
from ..spec.edge_models import EdgeSpec
from ..spec.workflow_models import (
    WorkflowSpec,
    WorkflowMetadata,
    WorkflowConfig,
)
from ..enum import WorkflowStatus
from ..defaults import DEFAULT_WORKFLOW_VERSION


class WorkflowBuilder:
    """
    Fluent builder for creating WorkflowSpec instances.
    
    Usage:
        # Build a simple workflow
        workflow = (WorkflowBuilder()
            .with_id("chat-flow")
            .with_name("Chat Flow")
            .with_description("A simple chat workflow")
            .add_node(greeting_node)
            .add_node(response_node)
            .add_node(end_node)
            .connect("greeting-node", "response-node")
            .connect("response-node", "end-node")
            .set_start_node("greeting-node")
            .set_end_nodes(["end-node"])
            .build())
        
        # Build with conditional routing
        workflow = (WorkflowBuilder()
            .with_id("support-flow")
            .add_node(router_node)
            .add_node(technical_node)
            .add_node(billing_node)
            .connect_conditional(
                "router-node", "technical-node",
                field="intent", operator=ConditionOperator.EQUALS, value="technical"
            )
            .connect_conditional(
                "router-node", "billing-node",
                field="intent", operator=ConditionOperator.EQUALS, value="billing"
            )
            .set_start_node("router-node")
            .build())
    """
    
    def __init__(self):
        """Initialize the builder."""
        self._id: Optional[str] = None
        self._name: Optional[str] = None
        self._description: str = ""
        
        # Graph
        self._nodes: Dict[str, NodeSpec] = {}
        self._edges: Dict[str, EdgeSpec] = {}
        self._start_node_id: Optional[str] = None
        self._end_node_ids: List[str] = []
        
        # Metadata
        self._version: str = DEFAULT_WORKFLOW_VERSION
        self._status: WorkflowStatus = WorkflowStatus.DRAFT
        self._tags: List[str] = []
        self._owner: Optional[str] = None
        self._environment: str = "dev"
        self._category: Optional[str] = None
        
        # Config
        self._timeout_s: int = 300
        self._max_parallel_nodes: int = 5
        self._retry_failed_nodes: bool = True
        self._stop_on_first_error: bool = False
        self._enable_checkpoints: bool = False
        
        # Variables
        self._global_variables: Dict[str, Any] = {}
        
        # Edge counter for auto-generated IDs
        self._edge_counter: int = 0
        
        # Additional properties
        self._properties: Dict[str, Any] = {}
    
    def with_id(self, workflow_id: str) -> WorkflowBuilder:
        """Set the workflow ID."""
        self._id = workflow_id
        return self
    
    def with_name(self, name: str) -> WorkflowBuilder:
        """Set the workflow name."""
        self._name = name
        return self
    
    def with_description(self, description: str) -> WorkflowBuilder:
        """Set the workflow description."""
        self._description = description
        return self
    
    # =========================================================================
    # Node methods
    # =========================================================================
    
    def add_node(self, node: NodeSpec) -> WorkflowBuilder:
        """Add a node to the workflow."""
        self._nodes[node.id] = node
        return self
    
    def add_nodes(self, nodes: List[NodeSpec]) -> WorkflowBuilder:
        """Add multiple nodes."""
        for node in nodes:
            self.add_node(node)
        return self
    
    def remove_node(self, node_id: str) -> WorkflowBuilder:
        """Remove a node."""
        self._nodes.pop(node_id, None)
        # Also remove connected edges
        edges_to_remove = [
            eid for eid, edge in self._edges.items()
            if edge.source_node_id == node_id or edge.target_node_id == node_id
        ]
        for eid in edges_to_remove:
            self._edges.pop(eid)
        return self
    
    def set_start_node(self, node_id: str) -> WorkflowBuilder:
        """Set the start node."""
        self._start_node_id = node_id
        return self
    
    def set_end_nodes(self, node_ids: List[str]) -> WorkflowBuilder:
        """Set the end nodes."""
        self._end_node_ids = node_ids
        return self
    
    def add_end_node(self, node_id: str) -> WorkflowBuilder:
        """Add an end node."""
        if node_id not in self._end_node_ids:
            self._end_node_ids.append(node_id)
        return self
    
    # =========================================================================
    # Edge methods
    # =========================================================================
    
    def add_edge(self, edge: EdgeSpec) -> WorkflowBuilder:
        """Add a pre-built edge."""
        self._edges[edge.id] = edge
        return self
    
    def connect(
        self,
        from_node: str,
        to_node: str,
        edge_id: Optional[str] = None
    ) -> WorkflowBuilder:
        """
        Create a simple default connection between nodes.
        
        Args:
            from_node: Source node ID
            to_node: Target node ID
            edge_id: Optional edge ID (auto-generated if not provided)
        """
        from .edge_builder import EdgeBuilder
        
        if not edge_id:
            self._edge_counter += 1
            edge_id = f"edge-{self._edge_counter}"
        
        edge = (EdgeBuilder()
            .with_id(edge_id)
            .from_node(from_node)
            .to_node(to_node)
            .as_default()
            .build())
        
        self._edges[edge.id] = edge
        return self
    
    def connect_conditional(
        self,
        from_node: str,
        to_node: str,
        field: str,
        operator: Any,  # ConditionOperator
        value: Any,
        edge_id: Optional[str] = None
    ) -> WorkflowBuilder:
        """
        Create a conditional connection.
        
        Args:
            from_node: Source node ID
            to_node: Target node ID
            field: Field to evaluate
            operator: Condition operator
            value: Value to compare against
            edge_id: Optional edge ID
        """
        from .edge_builder import EdgeBuilder
        
        if not edge_id:
            self._edge_counter += 1
            edge_id = f"edge-{self._edge_counter}"
        
        edge = (EdgeBuilder()
            .with_id(edge_id)
            .from_node(from_node)
            .to_node(to_node)
            .as_conditional()
            .with_condition(field, operator, value)
            .build())
        
        self._edges[edge.id] = edge
        return self
    
    def connect_error(
        self,
        from_node: str,
        to_node: str,
        edge_id: Optional[str] = None
    ) -> WorkflowBuilder:
        """Create an error handling connection."""
        from .edge_builder import EdgeBuilder
        
        if not edge_id:
            self._edge_counter += 1
            edge_id = f"edge-{self._edge_counter}"
        
        edge = (EdgeBuilder()
            .with_id(edge_id)
            .from_node(from_node)
            .to_node(to_node)
            .as_error_handler()
            .build())
        
        self._edges[edge.id] = edge
        return self
    
    # =========================================================================
    # Metadata methods
    # =========================================================================
    
    def with_version(self, version: str) -> WorkflowBuilder:
        """Set the version."""
        self._version = version
        return self
    
    def with_status(self, status: WorkflowStatus) -> WorkflowBuilder:
        """Set the status."""
        self._status = status
        return self
    
    def with_tags(self, tags: List[str]) -> WorkflowBuilder:
        """Set tags (replaces existing)."""
        self._tags = tags
        return self
    
    def with_tag(self, tag: str) -> WorkflowBuilder:
        """Add a single tag."""
        self._tags.append(tag)
        return self
    
    def with_owner(self, owner: str) -> WorkflowBuilder:
        """Set the owner."""
        self._owner = owner
        return self
    
    def with_environment(self, environment: str) -> WorkflowBuilder:
        """Set the target environment."""
        self._environment = environment
        return self
    
    def with_category(self, category: str) -> WorkflowBuilder:
        """Set the category."""
        self._category = category
        return self
    
    # =========================================================================
    # Config methods
    # =========================================================================
    
    def with_timeout(self, timeout_s: int) -> WorkflowBuilder:
        """Set workflow timeout."""
        self._timeout_s = timeout_s
        return self
    
    def with_max_parallel_nodes(self, max_parallel: int) -> WorkflowBuilder:
        """Set max parallel node executions."""
        self._max_parallel_nodes = max_parallel
        return self
    
    def with_retry_on_failure(self, enabled: bool = True) -> WorkflowBuilder:
        """Enable/disable retry on failed nodes."""
        self._retry_failed_nodes = enabled
        return self
    
    def with_stop_on_error(self, enabled: bool = True) -> WorkflowBuilder:
        """Enable/disable stopping on first error."""
        self._stop_on_first_error = enabled
        return self
    
    def with_checkpoints(self, enabled: bool = True) -> WorkflowBuilder:
        """Enable/disable execution checkpoints."""
        self._enable_checkpoints = enabled
        return self
    
    # =========================================================================
    # Variable methods
    # =========================================================================
    
    def with_variable(self, name: str, value: Any) -> WorkflowBuilder:
        """Add a global variable."""
        self._global_variables[name] = value
        return self
    
    def with_variables(self, variables: Dict[str, Any]) -> WorkflowBuilder:
        """Add multiple global variables."""
        self._global_variables.update(variables)
        return self
    
    # =========================================================================
    # Build method
    # =========================================================================
    
    def build(self) -> WorkflowSpec:
        """
        Build the WorkflowSpec.
        
        Raises:
            ValueError: If required fields are missing
        """
        if not self._id:
            raise ValueError("Workflow ID is required")
        if not self._name:
            raise ValueError("Workflow name is required")
        
        # Build metadata
        metadata = WorkflowMetadata(
            version=self._version,
            status=self._status,
            tags=self._tags,
            owner=self._owner,
            environment=self._environment,
            category=self._category,
        )
        
        # Build config
        config = WorkflowConfig(
            timeout_s=self._timeout_s,
            max_parallel_nodes=self._max_parallel_nodes,
            retry_failed_nodes=self._retry_failed_nodes,
            stop_on_first_error=self._stop_on_first_error,
            enable_checkpoints=self._enable_checkpoints,
        )
        
        return WorkflowSpec(
            id=self._id,
            name=self._name,
            description=self._description,
            nodes=self._nodes,
            edges=self._edges,
            start_node_id=self._start_node_id,
            end_node_ids=self._end_node_ids,
            metadata=metadata,
            config=config,
            global_variables=self._global_variables,
            properties=self._properties,
        )
