"""
Simple Agent Implementation.

A basic single-shot agent that processes input once without iteration.
"""

from typing import Any, Optional, List, Dict

from .base_agent import BaseAgent
from ..spec.agent_context import AgentContext


class SimpleAgent(BaseAgent):
    """
    Simple single-shot agent.
    
    Processes input once and returns the LLM response without
    tool use or iteration. Best for simple Q&A or text generation tasks.
    
    Usage:
        agent = (AgentBuilder()
            .with_name("simple_qa")
            .with_llm(llm)
            .with_system_prompt("You are a helpful assistant.")
            .as_type(AgentType.SIMPLE)
            .build())
        
        result = await agent.run("What is 2+2?", ctx)
    """
    
    async def _execute_iteration(
        self,
        input_data: Any,
        ctx: AgentContext,
        iteration: int,
        system_prompt: Optional[str]
    ) -> tuple[Any, bool]:
        """
        Execute single iteration.
        
        For SimpleAgent, this is always the only iteration.
        """
        messages = self._build_messages(input_data, system_prompt)
        response = await self._call_llm(messages, ctx)
        
        # Simple agent always completes after one iteration
        return response.content, False
    
    def _build_messages(
        self,
        input_data: Any,
        system_prompt: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Build messages for LLM."""
        messages = []
        
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        # Handle different input types
        if isinstance(input_data, str):
            messages.append({
                "role": "user",
                "content": input_data
            })
        elif isinstance(input_data, dict):
            if "messages" in input_data:
                messages.extend(input_data["messages"])
            elif "content" in input_data:
                messages.append({
                    "role": "user",
                    "content": input_data["content"]
                })
            else:
                messages.append({
                    "role": "user",
                    "content": str(input_data)
                })
        elif isinstance(input_data, list):
            # Assume it's a list of messages
            messages.extend(input_data)
        else:
            messages.append({
                "role": "user",
                "content": str(input_data)
            })
        
        return messages

