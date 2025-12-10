"""
Fallback Agent Node

Handles deviations, topic switches, and task queue management.

Version: 1.0.0
"""

from typing import Any, Dict, List, Optional

from core.workflows.spec import WorkflowExecutionContext
from core.llms import ILLM, LLMContext

from app.memory.session import VoiceAgentSession
from app.models.task import Task, TaskPriority, TaskState
from app.prompts.fallback_prompt import build_fallback_prompt

from ..base import BaseAgentNode, NodeConfig, NodeContext


class FallbackConfig(NodeConfig):
    """Configuration for Fallback agent."""
    
    temperature: float = 0.7
    max_tokens: int = 400


class FallbackAgent(BaseAgentNode):
    """
    Fallback and deviation handling agent.
    
    Manages:
    - Topic switches during conversation
    - Task queuing for interrupted flows
    - Context preservation for paused tasks
    - Resumption of unfinished tasks
    
    This agent ensures no user request is lost even when
    they switch topics mid-conversation.
    """
    
    def __init__(
        self,
        node_id: str = "fallback_agent",
        name: str = "FallbackAgent",
        config: Optional[FallbackConfig] = None,
        llm: Optional[ILLM] = None,
    ):
        super().__init__(
            node_id=node_id,
            name=name,
            description="Handle deviations and manage task queue",
            config=config or FallbackConfig(),
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
        """Build system prompt with task context."""
        return build_fallback_prompt(
            current_task=kwargs.get("current_task", "None"),
            task_state=kwargs.get("task_state", "idle"),
            current_step=kwargs.get("current_step", "None"),
            pending_steps=kwargs.get("pending_steps", "[]"),
            queue_count=kwargs.get("queue_count", 0),
            has_paused_tasks=kwargs.get("has_paused_tasks", False),
            previous_topic=kwargs.get("previous_topic", ""),
            user_message=kwargs.get("user_message", ""),
            detected_intent=kwargs.get("detected_intent", "UNKNOWN"),
            custom_instructions=self.config.customer_instructions,
        )
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get tool definitions."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "HandoverCallToHuman",
                    "description": "Transfer to human agent",
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
        """Execute fallback agent."""
        
        if not session or not self._llm:
            raise ValueError("Session and LLM are required")
        
        # Get inputs
        data = input_data if isinstance(input_data, dict) else {}
        user_input = data.get("user_input", "")
        
        # Get current task context
        current_task = await session.get_current_task()
        
        task_info = "None"
        task_state = "idle"
        current_step = "None"
        pending_steps = "[]"
        
        if current_task:
            task_info = f"{current_task.intent}: {current_task.original_input}"
            task_state = current_task.state.value if isinstance(current_task.state, TaskState) else current_task.state
            
            if current_task.plan:
                current_step_obj = current_task.plan.get_current_step()
                if current_step_obj:
                    current_step = current_step_obj.step_name
                pending = current_task.plan.get_pending_steps()
                pending_steps = str([s.step_name for s in pending])
        
        # Check for paused tasks
        paused_tasks = [
            t for t in (await session.task_queue.get_all_pending())
            if t.state == TaskState.PAUSED
        ]
        
        # Detect intent of new message
        detected_intent = self._detect_intent(user_input)
        
        # Build prompt with context
        system_prompt = self.get_system_prompt(
            session,
            current_task=task_info,
            task_state=task_state,
            current_step=current_step,
            pending_steps=pending_steps,
            queue_count=await session.task_queue.get_pending_count(),
            has_paused_tasks=len(paused_tasks) > 0,
            previous_topic=task_info if current_task else "",
            user_message=user_input,
            detected_intent=detected_intent,
        )
        
        # Build messages
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(session.get_llm_messages())
        
        if user_input:
            messages.append({"role": "user", "content": user_input})
            session.add_user_message(user_input)
        
        # Decide whether to pause current task and create new one
        should_switch = self._should_switch_task(current_task, detected_intent)
        
        if should_switch and current_task:
            # Pause current task
            current_task.pause(reason=f"User switched to: {detected_intent}")
            await session.task_queue.update(current_task)
            
            # Create new task with higher priority
            new_task = await session.create_task(
                intent=detected_intent,
                original_input=user_input,
                priority=TaskPriority.HIGH,
            )
            await session.start_task(new_task.task_id)
        
        # Call LLM
        response = await self._llm.get_answer(
            messages=messages,
            ctx=LLMContext(),
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            tools=self.get_tools(),
        )
        
        session.add_assistant_message(response.content)
        
        # Determine next action
        next_node = self._determine_next_node(detected_intent, should_switch)
        
        return {
            "response": response.content,
            "detected_intent": detected_intent,
            "task_switched": should_switch,
            "next_node": next_node,
            "paused_tasks_count": len(paused_tasks),
        }
    
    def _detect_intent(self, user_input: str) -> str:
        """Detect intent from user message."""
        user_lower = user_input.lower()
        
        if any(word in user_lower for word in ["book", "appointment", "schedule"]):
            return "BOOK"
        if any(word in user_lower for word in ["cancel"]):
            return "CANCEL"
        if any(word in user_lower for word in ["reschedule", "change time"]):
            return "RESCHEDULE"
        if any(word in user_lower for word in ["human", "operator", "agent", "person"]):
            return "HANDOVER"
        if "?" in user_input:
            return "FAQ"
        
        return "UNKNOWN"
    
    def _should_switch_task(
        self,
        current_task: Optional[Task],
        new_intent: str,
    ) -> bool:
        """Determine if we should switch to a new task."""
        if not current_task:
            return True
        
        # Same intent - don't switch
        if current_task.intent == new_intent:
            return False
        
        # Unknown intent - don't switch, handle in current context
        if new_intent == "UNKNOWN":
            return False
        
        # Different intent - switch
        return True
    
    def _determine_next_node(
        self,
        intent: str,
        task_switched: bool,
    ) -> Optional[str]:
        """Determine which node to route to."""
        if intent == "BOOK":
            return "transformation_tool"
        elif intent == "CANCEL":
            return "cancellation_agent"
        elif intent == "RESCHEDULE":
            return "reschedule_agent"
        elif intent == "HANDOVER":
            return "handover_tool"
        
        # Stay in current flow
        return None

