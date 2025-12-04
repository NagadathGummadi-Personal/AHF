"""
Error Edge Implementation Module.

This module provides an edge for error handling paths.
"""

import logging
from typing import Any, Dict, Optional

from ..interfaces import IWorkflowContext, IDataTransformer
from ..enum import EdgeType
from ..spec import EdgeSpec
from .base_edge import BaseEdge

logger = logging.getLogger(__name__)


class ErrorEdge(BaseEdge):
    """
    An edge specifically for error handling paths.
    
    Error edges are traversed when the source node encounters an error.
    They can optionally filter by error type.
    """
    
    def __init__(
        self,
        spec: EdgeSpec,
        transformer: Optional[IDataTransformer] = None,
    ):
        """
        Initialize the error edge.
        
        Args:
            spec: Edge specification.
            transformer: Optional data transformer.
        """
        if spec.edge_type != EdgeType.ERROR:
            spec.edge_type = EdgeType.ERROR
        
        super().__init__(spec, transformer)
        
        # Error type filtering
        self._error_types = self._metadata.get("error_types", [])
    
    def can_traverse(self, context: IWorkflowContext) -> bool:
        """
        Check if this error edge should be taken.
        
        Checks if there's an error in context and optionally
        filters by error type.
        
        Args:
            context: Workflow execution context.
            
        Returns:
            True if there's a matching error.
        """
        # Check for error in context
        error = context.get("__current_error__")
        if error is None:
            return False
        
        # If no specific error types, match any error
        if not self._error_types:
            logger.debug(f"Error edge {self._id}: Handling error")
            return True
        
        # Check if error type matches
        error_type = type(error).__name__
        error_code = getattr(error, "error_code", None)
        
        if error_type in self._error_types or error_code in self._error_types:
            logger.debug(f"Error edge {self._id}: Handling {error_type}")
            return True
        
        logger.debug(
            f"Error edge {self._id}: Error type {error_type} "
            f"not in {self._error_types}"
        )
        return False
    
    async def transform_data(
        self,
        data: Any,
        context: IWorkflowContext,
    ) -> Any:
        """
        Transform error data for the error handler.
        
        Adds error information to the data.
        
        Args:
            data: Data from the failed node.
            context: Workflow execution context.
            
        Returns:
            Data with error information added.
        """
        # Get the error
        error = context.get("__current_error__")
        
        # Create error info dict
        error_info = {
            "error_type": type(error).__name__ if error else None,
            "error_message": str(error) if error else None,
            "error_code": getattr(error, "error_code", None) if error else None,
            "error_details": getattr(error, "details", {}) if error else {},
            "source_node_id": self._source_id,
        }
        
        # Apply base transformation first
        transformed = await super().transform_data(data, context)
        
        # Add error info
        if isinstance(transformed, dict):
            transformed["__error__"] = error_info
        else:
            transformed = {
                "original_data": transformed,
                "__error__": error_info,
            }
        
        return transformed

