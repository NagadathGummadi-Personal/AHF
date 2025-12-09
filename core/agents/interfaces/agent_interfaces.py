"""
Interfaces for Agents Subsystem.

This module defines the core protocols (interfaces) that all agent implementations
must follow, ensuring a consistent API across all agent types.

Pluggable Components:
- IAgent: Core agent interface
- IAgentMemory: Memory/storage for context and history (from core.memory)
- IAgentScratchpad: Temporary workspace for reasoning (from core.memory)
- IAgentChecklist: Goal tracking and progress (from core.memory)
- IAgentPlanner: Planning and task decomposition
- IAgentObserver: Event observation and hooks (from core.memory)
- IAgentInputProcessor: Input preprocessing and validation
- IAgentOutputProcessor: Output postprocessing and formatting

Note: Memory-related interfaces (IAgentMemory, IAgentScratchpad, IAgentChecklist,
IAgentObserver) are now defined in core.memory.interfaces and re-exported here
for backward compatibility.
"""

from __future__ import annotations
from typing import (
    Any,
    AsyncIterator,
    Dict,
    List,
    Optional,
    Protocol,
    runtime_checkable,
    TYPE_CHECKING,
)

if TYPE_CHECKING:
    from ..spec.agent_result import AgentResult, AgentStreamChunk
    from ..spec.agent_context import AgentContext
    from ..enum import AgentInputType, AgentOutputType

# Re-export memory interfaces from core.memory for backward compatibility
from core.memory.interfaces import (
    IAgentMemory,
    IAgentScratchpad,
    IAgentChecklist,
    IAgentObserver,
)


@runtime_checkable
class IAgent(Protocol):
    """
    Core Agent Interface.
    
    Represents an autonomous entity that can perceive, reason, and act.
    All agent implementations must implement this interface.
    
    Required Methods:
    1. run() - Execute the agent's main logic (non-streaming)
    2. stream() - Stream the agent's execution steps
    3. get_state() - Get current internal state
    
    Optional Methods (via base implementation):
    - stop() - Stop ongoing execution
    - reset() - Reset agent to initial state
    
    Example:
        class MyAgent(IAgent):
            async def run(self, input_data, ctx, **kwargs):
                # Process input and return result
                return AgentResult(content="Done", ...)
            
            async def stream(self, input_data, ctx, **kwargs):
                # Stream execution steps
                yield AgentStreamChunk(content="Step 1", ...)
            
            def get_state(self):
                return {"status": "idle", ...}
    """
    
    async def run(
        self,
        input_data: Any,
        ctx: 'AgentContext',
        **kwargs: Any
    ) -> 'AgentResult':
        """
        Execute the agent's main loop or logic.
        
        Args:
            input_data: Input to process (can be text, structured data, etc.)
            ctx: Agent execution context
            **kwargs: Additional parameters
            
        Returns:
            AgentResult with the final output
            
        Raises:
            AgentExecutionError: If execution fails
            MaxIterationsError: If max iterations exceeded
            AgentTimeoutError: If execution times out
        """
        ...
    
    async def stream(
        self,
        input_data: Any,
        ctx: 'AgentContext',
        **kwargs: Any
    ) -> AsyncIterator['AgentStreamChunk']:
        """
        Stream the agent's execution steps or output.
        
        Yields chunks of execution progress as they occur.
        
        Args:
            input_data: Input to process
            ctx: Agent execution context
            **kwargs: Additional parameters
            
        Yields:
            AgentStreamChunk objects with execution progress
            
        Raises:
            AgentExecutionError: If execution fails
            MaxIterationsError: If max iterations exceeded
        """
        ...
    
    def get_state(self) -> Dict[str, Any]:
        """
        Get the current internal state of the agent.
        
        Returns:
            Dictionary containing:
            - status: Current agent status (idle, running, etc.)
            - iteration: Current iteration number
            - last_action: Last action taken
            - Additional state depending on agent type
        """
        ...


@runtime_checkable
class IAgentPlanner(Protocol):
    """
    Interface for Agent Planning.
    
    Responsible for breaking down high-level goals into actionable steps.
    Used by goal-based and hierarchical agents.
    
    Example:
        planner = HierarchicalPlanner()
        plan = await planner.create_plan(
            goal="Write a research paper on AI",
            context=ctx
        )
        # plan = [
        #     {"step": 1, "action": "research", "description": "Research AI topics"},
        #     {"step": 2, "action": "outline", "description": "Create outline"},
        #     ...
        # ]
    """
    
    async def create_plan(
        self,
        goal: str,
        ctx: 'AgentContext',
        **kwargs: Any
    ) -> List[Dict[str, Any]]:
        """
        Create a plan to achieve the goal.
        
        Args:
            goal: High-level goal description
            ctx: Agent context
            **kwargs: Additional parameters
            
        Returns:
            List of plan steps
        """
        ...
    
    async def refine_plan(
        self,
        plan: List[Dict[str, Any]],
        feedback: str,
        ctx: 'AgentContext'
    ) -> List[Dict[str, Any]]:
        """
        Refine an existing plan based on feedback.
        
        Args:
            plan: Current plan
            feedback: Feedback on what needs to change
            ctx: Agent context
            
        Returns:
            Refined plan
        """
        ...
    
    async def get_next_step(
        self,
        plan: List[Dict[str, Any]],
        completed_steps: List[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Get the next step to execute.
        
        Args:
            plan: The full plan
            completed_steps: List of completed step IDs
            
        Returns:
            Next step to execute or None if plan is complete
        """
        ...


@runtime_checkable
class IAgentInputProcessor(Protocol):
    """
    Interface for Input Processing.
    
    Preprocesses and validates input before the agent processes it.
    Can handle type conversion, validation, and normalization.
    
    Example:
        class MultimodalInputProcessor(IAgentInputProcessor):
            def get_supported_types(self):
                return [AgentInputType.TEXT, AgentInputType.IMAGE]
            
            async def process(self, input_data, input_type, ctx):
                if input_type == AgentInputType.IMAGE:
                    return await self.process_image(input_data)
                return input_data
    """
    
    def get_supported_types(self) -> List['AgentInputType']:
        """
        Get list of supported input types.
        
        Returns:
            List of AgentInputType values
        """
        ...
    
    async def validate(
        self,
        input_data: Any,
        input_type: 'AgentInputType',
        ctx: 'AgentContext'
    ) -> bool:
        """
        Validate input data.
        
        Args:
            input_data: Input to validate
            input_type: Expected input type
            ctx: Agent context
            
        Returns:
            True if valid, False otherwise
        """
        ...
    
    async def process(
        self,
        input_data: Any,
        input_type: 'AgentInputType',
        ctx: 'AgentContext'
    ) -> Any:
        """
        Process and normalize input.
        
        Args:
            input_data: Raw input
            input_type: Input type
            ctx: Agent context
            
        Returns:
            Processed input ready for agent consumption
        """
        ...


@runtime_checkable
class IAgentOutputProcessor(Protocol):
    """
    Interface for Output Processing.
    
    Postprocesses agent output before returning to the caller.
    Can handle type conversion, formatting, and validation.
    
    Example:
        class JSONOutputProcessor(IAgentOutputProcessor):
            def get_supported_types(self):
                return [AgentOutputType.STRUCTURED]
            
            async def process(self, output_data, output_type, ctx):
                return json.dumps(output_data, indent=2)
    """
    
    def get_supported_types(self) -> List['AgentOutputType']:
        """
        Get list of supported output types.
        
        Returns:
            List of AgentOutputType values
        """
        ...
    
    async def validate(
        self,
        output_data: Any,
        output_type: 'AgentOutputType',
        ctx: 'AgentContext'
    ) -> bool:
        """
        Validate output data.
        
        Args:
            output_data: Output to validate
            output_type: Expected output type
            ctx: Agent context
            
        Returns:
            True if valid, False otherwise
        """
        ...
    
    async def process(
        self,
        output_data: Any,
        output_type: 'AgentOutputType',
        output_format: Optional[str] = None,
        ctx: Optional['AgentContext'] = None
    ) -> Any:
        """
        Process and format output.
        
        Args:
            output_data: Raw output from agent
            output_type: Desired output type
            output_format: Optional format specification
            ctx: Agent context
            
        Returns:
            Processed output ready for caller
        """
        ...
