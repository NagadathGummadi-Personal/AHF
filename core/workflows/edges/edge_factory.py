"""
Edge Factory Module.

This module provides a factory for creating and registering workflow edges.
"""

import logging
from typing import Any, Callable, Dict, List, Optional, Type

from ..interfaces import IEdge, IDataTransformer
from ..enum import EdgeType
from ..spec import EdgeSpec
from ..exceptions import WorkflowBuildError

logger = logging.getLogger(__name__)


class EdgeRegistration:
    """Registration info for an edge type."""
    
    def __init__(
        self,
        edge_type: EdgeType,
        edge_class: Type[IEdge],
        display_name: str,
        description: Optional[str] = None,
        default_config: Optional[Dict[str, Any]] = None,
        factory_func: Optional[Callable[..., IEdge]] = None,
    ):
        self.edge_type = edge_type
        self.edge_class = edge_class
        self.display_name = display_name
        self.description = description
        self.default_config = default_config or {}
        self.factory_func = factory_func


class EdgeFactory:
    """
    Factory for creating workflow edges.
    
    Manages edge type registration and instantiation.
    """
    
    _registrations: Dict[str, EdgeRegistration] = {}
    _initialized: bool = False
    
    def __init__(self):
        """Initialize the edge factory."""
        if not EdgeFactory._initialized:
            self._register_builtin_edges()
            EdgeFactory._initialized = True
    
    def _register_builtin_edges(self) -> None:
        """Register built-in edge types."""
        from .base_edge import BaseEdge
        from .conditional_edge import ConditionalEdge
        from .fallback_edge import FallbackEdge
        from .error_edge import ErrorEdge
        
        # Register built-in edges
        self.register(
            EdgeType.DEFAULT,
            BaseEdge,
            "Default Edge",
            "Standard edge with optional conditions",
        )
        self.register(
            EdgeType.CONDITIONAL,
            ConditionalEdge,
            "Conditional Edge",
            "Edge that requires conditions to be met",
        )
        self.register(
            EdgeType.FALLBACK,
            FallbackEdge,
            "Fallback Edge",
            "Edge used when no other edges match",
        )
        self.register(
            EdgeType.ERROR,
            ErrorEdge,
            "Error Edge",
            "Edge taken when an error occurs",
        )
        
        # Use BaseEdge for other types
        for edge_type in [EdgeType.TIMEOUT, EdgeType.LOOP_BACK, EdgeType.PARALLEL_JOIN]:
            self.register(
                edge_type,
                BaseEdge,
                edge_type.value.replace("_", " ").title() + " Edge",
                f"Edge for {edge_type.value} handling",
            )
        
        logger.debug(f"Registered {len(self._registrations)} built-in edge types")
    
    @classmethod
    def register(
        cls,
        edge_type: EdgeType,
        edge_class: Type[IEdge],
        display_name: str,
        description: Optional[str] = None,
        default_config: Optional[Dict[str, Any]] = None,
        factory_func: Optional[Callable[..., IEdge]] = None,
        override: bool = False,
    ) -> None:
        """
        Register an edge type.
        
        Args:
            edge_type: The EdgeType enum value.
            edge_class: The class implementing IEdge.
            display_name: Human-readable name.
            description: Optional description.
            default_config: Default configuration.
            factory_func: Optional custom factory function.
            override: Allow overriding existing registration.
        """
        type_id = edge_type.value
        
        if type_id in cls._registrations and not override:
            raise ValueError(f"Edge type '{type_id}' already registered")
        
        registration = EdgeRegistration(
            edge_type=edge_type,
            edge_class=edge_class,
            display_name=display_name,
            description=description,
            default_config=default_config,
            factory_func=factory_func,
        )
        
        cls._registrations[type_id] = registration
        logger.info(f"Registered edge type: {type_id}")
    
    @classmethod
    def register_custom(
        cls,
        type_id: str,
        edge_class: Type[IEdge],
        display_name: str,
        description: Optional[str] = None,
        default_config: Optional[Dict[str, Any]] = None,
        factory_func: Optional[Callable[..., IEdge]] = None,
    ) -> None:
        """Register a custom edge type."""
        registration = EdgeRegistration(
            edge_type=EdgeType.CUSTOM,
            edge_class=edge_class,
            display_name=display_name,
            description=description,
            default_config=default_config,
            factory_func=factory_func,
        )
        
        cls._registrations[type_id] = registration
        logger.info(f"Registered custom edge type: {type_id}")
    
    @classmethod
    def unregister(cls, type_id: str) -> None:
        """Unregister an edge type."""
        if type_id in cls._registrations:
            del cls._registrations[type_id]
            logger.info(f"Unregistered edge type: {type_id}")
    
    @classmethod
    def create(
        cls,
        spec: EdgeSpec,
        transformer: Optional[IDataTransformer] = None,
        **kwargs
    ) -> IEdge:
        """
        Create an edge from specification.
        
        Args:
            spec: Edge specification.
            transformer: Optional data transformer.
            **kwargs: Additional arguments.
        
        Returns:
            Edge instance.
        """
        type_id = spec.edge_type.value
        
        registration = cls._registrations.get(type_id)
        if not registration:
            # Default to BaseEdge
            from .base_edge import BaseEdge
            return BaseEdge(spec, transformer=transformer)
        
        try:
            if registration.factory_func:
                return registration.factory_func(spec, transformer=transformer, **kwargs)
            
            return registration.edge_class(spec, transformer=transformer, **kwargs)
            
        except Exception as e:
            raise WorkflowBuildError(
                f"Failed to create edge of type '{type_id}': {e}",
                details={"edge_id": spec.id, "error": str(e)},
            ) from e
    
    @classmethod
    def create_from_dict(
        cls,
        data: Dict[str, Any],
        **kwargs
    ) -> IEdge:
        """Create an edge from dictionary."""
        spec = EdgeSpec(**data)
        return cls.create(spec, **kwargs)
    
    @classmethod
    def list_registered_types(cls) -> List[EdgeRegistration]:
        """List all registered edge types."""
        return list(cls._registrations.values())
    
    @classmethod
    def is_registered(cls, type_id: str) -> bool:
        """Check if edge type is registered."""
        return type_id in cls._registrations

