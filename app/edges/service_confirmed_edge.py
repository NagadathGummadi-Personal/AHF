"""
Service Confirmed Edge

Edge that triggers when service is confirmed by user.

Version: 1.0.0
"""

from typing import Any, Dict

from .base import BaseEdge, EdgeCondition


class ServiceConfirmedEdge(BaseEdge):
    """
    Edge for service confirmation routing.
    
    Triggers when user confirms a service suggestion
    from the service check agent.
    """
    
    def __init__(
        self,
        edge_id: str = "service_confirmed_edge",
        source_node: str = "service_check_agent",
        target_node: str = "service_info_retrieval",
        **kwargs,
    ):
        super().__init__(
            edge_id=edge_id,
            source_node=source_node,
            target_node=target_node,
            name="Service Confirmed Edge",
            description="Route to service info when user confirms service",
            condition=EdgeCondition(
                condition_type="output",
                output_field="proceed",
                expected_value=True,
                operator="eq",
            ),
            **kwargs,
        )
    
    def should_traverse(self, context: Dict[str, Any]) -> bool:
        """Check if user confirmed the service."""
        node_output = context.get("node_output", {})
        return node_output.get("proceed", False) is True


class ServiceDeclinedEdge(BaseEdge):
    """
    Edge for when user declines service suggestions.
    
    Routes to fallback or handover.
    """
    
    def __init__(
        self,
        edge_id: str = "service_declined_edge",
        source_node: str = "service_check_agent",
        target_node: str = "fallback_agent",
        **kwargs,
    ):
        super().__init__(
            edge_id=edge_id,
            source_node=source_node,
            target_node=target_node,
            name="Service Declined Edge",
            description="Route to fallback when user declines services",
            condition=EdgeCondition(
                condition_type="output",
                output_field="proceed",
                expected_value=False,
                operator="eq",
            ),
            **kwargs,
        )
    
    def should_traverse(self, context: Dict[str, Any]) -> bool:
        """Check if user declined the service."""
        node_output = context.get("node_output", {})
        
        # Check explicit decline
        if node_output.get("proceed", True) is False:
            return True
        
        return False

