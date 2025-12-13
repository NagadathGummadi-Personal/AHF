"""
WorkflowInit Node

First node in the workflow. Calls the initialization API
and populates dynamic variables.

Uses core.tools.AioHttpExecutor for HTTP operations.

Version: 1.1.0
"""

from typing import Any, Dict, Optional

from core.workflows.spec import WorkflowExecutionContext
from core.tools import AioHttpExecutor, HttpToolSpec, ToolContext

from air.config import get_settings, Defaults
from air.models.dynamic_variables import DynamicVariables
from air.memory.session import VoiceAgentSession

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
        
        self._executor: Optional[AioHttpExecutor] = None
    
    def _create_executor(self, url: str) -> AioHttpExecutor:
        """Create HTTP executor for the given URL."""
        spec = HttpToolSpec(
            id="workflow-init-v1",
            tool_name="workflow_init",
            description="Initialize workflow",
            url=url,
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
        
        # Create executor for this URL
        executor = self._create_executor(url)
        
        try:
            # Make API call via AioHttpExecutor
            result = await executor.execute(
                args={"headers": headers, "body": body},
                ctx=ToolContext(),
            )
            
            if result.content and "error" in result.content:
                raise Exception(f"WorkflowInit API failed: {result.content.get('error')}")
            
            # Parse response
            response_data = result.content.get("response", {}) if result.content else {}
            status_code = result.content.get("status_code", 0) if result.content else 0
            
            if not (200 <= status_code < 300):
                raise Exception(f"WorkflowInit API failed: HTTP {status_code}")
            
            data = response_data
            
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
        finally:
            await executor.close()
    
    async def close(self) -> None:
        """Clean up resources."""
        if self._executor:
            await self._executor.close()
            self._executor = None


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

