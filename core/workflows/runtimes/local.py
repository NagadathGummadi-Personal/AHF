"""
Local Workflow Storage and Registry

File-based storage implementation for workflows, nodes, and edges.
Stores data as JSON files in the local filesystem.

Version: 1.0.0
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..interfaces.workflow_interfaces import IWorkflowStorage
from ..spec.node_models import NodeEntry
from ..spec.edge_models import EdgeEntry
from ..spec.workflow_models import WorkflowEntry
from ..defaults import (
    DEFAULT_STORAGE_PATH,
    DEFAULT_FILE_EXTENSION,
)
from .base_registry import BaseWorkflowRegistry


class LocalWorkflowStorage(IWorkflowStorage):
    """
    Local file-based storage for workflows, nodes, and edges.
    
    Stores each entity as a JSON file in designated directories:
    - workflows: {storage_path}/workflows/{id}.json
    - nodes: {storage_path}/nodes/{id}.json
    - edges: {storage_path}/edges/{id}.json
    
    Attributes:
        storage_path: Base path for storage
        file_extension: File extension to use (.json or .yaml)
    """
    
    def __init__(
        self,
        storage_path: str = DEFAULT_STORAGE_PATH,
        file_extension: str = DEFAULT_FILE_EXTENSION
    ):
        """
        Initialize local storage.
        
        Args:
            storage_path: Base directory for storing files
            file_extension: File extension (.json or .yaml)
        """
        self._storage_path = Path(storage_path)
        self._file_extension = file_extension
        
        # Create subdirectories
        self._workflows_path = self._storage_path / "workflows"
        self._nodes_path = self._storage_path / "nodes"
        self._edges_path = self._storage_path / "edges"
        
        # Ensure directories exist
        self._ensure_directories()
    
    def _ensure_directories(self) -> None:
        """Create storage directories if they don't exist."""
        self._workflows_path.mkdir(parents=True, exist_ok=True)
        self._nodes_path.mkdir(parents=True, exist_ok=True)
        self._edges_path.mkdir(parents=True, exist_ok=True)
    
    def _get_workflow_path(self, workflow_id: str) -> Path:
        """Get file path for a workflow."""
        safe_id = self._sanitize_id(workflow_id)
        return self._workflows_path / f"{safe_id}{self._file_extension}"
    
    def _get_node_path(self, node_id: str) -> Path:
        """Get file path for a node."""
        safe_id = self._sanitize_id(node_id)
        return self._nodes_path / f"{safe_id}{self._file_extension}"
    
    def _get_edge_path(self, edge_id: str) -> Path:
        """Get file path for an edge."""
        safe_id = self._sanitize_id(edge_id)
        return self._edges_path / f"{safe_id}{self._file_extension}"
    
    def _sanitize_id(self, entity_id: str) -> str:
        """Sanitize ID for use as filename."""
        # Replace problematic characters
        return entity_id.replace("/", "_").replace("\\", "_").replace(":", "_")
    
    def _read_json(self, path: Path) -> Optional[Dict[str, Any]]:
        """Read JSON from file."""
        if not path.exists():
            return None
        
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def _write_json(self, path: Path, data: Dict[str, Any]) -> None:
        """Write JSON to file."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
    
    # =========================================================================
    # WORKFLOW OPERATIONS
    # =========================================================================
    
    async def save_workflow(self, workflow: WorkflowEntry) -> None:
        """Save a workflow entry to file."""
        path = self._get_workflow_path(workflow.id)
        self._write_json(path, workflow.to_dict())
    
    async def load_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Load a workflow entry from file."""
        path = self._get_workflow_path(workflow_id)
        return self._read_json(path)
    
    async def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow file."""
        path = self._get_workflow_path(workflow_id)
        if path.exists():
            path.unlink()
            return True
        return False
    
    async def list_workflows(self) -> List[str]:
        """List all workflow IDs."""
        workflows = []
        for file in self._workflows_path.glob(f"*{self._file_extension}"):
            workflow_id = file.stem
            workflows.append(workflow_id)
        return workflows
    
    # =========================================================================
    # NODE OPERATIONS
    # =========================================================================
    
    async def save_node(self, node: NodeEntry) -> None:
        """Save a node entry to file."""
        path = self._get_node_path(node.id)
        self._write_json(path, node.to_dict())
    
    async def load_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Load a node entry from file."""
        path = self._get_node_path(node_id)
        return self._read_json(path)
    
    async def delete_node(self, node_id: str) -> bool:
        """Delete a node file."""
        path = self._get_node_path(node_id)
        if path.exists():
            path.unlink()
            return True
        return False
    
    async def list_nodes(self) -> List[str]:
        """List all node IDs."""
        nodes = []
        for file in self._nodes_path.glob(f"*{self._file_extension}"):
            node_id = file.stem
            nodes.append(node_id)
        return nodes
    
    # =========================================================================
    # EDGE OPERATIONS
    # =========================================================================
    
    async def save_edge(self, edge: EdgeEntry) -> None:
        """Save an edge entry to file."""
        path = self._get_edge_path(edge.id)
        self._write_json(path, edge.to_dict())
    
    async def load_edge(self, edge_id: str) -> Optional[Dict[str, Any]]:
        """Load an edge entry from file."""
        path = self._get_edge_path(edge_id)
        return self._read_json(path)
    
    async def delete_edge(self, edge_id: str) -> bool:
        """Delete an edge file."""
        path = self._get_edge_path(edge_id)
        if path.exists():
            path.unlink()
            return True
        return False
    
    async def list_edges(self) -> List[str]:
        """List all edge IDs."""
        edges = []
        for file in self._edges_path.glob(f"*{self._file_extension}"):
            edge_id = file.stem
            edges.append(edge_id)
        return edges


class LocalWorkflowRegistry(BaseWorkflowRegistry):
    """
    Local file-based workflow registry.
    
    Uses LocalWorkflowStorage for persistence and provides
    all workflow, node, and edge management operations.
    
    Usage:
        registry = LocalWorkflowRegistry(storage_path=".workflows")
        
        # Save a node
        node_spec = NodeSpec(id="greeting-node", name="Greeting", ...)
        version = await registry.save_node("greeting-node", node_spec)
        
        # Get a node
        node = await registry.get_node("greeting-node")
        
        # Save workflow
        workflow_spec = WorkflowSpec(id="chat-flow", name="Chat Flow", ...)
        await registry.save_workflow("chat-flow", workflow_spec)
    """
    
    def __init__(
        self,
        storage_path: str = DEFAULT_STORAGE_PATH,
        file_extension: str = DEFAULT_FILE_EXTENSION
    ):
        """
        Initialize local workflow registry.
        
        Args:
            storage_path: Base directory for storing workflow files
            file_extension: File extension (.json or .yaml)
        """
        storage = LocalWorkflowStorage(
            storage_path=storage_path,
            file_extension=file_extension
        )
        super().__init__(storage=storage)
        self._storage_path = storage_path
    
    @property
    def storage_path(self) -> str:
        """Get the storage path."""
        return self._storage_path
