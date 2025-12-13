"""
Base Tool Classes

Foundation for all tool implementations.
Uses core.tools.AioHttpExecutor for HTTP operations.

Version: 1.1.0
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Generic, Optional, TypeVar, TYPE_CHECKING
import uuid

from pydantic import BaseModel, Field

from core.tools import AioHttpExecutor, HttpToolSpec, ToolContext

if TYPE_CHECKING:
    from air.memory.session import VoiceAgentSession


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


class BaseHttpTool(BaseTool):
    """
    Base class for HTTP-based tools using core.tools.AioHttpExecutor.
    
    Provides:
    - Connection pooling via shared aiohttp session
    - Automatic retries with exponential backoff
    - Full integration with core.tools validation and metrics
    - Session-aware header building
    
    Usage:
        class MyTool(BaseHttpTool):
            def __init__(self):
                super().__init__(
                    name="my_tool",
                    description="My tool description",
                    url="https://api.example.com/endpoint",
                    method="POST",
                )
            
            def get_parameters_schema(self) -> Dict[str, Any]:
                return {
                    "type": "object",
                    "properties": {...},
                    "required": [...],
                }
            
            def _build_request_body(self, params: Dict[str, Any]) -> Dict[str, Any]:
                return {"key": params["value"]}
    """
    
    # Shared executor for connection pooling across tools
    _shared_executor: Optional[AioHttpExecutor] = None
    
    def __init__(
        self,
        name: str,
        description: str,
        url: str,
        method: str = "POST",
        timeout_ms: int = 30000,
        max_retries: int = 3,
        retry_delay_ms: int = 1000,
    ):
        super().__init__(name, description, timeout_ms, max_retries)
        self._url = url
        self._method = method
        self._retry_delay_ms = retry_delay_ms
        self._executor: Optional[AioHttpExecutor] = None
    
    def _create_spec(self) -> HttpToolSpec:
        """Create HttpToolSpec for this tool."""
        from core.tools.spec import RetryConfig
        
        return HttpToolSpec(
            id=f"{self.name}-v1",
            tool_name=self.name,
            description=self.description,
            url=self._url,
            method=self._method,
            timeout_s=self.timeout_ms // 1000,
            retry=RetryConfig(
                enabled=self.max_retries > 0,
                max_retries=self.max_retries,
                base_delay_ms=self._retry_delay_ms,
            ),
        )
    
    async def _get_executor(self) -> AioHttpExecutor:
        """Get or create the AioHttpExecutor."""
        if self._executor is None:
            spec = self._create_spec()
            self._executor = AioHttpExecutor(spec)
        return self._executor
    
    def _build_headers(
        self,
        session: Optional["VoiceAgentSession"] = None,
    ) -> Dict[str, str]:
        """
        Build request headers from session.
        
        Override in subclasses for custom header logic.
        """
        headers = {"Content-Type": "application/json"}
        
        if session and session.dynamic_vars:
            dv = session.dynamic_vars
            if hasattr(dv, 'org_id') and dv.org_id:
                headers["x-org-id"] = str(dv.org_id)
            if hasattr(dv, 'center_id') and dv.center_id:
                headers["center_id"] = str(dv.center_id)
        
        return headers
    
    def _build_request_body(
        self,
        params: Dict[str, Any],
        session: Optional["VoiceAgentSession"] = None,
    ) -> Dict[str, Any]:
        """
        Build request body from params.
        
        Override in subclasses for custom body logic.
        """
        return params
    
    def _process_response(
        self,
        response: Dict[str, Any],
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Process the HTTP response.
        
        Override in subclasses for custom response processing.
        """
        status_code = response.get("status_code", 0)
        data = response.get("response", {})
        
        if 200 <= status_code < 300:
            return {
                "success": True,
                **(data if isinstance(data, dict) else {"data": data}),
            }
        else:
            return {
                "success": False,
                "error": f"HTTP {status_code}",
                "response": data,
            }
    
    def _get_fallback_response(
        self,
        params: Dict[str, Any],
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get fallback response when API fails.
        
        Override in subclasses to provide mock data for development.
        """
        return {
            "success": False,
            "error": error or "API request failed",
        }
    
    async def execute(
        self,
        params: Dict[str, Any],
        session: Optional["VoiceAgentSession"] = None,
        ctx: Optional[ToolContext] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Execute the HTTP tool.
        
        Args:
            params: Tool parameters
            session: Voice agent session (for header building)
            ctx: Tool context (optional)
            **kwargs: Additional arguments
            
        Returns:
            Tool result as dictionary
        """
        executor = await self._get_executor()
        
        # Build request
        headers = self._build_headers(session)
        body = self._build_request_body(params, session)
        
        # Create context if not provided
        if ctx is None:
            ctx = ToolContext()
        
        try:
            # Execute via AioHttpExecutor
            result = await executor.execute(
                args={
                    "headers": headers,
                    "body": body,
                },
                ctx=ctx,
            )
            
            # Process response
            if result.content and "error" not in result.content:
                return self._process_response(result.content, params)
            else:
                # API error - try fallback
                return self._get_fallback_response(
                    params,
                    error=str(result.content.get("error")) if result.content else None,
                )
                
        except Exception as e:
            # Exception - try fallback
            return self._get_fallback_response(params, error=str(e))
    
    async def close(self) -> None:
        """Clean up resources."""
        if self._executor:
            await self._executor.close()
            self._executor = None

