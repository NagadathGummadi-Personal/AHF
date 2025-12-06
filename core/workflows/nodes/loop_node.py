"""
Loop Node Implementation Module.

This module provides a node that implements loop/repeat functionality,
sending results back to an earlier node until a condition is met.
"""

import logging
from typing import Any, Dict, List, Optional

from ..interfaces import IWorkflowContext
from ..enum import NodeType, DataFormat, DataType, ConditionOperator
from ..spec import NodeSpec, IOSpec, IOFieldSpec, ConditionSpec
from ..exceptions import NodeExecutionError
from .base_node import BaseNode

logger = logging.getLogger(__name__)


class LoopNode(BaseNode):
    """
    A node that implements loop/repeat functionality.
    
    Evaluates a condition and either continues the loop (routes back to 
    loop start) or exits (routes to next node).
    
    Configuration:
        condition: Condition to check for loop continuation
        max_iterations: Maximum iterations before forced exit (default: 10)
        loop_back_to: Node ID to loop back to when continuing
        exit_to: Node ID to go to when condition met
        iteration_var: Variable name to track iteration count
        accumulator_var: Variable name to accumulate results (optional)
        
    Input Spec:
        - data: Input data from the loop body (any)
        
    Output Spec:
        - continue_loop: Whether to continue looping (boolean)
        - iteration: Current iteration count (integer)
        - data: Pass-through data (any)
        - accumulated: Accumulated results if accumulator enabled (array)
    """
    
    DEFAULT_INPUT_SPEC = IOSpec(
        fields=[
            IOFieldSpec(
                name="data",
                data_type=DataType.ANY,
                required=False,
                description="Data from loop body"
            ),
        ],
        format=DataFormat.JSON,
        description="Input for Loop node"
    )
    
    DEFAULT_OUTPUT_SPEC = IOSpec(
        fields=[
            IOFieldSpec(
                name="continue_loop",
                data_type=DataType.BOOLEAN,
                required=True,
                description="Whether to continue looping"
            ),
            IOFieldSpec(
                name="iteration",
                data_type=DataType.INTEGER,
                required=True,
                description="Current iteration count"
            ),
            IOFieldSpec(
                name="data",
                data_type=DataType.ANY,
                required=False,
                description="Pass-through data"
            ),
            IOFieldSpec(
                name="accumulated",
                data_type=DataType.ARRAY,
                required=False,
                description="Accumulated results from all iterations"
            ),
        ],
        format=DataFormat.JSON,
        description="Output from Loop node"
    )
    
    def __init__(self, spec: NodeSpec):
        """
        Initialize the loop node.
        
        Args:
            spec: Node specification.
        """
        if spec.node_type != NodeType.LOOP:
            spec.node_type = NodeType.LOOP
        
        if not spec.input_spec:
            spec.input_spec = self.DEFAULT_INPUT_SPEC
        if not spec.output_spec:
            spec.output_spec = self.DEFAULT_OUTPUT_SPEC
        
        super().__init__(spec)
        
        self._max_iterations = self._config.get("max_iterations", 10)
        self._loop_back_to = self._config.get("loop_back_to")
        self._exit_to = self._config.get("exit_to")
        self._iteration_var = self._config.get("iteration_var", "loop_iteration")
        self._accumulator_var = self._config.get("accumulator_var")
        
        # Parse condition
        condition_config = self._config.get("condition", {})
        self._condition = ConditionSpec(**condition_config) if condition_config else None
        
        # Exit condition (alternative way to specify)
        self._exit_field = self._config.get("exit_field")
        self._exit_value = self._config.get("exit_value", True)
    
    async def execute(
        self,
        input_data: Any,
        context: IWorkflowContext,
    ) -> Any:
        """
        Execute the loop control logic.
        
        Args:
            input_data: Input from loop body.
            context: Workflow execution context.
            
        Returns:
            Output indicating whether to continue looping.
        """
        logger.info(f"Executing loop node: {self._name}")
        
        # Resolve input
        resolved_input = self._resolve_input(context, input_data)
        
        # Get/increment iteration counter
        iteration = context.get(self._iteration_var, 0)
        iteration += 1
        context.set(self._iteration_var, iteration)
        
        logger.debug(f"Loop iteration: {iteration}")
        
        # Accumulate results if configured
        accumulated = []
        if self._accumulator_var:
            accumulated = context.get(self._accumulator_var, [])
            if input_data is not None:
                accumulated.append(input_data)
            context.set(self._accumulator_var, accumulated)
        
        # Check max iterations
        if iteration >= self._max_iterations:
            logger.info(f"Loop {self._name}: max iterations ({self._max_iterations}) reached")
            return self._build_exit_output(iteration, input_data, accumulated)
        
        # Evaluate exit condition
        should_exit = self._evaluate_exit_condition(context, input_data)
        
        if should_exit:
            logger.info(f"Loop {self._name}: exit condition met at iteration {iteration}")
            return self._build_exit_output(iteration, input_data, accumulated)
        
        # Continue looping
        logger.info(f"Loop {self._name}: continuing at iteration {iteration}")
        
        # Store loop state for edge evaluation
        context.set("loop_continue", True)
        context.set("loop_target", self._loop_back_to)
        
        return {
            "continue_loop": True,
            "iteration": iteration,
            "data": input_data,
            "accumulated": accumulated,
            "loop_back_to": self._loop_back_to,
        }
    
    def _build_exit_output(
        self,
        iteration: int,
        data: Any,
        accumulated: List[Any],
    ) -> Dict[str, Any]:
        """Build output for loop exit."""
        return {
            "continue_loop": False,
            "iteration": iteration,
            "data": data,
            "accumulated": accumulated,
            "exit_to": self._exit_to,
        }
    
    def _evaluate_exit_condition(
        self,
        context: IWorkflowContext,
        input_data: Any,
    ) -> bool:
        """Evaluate whether to exit the loop."""
        # Check using condition spec
        if self._condition:
            value = self._resolve_path(self._condition.field, context, input_data)
            return self._evaluate_condition(value, self._condition)
        
        # Check using exit_field
        if self._exit_field:
            value = self._resolve_path(self._exit_field, context, input_data)
            return value == self._exit_value
        
        # Default: never exit (rely on max_iterations)
        return False
    
    def _evaluate_condition(self, value: Any, condition: ConditionSpec) -> bool:
        """Evaluate a single condition."""
        target = condition.value
        op = condition.operator
        
        if op == ConditionOperator.EQUALS:
            result = value == target
        elif op == ConditionOperator.NOT_EQUALS:
            result = value != target
        elif op == ConditionOperator.GREATER_THAN:
            result = value > target
        elif op == ConditionOperator.LESS_THAN:
            result = value < target
        elif op == ConditionOperator.GREATER_OR_EQUAL:
            result = value >= target
        elif op == ConditionOperator.LESS_OR_EQUAL:
            result = value <= target
        elif op == ConditionOperator.IS_TRUE:
            result = bool(value)
        elif op == ConditionOperator.IS_FALSE:
            result = not bool(value)
        elif op == ConditionOperator.IS_EMPTY:
            result = not value
        elif op == ConditionOperator.IS_NOT_EMPTY:
            result = bool(value)
        elif op == ConditionOperator.CONTAINS:
            result = target in value if value else False
        else:
            result = value == target
        
        return not result if condition.negate else result
    
    async def validate(self, context: IWorkflowContext) -> List[str]:
        """Validate loop node configuration."""
        errors = await super().validate(context)
        
        if self._max_iterations < 1:
            errors.append(f"Loop node {self._name}: max_iterations must be >= 1")
        
        if not self._condition and not self._exit_field:
            logger.warning(
                f"Loop node {self._name}: no exit condition, will run until max_iterations"
            )
        
        return errors
    
    def reset_iteration(self, context: IWorkflowContext) -> None:
        """Reset iteration counter in context."""
        context.set(self._iteration_var, 0)
        if self._accumulator_var:
            context.set(self._accumulator_var, [])


