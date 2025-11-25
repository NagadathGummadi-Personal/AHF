"""
ReAct Agent Implementation.

Implements the Reason-Act pattern: Thought -> Action -> Observation -> Thought.
"""

import json
import re
from typing import Any, Optional, List, Dict, AsyncIterator

from .base_agent import BaseAgent
from ..spec.agent_context import AgentContext
from ..spec.agent_result import AgentStreamChunk
from ..enum import AgentState
from ..constants import (
    REACT_THOUGHT,
    REACT_ACTION,
    REACT_ACTION_INPUT,
    REACT_OBSERVATION,
    REACT_FINAL_ANSWER,
    SCRATCHPAD_THOUGHT_PREFIX,
    SCRATCHPAD_ACTION_PREFIX,
    SCRATCHPAD_OBSERVATION_PREFIX,
)


class ReactAgent(BaseAgent):
    """
    ReAct (Reason + Act) Agent.
    
    Implements the ReAct pattern where the agent:
    1. Thinks about what to do (Thought)
    2. Takes an action using a tool (Action)
    3. Observes the result (Observation)
    4. Repeats until reaching a final answer
    
    The agent uses a scratchpad to maintain the reasoning trace.
    
    Usage:
        agent = (AgentBuilder()
            .with_name("react_agent")
            .with_llm(llm)
            .with_tools([search_tool, calculator_tool])
            .with_scratchpad(StructuredScratchpad())
            .as_type(AgentType.REACT)
            .build())
        
        result = await agent.run("What is the population of France?", ctx)
    
    Response Format Expected from LLM:
        Thought: <reasoning about what to do>
        Action: <tool_name>
        Action Input: <json parameters>
        
        OR
        
        Thought: <reasoning>
        Final Answer: <the final response>
    """
    
    REACT_PROMPT_TEMPLATE = '''You are a helpful AI assistant that can use tools to answer questions.

Available tools:
{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action (as valid JSON)
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {question}
{scratchpad}'''
    
    async def _execute_iteration(
        self,
        input_data: Any,
        ctx: AgentContext,
        iteration: int,
        system_prompt: Optional[str]
    ) -> tuple[Any, bool]:
        """
        Execute a single ReAct iteration.
        
        Returns:
            Tuple of (result, should_continue)
            - If Final Answer found: (answer, False)
            - If action needed: (None, True)
        """
        # Build prompt with scratchpad
        prompt = self._build_react_prompt(input_data, system_prompt)
        
        messages = [{"role": "user", "content": prompt}]
        
        # Get LLM response
        response = await self._call_llm(messages, ctx)
        response_text = response.content if hasattr(response, 'content') else str(response)
        
        # Parse response
        parsed = self._parse_react_response(response_text)
        
        # Check for final answer
        if parsed.get(REACT_FINAL_ANSWER):
            return parsed[REACT_FINAL_ANSWER], False
        
        # Process thought
        if parsed.get(REACT_THOUGHT):
            if self.scratchpad:
                if hasattr(self.scratchpad, 'add_thought'):
                    self.scratchpad.add_thought(parsed[REACT_THOUGHT])
                else:
                    self.scratchpad.append(f"{SCRATCHPAD_THOUGHT_PREFIX}{parsed[REACT_THOUGHT]}")
        
        # Process action
        if parsed.get(REACT_ACTION):
            action_name = parsed[REACT_ACTION]
            action_input = parsed.get(REACT_ACTION_INPUT, {})
            
            if self.scratchpad:
                if hasattr(self.scratchpad, 'add_action'):
                    self.scratchpad.add_action(action_name, action_input)
                else:
                    self.scratchpad.append(f"{SCRATCHPAD_ACTION_PREFIX}{action_name}")
                    if action_input:
                        self.scratchpad.append(f"Action Input: {json.dumps(action_input)}")
            
            # Execute tool
            try:
                tool_result = await self._execute_tool(action_name, action_input, ctx)
                
                # Format observation
                if hasattr(tool_result, 'content'):
                    observation = str(tool_result.content)
                else:
                    observation = str(tool_result)
                
            except Exception as e:
                observation = f"Error: {str(e)}"
            
            # Add observation to scratchpad
            if self.scratchpad:
                if hasattr(self.scratchpad, 'add_observation'):
                    self.scratchpad.add_observation(observation)
                else:
                    self.scratchpad.append(f"{SCRATCHPAD_OBSERVATION_PREFIX}{observation}")
            
            # Continue iteration
            return None, True
        
        # No action or final answer - unexpected response
        # Try to extract any content as final answer
        return response_text, False
    
    async def _stream_iteration(
        self,
        input_data: Any,
        ctx: AgentContext,
        iteration: int,
        system_prompt: Optional[str]
    ) -> AsyncIterator[AgentStreamChunk]:
        """Stream a ReAct iteration."""
        prompt = self._build_react_prompt(input_data, system_prompt)
        messages = [{"role": "user", "content": prompt}]
        
        # Stream LLM response
        response_text = ""
        async for chunk in self.llm.stream_answer(messages, ctx):
            response_text += chunk.content
            yield AgentStreamChunk(
                content=chunk.content,
                chunk_type="thought",
                iteration=iteration,
                is_final=False,
                state=AgentState.RUNNING,
            )
        
        # Parse completed response
        parsed = self._parse_react_response(response_text)
        
        if parsed.get(REACT_FINAL_ANSWER):
            yield AgentStreamChunk(
                content=parsed[REACT_FINAL_ANSWER],
                chunk_type="output",
                iteration=iteration,
                is_final=True,
                state=AgentState.COMPLETED,
            )
            return
        
        if parsed.get(REACT_ACTION):
            action_name = parsed[REACT_ACTION]
            action_input = parsed.get(REACT_ACTION_INPUT, {})
            
            yield AgentStreamChunk(
                content=f"Executing tool: {action_name}",
                chunk_type="action",
                iteration=iteration,
                is_final=False,
                state=AgentState.RUNNING,
                tool_name=action_name,
                tool_args=action_input,
            )
            
            try:
                result = await self._execute_tool(action_name, action_input, ctx)
                observation = str(result.content) if hasattr(result, 'content') else str(result)
            except Exception as e:
                observation = f"Error: {str(e)}"
            
            # Update scratchpad
            if self.scratchpad:
                if hasattr(self.scratchpad, 'add_thought'):
                    self.scratchpad.add_thought(parsed.get(REACT_THOUGHT, ""))
                    self.scratchpad.add_action(action_name, action_input)
                    self.scratchpad.add_observation(observation)
            
            yield AgentStreamChunk(
                content=observation,
                chunk_type="observation",
                iteration=iteration,
                is_final=False,
                state=AgentState.RUNNING,
                tool_name=action_name,
                tool_result=observation,
            )
    
    def _build_react_prompt(
        self,
        input_data: Any,
        system_prompt: Optional[str]
    ) -> str:
        """Build the ReAct prompt with scratchpad."""
        tool_descriptions = self._get_tool_descriptions()
        tool_names = ", ".join(self._tool_map.keys())
        
        scratchpad_content = ""
        if self.scratchpad:
            scratchpad_content = self.scratchpad.read()
        
        question = input_data if isinstance(input_data, str) else str(input_data)
        
        base_prompt = system_prompt or self.REACT_PROMPT_TEMPLATE
        
        if "{tools}" in base_prompt:
            return base_prompt.format(
                tools=tool_descriptions,
                tool_names=tool_names,
                question=question,
                scratchpad=scratchpad_content,
            )
        else:
            return self.REACT_PROMPT_TEMPLATE.format(
                tools=tool_descriptions,
                tool_names=tool_names,
                question=question,
                scratchpad=scratchpad_content,
            )
    
    def _parse_react_response(self, response: str) -> Dict[str, Any]:
        """
        Parse ReAct-formatted response.
        
        Returns:
            Dict with keys: thought, action, action_input, final_answer
        """
        result = {}
        
        # Extract thought
        thought_match = re.search(r'Thought:\s*(.+?)(?=Action:|Final Answer:|$)', response, re.DOTALL | re.IGNORECASE)
        if thought_match:
            result[REACT_THOUGHT] = thought_match.group(1).strip()
        
        # Check for final answer
        final_match = re.search(r'Final Answer:\s*(.+?)$', response, re.DOTALL | re.IGNORECASE)
        if final_match:
            result[REACT_FINAL_ANSWER] = final_match.group(1).strip()
            return result
        
        # Extract action
        action_match = re.search(r'Action:\s*(\w+)', response, re.IGNORECASE)
        if action_match:
            result[REACT_ACTION] = action_match.group(1).strip()
        
        # Extract action input
        input_match = re.search(r'Action Input:\s*(.+?)(?=Observation:|Thought:|$)', response, re.DOTALL | re.IGNORECASE)
        if input_match:
            input_str = input_match.group(1).strip()
            try:
                result[REACT_ACTION_INPUT] = json.loads(input_str)
            except json.JSONDecodeError:
                # Try to parse as simple value
                result[REACT_ACTION_INPUT] = {"input": input_str}
        
        return result

