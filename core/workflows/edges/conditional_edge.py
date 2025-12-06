"""
Conditional Edge Implementation Module.

This module provides an edge that requires conditions to be met.
"""

import logging
from typing import Any, Dict, List, Optional

from ..interfaces import IWorkflowContext, IDataTransformer
from ..enum import EdgeType
from ..spec import EdgeSpec
from .base_edge import BaseEdge

logger = logging.getLogger(__name__)


class ConditionalEdge(BaseEdge):
    """
    An edge that is only traversable when conditions are met.
    
    Unlike the base edge which treats empty conditions as always passable,
    conditional edges require at least one condition and all must pass.
    """
    
    def __init__(
        self,
        spec: EdgeSpec,
        transformer: Optional[IDataTransformer] = None,
    ):
        """
        Initialize the conditional edge.
        
        Args:
            spec: Edge specification.
            transformer: Optional data transformer.
        """
        if spec.edge_type != EdgeType.CONDITIONAL:
            spec.edge_type = EdgeType.CONDITIONAL
        
        super().__init__(spec, transformer)
    
    def can_traverse(self, context: IWorkflowContext) -> bool:
        """
        Check if this conditional edge can be traversed.
        
        Requires at least one condition, and all must pass.
        
        Args:
            context: Workflow execution context.
            
        Returns:
            True if all conditions pass.
        """
        if not self._conditions:
            logger.warning(
                f"Conditional edge {self._id} has no conditions, "
                "consider using DEFAULT edge type"
            )
            return False  # Conditional edges require conditions
        
        for condition in self._conditions:
            if not condition.evaluate(context):
                logger.debug(
                    f"Conditional edge {self._id}: Condition {condition.field} "
                    f"{condition.operator.value} {condition.value} failed"
                )
                return False
        
        logger.debug(f"Conditional edge {self._id}: All conditions passed")
        return True



