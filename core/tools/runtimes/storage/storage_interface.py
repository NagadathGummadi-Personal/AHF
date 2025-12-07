"""
Tool Storage Interface

Defines the abstract interface for tool specification storage backends.

Version: 1.0.0
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class ToolVersionInfo:
    """
    Information about a tool version.
    
    Attributes:
        version_id: Unique version identifier (S3 version ID or custom)
        version: Semantic version string (e.g., "1.0.0")
        created_at: ISO format timestamp
        is_latest: Whether this is the latest version
        size_bytes: Size of the spec in bytes
        etag: Entity tag for caching
    """
    version_id: str
    version: str
    created_at: str
    is_latest: bool = False
    size_bytes: int = 0
    etag: Optional[str] = None


@dataclass
class ToolStorageResult:
    """
    Result from a storage operation.
    
    Attributes:
        success: Whether the operation succeeded
        tool_id: Tool identifier
        version_id: Version identifier (if applicable)
        version: Semantic version string
        message: Success/error message
        data: Additional data (tool spec on read operations)
    """
    success: bool
    tool_id: str
    version_id: Optional[str] = None
    version: Optional[str] = None
    message: str = ""
    data: Optional[Dict[str, Any]] = None


class IToolStorage(ABC):
    """
    Abstract interface for tool specification storage.
    
    Implementations must provide methods for:
    - Saving tool specs (with versioning)
    - Loading tool specs (specific or latest version)
    - Listing tools
    - Deleting tools
    - Managing versions
    
    Example Implementation:
        class S3ToolStorage(IToolStorage):
            async def save(self, tool_id, spec, version=None):
                # Save to S3 with versioning
                ...
    """
    
    @abstractmethod
    async def save(
        self,
        tool_id: str,
        spec: Dict[str, Any],
        version: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> ToolStorageResult:
        """
        Save a tool specification.
        
        Args:
            tool_id: Unique tool identifier
            spec: Tool specification dictionary
            version: Optional semantic version (auto-increments if not provided)
            metadata: Optional metadata to store with the spec
            
        Returns:
            ToolStorageResult with version info
        """
        pass
    
    @abstractmethod
    async def load(
        self,
        tool_id: str,
        version: Optional[str] = None
    ) -> ToolStorageResult:
        """
        Load a tool specification.
        
        Args:
            tool_id: Tool identifier
            version: Specific version to load (None for latest)
            
        Returns:
            ToolStorageResult with spec in data field
        """
        pass
    
    @abstractmethod
    async def delete(
        self,
        tool_id: str,
        version: Optional[str] = None
    ) -> ToolStorageResult:
        """
        Delete a tool specification.
        
        Args:
            tool_id: Tool identifier
            version: Specific version to delete (None for all versions)
            
        Returns:
            ToolStorageResult indicating success/failure
        """
        pass
    
    @abstractmethod
    async def list_tools(
        self,
        prefix: Optional[str] = None,
        limit: int = 100
    ) -> List[str]:
        """
        List all tool identifiers.
        
        Args:
            prefix: Optional prefix filter
            limit: Maximum number of results
            
        Returns:
            List of tool identifiers
        """
        pass
    
    @abstractmethod
    async def list_versions(
        self,
        tool_id: str
    ) -> List[ToolVersionInfo]:
        """
        List all versions of a tool.
        
        Args:
            tool_id: Tool identifier
            
        Returns:
            List of ToolVersionInfo objects
        """
        pass
    
    @abstractmethod
    async def exists(
        self,
        tool_id: str,
        version: Optional[str] = None
    ) -> bool:
        """
        Check if a tool exists.
        
        Args:
            tool_id: Tool identifier
            version: Optional specific version to check
            
        Returns:
            True if exists
        """
        pass
    
    @abstractmethod
    async def get_latest_version(
        self,
        tool_id: str
    ) -> Optional[str]:
        """
        Get the latest version string for a tool.
        
        Args:
            tool_id: Tool identifier
            
        Returns:
            Latest version string or None if not found
        """
        pass
