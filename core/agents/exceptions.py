"""
Exceptions for Agents Subsystem.

This module defines all exception classes used throughout the Agents subsystem.
"""

from typing import Any, Dict, Optional


class AgentError(Exception):
    """
    Base exception for all agent-related errors.
    
    Attributes:
        message: Error message
        details: Additional error details
        retryable: Whether the operation can be retried
    """
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        retryable: bool = False
    ):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.retryable = retryable
    
    def __str__(self) -> str:
        if self.details:
            return f"{self.message} - Details: {self.details}"
        return self.message


class AgentBuildError(AgentError):
    """Raised when agent building fails."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details, retryable=False)


class AgentExecutionError(AgentError):
    """Raised when agent execution fails."""
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        retryable: bool = True
    ):
        super().__init__(message, details, retryable)


class MaxIterationsError(AgentError):
    """Raised when agent exceeds maximum iterations."""
    
    def __init__(self, iterations: int, max_iterations: int):
        super().__init__(
            f"Agent exceeded maximum iterations: {iterations}/{max_iterations}",
            details={"iterations": iterations, "max_iterations": max_iterations},
            retryable=False
        )


class ToolNotFoundError(AgentError):
    """Raised when a requested tool is not found."""
    
    def __init__(self, tool_name: str, available_tools: Optional[list] = None):
        super().__init__(
            f"Tool not found: {tool_name}",
            details={
                "tool_name": tool_name,
                "available_tools": available_tools or []
            },
            retryable=False
        )


class ToolExecutionError(AgentError):
    """Raised when tool execution fails."""
    
    def __init__(
        self,
        tool_name: str,
        original_error: Optional[Exception] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        error_details = details or {}
        error_details["tool_name"] = tool_name
        if original_error:
            error_details["original_error"] = str(original_error)
        
        super().__init__(
            f"Tool execution failed: {tool_name}",
            details=error_details,
            retryable=True
        )


class LLMFailoverError(AgentError):
    """Raised when both primary and backup LLMs fail."""
    
    def __init__(
        self,
        primary_error: Optional[Exception] = None,
        backup_error: Optional[Exception] = None
    ):
        details = {}
        if primary_error:
            details["primary_error"] = str(primary_error)
        if backup_error:
            details["backup_error"] = str(backup_error)
        
        super().__init__(
            "Both primary and backup LLMs failed",
            details=details,
            retryable=True
        )


class InvalidAgentStateError(AgentError):
    """Raised when agent is in an invalid state for the requested operation."""
    
    def __init__(self, current_state: str, expected_states: Optional[list] = None):
        super().__init__(
            f"Agent in invalid state: {current_state}",
            details={
                "current_state": current_state,
                "expected_states": expected_states or []
            },
            retryable=False
        )


class ChecklistItemNotFoundError(AgentError):
    """Raised when a checklist item is not found."""
    
    def __init__(self, item_id: str):
        super().__init__(
            f"Checklist item not found: {item_id}",
            details={"item_id": item_id},
            retryable=False
        )


class MemoryError(AgentError):
    """Raised when memory operations fail."""
    
    def __init__(self, operation: str, message: str, retryable: bool = True):
        super().__init__(
            f"Memory {operation} failed: {message}",
            details={"operation": operation},
            retryable=retryable
        )


class AgentTimeoutError(AgentError):
    """Raised when agent execution times out."""
    
    def __init__(self, timeout_seconds: float, current_iteration: int = 0):
        super().__init__(
            f"Agent execution timed out after {timeout_seconds}s",
            details={
                "timeout_seconds": timeout_seconds,
                "current_iteration": current_iteration
            },
            retryable=True
        )

