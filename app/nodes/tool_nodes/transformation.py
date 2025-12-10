"""
Transformation Node

Prepares task execution plan based on booking configuration.
Initiates background KB search.

Version: 1.0.0
"""

import asyncio
from typing import Any, Dict, List, Optional

from core.workflows.spec import WorkflowExecutionContext

from app.models.task import Task, TaskPriority
from app.memory.session import VoiceAgentSession

from ..base import BaseToolNode, NodeConfig, NodeContext


class TransformationConfig(NodeConfig):
    """Configuration for Transformation node."""
    
    # KB search configuration
    kb_search_enabled: bool = True
    kb_search_timeout_ms: int = 5000


class TransformationNode(BaseToolNode):
    """
    Transformation node for booking flow.
    
    Receives service_name(s) from the greeting agent
    and prepares the task execution plan.
    
    Actions:
    1. Create/update task with BOOKING intent
    2. Build execution plan based on center configuration
    3. Initiate background KB search for service info
    
    Input:
        - service_names: List of service names to book
        - (from session) center_allows_multiple_service_booking
        - (from session) center_allows_multiple_therapist_booking
        
    Output:
        - task: Updated Task with execution plan
        - kb_search_task: Background task for KB search
    """
    
    def __init__(
        self,
        node_id: str = "transformation_tool",
        name: str = "TransformationTool",
        config: Optional[TransformationConfig] = None,
    ):
        super().__init__(
            node_id=node_id,
            name=name,
            description="Prepare task execution plan for booking",
            config=config or TransformationConfig(),
        )
    
    async def _kb_search_background(
        self,
        service_names: List[str],
        session: VoiceAgentSession,
    ) -> Dict[str, str]:
        """
        Background KB search for service codes.
        
        This runs concurrently while the main flow continues.
        Results are stored in session for later retrieval.
        
        Returns:
            Mapping of service_name -> service_code
        """
        # TODO: Implement actual KB search API call
        # For now, return dummy service codes
        results = {}
        for name in service_names:
            # Dummy implementation - replace with actual API
            results[name] = f"ZENID{hash(name) % 10000:04d}"
        
        # Store results in session
        session.set_workflow_variable("kb_service_codes", results)
        
        return results
    
    async def _execute_tool(
        self,
        input_data: Any,
        context: WorkflowExecutionContext,
        session: Optional[VoiceAgentSession] = None,
        node_context: Optional[NodeContext] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Execute transformation logic."""
        
        if not session:
            raise ValueError("Session is required for TransformationNode")
        
        # Extract service names from input
        data = input_data if isinstance(input_data, dict) else {}
        service_names: List[str] = data.get("service_names", [])
        
        if not service_names:
            raise ValueError("No service names provided for booking")
        
        # Get booking configuration from dynamic variables
        dyn_vars = session.dynamic_vars
        allows_multiple_services = dyn_vars.center_allows_multiple_service_booking if dyn_vars else False
        allows_multiple_therapists = dyn_vars.center_allows_multiple_therapist_booking if dyn_vars else False
        
        # Get or create task
        current_task = await session.get_current_task()
        
        if not current_task or current_task.intent != "BOOK":
            # Create new booking task
            task = await session.create_task(
                intent="BOOK",
                original_input=f"Book services: {', '.join(service_names)}",
            )
        else:
            task = current_task
        
        # Add services to task
        for name in service_names:
            task.add_service(
                service_id="",  # Will be populated by KB search
                service_name=name,
            )
        
        # Create execution plan
        plan = task.create_plan(
            allows_multiple_services=allows_multiple_services,
            allows_multiple_therapists=allows_multiple_therapists,
        )
        
        # Update task in queue
        await session.task_queue.update(task)
        
        # Start background KB search
        kb_search_task = None
        if self.config.kb_search_enabled:
            kb_search_task = asyncio.create_task(
                self._kb_search_background(service_names, session)
            )
            # Store task reference so it can be awaited later
            session.set_workflow_variable("kb_search_task", kb_search_task)
        
        return {
            "task": task,
            "plan": plan,
            "service_names": service_names,
            "allows_multiple_services": allows_multiple_services,
            "allows_multiple_therapists": allows_multiple_therapists,
            "kb_search_initiated": kb_search_task is not None,
        }

