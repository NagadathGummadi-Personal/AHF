"""
Agent Result Models.

This module defines the data models for agent responses, including
complete responses and streaming chunks.
"""

from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field

from ..enum import AgentState, AgentOutputType, AgentOutputFormat


class AgentUsage(BaseModel):
    """
    Usage statistics for an agent execution.
    
    Tracks iterations, tool calls, LLM calls, tokens, and timing.
    
    Attributes:
        iterations: Number of iterations executed
        tool_calls: Number of tool calls made
        llm_calls: Number of LLM calls made
        prompt_tokens: Total input tokens used
        completion_tokens: Total output tokens generated
        total_tokens: Total tokens used
        duration_ms: Execution duration in milliseconds
        cost_usd: Estimated cost in USD (optional)
    """
    
    iterations: int = Field(default=0, ge=0, description="Number of iterations executed")
    tool_calls: int = Field(default=0, ge=0, description="Number of tool calls made")
    llm_calls: int = Field(default=0, ge=0, description="Number of LLM calls made")
    prompt_tokens: int = Field(default=0, ge=0, description="Total input tokens used")
    completion_tokens: int = Field(default=0, ge=0, description="Total output tokens generated")
    total_tokens: int = Field(default=0, ge=0, description="Total tokens used")
    duration_ms: Optional[int] = Field(default=None, ge=0, description="Execution duration in milliseconds")
    cost_usd: Optional[float] = Field(default=None, ge=0, description="Estimated cost in USD")
    
    def model_post_init(self, __context: Any) -> None:
        """Calculate total_tokens if not provided."""
        if self.total_tokens == 0 and (self.prompt_tokens > 0 or self.completion_tokens > 0):
            self.total_tokens = self.prompt_tokens + self.completion_tokens


class AgentResult(BaseModel):
    """
    Complete response from an agent (non-streaming).
    
    Contains the generated content, metadata, and usage statistics.
    
    Attributes:
        content: The generated content (can be text, structured data, etc.)
        output_type: Type of output (text, structured, etc.)
        output_format: Format of output (json, markdown, etc.)
        state: Final agent state (completed, failed, etc.)
        usage: Execution usage statistics
        metadata: Additional response metadata
        artifacts: Binary artifacts produced (files, images, etc.)
        reasoning_trace: Reasoning steps taken (for debugging)
        checklist_state: Final state of checklist (if applicable)
        warnings: Any warnings generated
        errors: Any errors encountered
    
    Example:
        result = AgentResult(
            content={"answer": "The capital of France is Paris"},
            output_type=AgentOutputType.STRUCTURED,
            output_format=AgentOutputFormat.JSON,
            state=AgentState.COMPLETED,
            usage=AgentUsage(iterations=3, tool_calls=1)
        )
    """
    
    content: Any = Field(description="Generated content")
    output_type: AgentOutputType = Field(
        default=AgentOutputType.TEXT,
        description="Type of output"
    )
    output_format: AgentOutputFormat = Field(
        default=AgentOutputFormat.TEXT,
        description="Format of output"
    )
    state: AgentState = Field(
        default=AgentState.COMPLETED,
        description="Final agent state"
    )
    usage: Optional[AgentUsage] = Field(
        default=None,
        description="Execution usage statistics"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    artifacts: Optional[Dict[str, bytes]] = Field(
        default=None,
        description="Binary artifacts produced"
    )
    reasoning_trace: Optional[List[str]] = Field(
        default=None,
        description="Reasoning steps taken"
    )
    checklist_state: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Final checklist state"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Warnings generated"
    )
    errors: List[str] = Field(
        default_factory=list,
        description="Errors encountered"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "content": "The answer to your question is 42.",
                    "output_type": "text",
                    "output_format": "text",
                    "state": "completed",
                    "usage": {
                        "iterations": 2,
                        "tool_calls": 1,
                        "llm_calls": 3,
                        "total_tokens": 500
                    }
                }
            ]
        }
    }
    
    def get_text_content(self) -> str:
        """
        Get content as text string.
        
        Returns:
            Text content, converting if necessary
        """
        if isinstance(self.content, str):
            return self.content
        elif isinstance(self.content, dict) and 'text' in self.content:
            return self.content['text']
        return str(self.content)
    
    def is_success(self) -> bool:
        """Check if agent completed successfully."""
        return self.state == AgentState.COMPLETED
    
    def is_failure(self) -> bool:
        """Check if agent failed."""
        return self.state == AgentState.FAILED
    
    def has_artifacts(self) -> bool:
        """Check if result has artifacts."""
        return self.artifacts is not None and len(self.artifacts) > 0
    
    def has_warnings(self) -> bool:
        """Check if result has warnings."""
        return len(self.warnings) > 0
    
    def has_errors(self) -> bool:
        """Check if result has errors."""
        return len(self.errors) > 0


class AgentStreamChunk(BaseModel):
    """
    A chunk from a streaming agent response.
    
    Represents a fragment of execution progress as it's being generated.
    
    Attributes:
        content: Content fragment
        chunk_type: Type of chunk (thought, action, observation, output)
        iteration: Current iteration number
        is_final: Whether this is the last chunk
        state: Current agent state
        usage: Usage statistics (usually only on final chunk)
        metadata: Additional chunk metadata
    
    Example:
        chunk = AgentStreamChunk(
            content="Searching for information...",
            chunk_type="action",
            iteration=1,
            is_final=False
        )
    """
    
    content: str = Field(default="", description="Content fragment")
    chunk_type: str = Field(
        default="output",
        description="Type of chunk (thought, action, observation, output)"
    )
    iteration: int = Field(default=0, ge=0, description="Current iteration number")
    is_final: bool = Field(default=False, description="Whether this is the last chunk")
    state: AgentState = Field(
        default=AgentState.RUNNING,
        description="Current agent state"
    )
    usage: Optional[AgentUsage] = Field(
        default=None,
        description="Usage statistics"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    tool_name: Optional[str] = Field(
        default=None,
        description="Tool name if this is a tool-related chunk"
    )
    tool_args: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Tool arguments if this is a tool call"
    )
    tool_result: Optional[Any] = Field(
        default=None,
        description="Tool result if this is a tool response"
    )
    
    def is_empty(self) -> bool:
        """Check if chunk has no content."""
        return len(self.content) == 0
    
    def has_usage(self) -> bool:
        """Check if chunk includes usage statistics."""
        return self.usage is not None
    
    def is_tool_chunk(self) -> bool:
        """Check if this is a tool-related chunk."""
        return self.tool_name is not None


class AgentError(BaseModel):
    """
    Error information from an agent execution.
    
    Used to structure error responses in a consistent way.
    
    Attributes:
        error_type: Type/category of error
        message: Error message
        code: Error code
        details: Additional error details
        iteration: Iteration when error occurred
        retryable: Whether the operation can be retried
    """
    
    error_type: str = Field(description="Error type/category")
    message: str = Field(description="Error message")
    code: Optional[str] = Field(default=None, description="Error code")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional error details")
    iteration: int = Field(default=0, description="Iteration when error occurred")
    retryable: bool = Field(default=False, description="Whether operation can be retried")


# Helper functions

def create_result(
    content: Any,
    usage: Optional[AgentUsage] = None,
    state: AgentState = AgentState.COMPLETED,
    **kwargs
) -> AgentResult:
    """
    Helper to create an AgentResult.
    
    Args:
        content: Generated content
        usage: Optional usage statistics
        state: Agent state
        **kwargs: Additional fields
        
    Returns:
        AgentResult instance
    """
    return AgentResult(
        content=content,
        usage=usage,
        state=state,
        **kwargs
    )


def create_chunk(
    content: str,
    chunk_type: str = "output",
    iteration: int = 0,
    is_final: bool = False,
    **kwargs
) -> AgentStreamChunk:
    """
    Helper to create an AgentStreamChunk.
    
    Args:
        content: Content fragment
        chunk_type: Type of chunk
        iteration: Current iteration
        is_final: Whether this is the final chunk
        **kwargs: Additional fields
        
    Returns:
        AgentStreamChunk instance
    """
    return AgentStreamChunk(
        content=content,
        chunk_type=chunk_type,
        iteration=iteration,
        is_final=is_final,
        **kwargs
    )

