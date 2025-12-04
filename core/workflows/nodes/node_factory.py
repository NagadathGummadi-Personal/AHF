"""
Node Factory Module.

This module provides a factory for creating and registering workflow nodes.
"""

import logging
from typing import Any, Callable, Dict, List, Optional, Type

from ..interfaces import INode
from ..enum import NodeType
from ..spec import NodeSpec
from ..exceptions import WorkflowBuildError

logger = logging.getLogger(__name__)


class NodeRegistration:
    """Registration info for a node type."""
    
    def __init__(
        self,
        node_type: NodeType,
        node_class: Type[INode],
        display_name: str,
        description: Optional[str] = None,
        default_config: Optional[Dict[str, Any]] = None,
        factory_func: Optional[Callable[..., INode]] = None,
    ):
        self.node_type = node_type
        self.node_class = node_class
        self.display_name = display_name
        self.description = description
        self.default_config = default_config or {}
        self.factory_func = factory_func


class NodeFactory:
    """
    Factory for creating workflow nodes.
    
    This factory manages node type registration and instantiation,
    allowing custom node types to be added at runtime.
    """
    
    _registrations: Dict[str, NodeRegistration] = {}
    _initialized: bool = False
    
    def __init__(self):
        """Initialize the node factory."""
        if not NodeFactory._initialized:
            self._register_builtin_nodes()
            NodeFactory._initialized = True
    
    def _register_builtin_nodes(self) -> None:
        """Register all built-in node types."""
        from .base_node import BaseNode
        from .agent_node import AgentNode
        from .tool_node import ToolNode
        from .decision_node import DecisionNode
        from .parallel_node import ParallelNode
        from .transform_node import TransformNode
        from .delay_node import DelayNode
        from .start_end_nodes import StartNode, EndNode
        from .subworkflow_node import SubworkflowNode
        from .webhook_node import WebhookNode
        
        # Register built-in nodes
        self.register(
            NodeType.AGENT,
            AgentNode,
            "Agent Node",
            "Executes an AI agent",
        )
        self.register(
            NodeType.TOOL,
            ToolNode,
            "Tool Node",
            "Executes a tool or function",
        )
        self.register(
            NodeType.DECISION,
            DecisionNode,
            "Decision Node",
            "Makes routing decisions based on conditions",
        )
        self.register(
            NodeType.PARALLEL,
            ParallelNode,
            "Parallel Node",
            "Executes multiple branches in parallel",
        )
        self.register(
            NodeType.TRANSFORM,
            TransformNode,
            "Transform Node",
            "Transforms data between formats",
        )
        self.register(
            NodeType.DELAY,
            DelayNode,
            "Delay Node",
            "Introduces a delay in execution",
        )
        self.register(
            NodeType.START,
            StartNode,
            "Start Node",
            "Workflow entry point",
        )
        self.register(
            NodeType.END,
            EndNode,
            "End Node",
            "Workflow exit point",
        )
        self.register(
            NodeType.SUBWORKFLOW,
            SubworkflowNode,
            "Subworkflow Node",
            "Executes another workflow",
        )
        self.register(
            NodeType.WEBHOOK,
            WebhookNode,
            "Webhook Node",
            "Makes HTTP webhook calls",
        )
        
        logger.debug(f"Registered {len(self._registrations)} built-in node types")
    
    @classmethod
    def register(
        cls,
        node_type: NodeType,
        node_class: Type[INode],
        display_name: str,
        description: Optional[str] = None,
        default_config: Optional[Dict[str, Any]] = None,
        factory_func: Optional[Callable[..., INode]] = None,
        override: bool = False,
    ) -> None:
        """
        Register a node type with the factory.
        
        Args:
            node_type: The NodeType enum value.
            node_class: The class implementing INode.
            display_name: Human-readable name.
            description: Optional description.
            default_config: Default configuration for this node type.
            factory_func: Optional custom factory function.
            override: If True, allow overriding existing registration.
        
        Raises:
            ValueError: If node type already registered and override is False.
        """
        type_id = node_type.value
        
        if type_id in cls._registrations and not override:
            raise ValueError(
                f"Node type '{type_id}' already registered. "
                "Use override=True to replace."
            )
        
        registration = NodeRegistration(
            node_type=node_type,
            node_class=node_class,
            display_name=display_name,
            description=description,
            default_config=default_config,
            factory_func=factory_func,
        )
        
        cls._registrations[type_id] = registration
        logger.info(f"Registered node type: {type_id} ({display_name})")
    
    @classmethod
    def register_custom(
        cls,
        type_id: str,
        node_class: Type[INode],
        display_name: str,
        description: Optional[str] = None,
        default_config: Optional[Dict[str, Any]] = None,
        factory_func: Optional[Callable[..., INode]] = None,
    ) -> None:
        """
        Register a custom node type.
        
        Args:
            type_id: Custom type identifier string.
            node_class: The class implementing INode.
            display_name: Human-readable name.
            description: Optional description.
            default_config: Default configuration.
            factory_func: Optional custom factory function.
        """
        registration = NodeRegistration(
            node_type=NodeType.CUSTOM,
            node_class=node_class,
            display_name=display_name,
            description=description,
            default_config=default_config,
            factory_func=factory_func,
        )
        
        cls._registrations[type_id] = registration
        logger.info(f"Registered custom node type: {type_id} ({display_name})")
    
    @classmethod
    def unregister(cls, type_id: str) -> None:
        """Unregister a node type."""
        if type_id in cls._registrations:
            del cls._registrations[type_id]
            logger.info(f"Unregistered node type: {type_id}")
    
    @classmethod
    def create(cls, spec: NodeSpec, **kwargs) -> INode:
        """
        Create a node instance from a specification.
        
        Args:
            spec: Node specification.
            **kwargs: Additional arguments for node constructor.
        
        Returns:
            Node instance.
        
        Raises:
            WorkflowBuildError: If node type is not registered.
        """
        type_id = spec.node_type.value
        
        registration = cls._registrations.get(type_id)
        if not registration:
            raise WorkflowBuildError(
                f"Unknown node type: {type_id}. "
                f"Available types: {list(cls._registrations.keys())}",
                details={"node_id": spec.id, "node_type": type_id},
            )
        
        # Merge default config with spec config
        merged_config = dict(registration.default_config)
        merged_config.update(spec.config)
        spec.config = merged_config
        
        try:
            # Use custom factory function if provided
            if registration.factory_func:
                return registration.factory_func(spec, **kwargs)
            
            # Otherwise use the class constructor
            return registration.node_class(spec, **kwargs)
            
        except Exception as e:
            raise WorkflowBuildError(
                f"Failed to create node of type '{type_id}': {e}",
                details={"node_id": spec.id, "error": str(e)},
            ) from e
    
    @classmethod
    def create_from_dict(cls, data: Dict[str, Any], **kwargs) -> INode:
        """
        Create a node from a dictionary specification.
        
        Args:
            data: Dictionary with node specification.
            **kwargs: Additional arguments for node constructor.
        
        Returns:
            Node instance.
        """
        spec = NodeSpec(**data)
        return cls.create(spec, **kwargs)
    
    @classmethod
    def get_registration(cls, type_id: str) -> Optional[NodeRegistration]:
        """Get registration info for a node type."""
        return cls._registrations.get(type_id)
    
    @classmethod
    def list_registered_types(cls) -> List[NodeRegistration]:
        """List all registered node types."""
        return list(cls._registrations.values())
    
    @classmethod
    def is_registered(cls, type_id: str) -> bool:
        """Check if a node type is registered."""
        return type_id in cls._registrations
    
    @classmethod
    def clear_custom_types(cls) -> None:
        """Remove all custom registered types, keeping built-in ones."""
        builtin_types = {nt.value for nt in NodeType}
        to_remove = [
            type_id for type_id in cls._registrations
            if type_id not in builtin_types
        ]
        for type_id in to_remove:
            del cls._registrations[type_id]
        logger.info(f"Cleared {len(to_remove)} custom node types")

