"""
Service Check Agent Node

Validates and matches service names using RAG.

Version: 1.0.0
"""

from typing import Any, Dict, List, Optional

from core.workflows.spec import WorkflowExecutionContext
from core.llms import ILLM, LLMContext

from air.memory.session import VoiceAgentSession
from air.prompts.service_check_prompt import build_service_check_prompt

from ..base import BaseAgentNode, NodeConfig, NodeContext


class ServiceCheckConfig(NodeConfig):
    """Configuration for Service Check agent."""
    
    temperature: float = 0.5
    max_tokens: int = 300
    
    # Fallback
    fallback_node: str = "fallback_agent"


class ServiceCheckAgent(BaseAgentNode):
    """
    Service check and validation agent.
    
    Uses RAG to validate service names and find matches.
    
    Input:
        - service_name: Service name to validate
        - kb_context: Retrieved KB context
        
    Output:
        - validated_service: Validated service info
        - suggestions: Alternative suggestions if no match
        - proceed: Whether to proceed to next step
    """
    
    def __init__(
        self,
        node_id: str = "service_check_agent",
        name: str = "ServiceCheckAgent",
        config: Optional[ServiceCheckConfig] = None,
        llm: Optional[ILLM] = None,
    ):
        super().__init__(
            node_id=node_id,
            name=name,
            description="Validate and match service names",
            config=config or ServiceCheckConfig(),
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
        """Build system prompt."""
        service_name = kwargs.get("service_name", "")
        kb_context = kwargs.get("kb_context", "")
        
        return build_service_check_prompt(
            service_name=service_name,
            dynamic_vars=session.dynamic_vars,
            kb_context=kb_context,
            custom_instructions=self.config.customer_instructions,
        )
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get tool definitions."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "GetPricingInfo",
                    "description": "Get pricing for a service",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "service_code": {"type": "string"}
                        },
                        "required": ["service_code"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "GetTherapistForService",
                    "description": "Get available therapists for a service",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "service_code": {"type": "string"}
                        },
                        "required": ["service_code"]
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
        """Execute service check."""
        
        if not session or not self._llm:
            raise ValueError("Session and LLM are required")
        
        # Get inputs
        data = input_data if isinstance(input_data, dict) else {}
        service_name = data.get("service_name", "")
        user_input = data.get("user_input", "")
        
        # Get KB context from background task if available
        kb_context = ""
        kb_task = session.get_workflow_variable("kb_search_task")
        if kb_task:
            try:
                await kb_task  # Wait for background task
                kb_results = session.get_workflow_variable("kb_service_codes", {})
                kb_context = str(kb_results)
            except Exception:
                pass
        
        # Update system prompt with context
        system_prompt = self.get_system_prompt(
            session,
            service_name=service_name,
            kb_context=kb_context,
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
        
        # Analyze response for next action
        proceed = self._should_proceed(response.content, user_input)
        
        return {
            "response": response.content,
            "service_name": service_name,
            "proceed": proceed,
            "kb_context": kb_context,
        }
    
    def _should_proceed(self, response: str, user_input: str) -> bool:
        """Determine if we should proceed to next step."""
        # Check for positive confirmation
        user_lower = user_input.lower()
        if any(word in user_lower for word in ["yes", "yeah", "yep", "correct", "right", "that's it"]):
            return True
        
        # Check for denial
        if any(word in user_lower for word in ["no", "nope", "not", "wrong", "different"]):
            return False
        
        return False

