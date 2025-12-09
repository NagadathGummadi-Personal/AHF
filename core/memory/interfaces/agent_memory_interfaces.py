"""
Agent Memory Interfaces.

Defines the protocols for agent-specific memory components:
- IAgentMemory: Key-value storage for agent context
- IAgentScratchpad: Temporary workspace for reasoning
- IAgentChecklist: Goal/task tracking
- IAgentObserver: Execution observation hooks

These interfaces are used by agents but defined here to centralize
all memory-related protocols in one location.

Version: 1.0.0
"""

from __future__ import annotations
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Protocol,
    runtime_checkable,
    TYPE_CHECKING,
)

if TYPE_CHECKING:
    from core.agents.spec.agent_result import AgentResult
    from core.agents.spec.agent_context import AgentContext


@runtime_checkable
class IAgentMemory(Protocol):
    """
    Interface for Agent Memory.
    
    Allows storage and retrieval of context, conversation history, or facts.
    Different implementations can use different storage backends.
    
    Built-in implementations:
    - DictMemory: Simple in-memory dictionary
    - NoOpAgentMemory: No-op for stateless agents
    
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


