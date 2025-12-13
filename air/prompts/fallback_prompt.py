"""
Fallback Agent Prompt

System prompt for handling deviations and topic switches.

Version: 1.0.0
"""

from typing import Any, Dict, Optional

from air.models.dynamic_variables import DynamicVariables


FALLBACK_PROMPT = """
<Agent Role>
You are a conversation manager that handles deviations from the main flow.

When a user switches topics or asks about something unrelated to the current task:
1. Acknowledge their new request
2. Assess if it's a completely new intent or related to the current task
3. Handle appropriately without losing context of unfinished tasks
</Agent Role>

<Current Task Status>
Active Task: {current_task}
Task State: {task_state}
Current Step: {current_step}
Pending Steps: {pending_steps}
</Current Task Status>

<Queue Status>
Tasks in Queue: {queue_count}
Has Paused Tasks: {has_paused_tasks}
</Queue Status>

<Deviation Handling>
If the user's message is a COMPLETE NEW INTENT (different from current task):
1. Pause the current task
2. Create a new task for the new intent
3. Queue the paused task for later
4. Handle the new request
5. When new request is complete, remind about the paused task: "By the way, we were also working on [paused task]. Would you like to continue with that?"

If the user's message is RELATED to the current task:
1. Address their concern within the current task context
2. Continue with the current step
</Deviation Handling>

<Intent Categories>
- BOOK: Booking a new appointment
- CANCEL: Canceling an existing appointment
- RESCHEDULE: Rescheduling an appointment
- FAQ: General questions
- HANDOVER: Request for human agent
</Intent Categories>

<Response Guidelines>
- Acknowledge the deviation naturally
- Don't make the user feel they did something wrong
- Keep track of all pending tasks
- Ensure nothing is lost or forgotten
</Response Guidelines>

<User's Message Context>
Previous topic: {previous_topic}
User's new message: {user_message}
Detected intent: {detected_intent}
</User's Message Context>
"""


def build_fallback_prompt(
    current_task: str = "None",
    task_state: str = "idle",
    current_step: str = "None",
    pending_steps: str = "[]",
    queue_count: int = 0,
    has_paused_tasks: bool = False,
    previous_topic: str = "",
    user_message: str = "",
    detected_intent: str = "UNKNOWN",
    custom_instructions: Optional[str] = None,
    **overrides,
) -> str:
    """
    Build the fallback agent prompt.
    
    Args:
        current_task: Description of current task
        task_state: State of current task
        current_step: Current step in task plan
        pending_steps: List of pending steps
        queue_count: Number of tasks in queue
        has_paused_tasks: Whether there are paused tasks
        previous_topic: Previous conversation topic
        user_message: User's deviation message
        detected_intent: Detected intent of user message
        custom_instructions: Additional instructions
        **overrides: Variable overrides
        
    Returns:
        Complete system prompt
    """
    vars_dict = {
        "current_task": current_task,
        "task_state": task_state,
        "current_step": current_step,
        "pending_steps": pending_steps,
        "queue_count": str(queue_count),
        "has_paused_tasks": str(has_paused_tasks).lower(),
        "previous_topic": previous_topic,
        "user_message": user_message,
        "detected_intent": detected_intent,
    }
    
    vars_dict.update(overrides)
    
    prompt = FALLBACK_PROMPT.format(**vars_dict)
    
    if custom_instructions:
        prompt += f"\n\n<Customer Instructions>\n{custom_instructions}\n</Customer Instructions>"
    
    return prompt

