"""
Base Edge Implementation Module.

This module provides the base class for all workflow edges.
"""

import logging
from typing import Any, Dict, List, Optional

from ..interfaces import IEdge, ICondition, IDataTransformer, IWorkflowContext
from ..enum import EdgeType, ConditionOperator
from ..spec import EdgeSpec, ConditionSpec, TransformSpec

logger = logging.getLogger(__name__)


class BaseCondition(ICondition):
    """
    Base implementation of a condition.
    
    Evaluates a single condition against workflow context.
    """
    
    def __init__(self, spec: ConditionSpec):
        """
        Initialize the condition.
        
        Args:
            spec: Condition specification.
        """
        self._spec = spec
        self._field = spec.field
        self._operator = spec.operator
        self._value = spec.value
        self._negate = spec.negate
    
    @property
    def operator(self) -> ConditionOperator:
        """Get the condition operator."""
        return self._operator
    
    @property
    def field(self) -> str:
        """Get the field to evaluate."""
        return self._field
    
    @property
    def value(self) -> Any:
        """Get the comparison value."""
        return self._value
    
    def evaluate(self, context: IWorkflowContext) -> bool:
        """
        Evaluate the condition against context.
        
        Args:
            context: Workflow execution context.
            
        Returns:
            True if condition is met.
        """
        import re
        
        # Resolve the field value
        field_value = self._resolve_field(self._field, context)
        compare_value = self._value
        
        # Apply operator
        result = self._apply_operator(field_value, compare_value)
        
        # Apply negation
        if self._negate:
            result = not result
        
        return result
    
    def _resolve_field(self, field: str, context: IWorkflowContext) -> Any:
        """Resolve a field path to its value."""
        if not field.startswith("$"):
            return field  # Literal value
        
        parts = field.split(".")
        prefix = parts[0]
        
        if prefix == "$input":
            value = context.input_data
            parts = parts[1:]
        elif prefix == "$output":
            value = context.output_data
            parts = parts[1:]
        elif prefix == "$node":
            if len(parts) < 2:
                return None
            node_id = parts[1]
            value = context.get_node_output(node_id)
            parts = parts[2:]
        elif prefix in ("$ctx", "$context"):
            if len(parts) < 2:
                return context.variables
            value = context.get(parts[1])
            parts = parts[2:]
        else:
            return None
        
        # Navigate nested path
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
    
    def _apply_operator(self, field_value: Any, compare_value: Any) -> bool:
        """Apply the comparison operator."""
        import re
        
        op = self._operator
        
        if op == ConditionOperator.EQUALS:
            return field_value == compare_value
        
        elif op == ConditionOperator.NOT_EQUALS:
            return field_value != compare_value
        
        elif op == ConditionOperator.CONTAINS:
            if isinstance(field_value, str):
                return str(compare_value) in field_value
            if isinstance(field_value, (list, tuple)):
                return compare_value in field_value
            return False
        
        elif op == ConditionOperator.NOT_CONTAINS:
            if isinstance(field_value, str):
                return str(compare_value) not in field_value
            if isinstance(field_value, (list, tuple)):
                return compare_value not in field_value
            return True
        
        elif op == ConditionOperator.GREATER_THAN:
            return field_value is not None and field_value > compare_value
        
        elif op == ConditionOperator.LESS_THAN:
            return field_value is not None and field_value < compare_value
        
        elif op == ConditionOperator.GREATER_OR_EQUAL:
            return field_value is not None and field_value >= compare_value
        
        elif op == ConditionOperator.LESS_OR_EQUAL:
            return field_value is not None and field_value <= compare_value
        
        elif op == ConditionOperator.IS_EMPTY:
            if field_value is None:
                return True
            if isinstance(field_value, (str, list, dict)):
                return len(field_value) == 0
            return False
        
        elif op == ConditionOperator.IS_NOT_EMPTY:
            if field_value is None:
                return False
            if isinstance(field_value, (str, list, dict)):
                return len(field_value) > 0
            return True
        
        elif op == ConditionOperator.MATCHES_REGEX:
            if not isinstance(field_value, str):
                return False
            try:
                return bool(re.match(str(compare_value), field_value))
            except re.error:
                return False
        
        elif op == ConditionOperator.STARTS_WITH:
            return str(field_value).startswith(str(compare_value))
        
        elif op == ConditionOperator.ENDS_WITH:
            return str(field_value).endswith(str(compare_value))
        
        elif op == ConditionOperator.IN_LIST:
            if isinstance(compare_value, (list, tuple)):
                return field_value in compare_value
            return False
        
        elif op == ConditionOperator.NOT_IN_LIST:
            if isinstance(compare_value, (list, tuple)):
                return field_value not in compare_value
            return True
        
        elif op == ConditionOperator.IS_TRUE:
            return bool(field_value) is True
        
        elif op == ConditionOperator.IS_FALSE:
            return bool(field_value) is False
        
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize condition to dictionary."""
        return {
            "field": self._field,
            "operator": self._operator.value,
            "value": self._value,
            "negate": self._negate,
        }


class BaseEdge(IEdge):
    """
    Base implementation of a workflow edge.
    
    Connects two nodes and supports conditions and data transformation.
    """
    
    def __init__(
        self,
        spec: EdgeSpec,
        transformer: Optional[IDataTransformer] = None,
    ):
        """
        Initialize the edge.
        
        Args:
            spec: Edge specification.
            transformer: Optional data transformer.
        """
        self._spec = spec
        self._id = spec.id
        self._source_id = spec.source_id
        self._target_id = spec.target_id
        self._edge_type = spec.edge_type
        self._priority = spec.priority
        self._metadata = dict(spec.metadata)
        
        # Build conditions
        self._conditions: List[ICondition] = []
        for cond_spec in spec.conditions:
            self._conditions.append(BaseCondition(cond_spec))
        
        # Set transformer
        self._transformer = transformer
        if spec.transform and not transformer:
            self._transformer = self._create_transformer(spec.transform)
        
        logger.debug(
            f"Initialized edge: {self._id} ({self._source_id} -> {self._target_id})"
        )
    
    @property
    def id(self) -> str:
        """Get the unique edge ID."""
        return self._id
    
    @property
    def source_id(self) -> str:
        """Get the source node ID."""
        return self._source_id
    
    @property
    def target_id(self) -> str:
        """Get the target node ID."""
        return self._target_id
    
    @property
    def edge_type(self) -> EdgeType:
        """Get the edge type."""
        return self._edge_type
    
    @property
    def conditions(self) -> List[ICondition]:
        """Get the edge conditions."""
        return self._conditions
    
    @property
    def transformer(self) -> Optional[IDataTransformer]:
        """Get the data transformer."""
        return self._transformer
    
    @property
    def priority(self) -> int:
        """Get the edge priority."""
        return self._priority
    
    @property
    def metadata(self) -> Dict[str, Any]:
        """Get edge metadata."""
        return self._metadata
    
    def can_traverse(self, context: IWorkflowContext) -> bool:
        """
        Check if this edge can be traversed.
        
        All conditions must be met (AND logic).
        
        Args:
            context: Workflow execution context.
            
        Returns:
            True if all conditions pass.
        """
        if not self._conditions:
            return True  # No conditions = always passable
        
        for condition in self._conditions:
            if not condition.evaluate(context):
                return False
        
        return True
    
    async def transform_data(
        self,
        data: Any,
        context: IWorkflowContext,
    ) -> Any:
        """
        Apply transformation to data.
        
        Args:
            data: Data to transform.
            context: Workflow execution context.
            
        Returns:
            Transformed data.
        """
        if self._transformer:
            return await self._transformer.transform(data, context)
        return data
    
    def _create_transformer(self, spec: TransformSpec) -> Optional[IDataTransformer]:
        """Create a transformer from spec."""
        from .data_transformer import DataTransformer
        return DataTransformer(spec)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize edge to dictionary."""
        return {
            "id": self._id,
            "source_id": self._source_id,
            "target_id": self._target_id,
            "edge_type": self._edge_type.value,
            "conditions": [c.to_dict() for c in self._conditions],
            "transform": self._spec.transform.model_dump() if self._spec.transform else None,
            "priority": self._priority,
            "metadata": self._metadata,
        }
    
    def __repr__(self) -> str:
        return f"<Edge(id={self._id}, {self._source_id} -> {self._target_id})>"

