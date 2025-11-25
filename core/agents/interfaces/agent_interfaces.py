"""
Interfaces for Agents Subsystem.

This module defines the core protocols (interfaces) that all agent implementations
must follow, ensuring a consistent API across all agent types.

Pluggable Components:
- IAgent: Core agent interface
- IAgentMemory: Memory/storage for context and history
- IAgentScratchpad: Temporary workspace for reasoning
- IAgentChecklist: Goal tracking and progress
- IAgentPlanner: Planning and task decomposition
- IAgentObserver: Event observation and hooks
- IAgentInputProcessor: Input preprocessing and validation
- IAgentOutputProcessor: Output postprocessing and formatting
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
    Union,
)

if TYPE_CHECKING:
    from ..spec.agent_result import AgentResult, AgentStreamChunk
    from ..spec.agent_context import AgentContext
    from ..spec.agent_spec import AgentSpec
    from ..enum import AgentInputType, AgentOutputType


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
class IAgentMemory(Protocol):
    """
    Interface for Agent Memory.
    
    Allows storage and retrieval of context, conversation history, or facts.
    Different implementations can use different storage backends.
    
    Built-in implementations:
    - DictMemory: Simple in-memory dictionary
    - NoOpMemory: No-op for stateless agents
    
    Future implementations:
    - VectorMemory: Embedding-based semantic search
    - RedisMemory: Distributed Redis storage
    - SQLMemory: SQL database storage
    
    Example:
        class VectorMemory(IAgentMemory):
            async def add(self, key, value, metadata=None):
                # Store with embeddings
                embedding = await self.embed(value)
                await self.store.add(key, value, embedding, metadata)
            
            async def get(self, query, **kwargs):
                # Semantic search
                query_embedding = await self.embed(query)
                return await self.store.search(query_embedding, **kwargs)
    """
    
    async def add(
        self,
        key: str,
        value: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add an item to memory.
        
        Args:
            key: Unique identifier for the memory item
            value: Content to store (can be any serializable type)
            metadata: Optional metadata (tags, timestamps, etc.)
        """
        ...
    
    async def get(
        self,
        query: str,
        **kwargs: Any
    ) -> Any:
        """
        Retrieve item(s) from memory.
        
        Args:
            query: Query string or key to search for
            **kwargs: Additional search parameters (limit, filters, etc.)
            
        Returns:
            Retrieved content or None if not found
        """
        ...
    
    async def update(
        self,
        key: str,
        value: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Update an existing memory item.
        
        Args:
            key: Key of the item to update
            value: New value
            metadata: Optional updated metadata
        """
        ...
    
    async def delete(self, key: str) -> None:
        """
        Delete an item from memory.
        
        Args:
            key: Key of the item to delete
        """
        ...
    
    async def clear(self) -> None:
        """Clear all items from memory."""
        ...
    
    async def list_keys(self, prefix: Optional[str] = None) -> List[str]:
        """
        List all keys in memory.
        
        Args:
            prefix: Optional prefix to filter keys
            
        Returns:
            List of keys
        """
        ...


@runtime_checkable
class IAgentScratchpad(Protocol):
    """
    Interface for Agent Scratchpad.
    
    A temporary workspace for the agent to store intermediate thoughts,
    calculations, or reasoning chains. Essential for ReAct-style agents.
    
    Built-in implementations:
    - BasicScratchpad: Simple string-based scratchpad
    - StructuredScratchpad: JSON-based structured scratchpad
    
    Example:
        scratchpad = BasicScratchpad()
        scratchpad.append("Thought: I need to search for the user's question")
        scratchpad.append("Action: search")
        scratchpad.append("Observation: Found 3 results...")
        
        trace = scratchpad.read()  # Get full reasoning trace
    """
    
    def read(self) -> str:
        """
        Read the entire scratchpad contents.
        
        Returns:
            String containing all scratchpad contents
        """
        ...
    
    def write(self, content: str) -> None:
        """
        Overwrite the scratchpad with new content.
        
        Args:
            content: Content to write
        """
        ...
    
    def append(self, content: str) -> None:
        """
        Append content to the scratchpad.
        
        Args:
            content: Content to append
        """
        ...
    
    def clear(self) -> None:
        """Clear the scratchpad."""
        ...
    
    def get_last_n_entries(self, n: int) -> str:
        """
        Get the last N entries from the scratchpad.
        
        Args:
            n: Number of entries to retrieve
            
        Returns:
            String containing the last N entries
        """
        ...


@runtime_checkable
class IAgentChecklist(Protocol):
    """
    Interface for tracking goals and progress.
    
    Used by goal-based agents to track task completion and progress.
    Can serialize to JSON for persistence or LLM consumption.
    
    Built-in implementations:
    - BasicChecklist: Simple list-based checklist
    - JSONChecklist: JSON-serializable checklist
    
    Example:
        checklist = BasicChecklist()
        checklist.add_item("Research the topic", priority=1)
        checklist.add_item("Write summary", priority=2)
        
        checklist.update_status("Research the topic", "completed")
        
        if checklist.is_complete():
            print("All tasks done!")
        
        # Export for LLM
        json_state = checklist.to_json()
    """
    
    def add_item(
        self,
        item: str,
        status: str = "pending",
        priority: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add an item to the checklist.
        
        Args:
            item: Description of the task
            status: Initial status (pending, in_progress, completed, failed, skipped)
            priority: Priority level (lower = higher priority)
            metadata: Optional metadata
            
        Returns:
            Unique ID for the checklist item
        """
        ...
    
    def update_status(self, item_id: str, status: str) -> None:
        """
        Update the status of a checklist item.
        
        Args:
            item_id: ID of the item to update
            status: New status
        """
        ...
    
    def get_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a checklist item by ID.
        
        Args:
            item_id: ID of the item
            
        Returns:
            Item dict or None if not found
        """
        ...
    
    def get_pending_items(self) -> List[Dict[str, Any]]:
        """
        Get all pending items.
        
        Returns:
            List of pending item dicts
        """
        ...
    
    def get_in_progress_items(self) -> List[Dict[str, Any]]:
        """
        Get all in-progress items.
        
        Returns:
            List of in-progress item dicts
        """
        ...
    
    def get_completed_items(self) -> List[Dict[str, Any]]:
        """
        Get all completed items.
        
        Returns:
            List of completed item dicts
        """
        ...
    
    def is_complete(self) -> bool:
        """
        Check if all items are completed.
        
        Returns:
            True if all items are completed or skipped
        """
        ...
    
    def get_progress(self) -> Dict[str, int]:
        """
        Get progress statistics.
        
        Returns:
            Dict with counts: {pending, in_progress, completed, failed, skipped, total}
        """
        ...
    
    def to_json(self) -> str:
        """
        Serialize the checklist to JSON.
        
        Returns:
            JSON string representation
        """
        ...
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary.
        
        Returns:
            Dictionary representation
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
class IAgentObserver(Protocol):
    """
    Interface for Agent Observation/Hooks.
    
    Allows external components to observe agent execution without
    modifying the agent's behavior. Useful for logging, debugging,
    and monitoring.
    
    Example:
        class LoggingObserver(IAgentObserver):
            async def on_iteration_start(self, iteration, ctx):
                logger.info(f"Starting iteration {iteration}")
            
            async def on_tool_call(self, tool_name, args, ctx):
                logger.debug(f"Calling tool: {tool_name}")
    """
    
    async def on_agent_start(
        self,
        input_data: Any,
        ctx: 'AgentContext'
    ) -> None:
        """Called when agent execution starts."""
        ...
    
    async def on_agent_end(
        self,
        result: 'AgentResult',
        ctx: 'AgentContext'
    ) -> None:
        """Called when agent execution ends."""
        ...
    
    async def on_iteration_start(
        self,
        iteration: int,
        ctx: 'AgentContext'
    ) -> None:
        """Called at the start of each iteration."""
        ...
    
    async def on_iteration_end(
        self,
        iteration: int,
        ctx: 'AgentContext'
    ) -> None:
        """Called at the end of each iteration."""
        ...
    
    async def on_tool_call(
        self,
        tool_name: str,
        args: Dict[str, Any],
        ctx: 'AgentContext'
    ) -> None:
        """Called when a tool is invoked."""
        ...
    
    async def on_tool_result(
        self,
        tool_name: str,
        result: Any,
        ctx: 'AgentContext'
    ) -> None:
        """Called when a tool returns a result."""
        ...
    
    async def on_llm_call(
        self,
        messages: List[Dict[str, Any]],
        ctx: 'AgentContext'
    ) -> None:
        """Called when the LLM is invoked."""
        ...
    
    async def on_llm_response(
        self,
        response: Any,
        ctx: 'AgentContext'
    ) -> None:
        """Called when the LLM returns a response."""
        ...
    
    async def on_error(
        self,
        error: Exception,
        ctx: 'AgentContext'
    ) -> None:
        """Called when an error occurs."""
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

