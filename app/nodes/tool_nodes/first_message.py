"""
FirstMessage Node

Generates the first message based on customer preferences
and business hours.

Version: 1.0.0
"""

from typing import Any, Dict, List, Optional

from core.workflows.spec import WorkflowExecutionContext

from app.config import Defaults
from app.models.dynamic_variables import CustomerPreferences
from app.memory.session import VoiceAgentSession
from app.tools.http_client import AsyncHTTPClient

from ..base import BaseToolNode, NodeConfig, NodeContext


class FirstMessageConfig(NodeConfig):
    """Configuration for FirstMessage node."""
    
    # Customer preferences API
    preferences_url: Optional[str] = None  # If None, use defaults
    
    # Default templates
    default_templates: Dict[str, str] = {
        "outside_business_new_user": Defaults.OUTSIDE_BUSINESS_NEW_USER_MESSAGE,
        "inside_business_new_user": Defaults.INSIDE_BUSINESS_NEW_USER_MESSAGE,
        "outside_business_existing_user": Defaults.OUTSIDE_BUSINESS_EXISTING_USER_MESSAGE,
        "inside_business_existing_user": Defaults.INSIDE_BUSINESS_EXISTING_USER_MESSAGE,
    }


class FirstMessageNode(BaseToolNode):
    """
    First message generation node.
    
    Determines the appropriate first message based on:
    - Business hours (inside/outside)
    - User type (new/existing)
    - Customer preference templates
    
    Also initializes conversation history and task queue.
    
    Input:
        - dynamic_variables from WorkflowInit
        
    Output:
        - first_message: The generated first message
        - preferences: CustomerPreferences object
    """
    
    def __init__(
        self,
        node_id: str = "first_message_maker",
        name: str = "FirstMessageMaker",
        config: Optional[FirstMessageConfig] = None,
    ):
        super().__init__(
            node_id=node_id,
            name=name,
            description="Generate first message based on context",
            config=config or FirstMessageConfig(),
        )
        
        self._http_client: Optional[AsyncHTTPClient] = None
    
    async def _get_customer_preferences(
        self,
        session: VoiceAgentSession,
    ) -> CustomerPreferences:
        """
        Get customer preferences (message templates).
        
        If API is configured, fetches from API.
        Otherwise uses defaults.
        """
        if self.config.preferences_url:
            # Fetch from API
            client = self._http_client or AsyncHTTPClient()
            response = await client.get(self.config.preferences_url)
            
            if response.is_success:
                return CustomerPreferences(
                    outside_business_new_user_message_template=response.data.get(
                        "outside_business_new_user_message_template",
                        self.config.default_templates["outside_business_new_user"]
                    ),
                    inside_business_new_user_message_template=response.data.get(
                        "inside_business_new_user_message_template",
                        self.config.default_templates["inside_business_new_user"]
                    ),
                    outside_business_existing_user_message_template=response.data.get(
                        "outside_business_existing_user_message_template",
                        self.config.default_templates["outside_business_existing_user"]
                    ),
                    inside_business_existing_user_message_template=response.data.get(
                        "inside_business_existing_user_message_template",
                        self.config.default_templates["inside_business_existing_user"]
                    ),
                )
        
        # Use defaults
        return CustomerPreferences(
            outside_business_new_user_message_template=self.config.default_templates["outside_business_new_user"],
            inside_business_new_user_message_template=self.config.default_templates["inside_business_new_user"],
            outside_business_existing_user_message_template=self.config.default_templates["outside_business_existing_user"],
            inside_business_existing_user_message_template=self.config.default_templates["inside_business_existing_user"],
        )
    
    async def _execute_tool(
        self,
        input_data: Any,
        context: WorkflowExecutionContext,
        session: Optional[VoiceAgentSession] = None,
        node_context: Optional[NodeContext] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Generate the first message."""
        
        if not session:
            raise ValueError("Session is required for FirstMessageNode")
        
        # Get customer preferences
        preferences = await self._get_customer_preferences(session)
        
        # Get dynamic variables
        dyn_vars = session.dynamic_vars
        if not dyn_vars:
            raise ValueError("Dynamic variables not set - WorkflowInit must run first")
        
        # Determine context
        is_outside_business_hours = dyn_vars.is_outside_business_hours
        is_new_user = dyn_vars.is_new_user
        guest_name = dyn_vars.get_guest_display_name()
        
        # Check if there's a template from conversation config
        first_message_template = session.get_workflow_variable("first_message_template")
        
        if first_message_template:
            # Use template from API response, substitute variables
            first_message = first_message_template.replace(
                "{{agent_name}}", dyn_vars.agent_name
            ).replace(
                "{{guest_name}}", guest_name
            ).replace(
                "{{org_name}}", dyn_vars.org_name
            ).replace(
                "{{center_name}}", dyn_vars.center_name
            )
        else:
            # Use customer preference templates
            first_message = preferences.get_first_message(
                is_outside_business_hours=is_outside_business_hours,
                is_new_user=is_new_user,
                guest_name=guest_name,
            )
        
        # Initialize conversation with first message
        session.add_assistant_message(first_message)
        
        # Store preferences in session
        session.set_workflow_variable("customer_preferences", preferences.model_dump())
        
        return {
            "first_message": first_message,
            "preferences": preferences,
            "is_outside_business_hours": is_outside_business_hours,
            "is_new_user": is_new_user,
        }

