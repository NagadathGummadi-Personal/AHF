"""
Edge Specification Models

Defines the structure for workflow edges including conditions,
metadata, and routing logic.

An edge connects two nodes and can include conditions for routing.

Version: 1.0.0
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field, PrivateAttr

from ..enum import (
    EdgeType,
    WorkflowStatus,
    ConditionOperator,
    ConditionJoinOperator,
)
from ..defaults import (
    DEFAULT_EDGE_VERSION,
    DEFAULT_EDGE_STATUS,
    DEFAULT_EDGE_TYPE,
    DEFAULT_EDGE_PRIORITY,
    DEFAULT_EDGE_WEIGHT,
)
from ..constants import (
    ARBITRARY_TYPES_ALLOWED,
    POPULATE_BY_NAME,
    ERROR_VERSION_EXISTS,
    ERROR_INVALID_CONDITION,
)


class EdgeCondition(BaseModel):
    """
    A single condition for edge evaluation.
    
    Conditions are evaluated against workflow variables or node outputs.
    
    Attributes:
        field: The field/variable to evaluate (supports dot notation)
        operator: Comparison operator
        value: Value to compare against
        custom_func: Custom evaluation function (for CUSTOM operator)
        negate: Whether to negate the result
    """
    field: str = Field(..., description="Field to evaluate (dot notation supported)")
    operator: ConditionOperator = Field(
        default=ConditionOperator.EQUALS,
        description="Comparison operator"
    )
    value: Optional[Any] = Field(
        default=None,
        description="Value to compare against"
    )
    custom_func: Optional[Callable[[Any, Dict[str, Any]], bool]] = Field(
        default=None,
        description="Custom evaluation function (context) -> bool"
    )
    negate: bool = Field(default=False, description="Negate the condition result")
    
    model_config = {ARBITRARY_TYPES_ALLOWED: True}
    
    def evaluate(self, context: Dict[str, Any]) -> bool:
        """
        Evaluate this condition against the given context.
        
        Args:
            context: Dictionary containing workflow variables and node outputs
            
        Returns:
            bool: Whether the condition is met
            
        Raises:
            ValueError: If condition is invalid or evaluation fails
        """
        try:
            # Get the field value from context using dot notation
            field_value = self._get_nested_value(context, self.field)
            
            # Evaluate based on operator
            result = self._evaluate_operator(field_value)
            
            # Apply negation if needed
            return not result if self.negate else result
            
        except Exception as e:
            raise ValueError(
                ERROR_INVALID_CONDITION.format(condition=f"{self.field} {self.operator.value} {self.value}: {e}")
            )
    
    def _get_nested_value(self, obj: Dict[str, Any], path: str) -> Any:
        """Get nested value using dot notation."""
        keys = path.split(".")
        value = obj
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        return value
    
    def _evaluate_operator(self, field_value: Any) -> bool:
        """Evaluate the operator against the field value."""
        op = self.operator
        
        if op == ConditionOperator.EQUALS:
            return field_value == self.value
        elif op == ConditionOperator.NOT_EQUALS:
            return field_value != self.value
        elif op == ConditionOperator.GREATER_THAN:
            return field_value is not None and field_value > self.value
        elif op == ConditionOperator.LESS_THAN:
            return field_value is not None and field_value < self.value
        elif op == ConditionOperator.GREATER_THAN_OR_EQUALS:
            return field_value is not None and field_value >= self.value
        elif op == ConditionOperator.LESS_THAN_OR_EQUALS:
            return field_value is not None and field_value <= self.value
        elif op == ConditionOperator.CONTAINS:
            return self.value in field_value if field_value else False
        elif op == ConditionOperator.NOT_CONTAINS:
            return self.value not in field_value if field_value else True
        elif op == ConditionOperator.STARTS_WITH:
            return str(field_value).startswith(str(self.value)) if field_value else False
        elif op == ConditionOperator.ENDS_WITH:
            return str(field_value).endswith(str(self.value)) if field_value else False
        elif op == ConditionOperator.MATCHES:
            import re
            return bool(re.match(str(self.value), str(field_value))) if field_value else False
        elif op == ConditionOperator.IN:
            return field_value in self.value if self.value else False
        elif op == ConditionOperator.NOT_IN:
            return field_value not in self.value if self.value else True
        elif op == ConditionOperator.IS_NULL:
            return field_value is None
        elif op == ConditionOperator.IS_NOT_NULL:
            return field_value is not None
        elif op == ConditionOperator.IS_EMPTY:
            return not field_value if field_value is not None else True
        elif op == ConditionOperator.IS_NOT_EMPTY:
            return bool(field_value)
        elif op == ConditionOperator.CUSTOM:
            if self.custom_func:
                return self.custom_func(field_value, {})
            return False
        else:
            raise ValueError(f"Unknown operator: {op}")


class EdgeConditionGroup(BaseModel):
    """
    A group of conditions joined by AND/OR.
    
    Supports nested condition groups for complex logic.
    
    Attributes:
        conditions: List of conditions in this group
        join_operator: How to join conditions (AND/OR)
        nested_groups: Nested condition groups
    """
    conditions: List[EdgeCondition] = Field(
        default_factory=list,
        description="Conditions in this group"
    )
    join_operator: ConditionJoinOperator = Field(
        default=ConditionJoinOperator.AND,
        description="How to join conditions"
    )
    nested_groups: List[EdgeConditionGroup] = Field(
        default_factory=list,
        description="Nested condition groups"
    )
    
    def evaluate(self, context: Dict[str, Any]) -> bool:
        """
        Evaluate all conditions in this group.
        
        Args:
            context: Dictionary containing workflow variables
            
        Returns:
            bool: Whether the condition group is satisfied
        """
        results = []
        
        # Evaluate individual conditions
        for condition in self.conditions:
            results.append(condition.evaluate(context))
        
        # Evaluate nested groups
        for group in self.nested_groups:
            results.append(group.evaluate(context))
        
        if not results:
            return True  # No conditions = always pass
        
        if self.join_operator == ConditionJoinOperator.AND:
            return all(results)
        else:  # OR
            return any(results)


class EdgeMetadata(BaseModel):
    """
    Metadata for an edge.
    
    Attributes:
        version: Edge version string
        status: Current status (draft, published, etc.)
        created_at: Creation timestamp
        updated_at: Last update timestamp
        created_by: User who created the edge
        tags: Tags for categorization
    """
    version: str = Field(default=DEFAULT_EDGE_VERSION, description="Edge version")
    status: WorkflowStatus = Field(default=WorkflowStatus(DEFAULT_EDGE_STATUS), description="Edge status")
    created_at: Optional[datetime] = Field(default=None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")
    created_by: Optional[str] = Field(default=None, description="Creator user ID")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")


class EdgeConfig(BaseModel):
    """
    Configuration for edge behavior.
    
    Attributes:
        priority: Edge priority (lower = higher priority)
        weight: Weight for weighted routing
        timeout_ms: Timeout for condition evaluation
    """
    priority: int = Field(
        default=DEFAULT_EDGE_PRIORITY,
        description="Edge priority (lower = higher priority)"
    )
    weight: float = Field(
        default=DEFAULT_EDGE_WEIGHT,
        description="Weight for weighted routing"
    )
    timeout_ms: Optional[int] = Field(
        default=None,
        description="Timeout for condition evaluation"
    )


class EdgeSpec(BaseModel):
    """
    Complete specification for a workflow edge.
    
    An edge connects two nodes and determines routing based on conditions.
    
    Attributes:
        id: Unique identifier
        name: Human-readable name
        description: Edge description
        edge_type: Type of edge (DEFAULT, CONDITIONAL, ERROR, etc.)
        
        # Connection
        source_node_id: ID of the source node
        target_node_id: ID of the target node
        
        # Conditions
        conditions: Condition group for evaluation
        
        # Configuration
        metadata: Edge metadata
        config: Edge configuration
        
        # Data transformation
        data_mapping: Mapping of source fields to target fields
    """
    # Identity
    id: str = Field(..., description="Unique edge identifier")
    name: str = Field(default="", description="Human-readable name")
    description: str = Field(default="", description="Edge description")
    edge_type: EdgeType = Field(default=EdgeType(DEFAULT_EDGE_TYPE), description="Type of edge")
    
    # Connection
    source_node_id: str = Field(..., description="ID of source node")
    target_node_id: str = Field(..., description="ID of target node")
    
    # Conditions (only for CONDITIONAL type)
    conditions: Optional[EdgeConditionGroup] = Field(
        default=None,
        description="Conditions for traversing this edge"
    )
    
    # Metadata and config
    metadata: EdgeMetadata = Field(default_factory=EdgeMetadata, description="Edge metadata")
    config: EdgeConfig = Field(default_factory=EdgeConfig, description="Edge configuration")
    
    # Data transformation between nodes
    data_mapping: Dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of source output fields to target input fields"
    )
    
    # Additional properties for extensibility
    properties: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional custom properties"
    )
    
    model_config = {
        ARBITRARY_TYPES_ALLOWED: True,
        POPULATE_BY_NAME: True,
    }
    
    def should_traverse(self, context: Dict[str, Any]) -> bool:
        """
        Determine if this edge should be traversed based on conditions.
        
        Args:
            context: Workflow context including variables and node outputs
            
        Returns:
            bool: Whether to traverse this edge
        """
        # Default edges always traverse
        if self.edge_type == EdgeType.DEFAULT:
            return True
        
        # Error edges only traverse on error
        if self.edge_type == EdgeType.ERROR:
            return context.get("_error", False)
        
        # Timeout edges only traverse on timeout
        if self.edge_type == EdgeType.TIMEOUT:
            return context.get("_timeout", False)
        
        # Conditional edges evaluate conditions
        if self.edge_type == EdgeType.CONDITIONAL:
            if self.conditions:
                return self.conditions.evaluate(context)
            return True  # No conditions = always pass
        
        # Fallback edges traverse if primary path failed
        if self.edge_type == EdgeType.FALLBACK:
            return context.get("_fallback_needed", False)
        
        return True
    
    def apply_data_mapping(self, source_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply data mapping to transform source output for target input.
        
        Args:
            source_output: Output from source node
            
        Returns:
            Dict: Transformed data for target node input
        """
        if not self.data_mapping:
            return source_output
        
        result = {}
        for target_field, source_field in self.data_mapping.items():
            value = self._get_nested_value(source_output, source_field)
            self._set_nested_value(result, target_field, value)
        
        return result
    
    def _get_nested_value(self, obj: Dict[str, Any], path: str) -> Any:
        """Get nested value using dot notation."""
        keys = path.split(".")
        value = obj
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        return value
    
    def _set_nested_value(self, obj: Dict[str, Any], path: str, value: Any) -> None:
        """Set nested value using dot notation."""
        keys = path.split(".")
        for key in keys[:-1]:
            obj = obj.setdefault(key, {})
        obj[keys[-1]] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EdgeSpec:
        """Create from dictionary."""
        return cls(**data)


class EdgeVersion(BaseModel):
    """
    A specific version of an edge.
    
    Versions are immutable once published.
    """
    version: str = Field(..., description="Version string")
    spec: EdgeSpec = Field(..., description="Edge specification")
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
    def from_dict(cls, data: Dict[str, Any]) -> EdgeVersion:
        """Create from dictionary."""
        spec_data = data.get("spec", {})
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        return cls(
            version=data["version"],
            spec=EdgeSpec.from_dict(spec_data),
            created_at=created_at or datetime.utcnow(),
            is_published=data.get("is_published", False),
        )


class EdgeEntry(BaseModel):
    """
    Entry containing all versions of an edge.
    
    Similar to NodeEntry, manages multiple versions.
    """
    id: str = Field(..., description="Edge ID")
    versions: Dict[str, EdgeVersion] = Field(default_factory=dict, description="Version map")
    
    # Private attrs for tracking
    _latest_version: str = PrivateAttr(default="")
    
    def model_post_init(self, __context: Any) -> None:
        """Initialize after model creation."""
        if self.versions:
            versions = sorted(self.versions.keys(), key=lambda v: [int(x) for x in v.split(".")])
            self._latest_version = versions[-1] if versions else ""
    
    def get_version(self, version: str) -> Optional[EdgeVersion]:
        """Get a specific version."""
        return self.versions.get(version)
    
    def get_latest_version(self) -> Optional[str]:
        """Get the latest version string."""
        return self._latest_version or None
    
    def get_latest(self) -> Optional[EdgeVersion]:
        """Get the latest version entry."""
        if self._latest_version:
            return self.versions.get(self._latest_version)
        return None
    
    def version_exists(self, version: str) -> bool:
        """Check if version exists."""
        return version in self.versions
    
    def add_version(self, edge_version: EdgeVersion) -> None:
        """Add a new version."""
        if self.version_exists(edge_version.version):
            raise ValueError(
                ERROR_VERSION_EXISTS.format(
                    version=edge_version.version,
                    entity_type="edge",
                    id=self.id
                )
            )
        self.versions[edge_version.version] = edge_version
        
        versions = sorted(self.versions.keys(), key=lambda v: [int(x) for x in v.split(".")])
        self._latest_version = versions[-1]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "versions": {v: ev.to_dict() for v, ev in self.versions.items()},
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EdgeEntry:
        """Create from dictionary."""
        versions = {
            v: EdgeVersion.from_dict(ev_data)
            for v, ev_data in data.get("versions", {}).items()
        }
        return cls(id=data["id"], versions=versions)
