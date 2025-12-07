"""
Workflow Interfaces

Defines protocols and abstract base classes for workflow components.

Version: 1.0.0
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional, Protocol, runtime_checkable

from ..spec.node_models import NodeSpec, NodeResult, NodeEntry
from ..spec.edge_models import EdgeSpec, EdgeEntry
from ..spec.workflow_models import (
    WorkflowSpec,
    WorkflowEntry,
    WorkflowExecutionContext,
    WorkflowResult,
)
from ..spec.io_types import IOTypeSpec


# =============================================================================
# CORE COMPONENT INTERFACES
# =============================================================================

@runtime_checkable
class INode(Protocol):
    """
    Protocol for executable nodes.
    
    A node takes input data and produces output based on its configuration.
    """
    
    @property
    def spec(self) -> NodeSpec:
        """Get the node specification."""
        ...
    
    async def execute(
        self,
        input_data: Any,
        context: WorkflowExecutionContext,
        user_prompt: Optional[str] = None,
        **kwargs: Any
    ) -> NodeResult:
        """
        Execute the node.
        
        Args:
            input_data: Input data for the node
            context: Workflow execution context
            user_prompt: Optional additional prompt from user
            **kwargs: Additional arguments
            
        Returns:
            NodeResult with output data
        """
        ...
    
    async def stream(
        self,
        input_data: Any,
        context: WorkflowExecutionContext,
        user_prompt: Optional[str] = None,
        **kwargs: Any
    ) -> AsyncIterator[Any]:
        """
        Stream execution results.
        
        Args:
            input_data: Input data for the node
            context: Workflow execution context
            user_prompt: Optional additional prompt from user
            **kwargs: Additional arguments
            
        Yields:
            Streaming output chunks
        """
        ...


@runtime_checkable
class IEdge(Protocol):
    """
    Protocol for workflow edges.
    
    An edge connects two nodes and determines routing.
    """
    
    @property
    def spec(self) -> EdgeSpec:
        """Get the edge specification."""
        ...
    
    def should_traverse(self, context: Dict[str, Any]) -> bool:
        """
        Determine if this edge should be traversed.
        
        Args:
            context: Current workflow context
            
        Returns:
            True if edge should be traversed
        """
        ...
    
    def transform_data(self, source_output: Any) -> Any:
        """
        Transform source node output for target node input.
        
        Args:
            source_output: Output from source node
            
        Returns:
            Transformed data for target node
        """
        ...


@runtime_checkable
class IWorkflow(Protocol):
    """
    Protocol for executable workflows.
    """
    
    @property
    def spec(self) -> WorkflowSpec:
        """Get the workflow specification."""
        ...
    
    async def execute(
        self,
        input_data: Any,
        variables: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> WorkflowResult:
        """
        Execute the complete workflow.
        
        Args:
            input_data: Initial input data
            variables: Initial workflow variables
            **kwargs: Additional arguments
            
        Returns:
            WorkflowResult with final output
        """
        ...
    
    async def execute_node(
        self,
        node_id: str,
        input_data: Any,
        context: WorkflowExecutionContext,
        **kwargs: Any
    ) -> NodeResult:
        """
        Execute a single node within the workflow.
        
        Args:
            node_id: Node to execute
            input_data: Input data for the node
            context: Execution context
            **kwargs: Additional arguments
            
        Returns:
            NodeResult from the executed node
        """
        ...


# =============================================================================
# STORAGE INTERFACES
# =============================================================================

class IWorkflowStorage(ABC):
    """
    Abstract base class for workflow storage backends.
    
    Implementations handle persistence of workflows, nodes, and edges.
    """
    
    @abstractmethod
    async def save_workflow(self, workflow: WorkflowEntry) -> None:
        """
        Save a workflow entry.
        
        Args:
            workflow: Workflow entry to save
        """
        pass
    
    @abstractmethod
    async def load_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Load a workflow entry by ID.
        
        Args:
            workflow_id: Workflow ID to load
            
        Returns:
            Workflow data dictionary or None if not found
        """
        pass
    
    @abstractmethod
    async def delete_workflow(self, workflow_id: str) -> bool:
        """
        Delete a workflow.
        
        Args:
            workflow_id: Workflow ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def list_workflows(self) -> List[str]:
        """
        List all workflow IDs.
        
        Returns:
            List of workflow IDs
        """
        pass
    
    @abstractmethod
    async def save_node(self, node: NodeEntry) -> None:
        """
        Save a node entry.
        
        Args:
            node: Node entry to save
        """
        pass
    
    @abstractmethod
    async def load_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """
        Load a node entry by ID.
        
        Args:
            node_id: Node ID to load
            
        Returns:
            Node data dictionary or None if not found
        """
        pass
    
    @abstractmethod
    async def delete_node(self, node_id: str) -> bool:
        """
        Delete a node.
        
        Args:
            node_id: Node ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def list_nodes(self) -> List[str]:
        """
        List all node IDs.
        
        Returns:
            List of node IDs
        """
        pass
    
    @abstractmethod
    async def save_edge(self, edge: EdgeEntry) -> None:
        """
        Save an edge entry.
        
        Args:
            edge: Edge entry to save
        """
        pass
    
    @abstractmethod
    async def load_edge(self, edge_id: str) -> Optional[Dict[str, Any]]:
        """
        Load an edge entry by ID.
        
        Args:
            edge_id: Edge ID to load
            
        Returns:
            Edge data dictionary or None if not found
        """
        pass
    
    @abstractmethod
    async def delete_edge(self, edge_id: str) -> bool:
        """
        Delete an edge.
        
        Args:
            edge_id: Edge ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def list_edges(self) -> List[str]:
        """
        List all edge IDs.
        
        Returns:
            List of edge IDs
        """
        pass


# =============================================================================
# REGISTRY INTERFACES
# =============================================================================

class IWorkflowRegistry(ABC):
    """
    Abstract base class for workflow registry.
    
    Provides high-level operations for managing workflows, nodes, and edges.
    """
    
    # -------------------------------------------------------------------------
    # Workflow operations
    # -------------------------------------------------------------------------
    
    @abstractmethod
    async def save_workflow(
        self,
        workflow_id: str,
        spec: WorkflowSpec,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Save a workflow with optional metadata.
        
        Args:
            workflow_id: Unique workflow identifier
            spec: Workflow specification
            metadata: Optional metadata overrides
            
        Returns:
            Version string of saved workflow
        """
        pass
    
    @abstractmethod
    async def get_workflow(
        self,
        workflow_id: str,
        version: Optional[str] = None
    ) -> Optional[WorkflowSpec]:
        """
        Get a workflow specification.
        
        Args:
            workflow_id: Workflow ID
            version: Specific version (None for latest)
            
        Returns:
            Workflow specification or None
        """
        pass
    
    @abstractmethod
    async def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow."""
        pass
    
    @abstractmethod
    async def list_workflows(self) -> List[str]:
        """List all workflow IDs."""
        pass
    
    # -------------------------------------------------------------------------
    # Node operations
    # -------------------------------------------------------------------------
    
    @abstractmethod
    async def save_node(
        self,
        node_id: str,
        spec: NodeSpec,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Save a node with optional metadata.
        
        Args:
            node_id: Unique node identifier
            spec: Node specification
            metadata: Optional metadata overrides
            
        Returns:
            Version string of saved node
        """
        pass
    
    @abstractmethod
    async def get_node(
        self,
        node_id: str,
        version: Optional[str] = None
    ) -> Optional[NodeSpec]:
        """
        Get a node specification.
        
        Args:
            node_id: Node ID
            version: Specific version (None for latest)
            
        Returns:
            Node specification or None
        """
        pass
    
    @abstractmethod
    async def delete_node(self, node_id: str) -> bool:
        """Delete a node."""
        pass
    
    @abstractmethod
    async def list_nodes(self) -> List[str]:
        """List all node IDs."""
        pass
    
    # -------------------------------------------------------------------------
    # Edge operations
    # -------------------------------------------------------------------------
    
    @abstractmethod
    async def save_edge(
        self,
        edge_id: str,
        spec: EdgeSpec,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Save an edge with optional metadata.
        
        Args:
            edge_id: Unique edge identifier
            spec: Edge specification
            metadata: Optional metadata overrides
            
        Returns:
            Version string of saved edge
        """
        pass
    
    @abstractmethod
    async def get_edge(
        self,
        edge_id: str,
        version: Optional[str] = None
    ) -> Optional[EdgeSpec]:
        """
        Get an edge specification.
        
        Args:
            edge_id: Edge ID
            version: Specific version (None for latest)
            
        Returns:
            Edge specification or None
        """
        pass
    
    @abstractmethod
    async def delete_edge(self, edge_id: str) -> bool:
        """Delete an edge."""
        pass
    
    @abstractmethod
    async def list_edges(self) -> List[str]:
        """List all edge IDs."""
        pass


# =============================================================================
# EXECUTION INTERFACES
# =============================================================================

class IWorkflowExecutor(ABC):
    """
    Abstract base class for workflow executors.
    """
    
    @abstractmethod
    async def execute(
        self,
        workflow: WorkflowSpec,
        input_data: Any,
        variables: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> WorkflowResult:
        """
        Execute a workflow.
        
        Args:
            workflow: Workflow specification to execute
            input_data: Initial input data
            variables: Initial workflow variables
            **kwargs: Additional arguments
            
        Returns:
            Workflow execution result
        """
        pass
    
    @abstractmethod
    async def pause(self, execution_id: str) -> bool:
        """Pause a running execution."""
        pass
    
    @abstractmethod
    async def resume(self, execution_id: str) -> bool:
        """Resume a paused execution."""
        pass
    
    @abstractmethod
    async def cancel(self, execution_id: str) -> bool:
        """Cancel a running execution."""
        pass


class INodeExecutor(ABC):
    """
    Abstract base class for node executors.
    """
    
    @abstractmethod
    async def execute(
        self,
        node: NodeSpec,
        input_data: Any,
        context: WorkflowExecutionContext,
        user_prompt: Optional[str] = None,
        **kwargs: Any
    ) -> NodeResult:
        """
        Execute a node.
        
        Args:
            node: Node specification to execute
            input_data: Input data for the node
            context: Workflow execution context
            user_prompt: Optional additional prompt from user
            **kwargs: Additional arguments
            
        Returns:
            Node execution result
        """
        pass


# =============================================================================
# FORMATTER INTERFACE
# =============================================================================

class IIOFormatter(ABC):
    """
    Abstract base class for input/output type formatters.
    
    Formatters convert data between different IO types.
    """
    
    @property
    @abstractmethod
    def source_type(self) -> IOTypeSpec:
        """The source IO type this formatter handles."""
        pass
    
    @property
    @abstractmethod
    def target_type(self) -> IOTypeSpec:
        """The target IO type this formatter produces."""
        pass
    
    @abstractmethod
    async def format(self, data: Any) -> Any:
        """
        Format data from source type to target type.
        
        Args:
            data: Input data in source type format
            
        Returns:
            Data converted to target type format
        """
        pass
