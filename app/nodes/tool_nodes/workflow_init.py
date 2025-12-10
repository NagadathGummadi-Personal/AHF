"""
WorkflowInit Node

First node in the workflow. Calls the initialization API
and populates dynamic variables.

Version: 1.0.0
"""

from typing import Any, Dict, Optional

from core.workflows.spec import WorkflowExecutionContext

from app.config import get_settings, Defaults
from app.models.dynamic_variables import DynamicVariables
from app.memory.session import VoiceAgentSession
from app.tools.http_client import AsyncHTTPClient

from ..base import BaseToolNode, NodeConfig, NodeContext


class WorkflowInitConfig(NodeConfig):
    """Configuration for WorkflowInit node."""
    
    # API configuration
    init_url: str = Defaults.WORKFLOW_INIT_URL
    
    # Required input parameters
    required_params: list = ["caller_id", "center_id", "org_id", "agent_id"]


class WorkflowInitNode(BaseToolNode):
    """
    Workflow initialization node.
    
    Calls the ElevenLabsClientInitialization API and stores
    dynamic variables in session.
    
    Input:
        - caller_id: Caller phone number
        - center_id: Center UUID
        - org_id: Organization UUID
        - agent_id: Agent identifier
        - called_number: Called phone number
        - call_sid: Call SID (optional)
        
    Output:
        - dynamic_variables: DynamicVariables object
        - conversation_config: Agent configuration
    """
    
    def __init__(
        self,
        node_id: str = "workflow_init",
        name: str = "WorkflowInit",
        config: Optional[WorkflowInitConfig] = None,
    ):
        super().__init__(
            node_id=node_id,
            name=name,
            description="Initialize workflow and load dynamic variables",
            config=config or WorkflowInitConfig(),
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
        """Execute workflow initialization."""
        
        # Extract input parameters
        params = input_data if isinstance(input_data, dict) else {}
        
        caller_id = params.get("caller_id", "")
        center_id = params.get("center_id", "")
        org_id = params.get("org_id", "")
        agent_id = params.get("agent_id", "")
        called_number = params.get("called_number", "")
        call_sid = params.get("call_sid", "")
        
        # Build request
        url = f"{self.config.init_url}?center_id={center_id}"
        
        headers = {
            "x-org-id": org_id,
            "Content-Type": "application/json",
        }
        
        body = {
            "caller_id": caller_id,
            "agent_id": agent_id,
            "called_number": called_number,
        }
        
        if call_sid:
            body["call_sid"] = call_sid
        
        # Make API call
        client = await self._get_http_client()
        response = await client.post(url, headers=headers, json_data=body)
        
        if not response.is_success:
            raise Exception(f"WorkflowInit API failed: {response.error or response.status_code}")
        
        # Parse response
        data = response.data
        
        # Extract dynamic variables
        dynamic_vars = DynamicVariables.from_api_response(data)
        
        # Store in session
        if session:
            session.set_dynamic_variables(dynamic_vars)
            
            # Store conversation config for later use
            conv_config = data.get("conversation_config_override", {})
            session.set_workflow_variable("conversation_config", conv_config)
            session.set_workflow_variable("first_message_template", 
                conv_config.get("agent", {}).get("first_message", ""))
        
        return {
            "dynamic_variables": dynamic_vars,
            "conversation_config": data.get("conversation_config_override", {}),
            "raw_response": data,
        }
    
    async def close(self) -> None:
        """Clean up resources."""
        if self._http_client:
            await self._http_client.close()


# Factory function for easy creation
def create_workflow_init_node(
    center_id: str,
    org_id: str,
    **config_overrides,
) -> WorkflowInitNode:
    """
    Create a WorkflowInit node with configuration.
    
    Args:
        center_id: Default center ID
        org_id: Default organization ID
        **config_overrides: Additional config overrides
        
    Returns:
        Configured WorkflowInitNode
    """
    config = WorkflowInitConfig(**config_overrides)
    return WorkflowInitNode(config=config)

