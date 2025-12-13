"""
ServiceInfo Node

Retrieves service information from the API.

Uses core.tools.AioHttpExecutor for HTTP operations.

Version: 1.1.0
"""

from typing import Any, Dict, List, Optional

from core.workflows.spec import WorkflowExecutionContext
from core.tools import AioHttpExecutor, HttpToolSpec, ToolContext

from air.config import Defaults
from air.memory.session import VoiceAgentSession

from ..base import BaseToolNode, NodeConfig, NodeContext


class ServiceInfoConfig(NodeConfig):
    """Configuration for ServiceInfo node."""
    
    # API configuration
    service_info_url: str = Defaults.SERVICE_INFO_URL
    
    # Error handling
    fallback_node: str = "service_check_agent"
    error_context_enabled: bool = True


class ServiceInfoNode(BaseToolNode):
    """
    Service information retrieval node.
    
    Calls GetServicesInfoByServiceCodes API to get detailed
    service information including:
    - Description and guidelines
    - Add-ons
    - Prerequisites
    - Deposit info
    - Price notes
    
    Input:
        - service_codes: List of service codes to lookup
        - (from session) center_id, org_id, guest_id
        
    Output:
        - services: List of service info objects
        - error: Error details if failed (for fallback handling)
    """
    
    def __init__(
        self,
        node_id: str = "service_info_retrieval",
        name: str = "ServiceInfoRetrieval",
        config: Optional[ServiceInfoConfig] = None,
    ):
        super().__init__(
            node_id=node_id,
            name=name,
            description="Retrieve detailed service information",
            config=config or ServiceInfoConfig(),
        )
        
        self._executor: Optional[AioHttpExecutor] = None
    
    def _create_executor(self) -> AioHttpExecutor:
        """Create HTTP executor for service info API."""
        spec = HttpToolSpec(
            id="service-info-v1",
            tool_name="get_service_info",
            description="Get service information by codes",
            url=self.config.service_info_url,
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
        """Retrieve service information."""
        
        if not session:
            raise ValueError("Session is required for ServiceInfoNode")
        
        # Get service codes from input or session
        data = input_data if isinstance(input_data, dict) else {}
        service_codes = data.get("service_codes", [])
        
        # Try to get from KB search results if not provided
        if not service_codes:
            kb_results = session.get_workflow_variable("kb_service_codes", {})
            service_codes = list(kb_results.values())
        
        if not service_codes:
            raise ValueError("No service codes available")
        
        # Get dynamic variables for API call
        dyn_vars = session.dynamic_vars
        if not dyn_vars:
            raise ValueError("Dynamic variables not set")
        
        # Build request
        headers = {
            "center_id": str(getattr(dyn_vars, 'center_id', '')),
            "x-org-id": str(getattr(dyn_vars, 'org_id', '')),
            "Content-Type": "application/json",
        }
        
        if hasattr(dyn_vars, 'guest_id') and dyn_vars.guest_id:
            headers["guest_id"] = str(dyn_vars.guest_id)
        
        body = {
            "service_codes": service_codes,
        }
        
        # Create and execute
        executor = self._create_executor()
        
        try:
            result = await executor.execute(
                args={"headers": headers, "body": body},
                ctx=ToolContext(),
            )
            
            # Check for errors
            if result.content and "error" in result.content:
                error_msg = result.content.get("error", "Unknown error")
                error_info = {
                    "error": error_msg,
                    "status_code": result.content.get("status_code", 0),
                    "fallback_node": self.config.fallback_node,
                }
                
                if self.config.error_context_enabled:
                    error_info["error_context"] = {
                        "service_codes": service_codes,
                        "action_to_take": "",
                    }
                
                session.set_workflow_variable("last_error", error_info)
                raise Exception(error_msg)
            
            # Parse response
            response_data = result.content.get("response", {}) if result.content else {}
            status_code = result.content.get("status_code", 0) if result.content else 0
            
            if not (200 <= status_code < 300):
                raise Exception(f"Service info API failed: HTTP {status_code}")
            
            services = response_data if isinstance(response_data, list) else [response_data]
            
            # Store in session for later use
            session.set_workflow_variable("service_info", services)
            
            # Update task with service details
            current_task = await session.get_current_task()
            if current_task:
                for svc in services:
                    if isinstance(svc, dict):
                        current_task.set_data(f"service_info_{svc.get('service_id')}", svc)
                await session.task_queue.update(current_task)
            
            return {
                "services": services,
                "service_codes": service_codes,
            }
        finally:
            await executor.close()
    
    async def close(self) -> None:
        """Clean up resources."""
        if self._executor:
            await self._executor.close()
            self._executor = None

