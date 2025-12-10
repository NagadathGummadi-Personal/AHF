"""
ServiceInfo Node

Retrieves service information from the API.

Version: 1.0.0
"""

from typing import Any, Dict, List, Optional

from core.workflows.spec import WorkflowExecutionContext

from app.config import Defaults
from app.memory.session import VoiceAgentSession
from app.tools.http_client import AsyncHTTPClient

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
        
        self._http_client: Optional[AsyncHTTPClient] = None
    
    async def _get_http_client(self) -> AsyncHTTPClient:
        """Get or create HTTP client."""
        if not self._http_client:
            self._http_client = AsyncHTTPClient(
                timeout_ms=self.config.timeout_ms,
            )
        return self._http_client
    
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
            "center_id": dyn_vars.center_id,
            "x-org-id": dyn_vars.org_id,
            "Content-Type": "application/json",
        }
        
        if dyn_vars.guest_id:
            headers["guest_id"] = dyn_vars.guest_id
        
        body = {
            "service_codes": service_codes,
        }
        
        # Make API call
        client = await self._get_http_client()
        response = await client.post(
            self.config.service_info_url,
            headers=headers,
            json_data=body,
        )
        
        if not response.is_success:
            # Return error for fallback handling
            error_info = {
                "error": response.error or f"API error: {response.status_code}",
                "status_code": response.status_code,
                "fallback_node": self.config.fallback_node,
            }
            
            if self.config.error_context_enabled:
                error_info["error_context"] = {
                    "service_codes": service_codes,
                    "action_to_take": "",  # To be filled by configuration
                }
            
            # Store error in session for fallback handling
            session.set_workflow_variable("last_error", error_info)
            
            raise Exception(error_info["error"])
        
        # Parse response
        services = response.data if isinstance(response.data, list) else [response.data]
        
        # Store in session for later use
        session.set_workflow_variable("service_info", services)
        
        # Update task with service details
        current_task = await session.get_current_task()
        if current_task:
            for svc in services:
                current_task.set_data(f"service_info_{svc.get('service_id')}", svc)
            await session.task_queue.update(current_task)
        
        return {
            "services": services,
            "service_codes": service_codes,
        }
    
    async def close(self) -> None:
        """Clean up resources."""
        if self._http_client:
            await self._http_client.close()

