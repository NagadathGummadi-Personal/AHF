"""
Fallback Edge Implementation Module.

This module provides a fallback edge used when no other edges match.
"""

import logging
from typing import Any, Dict, Optional

from ..interfaces import IWorkflowContext, IDataTransformer
from ..enum import EdgeType
from ..spec import EdgeSpec
from .base_edge import BaseEdge

logger = logging.getLogger(__name__)


class FallbackEdge(BaseEdge):
    """
    A fallback edge that is taken when no other edges from a node match.
    
    Fallback edges should typically have the lowest priority and no conditions,
    ensuring they're only used when all other options have been exhausted.
    """
    
    def __init__(
        self,
        spec: EdgeSpec,
        transformer: Optional[IDataTransformer] = None,
    ):
        """
        Initialize the fallback edge.
        
        Args:
            spec: Edge specification.
            transformer: Optional data transformer.
        """
        if spec.edge_type != EdgeType.FALLBACK:
            spec.edge_type = EdgeType.FALLBACK
        
        # Ensure fallback has lowest priority
        if spec.priority >= 0:
            spec.priority = -1000
        
        super().__init__(spec, transformer)
    
    def can_traverse(self, context: IWorkflowContext) -> bool:
        """
        Fallback edges are always traversable.
        
        The workflow engine should only attempt to traverse a fallback
        edge after all other edges have been checked.
        
        Args:
            context: Workflow execution context.
            
        Returns:
            Always True.
        """
        logger.debug(f"Fallback edge {self._id}: Providing fallback route")
        return True

