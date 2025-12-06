"""
Switch Node Implementation Module.

This module provides a node that performs switch/case routing based on
matching a variable against multiple possible values.
"""

import logging
from typing import Any, Dict, List, Optional

from ..interfaces import IWorkflowContext
from ..enum import NodeType, DataFormat, DataType
from ..spec import NodeSpec, IOSpec, IOFieldSpec
from ..exceptions import NodeExecutionError
from .base_node import BaseNode

logger = logging.getLogger(__name__)


class CaseSpec:
    """Specification for a switch case."""
    
    def __init__(
        self,
        value: Any,
        target_node_id: str,
        label: Optional[str] = None,
    ):
        self.value = value
        self.target_node_id = target_node_id
        self.label = label or str(value)


class SwitchNode(BaseNode):
    """
    A node that performs switch/case routing.
    
    Examines a variable and routes to different target nodes based on
    the value. Supports multiple cases with a default fallback.
    
    Configuration:
        switch_field: Field/path to examine (e.g., "$output.intent", "$ctx.action")
        cases: List of case definitions with value and target_node_id
        default_target: Target node if no case matches (optional)
        case_sensitive: Whether string matching is case-sensitive (default: True)
        
    Input Spec:
        - value: The value to switch on (any type)
        
    Output Spec:
        - matched_case: The case label that matched (string)
        - target_node: The target node ID to route to (string)
        - value: The original value examined (any)
    """
    
    DEFAULT_INPUT_SPEC = IOSpec(
        fields=[
            IOFieldSpec(
                name="value",
                data_type=DataType.ANY,
                required=False,
                description="The value to switch on (or use switch_field config)"
            ),
        ],
        format=DataFormat.JSON,
        description="Input for Switch node"
    )
    
    DEFAULT_OUTPUT_SPEC = IOSpec(
        fields=[
            IOFieldSpec(
                name="matched_case",
                data_type=DataType.STRING,
                required=True,
                description="Label of the matched case"
            ),
            IOFieldSpec(
                name="target_node",
                data_type=DataType.STRING,
                required=True,
                description="Target node ID to route to"
            ),
            IOFieldSpec(
                name="value",
                data_type=DataType.ANY,
                required=True,
                description="The original value examined"
            ),
        ],
        format=DataFormat.JSON,
        description="Output from Switch node"
    )
    
    def __init__(self, spec: NodeSpec):
        """
        Initialize the switch node.
        
        Args:
            spec: Node specification.
        """
        if spec.node_type != NodeType.SWITCH:
            spec.node_type = NodeType.SWITCH
        
        if not spec.input_spec:
            spec.input_spec = self.DEFAULT_INPUT_SPEC
        if not spec.output_spec:
            spec.output_spec = self.DEFAULT_OUTPUT_SPEC
        
        super().__init__(spec)
        
        self._switch_field = self._config.get("switch_field")
        self._default_target = self._config.get("default_target")
        self._case_sensitive = self._config.get("case_sensitive", True)
        
        # Parse cases
        self._cases: List[CaseSpec] = []
        for case_def in self._config.get("cases", []):
            if isinstance(case_def, dict):
                self._cases.append(CaseSpec(
                    value=case_def.get("value"),
                    target_node_id=case_def.get("target_node_id", case_def.get("target")),
                    label=case_def.get("label"),
                ))
            elif isinstance(case_def, CaseSpec):
                self._cases.append(case_def)
    
    async def execute(
        self,
        input_data: Any,
        context: IWorkflowContext,
    ) -> Any:
        """
        Execute the switch logic.
        
        Args:
            input_data: Input containing the value to switch on.
            context: Workflow execution context.
            
        Returns:
            Output containing matched case and target node.
        """
        logger.info(f"Executing switch node: {self._name}")
        
        # Resolve input
        resolved_input = self._resolve_input(context, input_data)
        
        # Get the value to switch on
        if self._switch_field:
            switch_value = self._resolve_path(self._switch_field, context, input_data)
        else:
            switch_value = resolved_input.get("value", input_data)
        
        logger.debug(f"Switch value: {switch_value}")
        
        # Find matching case
        matched_case = None
        target_node = None
        
        for case in self._cases:
            if self._matches_case(switch_value, case.value):
                matched_case = case
                target_node = case.target_node_id
                break
        
        # Use default if no match
        if not matched_case and self._default_target:
            target_node = self._default_target
            matched_label = "default"
        elif matched_case:
            matched_label = matched_case.label
        else:
            raise NodeExecutionError(
                f"No matching case found for value: {switch_value}",
                node_id=self._id,
                node_type=self._node_type.value,
                details={"value": switch_value, "available_cases": [c.label for c in self._cases]},
            )
        
        # Store routing decision in context for edge evaluation
        context.set("switch_target", target_node)
        context.set("switch_value", switch_value)
        context.set("switch_case", matched_label)
        
        result = {
            "matched_case": matched_label,
            "target_node": target_node,
            "value": switch_value,
        }
        
        logger.info(f"Switch node {self._name}: matched '{matched_label}' -> {target_node}")
        return result
    
    def _matches_case(self, value: Any, case_value: Any) -> bool:
        """Check if value matches case value."""
        if isinstance(value, str) and isinstance(case_value, str):
            if self._case_sensitive:
                return value == case_value
            return value.lower() == case_value.lower()
        
        # Handle list case values (any match)
        if isinstance(case_value, list):
            for cv in case_value:
                if self._matches_case(value, cv):
                    return True
            return False
        
        return value == case_value
    
    async def validate(self, context: IWorkflowContext) -> List[str]:
        """Validate switch node configuration."""
        errors = await super().validate(context)
        
        if not self._cases and not self._default_target:
            errors.append(f"Switch node {self._name}: Must specify at least one case or default_target")
        
        for i, case in enumerate(self._cases):
            if not case.target_node_id:
                errors.append(f"Switch node {self._name}: Case {i} missing target_node_id")
        
        return errors
    
    def add_case(self, value: Any, target_node_id: str, label: Optional[str] = None) -> None:
        """Add a case to the switch."""
        self._cases.append(CaseSpec(value=value, target_node_id=target_node_id, label=label))
    
    def set_default(self, target_node_id: str) -> None:
        """Set the default target."""
        self._default_target = target_node_id
    
    def get_possible_targets(self) -> List[str]:
        """Get all possible target node IDs."""
        targets = [c.target_node_id for c in self._cases]
        if self._default_target:
            targets.append(self._default_target)
        return targets


