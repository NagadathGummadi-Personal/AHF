"""
Base Workflow Registry

Provides common functionality for workflow registries.
Specific implementations (Local, S3, etc.) extend this base.

Version: 1.0.0
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from ..interfaces.workflow_interfaces import IWorkflowRegistry, IWorkflowStorage
from ..spec.node_models import NodeSpec, NodeVersion, NodeEntry
from ..spec.edge_models import EdgeSpec, EdgeVersion, EdgeEntry
from ..spec.workflow_models import (
    WorkflowSpec,
    WorkflowVersion,
    WorkflowEntry,
)
from ..defaults import DEFAULT_VERSION
from ..constants import ERROR_VERSION_EXISTS, ERROR_IMMUTABLE_VERSION


class BaseWorkflowRegistry(IWorkflowRegistry):
    """
    Base implementation for workflow registry.
    
    Provides common versioning, validation, and management logic.
    Subclasses must provide a storage implementation.
    
    Attributes:
        storage: Storage backend implementation
    """
    
    def __init__(self, storage: IWorkflowStorage):
        """
        Initialize the registry.
        
        Args:
            storage: Storage backend to use
        """
        self._storage = storage
    
    @property
    def storage(self) -> IWorkflowStorage:
        """Get the storage backend."""
        return self._storage
    
    # =========================================================================
    # WORKFLOW OPERATIONS
    # =========================================================================
    
    async def save_workflow(
        self,
        workflow_id: str,
        spec: WorkflowSpec,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Save a workflow with versioning support.
        
        Args:
            workflow_id: Unique workflow identifier
            spec: Workflow specification
            metadata: Optional metadata overrides
            
        Returns:
            Version string of saved workflow
        """
        # Load existing entry or create new
        existing_data = await self._storage.load_workflow(workflow_id)
        
        if existing_data:
            entry = WorkflowEntry.from_dict(existing_data)
            
            # Determine version
            if metadata and "version" in metadata:
                version = metadata["version"]
            else:
                # Auto-increment from latest
                latest = entry.get_latest_version()
                version = self._increment_version(latest or DEFAULT_VERSION)
            
            # Check immutability
            if entry.version_exists(version):
                existing_version = entry.get_version(version)
                if existing_version and existing_version.is_published:
                    raise ValueError(ERROR_IMMUTABLE_VERSION.format(version=version))
                raise ValueError(
                    ERROR_VERSION_EXISTS.format(
                        version=version,
                        entity_type="workflow",
                        id=workflow_id
                    )
                )
        else:
            entry = WorkflowEntry(id=workflow_id, versions={})
            version = metadata.get("version", DEFAULT_VERSION) if metadata else DEFAULT_VERSION
        
        # Update spec metadata
        spec.metadata.version = version
        spec.metadata.updated_at = datetime.utcnow()
        if not spec.metadata.created_at:
            spec.metadata.created_at = datetime.utcnow()
        
        # Apply metadata overrides
        if metadata:
            for key, value in metadata.items():
                if hasattr(spec.metadata, key):
                    setattr(spec.metadata, key, value)
        
        # Create version entry
        workflow_version = WorkflowVersion(
            version=version,
            spec=spec,
            created_at=datetime.utcnow(),
            is_published=False,
        )
        
        # Add version and save
        entry.add_version(workflow_version)
        await self._storage.save_workflow(entry)
        
        return version
    
    async def get_workflow(
        self,
        workflow_id: str,
        version: Optional[str] = None
    ) -> Optional[WorkflowSpec]:
        """Get a workflow specification."""
        data = await self._storage.load_workflow(workflow_id)
        if not data:
            return None
        
        entry = WorkflowEntry.from_dict(data)
        
        if version:
            wv = entry.get_version(version)
        else:
            wv = entry.get_latest()
        
        return wv.spec if wv else None
    
    async def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow."""
        return await self._storage.delete_workflow(workflow_id)
    
    async def list_workflows(self) -> List[str]:
        """List all workflow IDs."""
        return await self._storage.list_workflows()
    
    async def publish_workflow(self, workflow_id: str, version: str) -> bool:
        """
        Publish a workflow version, making it immutable.
        
        Args:
            workflow_id: Workflow ID
            version: Version to publish
            
        Returns:
            True if published successfully
        """
        data = await self._storage.load_workflow(workflow_id)
        if not data:
            return False
        
        entry = WorkflowEntry.from_dict(data)
        wv = entry.get_version(version)
        
        if not wv:
            return False
        
        wv.is_published = True
        await self._storage.save_workflow(entry)
        return True
    
    # =========================================================================
    # NODE OPERATIONS
    # =========================================================================
    
    async def save_node(
        self,
        node_id: str,
        spec: NodeSpec,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Save a node with versioning support.
        
        Args:
            node_id: Unique node identifier
            spec: Node specification
            metadata: Optional metadata overrides
            
        Returns:
            Version string of saved node
        """
        # Load existing entry or create new
        existing_data = await self._storage.load_node(node_id)
        
        if existing_data:
            entry = NodeEntry.from_dict(existing_data)
            
            # Determine version
            if metadata and "version" in metadata:
                version = metadata["version"]
            else:
                latest = entry.get_latest_version()
                version = self._increment_version(latest or DEFAULT_VERSION)
            
            # Check immutability
            if entry.version_exists(version):
                existing_version = entry.get_version(version)
                if existing_version and existing_version.is_published:
                    raise ValueError(ERROR_IMMUTABLE_VERSION.format(version=version))
                raise ValueError(
                    ERROR_VERSION_EXISTS.format(
                        version=version,
                        entity_type="node",
                        id=node_id
                    )
                )
        else:
            entry = NodeEntry(id=node_id, versions={})
            version = metadata.get("version", DEFAULT_VERSION) if metadata else DEFAULT_VERSION
        
        # Update spec metadata
        spec.metadata.version = version
        spec.metadata.updated_at = datetime.utcnow()
        if not spec.metadata.created_at:
            spec.metadata.created_at = datetime.utcnow()
        
        # Apply metadata overrides
        if metadata:
            for key, value in metadata.items():
                if hasattr(spec.metadata, key):
                    setattr(spec.metadata, key, value)
        
        # Create version entry
        node_version = NodeVersion(
            version=version,
            spec=spec,
            created_at=datetime.utcnow(),
            is_published=False,
        )
        
        # Add version and save
        entry.add_version(node_version)
        await self._storage.save_node(entry)
        
        return version
    
    async def get_node(
        self,
        node_id: str,
        version: Optional[str] = None
    ) -> Optional[NodeSpec]:
        """Get a node specification."""
        data = await self._storage.load_node(node_id)
        if not data:
            return None
        
        entry = NodeEntry.from_dict(data)
        
        if version:
            nv = entry.get_version(version)
        else:
            nv = entry.get_latest()
        
        return nv.spec if nv else None
    
    async def delete_node(self, node_id: str) -> bool:
        """Delete a node."""
        return await self._storage.delete_node(node_id)
    
    async def list_nodes(self) -> List[str]:
        """List all node IDs."""
        return await self._storage.list_nodes()
    
    async def publish_node(self, node_id: str, version: str) -> bool:
        """Publish a node version, making it immutable."""
        data = await self._storage.load_node(node_id)
        if not data:
            return False
        
        entry = NodeEntry.from_dict(data)
        nv = entry.get_version(version)
        
        if not nv:
            return False
        
        nv.is_published = True
        await self._storage.save_node(entry)
        return True
    
    # =========================================================================
    # EDGE OPERATIONS
    # =========================================================================
    
    async def save_edge(
        self,
        edge_id: str,
        spec: EdgeSpec,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Save an edge with versioning support.
        
        Args:
            edge_id: Unique edge identifier
            spec: Edge specification
            metadata: Optional metadata overrides
            
        Returns:
            Version string of saved edge
        """
        # Load existing entry or create new
        existing_data = await self._storage.load_edge(edge_id)
        
        if existing_data:
            entry = EdgeEntry.from_dict(existing_data)
            
            # Determine version
            if metadata and "version" in metadata:
                version = metadata["version"]
            else:
                latest = entry.get_latest_version()
                version = self._increment_version(latest or DEFAULT_VERSION)
            
            # Check immutability
            if entry.version_exists(version):
                existing_version = entry.get_version(version)
                if existing_version and existing_version.is_published:
                    raise ValueError(ERROR_IMMUTABLE_VERSION.format(version=version))
                raise ValueError(
                    ERROR_VERSION_EXISTS.format(
                        version=version,
                        entity_type="edge",
                        id=edge_id
                    )
                )
        else:
            entry = EdgeEntry(id=edge_id, versions={})
            version = metadata.get("version", DEFAULT_VERSION) if metadata else DEFAULT_VERSION
        
        # Update spec metadata
        spec.metadata.version = version
        spec.metadata.updated_at = datetime.utcnow()
        if not spec.metadata.created_at:
            spec.metadata.created_at = datetime.utcnow()
        
        # Apply metadata overrides
        if metadata:
            for key, value in metadata.items():
                if hasattr(spec.metadata, key):
                    setattr(spec.metadata, key, value)
        
        # Create version entry
        edge_version = EdgeVersion(
            version=version,
            spec=spec,
            created_at=datetime.utcnow(),
            is_published=False,
        )
        
        # Add version and save
        entry.add_version(edge_version)
        await self._storage.save_edge(entry)
        
        return version
    
    async def get_edge(
        self,
        edge_id: str,
        version: Optional[str] = None
    ) -> Optional[EdgeSpec]:
        """Get an edge specification."""
        data = await self._storage.load_edge(edge_id)
        if not data:
            return None
        
        entry = EdgeEntry.from_dict(data)
        
        if version:
            ev = entry.get_version(version)
        else:
            ev = entry.get_latest()
        
        return ev.spec if ev else None
    
    async def delete_edge(self, edge_id: str) -> bool:
        """Delete an edge."""
        return await self._storage.delete_edge(edge_id)
    
    async def list_edges(self) -> List[str]:
        """List all edge IDs."""
        return await self._storage.list_edges()
    
    async def publish_edge(self, edge_id: str, version: str) -> bool:
        """Publish an edge version, making it immutable."""
        data = await self._storage.load_edge(edge_id)
        if not data:
            return False
        
        entry = EdgeEntry.from_dict(data)
        ev = entry.get_version(version)
        
        if not ev:
            return False
        
        ev.is_published = True
        await self._storage.save_edge(entry)
        return True
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def _increment_version(self, version: str) -> str:
        """
        Increment a semantic version string.
        
        Args:
            version: Current version (e.g., "1.0.0")
            
        Returns:
            Incremented version (e.g., "1.0.1")
        """
        parts = version.split(".")
        if len(parts) == 3:
            parts[2] = str(int(parts[2]) + 1)
        return ".".join(parts)
