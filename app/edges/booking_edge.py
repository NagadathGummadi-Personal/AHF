"""
Booking Edge

Conditional edge that triggers when user wants to book.

Version: 1.0.0
"""

from typing import Any, Dict, List, Optional

from core.workflows.spec import PassThroughField

from .base import BaseEdge, EdgeCondition


class BookingEdge(BaseEdge):
    """
    Edge for booking intent routing.
    
    Triggers when:
    - User expresses booking intent
    - Greeting agent detects BOOK intent
    - next_edge output is "booking_edge"
    
    Pass-through variables:
    - service_names: List of services to book (required)
    
    If service_names is empty, the prompt_for_variable
    logic will ask the user what they want to book.
    """
    
    def __init__(
        self,
        edge_id: str = "booking_edge",
        source_node: str = "greeting_routing_agent",
        target_node: str = "transformation_tool",
        center_allows_multiple: bool = True,
        ask_for_more_services: str = "ask_initially",
        **kwargs,
    ):
        # Define pass-through fields
        pass_through_fields = [
            PassThroughField(
                source_field="service_names",
                target_field="service_names",
                required=True,
            ),
        ]
        
        super().__init__(
            edge_id=edge_id,
            source_node=source_node,
            target_node=target_node,
            name="Booking Edge",
            description="Route to booking flow when user wants to book",
            condition=EdgeCondition(
                condition_type="output",
                output_field="detected_intent",
                expected_value="BOOK",
                operator="eq",
            ),
            pass_through_fields=pass_through_fields,
            **kwargs,
        )
        
        self._center_allows_multiple = center_allows_multiple
        self._ask_for_more_services = ask_for_more_services
    
    def should_traverse(self, context: Dict[str, Any]) -> bool:
        """
        Check if booking edge should be traversed.
        
        Conditions:
        1. Detected intent is BOOK
        2. OR next_edge output is "booking_edge"
        """
        node_output = context.get("node_output", {})
        
        # Check next_edge
        if node_output.get("next_edge") == "booking_edge":
            return True
        
        # Check detected intent
        intent = node_output.get("detected_intent", "")
        if intent == "BOOK":
            return True
        
        return False
    
    def get_service_prompt(self) -> str:
        """
        Get prompt for collecting service names.
        
        Based on configuration:
        - If center_allows_multiple and ask_initially:
          Ask what service and if they want more
        - If not center_allows_multiple:
          Just ask what service
        """
        if self._center_allows_multiple and self._ask_for_more_services == "ask_initially":
            return (
                "What service would you like to book? "
                "If you'd like to book multiple services, let me know."
            )
        else:
            return "What service would you like to book?"
    
    def transform_data(self, source_output: Any) -> Dict[str, Any]:
        """Transform and add configuration to output."""
        result = super().transform_data(source_output)
        
        if isinstance(result, dict):
            result["center_allows_multiple"] = self._center_allows_multiple
            result["ask_for_more_services"] = self._ask_for_more_services
        
        return result


# Factory function
def create_booking_edge(
    source: str = "greeting_routing_agent",
    target: str = "transformation_tool",
    center_allows_multiple: bool = True,
    ask_for_more_services: str = "ask_initially",
    **kwargs,
) -> BookingEdge:
    """Create a booking edge with configuration."""
    return BookingEdge(
        source_node=source,
        target_node=target,
        center_allows_multiple=center_allows_multiple,
        ask_for_more_services=ask_for_more_services,
        **kwargs,
    )

