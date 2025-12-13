"""
Booking Node

Final booking execution node.

Uses core.tools.AioHttpExecutor for HTTP operations.

Version: 1.1.0
"""

from typing import Any, Dict, List, Optional

from core.workflows.spec import WorkflowExecutionContext
from core.tools import AioHttpExecutor, HttpToolSpec, ToolContext

from air.config import Defaults
from air.memory.session import VoiceAgentSession

from ..base import BaseToolNode, NodeConfig, NodeContext


class BookingConfig(NodeConfig):
    """Configuration for Booking node."""
    
    # API configuration
    booking_url: str = "https://voice-agent.zenoti.com/workflow/CreateAppointment"
    
    # Confirmation required
    require_confirmation: bool = True


class BookingNode(BaseToolNode):
    """
    Booking execution node.
    
    Executes the final booking after all information
    has been collected and confirmed.
    
    Input:
        - booking_details: Complete booking information
        - confirmed: Whether user has confirmed
        
    Output:
        - booking_id: Created booking ID
        - confirmation_message: Message to user
    """
    
    def __init__(
        self,
        node_id: str = "booking_tool",
        name: str = "BookingTool",
        config: Optional[BookingConfig] = None,
    ):
        super().__init__(
            node_id=node_id,
            name=name,
            description="Execute final booking",
            config=config or BookingConfig(),
        )
        
        self._executor: Optional[AioHttpExecutor] = None
    
    def _create_executor(self) -> AioHttpExecutor:
        """Create HTTP executor for booking API."""
        spec = HttpToolSpec(
            id="booking-v1",
            tool_name="create_booking",
            description="Create appointment booking",
            url=self.config.booking_url,
            method="POST",
            timeout_s=self.config.timeout_ms // 1000,
        )
        return AioHttpExecutor(spec)
    
    async def _execute_tool(
        self,
        input_data: Any,
        context: WorkflowExecutionContext,
        session: Optional[VoiceAgentSession] = None,
        node_context: Optional[NodeContext] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Execute booking."""
        
        if not session:
            raise ValueError("Session is required for BookingNode")
        
        # Get booking details
        data = input_data if isinstance(input_data, dict) else {}
        
        # Check confirmation if required
        if self.config.require_confirmation and not data.get("confirmed", False):
            return {
                "success": False,
                "requires_confirmation": True,
                "message": "Booking requires confirmation",
            }
        
        # Get task and collected data
        current_task = await session.get_current_task()
        if not current_task:
            raise ValueError("No active booking task")
        
        # Get dynamic variables
        dyn_vars = session.dynamic_vars
        if not dyn_vars:
            raise ValueError("Dynamic variables not set")
        
        # Build booking request
        # TODO: Implement actual booking API call
        # For now, return dummy success response
        
        booking_id = f"BK{hash(current_task.task_id) % 1000000:06d}"
        
        # Complete the task
        await session.complete_task(current_task.task_id)
        
        # Build confirmation message
        services = current_task.services
        service_names = [s.get("service_name", "") for s in services]
        
        confirmation_message = (
            f"Great! I've booked your appointment for {', '.join(service_names)}. "
            f"Your booking reference is {booking_id}. "
            f"Is there anything else I can help you with?"
        )
        
        return {
            "success": True,
            "booking_id": booking_id,
            "confirmation_message": confirmation_message,
            "services_booked": services,
        }
    
    async def close(self) -> None:
        """Clean up resources."""
        if self._executor:
            await self._executor.close()
            self._executor = None

