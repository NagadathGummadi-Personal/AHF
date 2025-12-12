"""
Voice Agent Workflow Executor

Executes workflows with interrupt handling and timeout management.

IMPORTANT - Request Isolation (Fargate/Container Safety):
- Each WebSocket connection gets its OWN VoiceAgentExecutor instance
- The executor creates and owns a VoiceAgentSession
- All state is stored in instance variables (self._xxx)
- NEVER share executor instances between requests
- This ensures complete isolation between concurrent requests

Version: 1.0.0
"""

import asyncio
from datetime import datetime
from typing import Any, AsyncIterator, Dict, List, Optional

from core.workflows.interfaces import IWorkflowExecutor
from core.workflows.spec import WorkflowResult, WorkflowExecutionContext, NodeResult

from app.config import get_settings
from app.memory.session import VoiceAgentSession, create_session
from app.interrupt import InterruptHandler, TimeoutManager, SoftTimeoutHandler
from app.models.workflow_state import WorkflowState

from .salon_booking import SalonBookingWorkflow


class VoiceAgentExecutor:
    """
    Workflow executor for voice agent.
    
    Features:
    - Interrupt handling with response stashing
    - Timeout management
    - Low-latency execution
    
    Implements IWorkflowExecutor pattern from core.workflows.
    """
    
    def __init__(
        self,
        workflow: SalonBookingWorkflow,
        settings: Optional[Any] = None,
    ):
        self._workflow = workflow
        self._settings = settings or get_settings()
        
        # Session and handlers
        self._session: Optional[VoiceAgentSession] = None
        self._interrupt_handler: Optional[InterruptHandler] = None
        self._timeout_manager: Optional[TimeoutManager] = None
        
        # State
        self._is_running = False
        self._current_node: Optional[str] = None
        self._execution_id: Optional[str] = None
    
    async def start(
        self,
        session_id: Optional[str] = None,
        initial_vars: Optional[Dict[str, Any]] = None,
    ) -> VoiceAgentSession:
        """
        Start workflow execution.
        
        Args:
            session_id: Optional session ID
            initial_vars: Initial variables for workflow init
            
        Returns:
            Initialized session
        """
        # Create session
        self._session = await create_session(session_id=session_id)
        
        # Initialize handlers
        self._interrupt_handler = InterruptHandler(self._session)
        self._timeout_manager = TimeoutManager(
            soft_timeout_ms=self._settings.soft_timeout_ms,
            turn_timeout_ms=self._settings.turn_timeout_ms,
        )
        
        # Set timeout callbacks
        soft_handler = SoftTimeoutHandler()
        self._timeout_manager.set_soft_timeout_callback(
            lambda: self._on_soft_timeout(soft_handler)
        )
        
        self._is_running = True
        self._current_node = self._workflow.get_start_node()
        
        return self._session
    
    async def execute_init(
        self,
        caller_id: str,
        center_id: str,
        org_id: str,
        agent_id: str,
        called_number: str = "",
        call_sid: str = "",
    ) -> Dict[str, Any]:
        """
        Execute workflow initialization.
        
        This runs the WorkflowInit node and FirstMessage node.
        
        Args:
            caller_id: Caller phone number
            center_id: Center ID
            org_id: Organization ID
            agent_id: Agent ID
            called_number: Called phone number
            call_sid: Call SID
            
        Returns:
            First message and dynamic variables
        """
        if not self._session:
            await self.start()
        
        context = WorkflowExecutionContext()
        
        # Execute WorkflowInit
        init_node = self._workflow.get_node("workflow_init")
        init_result = await init_node.execute(
            input_data={
                "caller_id": caller_id,
                "center_id": center_id,
                "org_id": org_id,
                "agent_id": agent_id,
                "called_number": called_number,
                "call_sid": call_sid,
            },
            context=context,
            session=self._session,
        )
        
        if not init_result.success:
            raise Exception(f"WorkflowInit failed: {init_result.error}")
        
        # Move to first message
        self._session.move_to_node("first_message_maker")
        
        # Execute FirstMessage
        first_message_node = self._workflow.get_node("first_message_maker")
        first_message_result = await first_message_node.execute(
            input_data=init_result.output,
            context=context,
            session=self._session,
        )
        
        if not first_message_result.success:
            raise Exception(f"FirstMessage failed: {first_message_result.error}")
        
        # Move to greeting agent
        self._session.move_to_node("greeting_routing_agent")
        self._current_node = "greeting_routing_agent"
        
        return {
            "first_message": first_message_result.output.get("first_message"),
            "dynamic_variables": init_result.output.get("dynamic_variables"),
            "session_id": self._session.session_id,
        }
    
    async def process_user_input(
        self,
        user_input: str,
    ) -> Dict[str, Any]:
        """
        Process a user input message.
        
        This is the main entry point for each conversation turn.
        
        Args:
            user_input: User's message
            
        Returns:
            Agent response and any routing info
        """
        if not self._session:
            raise ValueError("Session not started. Call start() first.")
        
        # Reset timeout on user input
        self._timeout_manager.reset_activity()
        
        # Check for pending interrupts
        if self._interrupt_handler.is_interrupted:
            continuation = await self._interrupt_handler.get_continuation_context()
            if continuation:
                user_input = f"{continuation}\n\nUser: {user_input}"
            await self._interrupt_handler.clear_interrupt()
        
        # Get current node
        current_node = self._workflow.get_node(self._current_node)
        if not current_node:
            raise ValueError(f"Node not found: {self._current_node}")
        
        context = WorkflowExecutionContext()
        
        # Execute current node
        result = await current_node.execute(
            input_data={"user_input": user_input},
            context=context,
            session=self._session,
        )
        
        if not result.success:
            # Handle error with fallback
            return await self._handle_error(result, user_input)
        
        # Evaluate edges and determine next node
        next_node = await self._evaluate_edges(result)
        
        if next_node:
            self._current_node = next_node
            self._session.move_to_node(next_node)
        
        return {
            "response": result.output.get("response", ""),
            "next_node": next_node,
            "detected_intent": result.output.get("detected_intent"),
            "tool_calls": result.output.get("tool_calls", []),
        }
    
    async def stream_user_input(
        self,
        user_input: str,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream response for user input.
        
        Yields response chunks with interrupt handling.
        """
        if not self._session:
            raise ValueError("Session not started")
        
        current_node = self._workflow.get_node(self._current_node)
        if not current_node:
            raise ValueError(f"Node not found: {self._current_node}")
        
        context = WorkflowExecutionContext()
        
        # Wrap generator with interrupt handling
        generator = current_node.stream(
            input_data={"user_input": user_input},
            context=context,
            session=self._session,
        )
        
        async for chunk in self._interrupt_handler.create_interrupt_aware_generator(
            generator,
            on_interrupt=self._on_interrupt,
        ):
            yield chunk
    
    async def _evaluate_edges(self, result: NodeResult) -> Optional[str]:
        """Evaluate edges from current node to determine next node."""
        edges = self._workflow.get_edges_from_node(self._current_node)
        
        edge_context = {
            "node_output": result.output,
            "session": self._session,
        }
        
        for edge in edges:
            if edge.should_traverse(edge_context):
                # Transform data for target node
                transformed = edge.transform_data(result.output)
                
                # Check for missing required fields
                missing = edge.get_missing_required_fields(result.output)
                if missing:
                    # Need to prompt for missing fields
                    # For now, continue to target and let it handle
                    pass
                
                return edge.target_node
        
        return None
    
    async def _handle_error(
        self,
        result: NodeResult,
        user_input: str,
    ) -> Dict[str, Any]:
        """Handle node execution error."""
        # Route to fallback agent
        fallback = self._workflow.get_node("fallback_agent")
        
        if fallback:
            context = WorkflowExecutionContext()
            fallback_result = await fallback.execute(
                input_data={
                    "user_input": user_input,
                    "error_context": result.error,
                },
                context=context,
                session=self._session,
            )
            
            return {
                "response": fallback_result.output.get("response", "I apologize, something went wrong. How can I help you?"),
                "error_handled": True,
            }
        
        return {
            "response": "I apologize, something went wrong. Let me try again.",
            "error": result.error,
        }
    
    async def _on_interrupt(
        self,
        partial_content: str,
        interrupt_message: Optional[str],
    ) -> None:
        """Callback when interrupt occurs during streaming."""
        # Content is already stashed by interrupt handler
        pass
    
    async def _on_soft_timeout(
        self,
        handler: SoftTimeoutHandler,
    ) -> None:
        """Callback for soft timeout."""
        # Could emit engagement message here
        pass
    
    async def pause(self) -> bool:
        """Pause execution."""
        if self._session:
            self._is_running = False
            return True
        return False
    
    async def resume(self, session_id: str) -> bool:
        """Resume execution (for low-latency voice apps, sessions are ephemeral)."""
        # For low-latency voice applications, resume creates a new session
        # since checkpoints are not used
        self._session = await create_session(session_id=session_id)
        self._is_running = True
        self._current_node = self._session.get_current_node() or "greeting_routing_agent"
        return True
    
    async def cancel(self) -> bool:
        """Cancel execution."""
        if self._session:
            await self._session.close()
            self._is_running = False
            return True
        return False

