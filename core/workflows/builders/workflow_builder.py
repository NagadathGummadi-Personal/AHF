"""
Workflow Builder Module.

This module provides a fluent builder API for constructing workflows.
"""

import logging
import uuid
from typing import Any, Callable, Dict, List, Optional, Type

from ..interfaces import IWorkflow, INode, IEdge, IRouter, IWorkflowObserver, INodeObserver
from ..enum import NodeType, EdgeType, RoutingStrategy
from ..spec import (
    WorkflowSpec,
    NodeSpec,
    EdgeSpec,
    ConditionSpec,
    TransformSpec,
    WorkflowMetadata,
)
from ..nodes import NodeFactory
from ..edges import EdgeFactory
from ..implementations import Workflow
from ..exceptions import WorkflowBuildError

logger = logging.getLogger(__name__)


class WorkflowBuilder:
    """
    Fluent builder for creating workflows.
    
    Example:
        workflow = (
            WorkflowBuilder()
            .with_name("My Workflow")
            .with_description("Does something useful")
            .add_node("start", NodeType.START, name="Begin")
            .add_node("process", NodeType.AGENT, config={"agent_id": "my_agent"})
            .add_node("end", NodeType.END, name="Finish")
            .add_edge("start", "process")
            .add_edge("process", "end")
            .build()
        )
    """
    
    def __init__(self):
        """Initialize the workflow builder."""
        self._id: Optional[str] = None
        self._name: Optional[str] = None
        self._description: Optional[str] = None
        self._version: str = "1.0.0"
        self._routing_strategy: RoutingStrategy = RoutingStrategy.FIRST_MATCH
        
        self._node_specs: List[NodeSpec] = []
        self._edge_specs: List[EdgeSpec] = []
        
        self._node_instances: Dict[str, INode] = {}
        self._edge_instances: List[IEdge] = []
        
        self._start_node_id: Optional[str] = None
        self._end_node_ids: List[str] = []
        
        self._router: Optional[IRouter] = None
        self._metadata: Dict[str, Any] = {}
        
        self._max_iterations: int = 100
        self._timeout_seconds: float = 3600
    
    def with_id(self, workflow_id: str) -> "WorkflowBuilder":
        """Set the workflow ID."""
        self._id = workflow_id
        return self
    
    def with_name(self, name: str) -> "WorkflowBuilder":
        """Set the workflow name."""
        self._name = name
        return self
    
    def with_description(self, description: str) -> "WorkflowBuilder":
        """Set the workflow description."""
        self._description = description
        return self
    
    def with_version(self, version: str) -> "WorkflowBuilder":
        """Set the workflow version."""
        self._version = version
        return self
    
    def with_routing_strategy(self, strategy: RoutingStrategy) -> "WorkflowBuilder":
        """Set the routing strategy."""
        self._routing_strategy = strategy
        return self
    
    def with_router(self, router: IRouter) -> "WorkflowBuilder":
        """Set a custom router."""
        self._router = router
        return self
    
    def with_metadata(self, **kwargs) -> "WorkflowBuilder":
        """Add metadata to the workflow."""
        self._metadata.update(kwargs)
        return self
    
    def with_max_iterations(self, max_iterations: int) -> "WorkflowBuilder":
        """Set maximum iterations."""
        self._max_iterations = max_iterations
        return self
    
    def with_timeout(self, timeout_seconds: float) -> "WorkflowBuilder":
        """Set execution timeout."""
        self._timeout_seconds = timeout_seconds
        return self
    
    def add_node(
        self,
        node_id: str,
        node_type: NodeType,
        name: Optional[str] = None,
        description: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> "WorkflowBuilder":
        """
        Add a node to the workflow.
        
        Args:
            node_id: Unique node identifier.
            node_type: Type of node.
            name: Human-readable name (defaults to node_id).
            description: Node description.
            config: Node-specific configuration.
            **kwargs: Additional NodeSpec fields.
        
        Returns:
            Self for chaining.
        """
        spec = NodeSpec(
            id=node_id,
            name=name or node_id,
            node_type=node_type,
            description=description,
            config=config or {},
            **kwargs
        )
        
        self._node_specs.append(spec)
        
        # Auto-detect start/end nodes
        if node_type == NodeType.START:
            self._start_node_id = node_id
        elif node_type == NodeType.END:
            self._end_node_ids.append(node_id)
        
        return self
    
    def add_node_instance(self, node_id: str, node: INode) -> "WorkflowBuilder":
        """Add a pre-built node instance."""
        self._node_instances[node_id] = node
        return self
    
    def add_agent_node(
        self,
        node_id: str,
        agent_id: Optional[str] = None,
        agent_config: Optional[Dict[str, Any]] = None,
        name: Optional[str] = None,
        **kwargs
    ) -> "WorkflowBuilder":
        """Convenience method for adding an agent node."""
        config = kwargs.pop("config", {})
        if agent_id:
            config["agent_id"] = agent_id
        if agent_config:
            config["agent_config"] = agent_config
        
        return self.add_node(
            node_id,
            NodeType.AGENT,
            name=name or f"Agent: {agent_id or node_id}",
            config=config,
            **kwargs
        )
    
    def add_tool_node(
        self,
        node_id: str,
        tool_name: str,
        name: Optional[str] = None,
        **kwargs
    ) -> "WorkflowBuilder":
        """Convenience method for adding a tool node."""
        config = kwargs.pop("config", {})
        config["tool_name"] = tool_name
        
        return self.add_node(
            node_id,
            NodeType.TOOL,
            name=name or f"Tool: {tool_name}",
            config=config,
            **kwargs
        )
    
    def add_decision_node(
        self,
        node_id: str,
        conditions: List[Dict[str, Any]],
        name: Optional[str] = None,
        **kwargs
    ) -> "WorkflowBuilder":
        """Convenience method for adding a decision node."""
        config = kwargs.pop("config", {})
        config["conditions"] = conditions
        
        return self.add_node(
            node_id,
            NodeType.DECISION,
            name=name or f"Decision: {node_id}",
            config=config,
            **kwargs
        )
    
    def add_transform_node(
        self,
        node_id: str,
        transform_type: str,
        transform_config: Optional[Dict[str, Any]] = None,
        name: Optional[str] = None,
        **kwargs
    ) -> "WorkflowBuilder":
        """Convenience method for adding a transform node."""
        config = kwargs.pop("config", {})
        config["transform_type"] = transform_type
        if transform_config:
            config.update(transform_config)
        
        return self.add_node(
            node_id,
            NodeType.TRANSFORM,
            name=name or f"Transform: {transform_type}",
            config=config,
            **kwargs
        )
    
    def add_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: EdgeType = EdgeType.DEFAULT,
        conditions: Optional[List[Dict[str, Any]]] = None,
        priority: int = 0,
        **kwargs
    ) -> "WorkflowBuilder":
        """
        Add an edge between nodes.
        
        Args:
            source_id: Source node ID.
            target_id: Target node ID.
            edge_type: Type of edge.
            conditions: Optional list of condition specifications.
            priority: Edge priority (higher = checked first).
            **kwargs: Additional EdgeSpec fields.
        
        Returns:
            Self for chaining.
        """
        edge_id = kwargs.pop("id", f"edge_{source_id}_{target_id}")
        
        condition_specs = []
        if conditions:
            for cond in conditions:
                condition_specs.append(ConditionSpec(**cond))
        
        spec = EdgeSpec(
            id=edge_id,
            source_id=source_id,
            target_id=target_id,
            edge_type=edge_type,
            conditions=condition_specs,
            priority=priority,
            **kwargs
        )
        
        self._edge_specs.append(spec)
        return self
    
    def add_conditional_edge(
        self,
        source_id: str,
        target_id: str,
        field: str,
        operator: str,
        value: Any,
        priority: int = 0,
        **kwargs
    ) -> "WorkflowBuilder":
        """Convenience method for adding a conditional edge."""
        return self.add_edge(
            source_id,
            target_id,
            edge_type=EdgeType.CONDITIONAL,
            conditions=[{
                "field": field,
                "operator": operator,
                "value": value,
            }],
            priority=priority,
            **kwargs
        )
    
    def add_fallback_edge(
        self,
        source_id: str,
        target_id: str,
        **kwargs
    ) -> "WorkflowBuilder":
        """Convenience method for adding a fallback edge."""
        return self.add_edge(
            source_id,
            target_id,
            edge_type=EdgeType.FALLBACK,
            priority=-1000,
            **kwargs
        )
    
    def add_error_edge(
        self,
        source_id: str,
        error_handler_id: str,
        error_types: Optional[List[str]] = None,
        **kwargs
    ) -> "WorkflowBuilder":
        """Convenience method for adding an error handling edge."""
        metadata = kwargs.pop("metadata", {})
        if error_types:
            metadata["error_types"] = error_types
        
        return self.add_edge(
            source_id,
            error_handler_id,
            edge_type=EdgeType.ERROR,
            metadata=metadata,
            **kwargs
        )
    
    def add_edge_instance(self, edge: IEdge) -> "WorkflowBuilder":
        """Add a pre-built edge instance."""
        self._edge_instances.append(edge)
        return self
    
    def set_start_node(self, node_id: str) -> "WorkflowBuilder":
        """Explicitly set the start node."""
        self._start_node_id = node_id
        return self
    
    def add_end_node(self, node_id: str) -> "WorkflowBuilder":
        """Add an end node."""
        if node_id not in self._end_node_ids:
            self._end_node_ids.append(node_id)
        return self
    
    def validate(self) -> List[str]:
        """Validate the workflow configuration."""
        errors = []
        
        if not self._name:
            errors.append("Workflow name is required")
        
        all_node_ids = {s.id for s in self._node_specs} | set(self._node_instances.keys())
        
        if not all_node_ids:
            errors.append("Workflow must have at least one node")
        
        # Validate edge references
        for spec in self._edge_specs:
            if spec.source_id not in all_node_ids:
                errors.append(f"Edge source not found: {spec.source_id}")
            if spec.target_id not in all_node_ids:
                errors.append(f"Edge target not found: {spec.target_id}")
        
        return errors
    
    def build(self) -> IWorkflow:
        """
        Build the workflow.
        
        Returns:
            Configured workflow instance.
        
        Raises:
            WorkflowBuildError: If validation fails.
        """
        # Validate
        errors = self.validate()
        if errors:
            raise WorkflowBuildError(
                f"Workflow validation failed: {'; '.join(errors)}",
                details={"errors": errors}
            )
        
        # Build nodes
        node_factory = NodeFactory()
        nodes = dict(self._node_instances)
        
        for spec in self._node_specs:
            if spec.id not in nodes:
                try:
                    nodes[spec.id] = node_factory.create(spec)
                except Exception as e:
                    raise WorkflowBuildError(
                        f"Failed to create node {spec.id}: {e}"
                    ) from e
        
        # Build edges
        edge_factory = EdgeFactory()
        edges = list(self._edge_instances)
        
        for spec in self._edge_specs:
            try:
                edges.append(edge_factory.create(spec))
            except Exception as e:
                raise WorkflowBuildError(
                    f"Failed to create edge {spec.id}: {e}"
                ) from e
        
        # Create spec
        spec = WorkflowSpec(
            id=self._id or str(uuid.uuid4()),
            name=self._name,
            version=self._version,
            description=self._description,
            nodes=self._node_specs,
            edges=self._edge_specs,
            start_node_id=self._start_node_id,
            end_node_ids=self._end_node_ids,
            routing_strategy=self._routing_strategy,
            max_iterations=self._max_iterations,
            timeout_seconds=self._timeout_seconds,
        )
        
        # Create workflow
        return Workflow(
            spec=spec,
            nodes=nodes,
            edges=edges,
            router=self._router,
        )
    
    def to_spec(self) -> WorkflowSpec:
        """Export as WorkflowSpec without building."""
        return WorkflowSpec(
            id=self._id or str(uuid.uuid4()),
            name=self._name or "Unnamed Workflow",
            version=self._version,
            description=self._description,
            nodes=self._node_specs,
            edges=self._edge_specs,
            start_node_id=self._start_node_id,
            end_node_ids=self._end_node_ids,
            routing_strategy=self._routing_strategy,
            max_iterations=self._max_iterations,
            timeout_seconds=self._timeout_seconds,
        )



