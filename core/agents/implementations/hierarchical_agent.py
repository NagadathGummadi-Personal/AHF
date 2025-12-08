"""
Hierarchical Agent Implementation.

A manager agent that delegates tasks to worker agents.
Uses the prompt registry for prompt management with fallback to built-in defaults.
"""

from typing import Any, Optional, Dict

from .base_agent import BaseAgent
from ..spec.agent_context import AgentContext
from ..interfaces.agent_interfaces import IAgent

# Import prompt registry constants
try:
    from ...promptregistry.constants import PROMPT_LABEL_HIERARCHICAL_MANAGER
except ImportError:
    PROMPT_LABEL_HIERARCHICAL_MANAGER = "agent.hierarchical.manager"


class HierarchicalAgent(BaseAgent):
    """
    Hierarchical Agent.
    
    A manager agent that can delegate tasks to worker (sub) agents.
    The manager decides which worker to use and coordinates their outputs.
    
    Prompt Management:
    - Uses prompt registry if configured (recommended)
    - Falls back to built-in prompt if registry unavailable
    - Supports dynamic variables: {workers}, {task}, {context}
    
    Usage:
        # Create worker agents
        research_agent = (AgentBuilder()
            .with_name("researcher")
            .with_llm(llm)
            .with_tools([search_tool])
            .as_type(AgentType.REACT)
            .build())
        
        writer_agent = (AgentBuilder()
            .with_name("writer")
            .with_llm(llm)
            .as_type(AgentType.SIMPLE)
            .build())
        
        # Create manager with prompt registry
        manager = (AgentBuilder()
            .with_name("manager")
            .with_llm(llm)
            .with_prompt_registry(LocalPromptRegistry())  # Optional but recommended
            .as_type(AgentType.HIERARCHICAL)
            .build())
        
        # Add workers
        manager.add_worker("research", research_agent)
        manager.add_worker("write", writer_agent)
        
        result = await manager.run("Research AI and write a summary", ctx)
    """
    
    # Default prompt (used as fallback when registry is unavailable)
    DEFAULT_MANAGER_PROMPT = '''You are a manager AI that coordinates work between specialized workers.

Available workers:
{workers}

Your task: {task}

Decide which worker to delegate to and what instructions to give them.
You can delegate multiple times in sequence to different workers.

Respond with one of:

DELEGATE:
Worker: <worker_name>
Instructions: <what the worker should do>

OR when you have the final answer:

FINAL ANSWER:
<the complete final answer>

{context}

Your decision:'''
    
    # Prompt label for registry lookup
    MANAGER_PROMPT_LABEL = PROMPT_LABEL_HIERARCHICAL_MANAGER

    def __init__(self, *args, **kwargs):
        """Initialize hierarchical agent."""
        super().__init__(*args, **kwargs)
        self._workers: Dict[str, IAgent] = {}
        self._worker_descriptions: Dict[str, str] = {}
        self._cached_prompt_template: Optional[str] = None
        self._prompt_id: Optional[str] = None
    
    async def _get_manager_prompt_template(self) -> str:
        """
        Get the manager prompt template.
        
        Tries to fetch from prompt registry first, falls back to default.
        Caches the result for performance.
        
        Returns:
            Prompt template string
        """
        if self._cached_prompt_template:
            return self._cached_prompt_template
        
        # Try prompt registry first
        if self.prompt_registry:
            try:
                result = await self.prompt_registry.get_prompt_with_fallback(
                    self.MANAGER_PROMPT_LABEL,
                    model=getattr(self.llm, 'model_name', None),
                )
                self._cached_prompt_template = result.content
                self._prompt_id = result.prompt_id
                return self._cached_prompt_template
            except (ValueError, AttributeError):
                # Prompt not found in registry, use default
                pass
        
        # Use default
        self._cached_prompt_template = self.DEFAULT_MANAGER_PROMPT
        return self._cached_prompt_template
    
    def add_worker(
        self,
        name: str,
        agent: IAgent,
        description: Optional[str] = None
    ) -> None:
        """
        Add a worker agent.
        
        Args:
            name: Unique name for the worker
            agent: Agent instance
            description: Description of what this worker does
        """
        self._workers[name] = agent
        if description:
            self._worker_descriptions[name] = description
        elif hasattr(agent, 'spec') and hasattr(agent.spec, 'description'):
            self._worker_descriptions[name] = agent.spec.description
        else:
            self._worker_descriptions[name] = f"Worker: {name}"
    
    def remove_worker(self, name: str) -> None:
        """Remove a worker agent."""
        self._workers.pop(name, None)
        self._worker_descriptions.pop(name, None)
    
    def get_workers(self) -> Dict[str, IAgent]:
        """Get all worker agents."""
        return self._workers.copy()
    
    async def _execute_iteration(
        self,
        input_data: Any,
        ctx: AgentContext,
        iteration: int,
        system_prompt: Optional[str]
    ) -> tuple[Any, bool]:
        """
        Execute a hierarchical iteration.
        
        Manager decides what to delegate and to whom.
        """
        task = input_data if isinstance(input_data, str) else str(input_data)
        
        # Build worker descriptions
        worker_list = "\n".join([
            f"- {name}: {desc}"
            for name, desc in self._worker_descriptions.items()
        ])
        
        # Build context from scratchpad
        context = ""
        if self.scratchpad:
            scratchpad_content = self.scratchpad.read()
            if scratchpad_content:
                context = f"Previous work:\n{scratchpad_content}"
        
        # Get prompt from registry or use default
        prompt_template = await self._get_manager_prompt_template()
        
        # Use system prompt if provided and has our variables, otherwise use template
        if system_prompt and "{workers}" in system_prompt:
            prompt = system_prompt.format(
                workers=worker_list,
                task=task,
                context=context
            )
        else:
            prompt = prompt_template.format(
                workers=worker_list,
                task=task,
                context=context
            )
        
        messages = [{"role": "user", "content": prompt}]
        # Pass prompt_id for metrics tracking
        response = await self._call_llm(messages, ctx, prompt_id=self._prompt_id)
        content = response.content if hasattr(response, 'content') else str(response)
        
        # Parse response
        if "FINAL ANSWER:" in content.upper():
            # Extract final answer
            import re
            match = re.search(r'FINAL ANSWER:\s*(.+?)$', content, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip(), False
            return content, False
        
        if "DELEGATE:" in content.upper():
            # Extract delegation
            import re
            worker_match = re.search(r'Worker:\s*(\w+)', content, re.IGNORECASE)
            instructions_match = re.search(r'Instructions:\s*(.+?)(?=\n\n|$)', content, re.DOTALL | re.IGNORECASE)
            
            if worker_match:
                worker_name = worker_match.group(1).strip()
                instructions = instructions_match.group(1).strip() if instructions_match else task
                
                if worker_name in self._workers:
                    # Delegate to worker
                    worker = self._workers[worker_name]
                    
                    # Create child context
                    child_ctx = ctx.child_context(parent_agent_id=self.spec.id)
                    
                    # Execute worker
                    worker_result = await worker.run(instructions, child_ctx)
                    
                    # Get result content
                    result_content = worker_result.content if hasattr(worker_result, 'content') else str(worker_result)
                    
                    # Record in scratchpad
                    if self.scratchpad:
                        self.scratchpad.append(
                            f"Delegated to {worker_name}:\n"
                            f"Instructions: {instructions}\n"
                            f"Result: {result_content}"
                        )
                    
                    # Continue iteration
                    return None, True
                else:
                    # Unknown worker
                    if self.scratchpad:
                        self.scratchpad.append(f"Unknown worker: {worker_name}")
                    return None, True
        
        # Couldn't parse - return as final answer
        return content, False
    
    def _get_tool_descriptions(self) -> str:
        """Override to include workers as 'tools'."""
        # Include both tools and workers
        descriptions = []
        
        # Add regular tools
        for name, tool in self._tool_map.items():
            if hasattr(tool, 'spec') and hasattr(tool.spec, 'description'):
                descriptions.append(f"- {name} (tool): {tool.spec.description}")
            else:
                descriptions.append(f"- {name} (tool)")
        
        # Add workers
        for name, desc in self._worker_descriptions.items():
            descriptions.append(f"- {name} (worker): {desc}")
        
        return "\n".join(descriptions)
