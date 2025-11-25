"""
Goal-Based Agent Implementation.

An agent that works towards achieving specific goals using a checklist.
"""

from typing import Any, Optional, List, Dict

from .base_agent import BaseAgent
from ..spec.agent_context import AgentContext
from ..enum import ChecklistStatus


class GoalBasedAgent(BaseAgent):
    """
    Goal-Based Agent.
    
    Works towards achieving specific goals by:
    1. Breaking down the goal into tasks (using planner or LLM)
    2. Tracking progress with a checklist
    3. Executing tasks in order
    4. Completing when all tasks are done
    
    Usage:
        agent = (AgentBuilder()
            .with_name("goal_agent")
            .with_llm(llm)
            .with_tools([research_tool, write_tool])
            .with_checklist(BasicChecklist())
            .as_type(AgentType.GOAL_BASED)
            .build())
        
        result = await agent.run("Write a summary about AI", ctx)
    """
    
    PLANNING_PROMPT = '''You are a helpful AI assistant. Break down the following goal into a list of specific, actionable tasks.

Goal: {goal}

Available tools:
{tools}

Return a JSON list of tasks, each with:
- "task": description of the task
- "tool": which tool to use (or "none" for reasoning tasks)
- "priority": priority number (lower = higher priority)

Example response:
[
    {{"task": "Search for information", "tool": "search", "priority": 1}},
    {{"task": "Analyze the results", "tool": "none", "priority": 2}},
    {{"task": "Write summary", "tool": "write", "priority": 3}}
]

Tasks (as JSON):'''

    TASK_EXECUTION_PROMPT = '''You are working on the following goal: {goal}

Current task: {task}

{context}

{tools_available}

Complete this task. If you need to use a tool, respond with:
Action: <tool_name>
Action Input: <json parameters>

If you can complete without a tool, respond with:
Result: <your answer or output>'''

    async def _execute_iteration(
        self,
        input_data: Any,
        ctx: AgentContext,
        iteration: int,
        system_prompt: Optional[str]
    ) -> tuple[Any, bool]:
        """
        Execute a goal-based iteration.
        
        First iteration: Create plan
        Subsequent iterations: Execute next task
        """
        goal = input_data if isinstance(input_data, str) else str(input_data)
        
        # First iteration: Create plan if checklist is empty
        if iteration == 1 and self.checklist:
            pending = self.checklist.get_pending_items()
            if not pending:
                await self._create_plan(goal, ctx)
        
        # Get next task
        if self.checklist:
            pending = self.checklist.get_pending_items()
            
            if not pending:
                # All tasks complete - generate final result
                return await self._generate_final_result(goal, ctx), False
            
            # Get highest priority task
            current_task = min(pending, key=lambda x: x.get('priority', 0))
            task_id = current_task.get('id')
            task_desc = current_task.get('description', '')
            
            # Mark as in progress
            self.checklist.update_status(task_id, ChecklistStatus.IN_PROGRESS.value)
            
            # Execute task
            try:
                result = await self._execute_task(goal, current_task, ctx)
                
                # Mark as completed
                self.checklist.update_status(task_id, ChecklistStatus.COMPLETED.value)
                
                # Record in scratchpad
                if self.scratchpad:
                    self.scratchpad.append(f"Task: {task_desc}\nResult: {result}")
                
                # Check if all done
                if self.checklist.is_complete():
                    return await self._generate_final_result(goal, ctx), False
                
                return None, True
                
            except Exception as e:
                self.checklist.update_status(task_id, ChecklistStatus.FAILED.value)
                if self.scratchpad:
                    self.scratchpad.append(f"Task: {task_desc}\nFailed: {str(e)}")
                return None, True
        
        # No checklist - just execute directly
        messages = self._build_simple_messages(goal, system_prompt)
        response = await self._call_llm(messages, ctx)
        return response.content, False
    
    async def _create_plan(self, goal: str, ctx: AgentContext) -> None:
        """Create a plan and populate the checklist."""
        if self.planner:
            # Use custom planner
            plan = await self.planner.create_plan(goal, ctx)
            for step in plan:
                self.checklist.add_item(
                    step.get('task', step.get('description', '')),
                    priority=step.get('priority', 0),
                    metadata=step
                )
        else:
            # Use LLM to create plan
            tool_descriptions = self._get_tool_descriptions()
            prompt = self.PLANNING_PROMPT.format(
                goal=goal,
                tools=tool_descriptions
            )
            
            messages = [{"role": "user", "content": prompt}]
            response = await self._call_llm(messages, ctx)
            
            # Parse plan from response
            try:
                import json
                # Extract JSON from response
                content = response.content if hasattr(response, 'content') else str(response)
                
                # Try to find JSON array in response
                start = content.find('[')
                end = content.rfind(']') + 1
                if start >= 0 and end > start:
                    json_str = content[start:end]
                    tasks = json.loads(json_str)
                    
                    for task in tasks:
                        self.checklist.add_item(
                            task.get('task', ''),
                            priority=task.get('priority', 0),
                            metadata={"tool": task.get('tool', 'none')}
                        )
            except Exception:
                # Fallback: create single task
                self.checklist.add_item(f"Complete: {goal}", priority=1)
    
    async def _execute_task(
        self,
        goal: str,
        task: Dict[str, Any],
        ctx: AgentContext
    ) -> str:
        """Execute a single task."""
        task_desc = task.get('description', '')
        tool_hint = task.get('metadata', {}).get('tool', 'none')
        
        # Build context from scratchpad
        context = ""
        if self.scratchpad:
            context = f"Previous work:\n{self.scratchpad.read()}"
        
        tools_available = ""
        if self._tool_map:
            tools_available = f"Available tools: {', '.join(self._tool_map.keys())}"
        
        prompt = self.TASK_EXECUTION_PROMPT.format(
            goal=goal,
            task=task_desc,
            context=context,
            tools_available=tools_available
        )
        
        messages = [{"role": "user", "content": prompt}]
        response = await self._call_llm(messages, ctx)
        content = response.content if hasattr(response, 'content') else str(response)
        
        # Check if tool use is indicated
        if "Action:" in content:
            import re
            action_match = re.search(r'Action:\s*(\w+)', content)
            if action_match:
                action_name = action_match.group(1)
                
                input_match = re.search(r'Action Input:\s*(.+?)(?=$)', content, re.DOTALL)
                action_input = {}
                if input_match:
                    try:
                        import json
                        action_input = json.loads(input_match.group(1).strip())
                    except:
                        action_input = {"input": input_match.group(1).strip()}
                
                result = await self._execute_tool(action_name, action_input, ctx)
                return str(result.content) if hasattr(result, 'content') else str(result)
        
        # Check for result
        if "Result:" in content:
            import re
            result_match = re.search(r'Result:\s*(.+?)$', content, re.DOTALL)
            if result_match:
                return result_match.group(1).strip()
        
        return content
    
    async def _generate_final_result(self, goal: str, ctx: AgentContext) -> str:
        """Generate final result after all tasks complete."""
        context = ""
        if self.scratchpad:
            context = self.scratchpad.read()
        
        checklist_summary = ""
        if self.checklist:
            progress = self.checklist.get_progress()
            checklist_summary = f"\nCompleted {progress['completed']} of {progress['total']} tasks."
        
        prompt = f'''Based on the following work, provide the final answer to the goal.

Goal: {goal}

Work completed:
{context}
{checklist_summary}

Final Answer:'''
        
        messages = [{"role": "user", "content": prompt}]
        response = await self._call_llm(messages, ctx)
        return response.content if hasattr(response, 'content') else str(response)
    
    def _build_simple_messages(
        self,
        goal: str,
        system_prompt: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Build simple messages without checklist."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": goal})
        return messages

