"""
Greeting and Routing Agent Node

Main conversational agent that greets users and routes to appropriate flows.

Version: 1.0.0
"""

from typing import Any, AsyncIterator, Dict, List, Optional

from core.workflows.spec import WorkflowExecutionContext
from core.llms import ILLM, LLMContext
from core.agents.interfaces import IAgent

from air.memory.session import VoiceAgentSession
from air.models.task import Task, TaskPriority
from air.prompts.greeting_prompt import build_greeting_prompt

from ..base import BaseAgentNode, NodeConfig, NodeContext


class GreetingAgentConfig(NodeConfig):
    """Configuration for Greeting agent node."""
    
    # LLM configuration
    temperature: float = 0.7
    max_tokens: int = 500
    
    # Routing configuration
    booking_edge: str = "booking_edge"
    cancel_edge: str = "cancel_edge"
    reschedule_edge: str = "reschedule_edge"
    faq_edge: str = "faq_edge"
    handover_edge: str = "handover_edge"


class GreetingRoutingAgent(BaseAgentNode):
    """
    Greeting and routing agent.
    
    Handles:
    - Initial greeting and context gathering
    - Intent detection (booking, cancellation, FAQ, etc.)
    - Routing to appropriate flow
    - Task creation for user requests
    
    Tools:
    - HandoverCallToHuman: Transfer to human agent
    - GetPricingInfo: Get service pricing
    - GetTherapistForService: Get therapist availability
    
    Edges:
    - booking_edge: When user wants to book (conditional)
    - handover_edge: When handover is needed
    """
    
    def __init__(
        self,
        node_id: str = "greeting_routing_agent",
        name: str = "GreetingRoutingAgent",
        config: Optional[GreetingAgentConfig] = None,
        llm: Optional[ILLM] = None,
    ):
        super().__init__(
            node_id=node_id,
            name=name,
            description="Greeting and intent routing agent",
            config=config or GreetingAgentConfig(),
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
        """Build system prompt with dynamic variables."""
        return build_greeting_prompt(
            dynamic_vars=session.dynamic_vars,
            custom_instructions=self.config.customer_instructions,
        )
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get tool definitions for LLM function calling."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "HandoverCallToHuman",
                    "description": "Transfer the call to a human agent",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "reason": {
                                "type": "string",
                                "description": "Reason for handover"
                            },
                            "call_summary": {
                                "type": "string",
                                "description": "Summary of the call so far"
                            }
                        },
                        "required": ["reason"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "GetPricingInfo",
                    "description": "Get pricing information for a service",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "service_code": {
                                "type": "string",
                                "description": "Service code to get pricing for"
                            },
                            "addon_codes": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Optional addon codes"
                            }
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
        """Execute greeting agent logic."""
        
        if not session:
            raise ValueError("Session is required for GreetingRoutingAgent")
        
        if not self._llm:
            raise ValueError("LLM is required for GreetingRoutingAgent")
        
        # Get user input
        user_input = ""
        if isinstance(input_data, dict):
            user_input = input_data.get("user_input", "")
        elif isinstance(input_data, str):
            user_input = input_data
        
        # Build messages
        messages = [
            {"role": "system", "content": system_prompt},
        ]
        
        # Add conversation history
        history = session.get_llm_messages()
        messages.extend(history)
        
        # Add current user message
        if user_input:
            messages.append({"role": "user", "content": user_input})
            session.add_user_message(user_input)
        
        # Check for stashed context (from interrupt)
        stashed_context = session.get_stashed_context()
        if stashed_context:
            messages[-1]["content"] = f"{stashed_context}\n\nUser: {user_input}"
        
        # Call LLM
        llm_context = LLMContext()
        response = await self._llm.get_answer(
            messages=messages,
            ctx=llm_context,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            tools=self.get_tools(),
        )
        
        # Process response
        assistant_message = response.content
        tool_calls = response.tool_calls if hasattr(response, "tool_calls") else []
        
        # Detect intent from response
        detected_intent = self._detect_intent(user_input, assistant_message, tool_calls)
        
        # Create/update task if intent detected
        task = None
        if detected_intent and detected_intent != "UNKNOWN":
            current_task = await session.get_current_task()
            
            if not current_task or current_task.intent != detected_intent:
                task = await session.create_task(
                    intent=detected_intent,
                    original_input=user_input,
                )
                await session.start_task(task.task_id)
        
        # Add assistant response to conversation
        session.add_assistant_message(assistant_message)
        
        # Determine next edge
        next_edge = self._determine_edge(detected_intent, tool_calls)
        
        return {
            "response": assistant_message,
            "detected_intent": detected_intent,
            "tool_calls": tool_calls,
            "next_edge": next_edge,
            "task": task,
            "service_names": self._extract_service_names(user_input, assistant_message),
        }
    
    def _detect_intent(
        self,
        user_input: str,
        assistant_response: str,
        tool_calls: List[Any],
    ) -> str:
        """Detect user intent from conversation."""
        user_lower = user_input.lower()
        
        # Check for explicit intents
        if any(word in user_lower for word in ["book", "appointment", "schedule", "reserve"]):
            return "BOOK"
        
        if any(word in user_lower for word in ["cancel", "remove"]):
            return "CANCEL"
        
        if any(word in user_lower for word in ["reschedule", "change", "move"]):
            return "RESCHEDULE"
        
        # Check tool calls for handover
        for tc in tool_calls:
            if tc.get("name") == "HandoverCallToHuman":
                return "HANDOVER"
        
        return "UNKNOWN"
    
    def _determine_edge(
        self,
        intent: str,
        tool_calls: List[Any],
    ) -> Optional[str]:
        """Determine which edge to traverse based on intent."""
        if intent == "BOOK":
            return self.config.booking_edge
        elif intent == "CANCEL":
            return self.config.cancel_edge
        elif intent == "RESCHEDULE":
            return self.config.reschedule_edge
        elif intent == "HANDOVER":
            return self.config.handover_edge
        
        return None
    
    def _extract_service_names(
        self,
        user_input: str,
        assistant_response: str,
    ) -> List[str]:
        """Extract service names mentioned by user."""
        # TODO: Implement proper NER or use LLM for extraction
        # For now, return empty list - actual extraction happens in transformation node
        return []
    
    async def stream(
        self,
        input_data: Any,
        context: WorkflowExecutionContext,
        user_prompt: Optional[str] = None,
        **kwargs,
    ) -> AsyncIterator[Any]:
        """Stream agent responses."""
        session: Optional[VoiceAgentSession] = kwargs.get("session")
        
        if not session or not self._llm:
            result = await self.execute(input_data, context, user_prompt, **kwargs)
            yield result
            return
        
        system_prompt = self.get_system_prompt(session)
        
        # Build messages
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(session.get_llm_messages())
        
        user_input = input_data.get("user_input", "") if isinstance(input_data, dict) else str(input_data)
        if user_input:
            messages.append({"role": "user", "content": user_input})
        
        # Stream from LLM
        llm_context = LLMContext()
        async for chunk in self._llm.stream_answer(
            messages=messages,
            ctx=llm_context,
            temperature=self.config.temperature,
            tools=self.get_tools(),
        ):
            # Check for interrupts during streaming
            if session.has_interrupt_sync():
                # Stash current response
                session.stash_response(
                    content=chunk.content,
                    interrupt_message="User interrupted",
                )
                break
            
            yield {
                "chunk": chunk.content,
                "is_final": chunk.is_final if hasattr(chunk, "is_final") else False,
            }

