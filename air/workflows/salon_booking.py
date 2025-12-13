"""
Salon Booking Workflow

Complete workflow definition for voice agent booking flow.

Version: 1.0.0
"""

from typing import Any, Dict, List, Optional

from core.llms import ILLM
from core.workflows.spec import WorkflowSpec

from air.config import get_settings, Defaults
from air.nodes.tool_nodes import (
    WorkflowInitNode,
    FirstMessageNode,
    TransformationNode,
    ServiceInfoNode,
    BookingNode,
)
from air.nodes.agent_nodes import (
    GreetingRoutingAgent,
    ServiceCheckAgent,
    ServiceGuidelinesAgent,
    FallbackAgent,
)
from air.edges import (
    UnconditionalEdge,
    BookingEdge,
    ServiceConfirmedEdge,
    GuidelinesCompleteEdge,
    FallbackEdge,
)
from air.edges.unconditional import create_unconditional_edge


class SalonBookingWorkflow:
    """
    Complete salon booking workflow.
    
    Nodes:
    1. WorkflowInit - Initialize session and load dynamic variables
    2. FirstMessage - Generate first message
    3. GreetingRoutingAgent - Main conversation and routing
    4. TransformationTool - Prepare booking plan
    5. ServiceCheckAgent - Validate service with RAG
    6. ServiceInfoRetrieval - Get detailed service info
    7. ServiceGuidelinesAgent - Handle prerequisites and add-ons
    8. BookingTool - Execute booking
    10. FallbackAgent - Handle deviations
    
    Edges:
    - Unconditional edges between sequential nodes
    - Booking edge from greeting to transformation
    - Conditional edges based on user responses
    - Fallback edges for error handling
    """
    
    def __init__(
        self,
        llm: Optional[ILLM] = None,
        settings: Optional[Any] = None,
    ):
        self._llm = llm
        self._settings = settings or get_settings()
        
        # Initialize nodes
        self._nodes: Dict[str, Any] = {}
        self._edges: Dict[str, Any] = {}
        
        self._init_nodes()
        self._init_edges()
    
    def _init_nodes(self) -> None:
        """Initialize all workflow nodes."""
        # Tool nodes
        self._nodes["workflow_init"] = WorkflowInitNode()
        self._nodes["first_message_maker"] = FirstMessageNode()
        self._nodes["transformation_tool"] = TransformationNode()
        self._nodes["service_info_retrieval"] = ServiceInfoNode()
        self._nodes["booking_tool"] = BookingNode()
        
        # Agent nodes
        self._nodes["greeting_routing_agent"] = GreetingRoutingAgent(llm=self._llm)
        self._nodes["service_check_agent"] = ServiceCheckAgent(llm=self._llm)
        self._nodes["service_guidelines_agent"] = ServiceGuidelinesAgent(llm=self._llm)
        self._nodes["fallback_agent"] = FallbackAgent(llm=self._llm)
    
    def _init_edges(self) -> None:
        """Initialize all workflow edges."""
        # Sequential edges
        self._edges["init_to_first_message"] = create_unconditional_edge(
            source="workflow_init",
            target="first_message_maker",
        )
        
        self._edges["first_message_to_greeting"] = create_unconditional_edge(
            source="first_message_maker",
            target="greeting_routing_agent",
        )
        
        # Booking flow edges
        self._edges["booking_edge"] = BookingEdge(
            source_node="greeting_routing_agent",
            target_node="transformation_tool",
        )
        
        self._edges["transformation_to_service_check"] = create_unconditional_edge(
            source="transformation_tool",
            target="service_check_agent",
        )
        
        self._edges["service_confirmed_edge"] = ServiceConfirmedEdge(
            source_node="service_check_agent",
            target_node="service_info_retrieval",
        )
        
        self._edges["service_info_to_guidelines"] = create_unconditional_edge(
            source="service_info_retrieval",
            target="service_guidelines_agent",
        )
        
        self._edges["guidelines_complete_edge"] = GuidelinesCompleteEdge(
            source_node="service_guidelines_agent",
            target_node="booking_tool",
        )
        
        # Fallback edges
        self._edges["fallback_edge"] = FallbackEdge(
            source_node="any",
            target_node="fallback_agent",
        )
    
    def set_llm(self, llm: ILLM) -> None:
        """Set LLM for all agent nodes."""
        self._llm = llm
        
        for node in self._nodes.values():
            if hasattr(node, "set_llm"):
                node.set_llm(llm)
    
    def get_node(self, node_id: str) -> Optional[Any]:
        """Get a node by ID."""
        return self._nodes.get(node_id)
    
    def get_edge(self, edge_id: str) -> Optional[Any]:
        """Get an edge by ID."""
        return self._edges.get(edge_id)
    
    def get_edges_from_node(self, node_id: str) -> List[Any]:
        """Get all edges from a specific node."""
        return [
            edge for edge in self._edges.values()
            if edge.source_node == node_id
        ]
    
    def get_start_node(self) -> str:
        """Get the start node ID."""
        return "workflow_init"
    
    def get_spec(self) -> WorkflowSpec:
        """Get workflow specification."""
        return WorkflowSpec(
            workflow_id="salon_booking",
            workflow_name="Salon Booking Workflow",
            description="Voice agent workflow for salon appointment booking",
            start_node="workflow_init",
            node_ids=list(self._nodes.keys()),
            edge_ids=list(self._edges.keys()),
        )


def create_salon_workflow(
    llm: Optional[ILLM] = None,
    **kwargs,
) -> SalonBookingWorkflow:
    """
    Create a salon booking workflow.
    
    Args:
        llm: LLM instance for agent nodes
        **kwargs: Additional configuration
        
    Returns:
        Configured SalonBookingWorkflow
    """
    workflow = SalonBookingWorkflow(llm=llm, **kwargs)
    return workflow

