from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# Local imports
from ..enum import ToolReturnType, ToolReturnTarget
from .tool_context import ToolUsage
from ..constants import TOOL_ERROR


class ToolResult(BaseModel):
    """Standardized result format for tool execution"""
    return_type: ToolReturnType
    return_target: ToolReturnTarget
    content: Any
    artifacts: Optional[Dict[str, bytes]] = None
    usage: Optional[ToolUsage] = None
    latency_ms: Optional[int] = None
    warnings: List[str] = Field(default_factory=list)
    logs: List[str] = Field(default_factory=list)


class ToolError(Exception):
    """Exception class for tool errors with retry information"""
    def __init__(self, message: str, retryable: bool = False, code: str = TOOL_ERROR):
        super().__init__(message)
        self.retryable = retryable
        self.code = code

# Ensure forward references are resolved for Pydantic v2
ToolResult.model_rebuild()