"""
Base Edge Classes

Abstract base class for workflow edges.
Implements IEdge from core.workflows.interfaces.

Version: 1.0.0
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field

from core.workflows.interfaces import IEdge
from core.workflows.spec import EdgeSpec, PassThroughConfig, PassThroughField


class EdgeCondition(BaseModel):
    """
    Condition for edge traversal.
    
    Can be:
    - Static (always true/false)
    - Variable-based (check session variable)
    - Output-based (check previous node output)
    - LLM-based (use LLM to evaluate)
    """
    
    condition_type: str = Field(
        default="static",
        description="Type: static, variable, output, llm"
    )
    
    # For static
    static_value: bool = Field(default=True)
    
    # For variable-based
    variable_name: Optional[str] = Field(default=None)
    expected_value: Optional[Any] = Field(default=None)
    operator: str = Field(default="eq", description="eq, ne, gt, lt, contains, in")
    
    # For output-based
    output_field: Optional[str] = Field(default=None)
    
    # For LLM-based
    llm_prompt: Optional[str] = Field(default=None)
    
    def evaluate(
        self,
        context: Dict[str, Any],
        node_output: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Evaluate the condition."""
        if self.condition_type == "static":
            return self.static_value
        
        elif self.condition_type == "variable":
            if not self.variable_name:
                return False
            actual = context.get(self.variable_name)
            return self._compare(actual, self.expected_value)
        
        elif self.condition_type == "output":
            if not node_output or not self.output_field:
                return False
            actual = node_output.get(self.output_field)
            return self._compare(actual, self.expected_value)
        
        return False
    
    def _compare(self, actual: Any, expected: Any) -> bool:
        """Compare values based on operator."""
        if self.operator == "eq":
            return actual == expected
        elif self.operator == "ne":
            return actual != expected
        elif self.operator == "gt":
            return actual > expected
        elif self.operator == "lt":
            return actual < expected
        elif self.operator == "contains":
            return expected in actual if actual else False
        elif self.operator == "in":
            return actual in expected if expected else False
        elif self.operator == "truthy":
            return bool(actual)
        elif self.operator == "falsy":
            return not bool(actual)
        return False


class BaseEdge(ABC):
    """
    Base class for workflow edges.
    
    Edges connect nodes and control workflow routing.
    They can:
    - Evaluate conditions for traversal
    - Transform data between nodes (pass-through)
    - Prompt for required variables
    """
    
    def __init__(
        self,
        edge_id: str,
        source_node: str,
        target_node: str,
        name: str = "",
        description: str = "",
        condition: Optional[EdgeCondition] = None,
        pass_through_fields: Optional[List[PassThroughField]] = None,
    ):
        self._edge_id = edge_id
        self._source_node = source_node
        self._target_node = target_node
        self._name = name or f"{source_node}_to_{target_node}"
        self._description = description
        self._condition = condition or EdgeCondition(condition_type="static", static_value=True)
        self._pass_through_fields = pass_through_fields or []
        
        # Build spec
        self._spec = EdgeSpec(
            edge_id=edge_id,
            edge_name=self._name,
            source_node=source_node,
            target_node=target_node,
            description=description,
        )
    
    @property
    def spec(self) -> EdgeSpec:
        """Get edge specification."""
        return self._spec
    
    @property
    def edge_id(self) -> str:
        """Get edge ID."""
        return self._edge_id
    
    @property
    def source_node(self) -> str:
        """Get source node ID."""
        return self._source_node
    
    @property
    def target_node(self) -> str:
        """Get target node ID."""
        return self._target_node
    
    def should_traverse(self, context: Dict[str, Any]) -> bool:
        """
        Determine if this edge should be traversed.
        
        Args:
            context: Current workflow context including:
                - session variables
                - previous node output
                - dynamic variables
                
        Returns:
            True if edge should be traversed
        """
        node_output = context.get("node_output")
        return self._condition.evaluate(context, node_output)
    
    def transform_data(self, source_output: Any) -> Any:
        """
        Transform source node output for target node input.
        
        Applies pass-through field mappings.
        
        Args:
            source_output: Output from source node
            
        Returns:
            Transformed data for target node
        """
        if not self._pass_through_fields:
            return source_output
        
        if not isinstance(source_output, dict):
            return source_output
        
        result = {}
        
        for field in self._pass_through_fields:
            value = self._extract_field(source_output, field.source_field)
            
            if value is None and field.required:
                # Field is required but missing - will need to prompt
                result[field.target_field] = None
                result[f"_missing_{field.target_field}"] = True
            else:
                result[field.target_field] = value
        
        return result
    
    def _extract_field(self, data: Dict[str, Any], field_path: str) -> Any:
        """Extract a field from nested data using dot notation."""
        parts = field_path.split(".")
        current = data
        
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
            
            if current is None:
                return None
        
        return current
    
    def get_missing_required_fields(
        self,
        source_output: Any,
    ) -> List[PassThroughField]:
        """Get list of required fields that are missing."""
        if not self._pass_through_fields or not isinstance(source_output, dict):
            return []
        
        missing = []
        for field in self._pass_through_fields:
            if field.required:
                value = self._extract_field(source_output, field.source_field)
                if value is None:
                    missing.append(field)
        
        return missing


class ConditionalEdge(BaseEdge):
    """
    Edge with a custom condition function.
    
    Allows complex condition logic via a callable.
    """
    
    def __init__(
        self,
        edge_id: str,
        source_node: str,
        target_node: str,
        condition_fn: Callable[[Dict[str, Any]], bool],
        **kwargs,
    ):
        super().__init__(edge_id, source_node, target_node, **kwargs)
        self._condition_fn = condition_fn
    
    def should_traverse(self, context: Dict[str, Any]) -> bool:
        """Evaluate custom condition function."""
        try:
            return self._condition_fn(context)
        except Exception:
            return False

