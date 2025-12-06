"""
Data Transformer Implementation Module.

This module provides data transformation between workflow nodes.
"""

import json
import logging
from typing import Any, Dict

from ..interfaces import IDataTransformer, IWorkflowContext
from ..enum import DataTransformType
from ..spec import TransformSpec
from ..exceptions import TransformError

logger = logging.getLogger(__name__)


class DataTransformer(IDataTransformer):
    """
    Data transformer for workflow edges.
    
    Transforms data as it passes between nodes.
    """
    
    def __init__(self, spec: TransformSpec):
        """
        Initialize the transformer.
        
        Args:
            spec: Transform specification.
        """
        self._spec = spec
        self._transform_type = spec.transform_type
        self._config = dict(spec.config)
        self._template = spec.template
        self._mapping = spec.mapping
        self._expression = spec.expression
    
    @property
    def transform_type(self) -> DataTransformType:
        """Get the transformation type."""
        return self._transform_type
    
    @property
    def config(self) -> Dict[str, Any]:
        """Get transformation configuration."""
        return self._config
    
    async def transform(
        self,
        data: Any,
        context: IWorkflowContext,
    ) -> Any:
        """
        Transform the data.
        
        Args:
            data: Data to transform.
            context: Workflow execution context.
            
        Returns:
            Transformed data.
        """
        try:
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
                return self._transform_python(data, context)
            
            else:
                logger.warning(f"Unknown transform type: {self._transform_type}")
                return data
                
        except TransformError:
            raise
        except Exception as e:
            raise TransformError(
                f"Transform failed: {e}",
                transform_type=self._transform_type.value,
            ) from e
    
    def _transform_map(self, data: Any) -> Any:
        """Apply field mapping."""
        if not self._mapping or not isinstance(data, dict):
            return data
        
        result = {}
        for target_key, source_key in self._mapping.items():
            if isinstance(source_key, str):
                if source_key.startswith("$literal:"):
                    result[target_key] = source_key[9:]
                else:
                    result[target_key] = self._get_nested(data, source_key)
            else:
                result[target_key] = source_key
        
        return result
    
    def _transform_filter(self, data: Any) -> Any:
        """Filter data based on configuration."""
        if not isinstance(data, list):
            return data
        
        field = self._config.get("field")
        value = self._config.get("value")
        operator = self._config.get("operator", "equals")
        
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
        
        return result
    
    def _transform_extract(self, data: Any) -> Any:
        """Extract specific fields."""
        fields = self._config.get("fields", [])
        
        if not fields or not isinstance(data, dict):
            return data
        
        return {field: self._get_nested(data, field) for field in fields}
    
    def _transform_template(self, data: Any, context: IWorkflowContext) -> Any:
        """Apply template transformation."""
        if not self._template:
            return data
        
        template_vars = {
            "input": data,
            "context": context.variables,
        }
        
        if isinstance(data, dict):
            template_vars.update(data)
        
        try:
            return self._template.format(**template_vars)
        except KeyError:
            result = self._template
            for key, value in template_vars.items():
                result = result.replace(f"{{{key}}}", str(value))
            return result
    
    def _transform_merge(self, data: Any, context: IWorkflowContext) -> Any:
        """Merge multiple data sources."""
        result = {}
        
        if isinstance(data, dict):
            result.update(data)
        
        merge_sources = self._config.get("merge_sources", [])
        for source in merge_sources:
            if source.startswith("$node."):
                node_id = source.split(".")[1]
                node_output = context.get_node_output(node_id)
                if isinstance(node_output, dict):
                    result.update(node_output)
        
        return result
    
    def _transform_split(self, data: Any) -> Any:
        """Split data into parts."""
        if isinstance(data, str):
            delimiter = self._config.get("delimiter", ",")
            return data.split(delimiter)
        
        if isinstance(data, dict):
            return [{"key": k, "value": v} for k, v in data.items()]
        
        return data
    
    def _transform_format(self, data: Any) -> Any:
        """Format data to specific output."""
        output_format = self._config.get("output_format", "json")
        
        if output_format == "json":
            return json.dumps(data, indent=2) if not isinstance(data, str) else data
        elif output_format == "string":
            return str(data)
        
        return data
    
    def _transform_jmespath(self, data: Any) -> Any:
        """Apply JMESPath expression."""
        if not self._expression:
            return data
        
        try:
            import jmespath
            return jmespath.search(self._expression, data)
        except ImportError:
            logger.warning("jmespath not installed")
            return data
    
    def _transform_jsonpath(self, data: Any) -> Any:
        """Apply JSONPath expression."""
        if not self._expression:
            return data
        
        try:
            from jsonpath_ng import parse
            expr = parse(self._expression)
            matches = [m.value for m in expr.find(data)]
            return matches[0] if len(matches) == 1 else matches
        except ImportError:
            logger.warning("jsonpath-ng not installed")
            return data
    
    def _transform_python(self, data: Any, context: IWorkflowContext) -> Any:
        """Execute Python expression."""
        if not self._expression:
            return data
        
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
        }
        
        return eval(self._expression, {"__builtins__": {}}, safe_globals)
    
    def _get_nested(self, data: Dict[str, Any], path: str) -> Any:
        """Get nested value using dot notation."""
        keys = path.split(".")
        value = data
        
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
            if value is None:
                return None
        
        return value
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize transformer to dictionary."""
        return {
            "transform_type": self._transform_type.value,
            "config": self._config,
            "template": self._template,
            "mapping": self._mapping,
            "expression": self._expression,
        }



