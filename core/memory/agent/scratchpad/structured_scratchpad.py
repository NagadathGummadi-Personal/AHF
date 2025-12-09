"""
Structured Scratchpad Implementation.

Provides a JSON-based structured scratchpad for agent reasoning.
"""

from typing import Any, Dict, List, Optional
import json
from datetime import datetime

from ...interfaces import IAgentScratchpad
from ...constants import (
    REACT_THOUGHT,
    REACT_ACTION,
    REACT_OBSERVATION,
)


class StructuredScratchpad(IAgentScratchpad):
    """
    Structured JSON-based scratchpad implementation.
    
    Stores entries as structured dictionaries with type information,
    timestamps, and metadata. Useful for complex reasoning traces
    and debugging.
    
    Usage:
        scratchpad = StructuredScratchpad()
        
        scratchpad.add_thought("I need to search for information")
        scratchpad.add_action("search", {"query": "AI trends"})
        scratchpad.add_observation("Found 3 results about AI")
        
        # Get as formatted string
        trace = scratchpad.read()
        
        # Get structured entries
        entries = scratchpad.get_entries()
        
        # Get just thoughts
        thoughts = scratchpad.get_by_type("thought")
    """
    
    def __init__(self):
        """Initialize structured scratchpad."""
        self._entries: List[Dict[str, Any]] = []
    
    def read(self) -> str:
        """
        Read the scratchpad as a formatted string.
        
        Returns:
            Formatted string representation
        """
        lines = []
        for entry in self._entries:
            entry_type = entry.get("type", "unknown")
            content = entry.get("content", "")
            
            if entry_type == REACT_THOUGHT:
                lines.append(f"Thought: {content}")
            elif entry_type == REACT_ACTION:
                action_input = entry.get("action_input", {})
                lines.append(f"Action: {content}")
                if action_input:
                    lines.append(f"Action Input: {json.dumps(action_input)}")
            elif entry_type == REACT_OBSERVATION:
                lines.append(f"Observation: {content}")
            else:
                lines.append(f"{entry_type.title()}: {content}")
        
        return "\n".join(lines)
    
    def write(self, content: str) -> None:
        """
        Overwrite the scratchpad (parses as generic entry).
        
        Args:
            content: Content to write
        """
        self._entries = []
        if content:
            self._entries.append({
                "type": "raw",
                "content": content,
                "timestamp": datetime.utcnow().isoformat(),
            })
    
    def append(self, content: str) -> None:
        """
        Append content as a generic entry.
        
        Args:
            content: Content to append
        """
        if content:
            self._entries.append({
                "type": "raw",
                "content": content,
                "timestamp": datetime.utcnow().isoformat(),
            })
    
    def clear(self) -> None:
        """Clear the scratchpad."""
        self._entries.clear()
    
    def get_last_n_entries(self, n: int) -> str:
        """
        Get the last N entries as formatted string.
        
        Args:
            n: Number of entries to retrieve
            
        Returns:
            Formatted string of last N entries
        """
        if n <= 0:
            return ""
        
        temp_scratchpad = StructuredScratchpad()
        temp_scratchpad._entries = self._entries[-n:]
        return temp_scratchpad.read()
    
    # ==================== Structured Methods ====================
    
    def add_thought(self, thought: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a thought entry.
        
        Args:
            thought: The thought content
            metadata: Optional metadata
        """
        self._entries.append({
            "type": REACT_THOUGHT,
            "content": thought,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        })
    
    def add_action(
        self,
        action: str,
        action_input: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add an action entry.
        
        Args:
            action: The action name
            action_input: Action input parameters
            metadata: Optional metadata
        """
        self._entries.append({
            "type": REACT_ACTION,
            "content": action,
            "action_input": action_input or {},
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        })
    
    def add_observation(
        self,
        observation: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add an observation entry.
        
        Args:
            observation: The observation content
            metadata: Optional metadata
        """
        self._entries.append({
            "type": REACT_OBSERVATION,
            "content": observation,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        })
    
    def add_entry(
        self,
        entry_type: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add a custom entry type.
        
        Args:
            entry_type: Type of entry
            content: Entry content
            metadata: Optional metadata
        """
        self._entries.append({
            "type": entry_type,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        })
    
    def get_entries(self) -> List[Dict[str, Any]]:
        """Get all entries as list of dicts."""
        return self._entries.copy()
    
    def get_by_type(self, entry_type: str) -> List[Dict[str, Any]]:
        """
        Get entries of a specific type.
        
        Args:
            entry_type: Type to filter by
            
        Returns:
            List of matching entries
        """
        return [e for e in self._entries if e.get("type") == entry_type]
    
    def get_thoughts(self) -> List[str]:
        """Get all thought contents."""
        return [e["content"] for e in self._entries if e.get("type") == REACT_THOUGHT]
    
    def get_actions(self) -> List[Dict[str, Any]]:
        """Get all action entries."""
        return [e for e in self._entries if e.get("type") == REACT_ACTION]
    
    def get_observations(self) -> List[str]:
        """Get all observation contents."""
        return [e["content"] for e in self._entries if e.get("type") == REACT_OBSERVATION]
    
    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps(self._entries, indent=2)
    
    def from_json(self, json_str: str) -> None:
        """Load from JSON."""
        self._entries = json.loads(json_str)
    
    def entry_count(self) -> int:
        """Get the number of entries."""
        return len(self._entries)
    
    def is_empty(self) -> bool:
        """Check if scratchpad is empty."""
        return len(self._entries) == 0
    
    def __len__(self) -> int:
        return self.entry_count()
    
    def __str__(self) -> str:
        return self.read()


