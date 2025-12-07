"""
Edge Builder

Fluent builder for creating workflow edges.

Version: 1.0.0
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from ..spec.edge_models import (
    EdgeSpec,
    EdgeMetadata,
    EdgeConfig,
    EdgeCondition,
    EdgeConditionGroup,
)
from ..enum import (
    EdgeType,
    WorkflowStatus,
    ConditionOperator,
    ConditionJoinOperator,
)
from ..defaults import DEFAULT_EDGE_VERSION


class EdgeBuilder:
    """
    Fluent builder for creating EdgeSpec instances.
    
    Usage:
        # Create a simple default edge
        edge = (EdgeBuilder()
            .with_id("edge-1")
            .from_node("node-a")
            .to_node("node-b")
            .build())
        
        # Create a conditional edge
        edge = (EdgeBuilder()
            .with_id("edge-2")
            .with_name("Success Path")
            .from_node("node-a")
            .to_node("node-success")
            .as_conditional()
            .with_condition("result.success", ConditionOperator.EQUALS, True)
            .build())
        
        # Create an error edge
        edge = (EdgeBuilder()
            .with_id("edge-3")
            .from_node("node-a")
            .to_node("node-error")
            .as_error_handler()
            .build())
    """
    
    def __init__(self):
        """Initialize the builder."""
        self._id: Optional[str] = None
        self._name: str = ""
        self._description: str = ""
        self._edge_type: EdgeType = EdgeType.DEFAULT
        
        # Connection
        self._source_node_id: Optional[str] = None
        self._target_node_id: Optional[str] = None
        
        # Conditions
        self._conditions: List[EdgeCondition] = []
        self._condition_join: ConditionJoinOperator = ConditionJoinOperator.AND
        
        # Metadata
        self._version: str = DEFAULT_EDGE_VERSION
        self._status: WorkflowStatus = WorkflowStatus.DRAFT
        self._tags: List[str] = []
        
        # Config
        self._priority: int = 0
        self._weight: float = 1.0
        self._timeout_ms: Optional[int] = None
        
        # Data mapping
        self._data_mapping: Dict[str, str] = {}
        
        # Additional properties
        self._properties: Dict[str, Any] = {}
    
    def with_id(self, edge_id: str) -> EdgeBuilder:
        """Set the edge ID."""
        self._id = edge_id
        return self
    
    def with_name(self, name: str) -> EdgeBuilder:
        """Set the edge name."""
        self._name = name
        return self
    
    def with_description(self, description: str) -> EdgeBuilder:
        """Set the edge description."""
        self._description = description
        return self
    
    # =========================================================================
    # Connection methods
    # =========================================================================
    
    def from_node(self, node_id: str) -> EdgeBuilder:
        """Set the source node ID."""
        self._source_node_id = node_id
        return self
    
    def to_node(self, node_id: str) -> EdgeBuilder:
        """Set the target node ID."""
        self._target_node_id = node_id
        return self
    
    # =========================================================================
    # Type methods
    # =========================================================================
    
    def as_default(self) -> EdgeBuilder:
        """Set as default edge (always traversed)."""
        self._edge_type = EdgeType.DEFAULT
        return self
    
    def as_conditional(self) -> EdgeBuilder:
        """Set as conditional edge."""
        self._edge_type = EdgeType.CONDITIONAL
        return self
    
    def as_error_handler(self) -> EdgeBuilder:
        """Set as error handling edge."""
        self._edge_type = EdgeType.ERROR
        return self
    
    def as_timeout_handler(self) -> EdgeBuilder:
        """Set as timeout handling edge."""
        self._edge_type = EdgeType.TIMEOUT
        return self
    
    def as_fallback(self) -> EdgeBuilder:
        """Set as fallback edge."""
        self._edge_type = EdgeType.FALLBACK
        return self
    
    # =========================================================================
    # Condition methods
    # =========================================================================
    
    def with_condition(
        self,
        field: str,
        operator: ConditionOperator,
        value: Any = None,
        negate: bool = False
    ) -> EdgeBuilder:
        """Add a condition."""
        self._conditions.append(EdgeCondition(
            field=field,
            operator=operator,
            value=value,
            negate=negate,
        ))
        return self
    
    def with_custom_condition(
        self,
        field: str,
        func: Callable[[Any, Dict[str, Any]], bool]
    ) -> EdgeBuilder:
        """Add a custom condition function."""
        self._conditions.append(EdgeCondition(
            field=field,
            operator=ConditionOperator.CUSTOM,
            custom_func=func,
        ))
        return self
    
    def join_conditions_with_and(self) -> EdgeBuilder:
        """Join conditions with AND."""
        self._condition_join = ConditionJoinOperator.AND
        return self
    
    def join_conditions_with_or(self) -> EdgeBuilder:
        """Join conditions with OR."""
        self._condition_join = ConditionJoinOperator.OR
        return self
    
    # =========================================================================
    # Metadata methods
    # =========================================================================
    
    def with_version(self, version: str) -> EdgeBuilder:
        """Set the version."""
        self._version = version
        return self
    
    def with_status(self, status: WorkflowStatus) -> EdgeBuilder:
        """Set the status."""
        self._status = status
        return self
    
    def with_tags(self, tags: List[str]) -> EdgeBuilder:
        """Set tags."""
        self._tags = tags
        return self
    
    # =========================================================================
    # Config methods
    # =========================================================================
    
    def with_priority(self, priority: int) -> EdgeBuilder:
        """Set edge priority (lower = higher priority)."""
        self._priority = priority
        return self
    
    def with_weight(self, weight: float) -> EdgeBuilder:
        """Set edge weight for weighted routing."""
        self._weight = weight
        return self
    
    def with_timeout(self, timeout_ms: int) -> EdgeBuilder:
        """Set condition evaluation timeout."""
        self._timeout_ms = timeout_ms
        return self
    
    # =========================================================================
    # Data mapping methods
    # =========================================================================
    
    def map_data(self, target_field: str, source_field: str) -> EdgeBuilder:
        """
        Add a data mapping from source to target.
        
        Args:
            target_field: Field name in target node input
            source_field: Field path in source node output (dot notation)
        """
        self._data_mapping[target_field] = source_field
        return self
    
    # =========================================================================
    # Build method
    # =========================================================================
    
    def build(self) -> EdgeSpec:
        """
        Build the EdgeSpec.
        
        Raises:
            ValueError: If required fields are missing
        """
        if not self._id:
            raise ValueError("Edge ID is required")
        if not self._source_node_id:
            raise ValueError("Source node ID is required")
        if not self._target_node_id:
            raise ValueError("Target node ID is required")
        
        # Build conditions group if we have conditions
        conditions = None
        if self._conditions:
            conditions = EdgeConditionGroup(
                conditions=self._conditions,
                join_operator=self._condition_join,
            )
        
        # Build metadata
        metadata = EdgeMetadata(
            version=self._version,
            status=self._status,
            tags=self._tags,
        )
        
        # Build config
        config = EdgeConfig(
            priority=self._priority,
            weight=self._weight,
            timeout_ms=self._timeout_ms,
        )
        
        return EdgeSpec(
            id=self._id,
            name=self._name,
            description=self._description,
            edge_type=self._edge_type,
            source_node_id=self._source_node_id,
            target_node_id=self._target_node_id,
            conditions=conditions,
            metadata=metadata,
            config=config,
            data_mapping=self._data_mapping,
            properties=self._properties,
        )
