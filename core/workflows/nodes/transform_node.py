"""
Transform Node Implementation Module.

This module provides a node that transforms data between formats.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from ..interfaces import IWorkflowContext
from ..enum import NodeType, DataTransformType
from ..spec import NodeSpec, TransformSpec
from ..exceptions import NodeExecutionError, TransformError
from .base_node import BaseNode

logger = logging.getLogger(__name__)


class TransformNode(BaseNode):
    """
    A node that transforms input data.
    
    Configuration:
        transform_type: Type of transformation
        template: Template string for TEMPLATE type
        mapping: Field mapping for MAP type
        expression: Expression for JMESPATH/JSONPATH/PYTHON types
        filter_config: Configuration for FILTER type
    """
    
    def __init__(self, spec: NodeSpec):
        """
        Initialize the transform node.
        
        Args:
            spec: Node specification.
        """
        if spec.node_type != NodeType.TRANSFORM:
            spec.node_type = NodeType.TRANSFORM
        
        super().__init__(spec)
        
        self._transform_type = DataTransformType(
            self._config.get("transform_type", DataTransformType.PASS_THROUGH)
        )
    
    async def execute(
        self,
        input_data: Any,
        context: IWorkflowContext,
    ) -> Any:
        """
        Transform the input data.
        
        Args:
            input_data: Input from previous node.
            context: Workflow execution context.
            
        Returns:
            Transformed data.
        """
        logger.info(f"Executing transform node: {self._name}")
        
        # Resolve input
        resolved_input = self._resolve_input(context, input_data)
        
        try:
            result = await self._apply_transform(resolved_input, context)
            logger.debug(f"Transform node {self._name} completed successfully")
            return result
            
        except TransformError:
            raise
        except Exception as e:
            logger.error(f"Transform node {self._name} failed: {e}")
            raise TransformError(
                f"Transform failed: {e}",
                transform_type=self._transform_type.value,
                details={"error": str(e)},
            ) from e
    
    async def _apply_transform(
        self,
        data: Any,
        context: IWorkflowContext,
    ) -> Any:
        """Apply the configured transformation."""
        if self._transform_type == DataTransformType.PASS_THROUGH:
            return data
        
        elif self._transform_type == DataTransformType.MAP:
            return self._transform_map(data)
        
        elif self._transform_type == DataTransformType.FILTER:
            return self._transform_filter(data)
        
        elif self._transform_type == DataTransformType.EXTRACT:
            return self._transform_extract(data)
        
        elif self._transform_type == DataTransformType.TEMPLATE:
            return self._transform_template(data, context)
        
        elif self._transform_type == DataTransformType.MERGE:
            return self._transform_merge(data, context)
        
        elif self._transform_type == DataTransformType.SPLIT:
            return self._transform_split(data)
        
        elif self._transform_type == DataTransformType.FORMAT:
            return self._transform_format(data)
        
        elif self._transform_type == DataTransformType.JMESPATH:
            return self._transform_jmespath(data)
        
        elif self._transform_type == DataTransformType.JSONPATH:
            return self._transform_jsonpath(data)
        
        elif self._transform_type == DataTransformType.PYTHON:
            return await self._transform_python(data, context)
        
        else:
            logger.warning(f"Unknown transform type: {self._transform_type}")
            return data
    
    def _transform_map(self, data: Any) -> Any:
        """Apply field mapping transformation."""
        mapping = self._config.get("mapping", {})
        
        if not mapping:
            return data
        
        if not isinstance(data, dict):
            return data
        
        result = {}
        for target_key, source_key in mapping.items():
            if isinstance(source_key, str):
                # Simple field mapping
                if source_key.startswith("$"):
                    # Literal value
                    result[target_key] = source_key[1:]
                else:
                    # Get from source data
                    result[target_key] = self._get_nested(data, source_key)
            else:
                # Direct value
                result[target_key] = source_key
        
        return result
    
    def _transform_filter(self, data: Any) -> Any:
        """Filter data based on configuration."""
        filter_config = self._config.get("filter_config", {})
        
        if not isinstance(data, list):
            return data
        
        field = filter_config.get("field")
        value = filter_config.get("value")
        operator = filter_config.get("operator", "equals")
        
        if not field:
            return data
        
        result = []
        for item in data:
            item_value = self._get_nested(item, field) if isinstance(item, dict) else None
            
            if operator == "equals" and item_value == value:
                result.append(item)
            elif operator == "not_equals" and item_value != value:
                result.append(item)
            elif operator == "contains" and value in str(item_value):
                result.append(item)
            elif operator == "exists" and item_value is not None:
                result.append(item)
        
        return result
    
    def _transform_extract(self, data: Any) -> Any:
        """Extract specific fields from data."""
        fields = self._config.get("fields", [])
        
        if not fields or not isinstance(data, dict):
            return data
        
        return {field: self._get_nested(data, field) for field in fields}
    
    def _transform_template(self, data: Any, context: IWorkflowContext) -> Any:
        """Apply template transformation."""
        template = self._config.get("template", "")
        
        if not template:
            return data
        
        # Build template context
        template_vars = {
            "input": data,
            "context": context.variables,
            "workflow_id": context.workflow_id,
        }
        
        if isinstance(data, dict):
            template_vars.update(data)
        
        # Simple string formatting
        try:
            return template.format(**template_vars)
        except KeyError:
            # Try with safer formatting
            import re
            result = template
            for key, value in template_vars.items():
                result = result.replace(f"{{{key}}}", str(value))
            return result
    
    def _transform_merge(self, data: Any, context: IWorkflowContext) -> Any:
        """Merge multiple data sources."""
        merge_sources = self._config.get("merge_sources", [])
        
        result = {}
        
        # Start with input data
        if isinstance(data, dict):
            result.update(data)
        
        # Merge additional sources from context
        for source in merge_sources:
            if source.startswith("$node."):
                node_id = source.split(".")[1]
                node_output = context.get_node_output(node_id)
                if isinstance(node_output, dict):
                    result.update(node_output)
            elif source.startswith("$ctx."):
                var_name = source.split(".")[1]
                var_value = context.get(var_name)
                if isinstance(var_value, dict):
                    result.update(var_value)
        
        return result
    
    def _transform_split(self, data: Any) -> Any:
        """Split data into multiple parts."""
        split_config = self._config.get("split_config", {})
        
        if isinstance(data, str):
            delimiter = split_config.get("delimiter", ",")
            return data.split(delimiter)
        
        if isinstance(data, dict):
            # Split into list of key-value pairs
            return [{"key": k, "value": v} for k, v in data.items()]
        
        return data
    
    def _transform_format(self, data: Any) -> Any:
        """Format data to specific output format."""
        output_format = self._config.get("output_format", "json")
        
        if output_format == "json":
            if isinstance(data, str):
                return data
            return json.dumps(data, indent=2)
        
        elif output_format == "string":
            return str(data)
        
        elif output_format == "pretty":
            return json.dumps(data, indent=2, sort_keys=True)
        
        return data
    
    def _transform_jmespath(self, data: Any) -> Any:
        """Apply JMESPath expression."""
        expression = self._config.get("expression", "")
        
        if not expression:
            return data
        
        try:
            import jmespath
            return jmespath.search(expression, data)
        except ImportError:
            logger.warning("jmespath not installed, returning data unchanged")
            return data
    
    def _transform_jsonpath(self, data: Any) -> Any:
        """Apply JSONPath expression."""
        expression = self._config.get("expression", "")
        
        if not expression:
            return data
        
        try:
            from jsonpath_ng import parse
            jsonpath_expr = parse(expression)
            matches = [match.value for match in jsonpath_expr.find(data)]
            return matches[0] if len(matches) == 1 else matches
        except ImportError:
            logger.warning("jsonpath-ng not installed, returning data unchanged")
            return data
    
    async def _transform_python(self, data: Any, context: IWorkflowContext) -> Any:
        """Execute Python expression."""
        expression = self._config.get("expression", "")
        
        if not expression:
            return data
        
        # Create safe execution context
        safe_globals = {
            "data": data,
            "context": context.variables,
            "len": len,
            "str": str,
            "int": int,
            "float": float,
            "list": list,
            "dict": dict,
            "bool": bool,
            "sum": sum,
            "min": min,
            "max": max,
            "sorted": sorted,
            "enumerate": enumerate,
            "zip": zip,
            "range": range,
        }
        
        try:
            result = eval(expression, {"__builtins__": {}}, safe_globals)
            return result
        except Exception as e:
            raise TransformError(
                f"Python expression evaluation failed: {e}",
                transform_type=self._transform_type.value,
            ) from e
    
    def _get_nested(self, data: Dict[str, Any], path: str) -> Any:
        """Get a nested value from a dictionary using dot notation."""
        keys = path.split(".")
        value = data
        
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            elif hasattr(value, key):
                value = getattr(value, key)
            else:
                return None
            
            if value is None:
                return None
        
        return value

