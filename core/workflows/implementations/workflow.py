"""
Workflow Implementation Module.

This module provides the main Workflow class implementation.
"""

import logging
from typing import Any, Dict, List, Optional, Set

from ..interfaces import IWorkflow, INode, IEdge, IRouter
from ..enum import WorkflowState, RoutingStrategy
from ..spec import WorkflowSpec, NodeSpec, EdgeSpec
from ..nodes import NodeFactory
from ..edges import EdgeFactory

logger = logging.getLogger(__name__)


class Workflow(IWorkflow):
    """
    Main Workflow implementation.
    
    Represents a complete workflow with nodes, edges, and configuration.
    """
    
    def __init__(
        self,
        spec: WorkflowSpec,
        nodes: Optional[Dict[str, INode]] = None,
        edges: Optional[List[IEdge]] = None,
        router: Optional[IRouter] = None,
    ):
        """
        Initialize the workflow.
        
        Args:
            spec: Workflow specification.
            nodes: Optional pre-built node dictionary.
            edges: Optional pre-built edge list.
            router: Optional custom router.
        """
        self._spec = spec
        self._id = spec.id
        self._name = spec.name
        self._version = spec.version
        self._description = spec.description
        self._metadata = spec.metadata.model_dump() if spec.metadata else {}
        
        # Build nodes if not provided
        if nodes is not None:
            self._nodes = nodes
        else:
            self._nodes = self._build_nodes(spec.nodes)
        
        # Build edges if not provided
        if edges is not None:
            self._edges = edges
        else:
            self._edges = self._build_edges(spec.edges)
        
        # Set router
        if router is not None:
            self._router = router
        else:
            from ..runtimes import DefaultRouter
            self._router = DefaultRouter(spec.routing_strategy)
        
        # Detect start/end nodes
        self._start_node_id = spec.start_node_id or self._detect_start_node()
        self._end_node_ids = set(spec.end_node_ids) if spec.end_node_ids else self._detect_end_nodes()
        
        logger.debug(
            f"Initialized workflow: {self._name} "
            f"({len(self._nodes)} nodes, {len(self._edges)} edges)"
        )
    
    @property
    def id(self) -> str:
        return self._id
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def version(self) -> str:
        return self._version
    
    @property
    def description(self) -> Optional[str]:
        return self._description
    
    @property
    def nodes(self) -> Dict[str, INode]:
        return self._nodes
    
    @property
    def edges(self) -> List[IEdge]:
        return self._edges
    
    @property
    def start_node_id(self) -> str:
        return self._start_node_id
    
    @property
    def end_node_ids(self) -> Set[str]:
        return self._end_node_ids
    
    @property
    def router(self) -> IRouter:
        return self._router
    
    @property
    def metadata(self) -> Dict[str, Any]:
        return self._metadata
    
    def get_node(self, node_id: str) -> Optional[INode]:
        return self._nodes.get(node_id)
    
    def get_outgoing_edges(self, node_id: str) -> List[IEdge]:
        return [e for e in self._edges if e.source_id == node_id]
    
    def get_incoming_edges(self, node_id: str) -> List[IEdge]:
        return [e for e in self._edges if e.target_id == node_id]
    
    def validate(self) -> List[str]:
        """Validate workflow structure."""
        errors = []
        
        # Check start node exists
        if self._start_node_id not in self._nodes:
            errors.append(f"Start node not found: {self._start_node_id}")
        
        # Check end nodes exist
        for end_id in self._end_node_ids:
            if end_id not in self._nodes:
                errors.append(f"End node not found: {end_id}")
        
        # Check edge targets exist
        for edge in self._edges:
            if edge.source_id not in self._nodes:
                errors.append(f"Edge source not found: {edge.source_id}")
            if edge.target_id not in self._nodes:
                errors.append(f"Edge target not found: {edge.target_id}")
        
        # Check for unreachable nodes
        reachable = self._find_reachable_nodes()
        for node_id in self._nodes:
            if node_id not in reachable and node_id != self._start_node_id:
                errors.append(f"Unreachable node: {node_id}")
        
        return errors
    
    def _build_nodes(self, node_specs: List[NodeSpec]) -> Dict[str, INode]:
        """Build nodes from specifications."""
        nodes = {}
        factory = NodeFactory()
        
        for spec in node_specs:
            try:
                node = factory.create(spec)
                nodes[spec.id] = node
            except Exception as e:
                logger.error(f"Failed to build node {spec.id}: {e}")
                raise
        
        return nodes
    
    def _build_edges(self, edge_specs: List[EdgeSpec]) -> List[IEdge]:
        """Build edges from specifications."""
        edges = []
        factory = EdgeFactory()
        
        for spec in edge_specs:
            try:
                edge = factory.create(spec)
                edges.append(edge)
            except Exception as e:
                logger.error(f"Failed to build edge {spec.id}: {e}")
                raise
        
        return edges
    
    def _detect_start_node(self) -> str:
        """Detect the start node (node with no incoming edges)."""
        from ..enum import NodeType
        from ..constants import NODE_ID_START
        
        # Check for explicit start node type
        for node_id, node in self._nodes.items():
            if node.node_type == NodeType.START:
                return node_id
        
        # Find nodes with no incoming edges
        targets = {e.target_id for e in self._edges}
        for node_id in self._nodes:
            if node_id not in targets:
                return node_id
        
        # Default
        return list(self._nodes.keys())[0] if self._nodes else NODE_ID_START
    
    def _detect_end_nodes(self) -> Set[str]:
        """Detect end nodes (nodes with no outgoing edges)."""
        from ..enum import NodeType
        
        end_nodes = set()
        
        # Check for explicit end node type
        for node_id, node in self._nodes.items():
            if node.node_type == NodeType.END:
                end_nodes.add(node_id)
        
        if end_nodes:
            return end_nodes
        
        # Find nodes with no outgoing edges
        sources = {e.source_id for e in self._edges}
        for node_id in self._nodes:
            if node_id not in sources:
                end_nodes.add(node_id)
        
        return end_nodes
    
    def _find_reachable_nodes(self) -> Set[str]:
        """Find all nodes reachable from start."""
        reachable = {self._start_node_id}
        queue = [self._start_node_id]
        
        while queue:
            current = queue.pop(0)
            for edge in self.get_outgoing_edges(current):
                if edge.target_id not in reachable:
                    reachable.add(edge.target_id)
                    queue.append(edge.target_id)
        
        return reachable
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize workflow to dictionary."""
        return {
            "id": self._id,
            "name": self._name,
            "version": self._version,
            "description": self._description,
            "nodes": {nid: n.to_dict() for nid, n in self._nodes.items()},
            "edges": [e.to_dict() for e in self._edges],
            "start_node_id": self._start_node_id,
            "end_node_ids": list(self._end_node_ids),
            "routing_strategy": self._router.strategy.value,
            "metadata": self._metadata,
        }
    
    def __repr__(self) -> str:
        return f"<Workflow(id={self._id}, name={self._name})>"



