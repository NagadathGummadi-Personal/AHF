"""
Workflow Specification Models

Defines the complete workflow container that holds nodes and edges.

Version: 1.0.0
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field, PrivateAttr

from ..enum import WorkflowStatus, ExecutionState
from ..defaults import (
    DEFAULT_WORKFLOW_VERSION,
    DEFAULT_STATUS,
    DEFAULT_TIMEOUT_S,
)
from ..constants import (
    ARBITRARY_TYPES_ALLOWED,
    POPULATE_BY_NAME,
    ERROR_VERSION_EXISTS,
    ERROR_NODE_NOT_FOUND,
    ERROR_EDGE_NOT_FOUND,
    ERROR_NO_START_NODE,
    ERROR_CYCLE_DETECTED,
    ERROR_DISCONNECTED_NODES,
)
from .node_models import NodeSpec, NodeResult
from .edge_models import EdgeSpec


class WorkflowMetadata(BaseModel):
    """
    Metadata for a workflow.
    
    Attributes:
        version: Workflow version string
        status: Current status (draft, published, etc.)
        created_at: Creation timestamp
        updated_at: Last update timestamp
        created_by: User who created the workflow
        tags: Tags for categorization
        owner: Owner identifier
        environment: Target environment
        category: Workflow category
    """
    version: str = Field(default=DEFAULT_WORKFLOW_VERSION, description="Workflow version")
    status: WorkflowStatus = Field(default=WorkflowStatus(DEFAULT_STATUS), description="Workflow status")
    created_at: Optional[datetime] = Field(default=None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")
    created_by: Optional[str] = Field(default=None, description="Creator user ID")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    owner: Optional[str] = Field(default=None, description="Owner identifier")
    environment: str = Field(default="dev", description="Target environment")
    category: Optional[str] = Field(default=None, description="Workflow category")


class WorkflowConfig(BaseModel):
    """
    Execution configuration for a workflow.
    
    Attributes:
        timeout_s: Total workflow timeout in seconds
        max_parallel_nodes: Maximum nodes to execute in parallel
        retry_failed_nodes: Whether to retry failed nodes
        stop_on_first_error: Whether to stop on first node error
        enable_checkpoints: Whether to enable execution checkpoints
    """
    timeout_s: int = Field(default=DEFAULT_TIMEOUT_S, description="Workflow timeout in seconds")
    max_parallel_nodes: int = Field(default=5, description="Max parallel node executions")
    retry_failed_nodes: bool = Field(default=True, description="Retry failed nodes")
    stop_on_first_error: bool = Field(default=False, description="Stop on first error")
    enable_checkpoints: bool = Field(default=False, description="Enable execution checkpoints")


class WorkflowSpec(BaseModel):
    """
    Complete specification for a workflow.
    
    A workflow is a directed graph of nodes connected by edges.
    
    Attributes:
        id: Unique identifier
        name: Human-readable name
        description: Workflow description
        
        # Graph structure
        nodes: Dictionary of node ID to NodeSpec
        edges: Dictionary of edge ID to EdgeSpec
        start_node_id: ID of the entry node
        end_node_ids: IDs of exit nodes
        
        # Configuration
        metadata: Workflow metadata
        config: Execution configuration
        
        # Variables
        global_variables: Variables accessible throughout workflow
    """
    # Identity
    id: str = Field(..., description="Unique workflow identifier")
    name: str = Field(..., description="Human-readable name")
    description: str = Field(default="", description="Workflow description")
    
    # Graph structure
    nodes: Dict[str, NodeSpec] = Field(default_factory=dict, description="Node map")
    edges: Dict[str, EdgeSpec] = Field(default_factory=dict, description="Edge map")
    start_node_id: Optional[str] = Field(default=None, description="Entry node ID")
    end_node_ids: List[str] = Field(default_factory=list, description="Exit node IDs")
    
    # Configuration
    metadata: WorkflowMetadata = Field(default_factory=WorkflowMetadata, description="Metadata")
    config: WorkflowConfig = Field(default_factory=WorkflowConfig, description="Configuration")
    
    # Global variables
    global_variables: Dict[str, Any] = Field(
        default_factory=dict,
        description="Variables accessible throughout workflow"
    )
    
    # Additional properties
    properties: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional custom properties"
    )
    
    model_config = {
        ARBITRARY_TYPES_ALLOWED: True,
        POPULATE_BY_NAME: True,
    }
    
    def add_node(self, node: NodeSpec) -> None:
        """Add a node to the workflow."""
        self.nodes[node.id] = node
    
    def remove_node(self, node_id: str) -> None:
        """Remove a node and its connected edges."""
        if node_id not in self.nodes:
            raise ValueError(ERROR_NODE_NOT_FOUND.format(node_id=node_id))
        
        # Remove connected edges
        edges_to_remove = [
            edge_id for edge_id, edge in self.edges.items()
            if edge.source_node_id == node_id or edge.target_node_id == node_id
        ]
        for edge_id in edges_to_remove:
            del self.edges[edge_id]
        
        del self.nodes[node_id]
    
    def add_edge(self, edge: EdgeSpec) -> None:
        """Add an edge to the workflow."""
        # Validate nodes exist
        if edge.source_node_id not in self.nodes:
            raise ValueError(ERROR_NODE_NOT_FOUND.format(node_id=edge.source_node_id))
        if edge.target_node_id not in self.nodes:
            raise ValueError(ERROR_NODE_NOT_FOUND.format(node_id=edge.target_node_id))
        
        self.edges[edge.id] = edge
    
    def remove_edge(self, edge_id: str) -> None:
        """Remove an edge from the workflow."""
        if edge_id not in self.edges:
            raise ValueError(ERROR_EDGE_NOT_FOUND.format(edge_id=edge_id))
        del self.edges[edge_id]
    
    def get_node(self, node_id: str) -> Optional[NodeSpec]:
        """Get a node by ID."""
        return self.nodes.get(node_id)
    
    def get_edge(self, edge_id: str) -> Optional[EdgeSpec]:
        """Get an edge by ID."""
        return self.edges.get(edge_id)
    
    def get_outgoing_edges(self, node_id: str) -> List[EdgeSpec]:
        """Get all edges originating from a node."""
        return [
            edge for edge in self.edges.values()
            if edge.source_node_id == node_id
        ]
    
    def get_incoming_edges(self, node_id: str) -> List[EdgeSpec]:
        """Get all edges leading to a node."""
        return [
            edge for edge in self.edges.values()
            if edge.target_node_id == node_id
        ]
    
    def get_next_nodes(self, node_id: str, context: Dict[str, Any]) -> List[str]:
        """
        Get the next node IDs based on edge conditions.
        
        Args:
            node_id: Current node ID
            context: Workflow context for condition evaluation
            
        Returns:
            List of next node IDs that should be traversed
        """
        outgoing = self.get_outgoing_edges(node_id)
        
        # Sort by priority
        outgoing.sort(key=lambda e: e.config.priority)
        
        next_nodes = []
        for edge in outgoing:
            if edge.should_traverse(context):
                next_nodes.append(edge.target_node_id)
        
        return next_nodes
    
    def validate(self) -> List[str]:
        """
        Validate the workflow structure.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Check for start node
        if not self.start_node_id:
            errors.append(ERROR_NO_START_NODE)
        elif self.start_node_id not in self.nodes:
            errors.append(ERROR_NODE_NOT_FOUND.format(node_id=self.start_node_id))
        
        # Check for cycles (simple DFS)
        if self._has_cycle():
            errors.append(ERROR_CYCLE_DETECTED)
        
        # Check for disconnected nodes
        disconnected = self._find_disconnected_nodes()
        if disconnected:
            errors.append(ERROR_DISCONNECTED_NODES.format(nodes=", ".join(disconnected)))
        
        # Validate edges reference existing nodes
        for edge in self.edges.values():
            if edge.source_node_id not in self.nodes:
                errors.append(ERROR_NODE_NOT_FOUND.format(node_id=edge.source_node_id))
            if edge.target_node_id not in self.nodes:
                errors.append(ERROR_NODE_NOT_FOUND.format(node_id=edge.target_node_id))
        
        return errors
    
    def _has_cycle(self) -> bool:
        """Check if the workflow graph has cycles."""
        if not self.start_node_id:
            return False
        
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        
        def dfs(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)
            
            for edge in self.get_outgoing_edges(node_id):
                next_id = edge.target_node_id
                if next_id not in visited:
                    if dfs(next_id):
                        return True
                elif next_id in rec_stack:
                    return True
            
            rec_stack.remove(node_id)
            return False
        
        return dfs(self.start_node_id)
    
    def _find_disconnected_nodes(self) -> Set[str]:
        """Find nodes not reachable from start node."""
        if not self.start_node_id:
            return set(self.nodes.keys())
        
        visited: Set[str] = set()
        
        def dfs(node_id: str) -> None:
            if node_id in visited:
                return
            visited.add(node_id)
            for edge in self.get_outgoing_edges(node_id):
                dfs(edge.target_node_id)
        
        dfs(self.start_node_id)
        
        return set(self.nodes.keys()) - visited
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "nodes": {nid: n.to_dict() for nid, n in self.nodes.items()},
            "edges": {eid: e.to_dict() for eid, e in self.edges.items()},
            "start_node_id": self.start_node_id,
            "end_node_ids": self.end_node_ids,
            "metadata": self.metadata.model_dump(),
            "config": self.config.model_dump(),
            "global_variables": self.global_variables,
            "properties": self.properties,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> WorkflowSpec:
        """Create from dictionary."""
        nodes = {
            nid: NodeSpec.from_dict(n_data)
            for nid, n_data in data.get("nodes", {}).items()
        }
        edges = {
            eid: EdgeSpec.from_dict(e_data)
            for eid, e_data in data.get("edges", {}).items()
        }
        
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            nodes=nodes,
            edges=edges,
            start_node_id=data.get("start_node_id"),
            end_node_ids=data.get("end_node_ids", []),
            metadata=WorkflowMetadata(**data.get("metadata", {})),
            config=WorkflowConfig(**data.get("config", {})),
            global_variables=data.get("global_variables", {}),
            properties=data.get("properties", {}),
        )


class WorkflowVersion(BaseModel):
    """
    A specific version of a workflow.
    
    Versions are immutable once published.
    """
    version: str = Field(..., description="Version string")
    spec: WorkflowSpec = Field(..., description="Workflow specification")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation time")
    is_published: bool = Field(default=False, description="Whether version is published")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "version": self.version,
            "spec": self.spec.to_dict(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_published": self.is_published,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> WorkflowVersion:
        """Create from dictionary."""
        spec_data = data.get("spec", {})
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        return cls(
            version=data["version"],
            spec=WorkflowSpec.from_dict(spec_data),
            created_at=created_at or datetime.utcnow(),
            is_published=data.get("is_published", False),
        )


class WorkflowEntry(BaseModel):
    """
    Entry containing all versions of a workflow.
    """
    id: str = Field(..., description="Workflow ID")
    versions: Dict[str, WorkflowVersion] = Field(default_factory=dict, description="Version map")
    
    _latest_version: str = PrivateAttr(default="")
    
    def model_post_init(self, __context: Any) -> None:
        """Initialize after model creation."""
        if self.versions:
            versions = sorted(self.versions.keys(), key=lambda v: [int(x) for x in v.split(".")])
            self._latest_version = versions[-1] if versions else ""
    
    def get_version(self, version: str) -> Optional[WorkflowVersion]:
        """Get a specific version."""
        return self.versions.get(version)
    
    def get_latest_version(self) -> Optional[str]:
        """Get the latest version string."""
        return self._latest_version or None
    
    def get_latest(self) -> Optional[WorkflowVersion]:
        """Get the latest version entry."""
        if self._latest_version:
            return self.versions.get(self._latest_version)
        return None
    
    def version_exists(self, version: str) -> bool:
        """Check if version exists."""
        return version in self.versions
    
    def add_version(self, workflow_version: WorkflowVersion) -> None:
        """Add a new version."""
        if self.version_exists(workflow_version.version):
            raise ValueError(
                ERROR_VERSION_EXISTS.format(
                    version=workflow_version.version,
                    entity_type="workflow",
                    id=self.id
                )
            )
        self.versions[workflow_version.version] = workflow_version
        
        versions = sorted(self.versions.keys(), key=lambda v: [int(x) for x in v.split(".")])
        self._latest_version = versions[-1]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "versions": {v: wv.to_dict() for v, wv in self.versions.items()},
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> WorkflowEntry:
        """Create from dictionary."""
        versions = {
            v: WorkflowVersion.from_dict(wv_data)
            for v, wv_data in data.get("versions", {}).items()
        }
        return cls(id=data["id"], versions=versions)


class WorkflowExecutionContext(BaseModel):
    """
    Context for workflow execution.
    
    Holds the current state and variables during execution.
    """
    workflow_id: str = Field(..., description="Workflow being executed")
    execution_id: str = Field(..., description="Unique execution ID")
    current_node_id: Optional[str] = Field(default=None, description="Currently executing node")
    state: ExecutionState = Field(default=ExecutionState.IDLE, description="Execution state")
    
    # Variables
    variables: Dict[str, Any] = Field(default_factory=dict, description="Workflow variables")
    node_outputs: Dict[str, NodeResult] = Field(
        default_factory=dict,
        description="Results from executed nodes"
    )
    
    # Tracking
    executed_nodes: List[str] = Field(default_factory=list, description="Nodes already executed")
    execution_path: List[str] = Field(default_factory=list, description="Path taken through workflow")
    start_time: Optional[datetime] = Field(default=None, description="Execution start time")
    end_time: Optional[datetime] = Field(default=None, description="Execution end time")
    
    # Error tracking
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="Errors encountered")
    
    model_config = {ARBITRARY_TYPES_ALLOWED: True}
    
    def get_variable(self, name: str, default: Any = None) -> Any:
        """Get a variable value."""
        return self.variables.get(name, default)
    
    def set_variable(self, name: str, value: Any) -> None:
        """Set a variable value."""
        self.variables[name] = value
    
    def record_node_result(self, node_id: str, result: NodeResult) -> None:
        """Record the result of a node execution."""
        self.node_outputs[node_id] = result
        self.executed_nodes.append(node_id)
        self.execution_path.append(node_id)
    
    def get_context_for_conditions(self) -> Dict[str, Any]:
        """Get context dictionary for edge condition evaluation."""
        return {
            "variables": self.variables,
            "outputs": {nid: nr.model_dump() for nid, nr in self.node_outputs.items()},
            "current_node": self.current_node_id,
            "_error": self.state == ExecutionState.FAILED,
            "_timeout": self.state == ExecutionState.TIMEOUT,
        }


class WorkflowResult(BaseModel):
    """
    Result of workflow execution.
    """
    workflow_id: str = Field(..., description="Workflow ID")
    execution_id: str = Field(..., description="Execution ID")
    success: bool = Field(default=True, description="Whether execution succeeded")
    state: ExecutionState = Field(default=ExecutionState.COMPLETED, description="Final state")
    
    # Output
    output: Any = Field(default=None, description="Final output")
    final_variables: Dict[str, Any] = Field(default_factory=dict, description="Final variables")
    
    # Execution details
    execution_path: List[str] = Field(default_factory=list, description="Nodes executed")
    node_results: Dict[str, NodeResult] = Field(default_factory=dict, description="Results by node")
    
    # Timing
    total_time_ms: float = Field(default=0.0, description="Total execution time")
    
    # Errors
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="Errors encountered")
    
    model_config = {ARBITRARY_TYPES_ALLOWED: True}
