"""
Service Guidelines Agent Node

Handles service prerequisites, add-ons, and booking guidelines.

Version: 1.0.0
"""

import json
from typing import Any, Dict, List, Optional

from core.workflows.spec import WorkflowExecutionContext
from core.llms import ILLM, LLMContext

from app.memory.session import VoiceAgentSession
from app.prompts.guidelines_prompt import build_guidelines_prompt

from ..base import BaseAgentNode, NodeConfig, NodeContext


class GuidelinesConfig(NodeConfig):
    """Configuration for Guidelines agent."""
    
    temperature: float = 0.6
    max_tokens: int = 400
    
    fallback_node: str = "fallback_agent"


class ServiceGuidelinesAgent(BaseAgentNode):
    """
    Service guidelines and requirements agent.
    
    Handles:
    - Prerequisites announcement and collection
    - Add-on suggestions and selection
    - Deposit information
    - Service-specific guidelines
    
    Input:
        - service_info: Detailed service information from API
        - user_input: User's response
        
    Output:
        - response: Agent response
        - prerequisites_complete: Whether prerequisites are handled
        - addons_complete: Whether add-ons are handled
        - ready_for_therapist: Whether ready to proceed to therapist selection
    """
    
    def __init__(
        self,
        node_id: str = "service_guidelines_agent",
        name: str = "ServiceGuidelinesAgent",
        config: Optional[GuidelinesConfig] = None,
        llm: Optional[ILLM] = None,
    ):
        super().__init__(
            node_id=node_id,
            name=name,
            description="Handle service prerequisites and add-ons",
            config=config or GuidelinesConfig(),
        )
        
        self._llm = llm
    
    def set_llm(self, llm: ILLM) -> None:
        """Set the LLM instance."""
        self._llm = llm
    
    def get_system_prompt(
        self,
        session: VoiceAgentSession,
        **kwargs,
    ) -> str:
        """Build system prompt with service info."""
        service_info = kwargs.get("service_info", {})
        current_service = kwargs.get("current_service", "")
        prerequisites_done = kwargs.get("prerequisites_done", False)
        addons_done = kwargs.get("addons_done", False)
        
        return build_guidelines_prompt(
            service_info=json.dumps(service_info, indent=2) if service_info else "{}",
            current_service=current_service,
            prerequisites_done=prerequisites_done,
            addons_done=addons_done,
            custom_instructions=self.config.customer_instructions,
        )
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get tool definitions."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "GetPricingInfo",
                    "description": "Get pricing for service and add-ons",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "service_code": {"type": "string"},
                            "addon_codes": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        },
                        "required": ["service_code"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "HandoverCallToHuman",
                    "description": "Transfer to human for complex requirements",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "reason": {"type": "string"}
                        },
                        "required": ["reason"]
                    }
                }
            },
        ]
    
    async def _execute_agent(
        self,
        input_data: Any,
        system_prompt: str,
        context: WorkflowExecutionContext,
        session: Optional[VoiceAgentSession] = None,
        node_context: Optional[NodeContext] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Execute guidelines agent."""
        
        if not session or not self._llm:
            raise ValueError("Session and LLM are required")
        
        # Get inputs
        data = input_data if isinstance(input_data, dict) else {}
        user_input = data.get("user_input", "")
        service_info = data.get("service_info") or session.get_workflow_variable("service_info", [])
        
        # Get current service (first one for now)
        current_service = ""
        if service_info and isinstance(service_info, list) and len(service_info) > 0:
            current_service = service_info[0].get("service_name", "")
        
        # Get step tracking
        prerequisites_done = session.is_step_completed("prerequisites")
        addons_done = session.is_step_completed("addons")
        
        # Update system prompt
        system_prompt = self.get_system_prompt(
            session,
            service_info=service_info[0] if service_info else {},
            current_service=current_service,
            prerequisites_done=prerequisites_done,
            addons_done=addons_done,
        )
        
        # Build messages
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(session.get_llm_messages())
        
        if user_input:
            messages.append({"role": "user", "content": user_input})
            session.add_user_message(user_input)
        
        # Call LLM
        response = await self._llm.get_answer(
            messages=messages,
            ctx=LLMContext(),
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            tools=self.get_tools(),
        )
        
        session.add_assistant_message(response.content)
        
        # Update step tracking based on conversation
        if self._prerequisites_completed(user_input, response.content, service_info):
            session.complete_step("prerequisites")
            prerequisites_done = True
        
        if self._addons_completed(user_input, response.content, service_info):
            session.complete_step("addons")
            addons_done = True
        
        # Determine if ready for therapist selection
        ready_for_therapist = prerequisites_done and addons_done
        
        return {
            "response": response.content,
            "prerequisites_complete": prerequisites_done,
            "addons_complete": addons_done,
            "ready_for_therapist": ready_for_therapist,
            "current_service": current_service,
        }
    
    def _prerequisites_completed(
        self,
        user_input: str,
        response: str,
        service_info: List[Dict],
    ) -> bool:
        """Check if prerequisites are handled."""
        if not service_info:
            return True
        
        # Check if service has prerequisites
        svc = service_info[0] if service_info else {}
        prereq_info = svc.get("prerequisites_info", "None")
        
        if prereq_info == "None" or prereq_info.lower() == "none":
            return True
        
        # Check user confirmation
        user_lower = user_input.lower()
        if any(word in user_lower for word in ["yes", "okay", "sure", "i understand"]):
            return True
        
        return False
    
    def _addons_completed(
        self,
        user_input: str,
        response: str,
        service_info: List[Dict],
    ) -> bool:
        """Check if add-ons are handled."""
        if not service_info:
            return True
        
        svc = service_info[0] if service_info else {}
        addon_info = svc.get("add_ons_info", {})
        has_addons = addon_info.get("has_add_ons", False)
        
        if not has_addons:
            return True
        
        # Check user response
        user_lower = user_input.lower()
        if any(word in user_lower for word in ["no", "no thanks", "that's all", "nothing else"]):
            return True
        
        return False

