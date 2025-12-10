"""
Base Tool Classes

Foundation for all tool implementations.

Version: 1.0.0
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Generic, Optional, TypeVar
import uuid

from pydantic import BaseModel, Field


T = TypeVar("T")


class ToolResult(BaseModel, Generic[T]):
    """Result from a tool execution."""
    
    result_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    
    # Success/failure
    success: bool = Field(default=True)
    error: Optional[str] = Field(default=None)
    error_code: Optional[str] = Field(default=None)
    
    # Result data
    data: Optional[T] = Field(default=None)
    
    # Metadata
    latency_ms: float = Field(default=0.0)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Retry info
    retries: int = Field(default=0)
    
    @classmethod
    def success_result(cls, data: T, latency_ms: float = 0.0) -> "ToolResult[T]":
        """Create a success result."""
        return cls(success=True, data=data, latency_ms=latency_ms)
    
    @classmethod
    def error_result(
        cls,
        error: str,
        error_code: Optional[str] = None,
        latency_ms: float = 0.0,
    ) -> "ToolResult[T]":
        """Create an error result."""
        return cls(
            success=False,
            error=error,
            error_code=error_code,
            latency_ms=latency_ms,
        )


class BaseTool(ABC):
    """
    Base class for all tools.
    
    Tools are stateless executors that can be invoked by nodes.
    """
    
    def __init__(
        self,
        name: str,
        description: str = "",
        timeout_ms: int = 30000,
        max_retries: int = 3,
    ):
        self.name = name
        self.description = description
        self.timeout_ms = timeout_ms
        self.max_retries = max_retries
    
    @abstractmethod
    async def execute(
        self,
        params: Dict[str, Any],
        **kwargs,
    ) -> ToolResult:
        """Execute the tool with given parameters."""
        ...
    
    def get_spec(self) -> Dict[str, Any]:
        """Get tool specification for LLM function calling."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.get_parameters_schema(),
            },
        }
    
    @abstractmethod
    def get_parameters_schema(self) -> Dict[str, Any]:
        """Get JSON Schema for tool parameters."""
        ...
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name})"

