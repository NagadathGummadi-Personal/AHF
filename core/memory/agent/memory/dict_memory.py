"""
Dictionary-based Memory Implementation for Agents.

Provides a simple in-memory dictionary-based memory implementation.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

from ...interfaces import IAgentMemory


class DictMemory(IAgentMemory):
    """
    Simple in-memory dictionary-based memory implementation.
    
    Stores data in a Python dictionary with optional metadata.
    Useful for development, testing, and simple single-process agents.
    
    Note: Data is lost when the process ends. For persistence,
    use a database-backed implementation.
    
    Usage:
        memory = DictMemory()
        
        await memory.add("user_name", "Alice", metadata={"type": "fact"})
        name = await memory.get("user_name")  # Returns "Alice"
        
        await memory.update("user_name", "Bob")
        await memory.delete("user_name")
        await memory.clear()
    """
    
    def __init__(self):
        """Initialize empty memory store."""
        self._store: Dict[str, Dict[str, Any]] = {}
    
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
            value: Content to store
            metadata: Optional metadata
        """
        self._store[key] = {
            "value": value,
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
    
    async def get(self, query: str, **kwargs: Any) -> Any:
        """
        Retrieve item(s) from memory.
        
        Args:
            query: Key to search for
            **kwargs: Additional parameters (ignored in this implementation)
            
        Returns:
            Value if found, None otherwise
        """
        item = self._store.get(query)
        if item:
            return item["value"]
        return None
    
    async def get_with_metadata(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve item with metadata.
        
        Args:
            key: Key to search for
            
        Returns:
            Dict with value and metadata if found, None otherwise
        """
        return self._store.get(key)
    
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
            metadata: Optional updated metadata (merges with existing)
        """
        if key in self._store:
            self._store[key]["value"] = value
            self._store[key]["updated_at"] = datetime.utcnow().isoformat()
            if metadata:
                self._store[key]["metadata"].update(metadata)
        else:
            # If doesn't exist, add it
            await self.add(key, value, metadata)
    
    async def delete(self, key: str) -> None:
        """Delete an item from memory."""
        self._store.pop(key, None)
    
    async def clear(self) -> None:
        """Clear all items from memory."""
        self._store.clear()
    
    async def list_keys(self, prefix: Optional[str] = None) -> List[str]:
        """
        List all keys in memory.
        
        Args:
            prefix: Optional prefix to filter keys
            
        Returns:
            List of keys
        """
        if prefix:
            return [k for k in self._store.keys() if k.startswith(prefix)]
        return list(self._store.keys())
    
    async def search(
        self,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search memory by metadata.
        
        Args:
            metadata_filter: Metadata key-value pairs to match
            
        Returns:
            List of matching items
        """
        if not metadata_filter:
            return list(self._store.values())
        
        results = []
        for item in self._store.values():
            item_metadata = item.get("metadata", {})
            if all(item_metadata.get(k) == v for k, v in metadata_filter.items()):
                results.append(item)
        return results
    
    def size(self) -> int:
        """Get number of items in memory."""
        return len(self._store)
    
    def __len__(self) -> int:
        return self.size()



