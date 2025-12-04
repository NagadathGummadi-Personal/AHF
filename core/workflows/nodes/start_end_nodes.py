"""
Start and End Node Implementation Module.

This module provides the start and end marker nodes for workflows.
"""

import logging
from typing import Any, Dict, List, Optional

from ..interfaces import IWorkflowContext
from ..enum import NodeType
from ..spec import NodeSpec
from ..constants import NODE_ID_START, NODE_ID_END
from .base_node import BaseNode

logger = logging.getLogger(__name__)


class StartNode(BaseNode):
    """
    The entry point node for a workflow.
    
    The start node receives the initial workflow input and can perform
    initial validation and transformation before passing to the first
    processing node.
    
    Configuration:
        validate_input: Whether to validate input schema (default: False)
        input_schema: JSON schema for input validation
        default_values: Default values for missing input fields
    """
    
    def __init__(self, spec: Optional[NodeSpec] = None):
        """
        Initialize the start node.
        
        Args:
            spec: Optional node specification. If not provided, a default is created.
        """
        if spec is None:
            spec = NodeSpec(
                id=NODE_ID_START,
                name="Start",
                node_type=NodeType.START,
                description="Workflow entry point",
            )
        elif spec.node_type != NodeType.START:
            spec.node_type = NodeType.START
        
        super().__init__(spec)
        
        self._validate_input = self._config.get("validate_input", False)
        self._input_schema = self._config.get("input_schema")
        self._default_values = self._config.get("default_values", {})
    
    async def execute(
        self,
        input_data: Any,
        context: IWorkflowContext,
    ) -> Any:
        """
        Process the initial workflow input.
        
        Args:
            input_data: Initial workflow input.
            context: Workflow execution context.
            
        Returns:
            Processed input ready for workflow processing.
        """
        logger.info(f"Start node: Beginning workflow execution")
        
        # Store original input in context
        context.set("__original_input__", input_data)
        
        # Apply default values
        if isinstance(input_data, dict) and self._default_values:
            for key, value in self._default_values.items():
                if key not in input_data:
                    input_data[key] = value
        
        # Validate input if configured
        if self._validate_input and self._input_schema:
            validation_errors = self._validate_against_schema(input_data)
            if validation_errors:
                context.set("__validation_errors__", validation_errors)
                logger.warning(f"Input validation errors: {validation_errors}")
        
        logger.debug(f"Start node: Input processed")
        return input_data
    
    def _validate_against_schema(self, data: Any) -> List[str]:
        """Validate data against JSON schema."""
        if not self._input_schema:
            return []
        
        try:
            import jsonschema
            validator = jsonschema.Draft7Validator(self._input_schema)
            errors = list(validator.iter_errors(data))
            return [str(e.message) for e in errors]
        except ImportError:
            logger.warning("jsonschema not installed, skipping validation")
            return []
        except Exception as e:
            return [f"Validation error: {e}"]
    
    async def validate(self, context: IWorkflowContext) -> List[str]:
        """Validate start node configuration."""
        errors = []
        
        if self._validate_input and not self._input_schema:
            errors.append(
                f"Start node: validate_input is True but no input_schema provided"
            )
        
        return errors


class EndNode(BaseNode):
    """
    The exit point node for a workflow.
    
    The end node receives the final output and can perform final
    transformation and validation before completing the workflow.
    
    Configuration:
        output_key: Key to extract from input as final output (optional)
        transform: Optional transformation to apply
        success_message: Message to include in result
    """
    
    def __init__(self, spec: Optional[NodeSpec] = None):
        """
        Initialize the end node.
        
        Args:
            spec: Optional node specification. If not provided, a default is created.
        """
        if spec is None:
            spec = NodeSpec(
                id=NODE_ID_END,
                name="End",
                node_type=NodeType.END,
                description="Workflow exit point",
            )
        elif spec.node_type != NodeType.END:
            spec.node_type = NodeType.END
        
        super().__init__(spec)
        
        self._output_key = self._config.get("output_key")
        self._success_message = self._config.get("success_message")
    
    async def execute(
        self,
        input_data: Any,
        context: IWorkflowContext,
    ) -> Any:
        """
        Process the final workflow output.
        
        Args:
            input_data: Output from the last processing node.
            context: Workflow execution context.
            
        Returns:
            Final workflow output.
        """
        logger.info(f"End node: Completing workflow execution")
        
        # Extract specific output key if configured
        if self._output_key and isinstance(input_data, dict):
            output = input_data.get(self._output_key, input_data)
        else:
            output = input_data
        
        # Store final output in context
        context.set("__final_output__", output)
        context.output_data = output
        
        # Add success message if configured
        if self._success_message and isinstance(output, dict):
            output["__message__"] = self._success_message
        
        logger.debug(f"End node: Workflow completed")
        return output
    
    async def validate(self, context: IWorkflowContext) -> List[str]:
        """Validate end node configuration."""
        return []  # End node has no required configuration

