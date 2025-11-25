"""
Basic Scratchpad Implementation.

Provides a simple string-based scratchpad for agent reasoning.
"""

from typing import List

from ...interfaces.agent_interfaces import IAgentScratchpad
from ...constants import SCRATCHPAD_SEPARATOR


class BasicScratchpad(IAgentScratchpad):
    """
    Basic string-based scratchpad implementation.
    
    Stores entries as a list of strings and provides methods
    for reading, writing, and appending content.
    
    Usage:
        scratchpad = BasicScratchpad()
        
        scratchpad.append("Thought: I need to search for information")
        scratchpad.append("Action: search")
        scratchpad.append("Observation: Found 3 results")
        
        full_trace = scratchpad.read()
        last_entries = scratchpad.get_last_n_entries(2)
        
        scratchpad.clear()
    """
    
    def __init__(self, separator: str = SCRATCHPAD_SEPARATOR):
        """
        Initialize scratchpad.
        
        Args:
            separator: String to use between entries
        """
        self._entries: List[str] = []
        self._separator = separator
    
    def read(self) -> str:
        """
        Read the entire scratchpad contents.
        
        Returns:
            String containing all entries joined by separator
        """
        return self._separator.join(self._entries)
    
    def write(self, content: str) -> None:
        """
        Overwrite the scratchpad with new content.
        
        Args:
            content: Content to write (replaces existing content)
        """
        self._entries = [content] if content else []
    
    def append(self, content: str) -> None:
        """
        Append content to the scratchpad.
        
        Args:
            content: Content to append
        """
        if content:
            self._entries.append(content)
    
    def clear(self) -> None:
        """Clear the scratchpad."""
        self._entries.clear()
    
    def get_last_n_entries(self, n: int) -> str:
        """
        Get the last N entries from the scratchpad.
        
        Args:
            n: Number of entries to retrieve
            
        Returns:
            String containing the last N entries
        """
        if n <= 0:
            return ""
        last_entries = self._entries[-n:]
        return self._separator.join(last_entries)
    
    def get_entries(self) -> List[str]:
        """
        Get all entries as a list.
        
        Returns:
            List of entries
        """
        return self._entries.copy()
    
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

