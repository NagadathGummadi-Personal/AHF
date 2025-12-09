"""
No-Op Memory Implementation for Agents.

Provides a no-op memory implementation for stateless agents.
"""

from typing import Any, Dict, List, Optional

from ...interfaces import IAgentMemory


class NoOpAgentMemory(IAgentMemory):
    """
    No-op implementation of IAgentMemory that doesn't store or retrieve data.
    
    Useful for:
    - Stateless agent executions
    - Testing without memory infrastructure
    - Development environments
    - Agents that don't need persistent memory
    
    Usage:
        memory = NoOpAgentMemory()
        
        # All operations are no-ops
        await memory.add("key", "value")  # Doesn't store
        value = await memory.get("key")  # Returns None
        await memory.delete("key")  # No-op
        await memory.clear()  # No-op
    """
    
    async def add(
        self,
        key: str,
        value: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add an item to memory (no-op)."""
        pass
    
    async def get(self, query: str, **kwargs: Any) -> Any:
        """Retrieve item(s) from memory (returns None)."""
        return None
    
    async def update(
        self,
        key: str,
        value: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update an existing memory item (no-op)."""
        pass
    
    async def delete(self, key: str) -> None:
        """Delete an item from memory (no-op)."""
        pass
    
    async def clear(self) -> None:
        """Clear all items from memory (no-op)."""
        pass
    
    async def list_keys(self, prefix: Optional[str] = None) -> List[str]:
        """List all keys in memory (returns empty list)."""
        return []


