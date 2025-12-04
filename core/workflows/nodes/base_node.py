"""
Base Node Implementation Module.

This module provides the abstract base class for all workflow nodes.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from ..interfaces import INode, IWorkflowContext
from ..enum import NodeType, NodeState
from ..spec import NodeSpec

logger = logging.getLogger(__name__)


class BaseNode(ABC, INode):
    """
    Abstract base class for workflow nodes.
    
    Provides common functionality for all node types including
    configuration management, validation, and serialization.
    """
    
    def __init__(self, spec: NodeSpec):
        """
        Initialize the node from a specification.
        
        Args:
            spec: Node specification containing configuration.
        """
        self._spec = spec
        self._id = spec.id
        self._name = spec.name
        self._node_type = spec.node_type
        self._config = dict(spec.config)
        self._metadata = dict(spec.metadata)
        self._timeout = spec.timeout_seconds
        self._retry_config = spec.retry_config
        
        logger.debug(f"Initialized {self._node_type.value} node: {self._name} ({self._id})")
    
    @property
    def id(self) -> str:
        """Get the unique node ID."""
        return self._id
    
    @property
    def name(self) -> str:
        """Get the human-readable node name."""
        return self._name
    
    @property
    def node_type(self) -> NodeType:
        """Get the type of this node."""
        return self._node_type
    
    @property
    def config(self) -> Dict[str, Any]:
        """Get the node configuration."""
        return self._config
    
    @property
    def metadata(self) -> Dict[str, Any]:
        """Get node metadata."""
        return self._metadata
    
    @property
    def spec(self) -> NodeSpec:
        """Get the full node specification."""
        return self._spec
    
    @abstractmethod
    async def execute(
        self,
        input_data: Any,
        context: IWorkflowContext,
    ) -> Any:
        """
        Execute the node with given input and context.
        
        This method must be implemented by subclasses to provide
        node-specific execution logic.
        
        Args:
            input_data: Input data from previous node(s) or workflow input.
            context: Workflow execution context.
            
        Returns:
            The output of node execution.
        """
        ...
    
    async def validate(self, context: IWorkflowContext) -> List[str]:
        """
        Validate node configuration.
        
        Override in subclasses for node-specific validation.
        
        Args:
            context: Workflow execution context.
            
        Returns:
            List of validation error messages (empty if valid).
        """
        errors = []
        
        if not self._id:
            errors.append(f"Node {self._name}: ID is required")
        
        if not self._name:
            errors.append(f"Node {self._id}: Name is required")
        
        return errors
    
    def get_required_inputs(self) -> List[str]:
        """
        Get list of required input keys for this node.
        
        Override in subclasses if node requires specific inputs.
        """
        return [m.target for m in self._spec.input_mappings if m.required]
    
    def get_output_schema(self) -> Optional[Dict[str, Any]]:
        """
        Get JSON schema for node output.
        
        Override in subclasses to define output schema.
        """
        return self._config.get("output_schema")
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize node to dictionary."""
        return {
            "id": self._id,
            "name": self._name,
            "node_type": self._node_type.value,
            "config": self._config,
            "metadata": self._metadata,
            "timeout_seconds": self._timeout,
            "retry_config": self._retry_config.model_dump() if self._retry_config else None,
            "input_mappings": [m.model_dump() for m in self._spec.input_mappings],
            "output_mappings": [m.model_dump() for m in self._spec.output_mappings],
        }
    
    def _resolve_input(
        self,
        context: IWorkflowContext,
        input_data: Any,
    ) -> Dict[str, Any]:
        """
        Resolve input mappings from context to node input.
        
        Args:
            context: Workflow context.
            input_data: Direct input data.
            
        Returns:
            Resolved input dictionary.
        """
        resolved = {}
        
        # Add direct input
        if isinstance(input_data, dict):
            resolved.update(input_data)
        else:
            resolved["$input"] = input_data
        
        # Apply input mappings
        for mapping in self._spec.input_mappings:
            value = self._resolve_path(mapping.source, context, input_data)
            if value is None and mapping.default is not None:
                value = mapping.default
            if value is None and mapping.required:
                raise ValueError(f"Required input '{mapping.target}' not found for node {self._name}")
            if value is not None:
                resolved[mapping.target] = value
        
        return resolved
    
    def _resolve_path(
        self,
        path: str,
        context: IWorkflowContext,
        input_data: Any,
    ) -> Any:
        """
        Resolve a variable path from context.
        
        Supports paths like:
        - $input.field
        - $node.nodeid.output
        - $ctx.variable
        - $workflow.id
        
        Args:
            path: Variable path to resolve.
            context: Workflow context.
            input_data: Current input data.
            
        Returns:
            Resolved value or None.
        """
        if not path.startswith("$"):
            return path  # Literal value
        
        parts = path.split(".")
        prefix = parts[0]
        
        if prefix == "$input":
            value = input_data
        elif prefix == "$node":
            if len(parts) < 2:
                return None
            node_id = parts[1]
            value = context.get_node_output(node_id)
            parts = parts[2:]  # Skip prefix and node_id
        elif prefix in ("$ctx", "$context"):
            if len(parts) < 2:
                return context.variables
            value = context.get(parts[1])
            parts = parts[2:]
        elif prefix == "$workflow":
            if len(parts) < 2:
                return {"id": context.workflow_id}
            if parts[1] == "id":
                return context.workflow_id
            return None
        else:
            return None
        
        # Navigate nested path
        for part in parts[1:]:
            if isinstance(value, dict):
                value = value.get(part)
            elif hasattr(value, part):
                value = getattr(value, part)
            else:
                return None
            if value is None:
                return None
        
        return value
    
    def _store_output(
        self,
        output: Any,
        context: IWorkflowContext,
    ) -> None:
        """
        Store output to context according to output mappings.
        
        Args:
            output: Node output.
            context: Workflow context.
        """
        # Store full output under node ID
        context.set_node_output(self._id, output)
        
        # Apply output mappings
        for mapping in self._spec.output_mappings:
            value = self._extract_from_output(mapping.source, output)
            if value is not None:
                context.set(mapping.target, value)
    
    def _extract_from_output(self, source: str, output: Any) -> Any:
        """Extract value from output using source path."""
        if source == "$output":
            return output
        
        if not source.startswith("$output."):
            return source  # Literal
        
        parts = source.split(".")[1:]  # Skip $output
        value = output
        
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            elif hasattr(value, part):
                value = getattr(value, part)
            else:
                return None
            if value is None:
                return None
        
        return value
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self._id}, name={self._name})>"

