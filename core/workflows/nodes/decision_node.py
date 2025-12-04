"""
Decision Node Implementation Module.

This module provides a node that makes routing decisions based on conditions.
"""

import logging
from typing import Any, Dict, List, Optional

from ..interfaces import IWorkflowContext
from ..enum import NodeType, ConditionOperator
from ..spec import NodeSpec, ConditionSpec
from ..exceptions import NodeExecutionError, ConditionEvaluationError
from .base_node import BaseNode

logger = logging.getLogger(__name__)


class DecisionNode(BaseNode):
    """
    A node that evaluates conditions and routes to different branches.
    
    The decision node doesn't transform data - it simply evaluates conditions
    and provides routing information for the workflow engine.
    
    Configuration:
        conditions: List of condition specs to evaluate
        default_output: Output value when no conditions match
        output_field: Field name for the decision result (default: "decision")
    """
    
    def __init__(self, spec: NodeSpec):
        """
        Initialize the decision node.
        
        Args:
            spec: Node specification.
        """
        if spec.node_type != NodeType.DECISION:
            spec.node_type = NodeType.DECISION
        
        super().__init__(spec)
        
        self._output_field = self._config.get("output_field", "decision")
        self._default_output = self._config.get("default_output", "default")
    
    async def execute(
        self,
        input_data: Any,
        context: IWorkflowContext,
    ) -> Any:
        """
        Evaluate conditions and return the decision result.
        
        The result can be used by the workflow router to determine
        which edge(s) to follow.
        
        Args:
            input_data: Input from previous node.
            context: Workflow execution context.
            
        Returns:
            Dictionary with decision field indicating the matched condition.
        """
        logger.info(f"Executing decision node: {self._name}")
        
        # Resolve input
        resolved_input = self._resolve_input(context, input_data)
        
        # Store input in context for condition evaluation
        context.set("__decision_input__", resolved_input)
        
        # Get conditions from config
        conditions = self._config.get("conditions", [])
        
        matched_result = None
        
        for condition_data in conditions:
            try:
                condition = ConditionSpec(**condition_data) if isinstance(condition_data, dict) else condition_data
                
                if self._evaluate_condition(condition, context, resolved_input):
                    matched_result = condition_data.get("result", condition_data.get("name", "matched"))
                    logger.debug(f"Decision node {self._name}: Matched condition -> {matched_result}")
                    break
                    
            except Exception as e:
                logger.warning(f"Error evaluating condition in {self._name}: {e}")
                continue
        
        # Use default if no match
        if matched_result is None:
            matched_result = self._default_output
            logger.debug(f"Decision node {self._name}: No match, using default -> {matched_result}")
        
        result = {
            self._output_field: matched_result,
            "input": resolved_input,
        }
        
        return result
    
    def _evaluate_condition(
        self,
        condition: ConditionSpec,
        context: IWorkflowContext,
        input_data: Any,
    ) -> bool:
        """
        Evaluate a single condition.
        
        Args:
            condition: Condition to evaluate.
            context: Workflow context.
            input_data: Resolved input data.
            
        Returns:
            True if condition is met, False otherwise.
        """
        # Resolve the field value
        field_value = self._resolve_field(condition.field, context, input_data)
        compare_value = condition.value
        
        try:
            result = self._apply_operator(condition.operator, field_value, compare_value)
            
            # Apply negation if specified
            if condition.negate:
                result = not result
            
            return result
            
        except Exception as e:
            raise ConditionEvaluationError(
                f"Failed to evaluate condition: {e}",
                condition=str(condition.model_dump()),
            ) from e
    
    def _resolve_field(
        self,
        field: str,
        context: IWorkflowContext,
        input_data: Any,
    ) -> Any:
        """Resolve a field path to its value."""
        if field.startswith("$"):
            return self._resolve_path(field, context, input_data)
        
        # Try to get from input_data
        if isinstance(input_data, dict):
            return input_data.get(field)
        
        return getattr(input_data, field, None) if hasattr(input_data, field) else None
    
    def _apply_operator(
        self,
        operator: ConditionOperator,
        field_value: Any,
        compare_value: Any,
    ) -> bool:
        """Apply a comparison operator."""
        import re
        
        if operator == ConditionOperator.EQUALS:
            return field_value == compare_value
        
        elif operator == ConditionOperator.NOT_EQUALS:
            return field_value != compare_value
        
        elif operator == ConditionOperator.CONTAINS:
            if isinstance(field_value, str):
                return str(compare_value) in field_value
            elif isinstance(field_value, (list, tuple)):
                return compare_value in field_value
            return False
        
        elif operator == ConditionOperator.NOT_CONTAINS:
            if isinstance(field_value, str):
                return str(compare_value) not in field_value
            elif isinstance(field_value, (list, tuple)):
                return compare_value not in field_value
            return True
        
        elif operator == ConditionOperator.GREATER_THAN:
            return field_value > compare_value
        
        elif operator == ConditionOperator.LESS_THAN:
            return field_value < compare_value
        
        elif operator == ConditionOperator.GREATER_OR_EQUAL:
            return field_value >= compare_value
        
        elif operator == ConditionOperator.LESS_OR_EQUAL:
            return field_value <= compare_value
        
        elif operator == ConditionOperator.IS_EMPTY:
            if field_value is None:
                return True
            if isinstance(field_value, (str, list, dict)):
                return len(field_value) == 0
            return False
        
        elif operator == ConditionOperator.IS_NOT_EMPTY:
            if field_value is None:
                return False
            if isinstance(field_value, (str, list, dict)):
                return len(field_value) > 0
            return True
        
        elif operator == ConditionOperator.MATCHES_REGEX:
            if not isinstance(field_value, str):
                return False
            try:
                return bool(re.match(str(compare_value), field_value))
            except re.error:
                return False
        
        elif operator == ConditionOperator.STARTS_WITH:
            return str(field_value).startswith(str(compare_value))
        
        elif operator == ConditionOperator.ENDS_WITH:
            return str(field_value).endswith(str(compare_value))
        
        elif operator == ConditionOperator.IN_LIST:
            if isinstance(compare_value, (list, tuple)):
                return field_value in compare_value
            return False
        
        elif operator == ConditionOperator.NOT_IN_LIST:
            if isinstance(compare_value, (list, tuple)):
                return field_value not in compare_value
            return True
        
        elif operator == ConditionOperator.IS_TRUE:
            return bool(field_value) is True
        
        elif operator == ConditionOperator.IS_FALSE:
            return bool(field_value) is False
        
        else:
            # Unknown operator
            return False
    
    async def validate(self, context: IWorkflowContext) -> List[str]:
        """Validate decision node configuration."""
        errors = await super().validate(context)
        
        conditions = self._config.get("conditions", [])
        if not conditions:
            errors.append(
                f"Decision node {self._name}: Must have at least one condition"
            )
        
        return errors

