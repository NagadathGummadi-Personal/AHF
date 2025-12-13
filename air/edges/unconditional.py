"""
Unconditional Edge

Edge that always traverses.

Version: 1.0.0
"""

from typing import Any, Dict, List, Optional

from core.workflows.spec import PassThroughField

from .base import BaseEdge, EdgeCondition


class UnconditionalEdge(BaseEdge):
    """
    Edge that always traverses unconditionally.
    
    Used for sequential node connections where no
    condition checking is needed.
    """
    
    def __init__(
        self,
        edge_id: str,
        source_node: str,
        target_node: str,
        name: str = "",
        pass_through_fields: Optional[List[PassThroughField]] = None,
        **kwargs,
    ):
        super().__init__(
            edge_id=edge_id,
            source_node=source_node,
            target_node=target_node,
            name=name or f"unconditional_{source_node}_to_{target_node}",
            condition=EdgeCondition(condition_type="static", static_value=True),
            pass_through_fields=pass_through_fields,
            **kwargs,
        )
    
    def should_traverse(self, context: Dict[str, Any]) -> bool:
        """Always returns True."""
        return True


# Convenience factory functions

def create_unconditional_edge(
    source: str,
    target: str,
    edge_id: Optional[str] = None,
    **kwargs,
) -> UnconditionalEdge:
    """Create an unconditional edge."""
    return UnconditionalEdge(
        edge_id=edge_id or f"{source}_to_{target}",
        source_node=source,
        target_node=target,
        **kwargs,
    )

