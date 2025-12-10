"""
Guidelines Complete Edge

Edge that triggers when all guidelines are handled.

Version: 1.0.0
"""

from typing import Any, Dict

from .base import BaseEdge, EdgeCondition


class GuidelinesCompleteEdge(BaseEdge):
    """
    Edge for completing guidelines flow.
    
    Triggers when:
    - Prerequisites are handled
    - Add-ons are handled
    - Ready for therapist selection
    """
    
    def __init__(
        self,
        edge_id: str = "guidelines_complete_edge",
        source_node: str = "service_guidelines_agent",
        target_node: str = "booking_tool",
        **kwargs,
    ):
        super().__init__(
            edge_id=edge_id,
            source_node=source_node,
            target_node=target_node,
            name="Guidelines Complete Edge",
            description="Route to booking when guidelines are complete",
            **kwargs,
        )
    
    def should_traverse(self, context: Dict[str, Any]) -> bool:
        """Check if all guidelines are complete."""
        node_output = context.get("node_output", {})
        
        prerequisites_done = node_output.get("prerequisites_complete", False)
        addons_done = node_output.get("addons_complete", False)
        ready = node_output.get("ready_for_therapist", False)
        
        return prerequisites_done and addons_done and ready


class GuidelinesIncompleteEdge(BaseEdge):
    """
    Edge for when guidelines still need handling.
    
    Loops back to guidelines agent for more interaction.
    """
    
    def __init__(
        self,
        edge_id: str = "guidelines_incomplete_edge",
        source_node: str = "service_guidelines_agent",
        target_node: str = "service_guidelines_agent",
        **kwargs,
    ):
        super().__init__(
            edge_id=edge_id,
            source_node=source_node,
            target_node=target_node,
            name="Guidelines Incomplete Edge",
            description="Loop back for more guideline handling",
            **kwargs,
        )
    
    def should_traverse(self, context: Dict[str, Any]) -> bool:
        """Check if more guidelines handling needed."""
        node_output = context.get("node_output", {})
        
        ready = node_output.get("ready_for_therapist", False)
        return not ready

