"""
AioHttp Executor for Tools Specification System.

This module provides a high-performance async HTTP executor using aiohttp
with native async I/O, connection pooling, and production-grade features.

Features:
=========
- Native async HTTP with aiohttp (no thread wrapping)
- Connection pooling for low-latency repeated requests
- Automatic retries with exponential backoff
- Full integration with core.tools validation, security, metrics
- Configurable timeouts

Usage:
======
    from core.tools.runtimes.executors.http_executors import AioHttpExecutor
    from core.tools.spec import HttpToolSpec
    
    spec = HttpToolSpec(
        id="my-api-v1",
        tool_name="my_api",
        description="Call my API",
        url="https://api.example.com/endpoint",
        method="POST",
    )
    
    executor = AioHttpExecutor(spec)
    result = await executor.execute({"key": "value"}, ctx)
    
    # Clean up when done
    await executor.close()

Version: 1.0.0
"""

import asyncio
import json
from typing import Any, Dict, Optional
from urllib.parse import urlencode, urlparse, urlunparse, parse_qsl

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

from .base_http_executor import BaseHttpExecutor
from ....spec.tool_types import HttpToolSpec
from ....spec.tool_context import ToolContext
from ....constants import HTTP
from utils.logging.LoggerAdaptor import LoggerAdaptor


class AioHttpExecutor(BaseHttpExecutor):
    """
    High-performance async HTTP executor using aiohttp.
    
    This executor provides native async HTTP operations with:
    - Connection pooling for reduced latency
    - Automatic retry with exponential backoff
    - Full observability (metrics, tracing, logging)
    - Proper resource cleanup
    
    Recommended for:
    - Low-latency voice applications
    - High-throughput API calls
    - Long-running connections with connection reuse
    
    Attributes:
        spec: HTTP tool specification
        _session: Shared aiohttp ClientSession (connection pool)
        _retry_on_status: HTTP status codes that trigger retry
    """
    
    # Default status codes to retry on
    DEFAULT_RETRY_STATUS_CODES = (429, 500, 502, 503, 504)
    
    def __init__(
        self,
        spec: HttpToolSpec,
        session: Optional["aiohttp.ClientSession"] = None,
        retry_on_status: Optional[tuple] = None,
    ):
        """
        Initialize AioHttp executor.
        
        Args:
            spec: HTTP tool specification
            session: Optional shared aiohttp session (for connection pooling)
            retry_on_status: HTTP status codes that should trigger retry
        """
        if not AIOHTTP_AVAILABLE:
            raise ImportError(
                "aiohttp is required for AioHttpExecutor. "
                "Install it with: pip install aiohttp"
            )
        
        super().__init__(spec)
        self.spec: HttpToolSpec = spec
        self._external_session = session is not None
        self._session: Optional[aiohttp.ClientSession] = session
        self._retry_on_status = retry_on_status or self.DEFAULT_RETRY_STATUS_CODES
        self.logger = LoggerAdaptor.get_logger(f"{HTTP}.aio.{spec.tool_name}") if LoggerAdaptor else None
    
    async def _get_session(self) -> "aiohttp.ClientSession":
        """
        Get or create the aiohttp session.
        
        Creates a session with appropriate timeout and connection settings
        if one doesn't exist.
        """
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(
                total=self.spec.timeout_s or 30,
                connect=10,
            )
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session
    
    async def close(self) -> None:
        """
        Close the aiohttp session.
        
        Only closes the session if it was created internally (not shared).
        """
        if self._session and not self._session.closed and not self._external_session:
            await self._session.close()
            self._session = None
    
    async def _execute_http_request(
        self,
        args: Dict[str, Any],
        ctx: ToolContext,
        timeout: float
    ) -> Any:
        """
        Execute the HTTP request using aiohttp.
        
        Implements the abstract method from BaseHttpExecutor.
        
        Args:
            args: Request arguments (can override url, method, headers, body)
            ctx: Tool execution context
            timeout: Request timeout in seconds
            
        Returns:
            Dict with status_code, response, and args
        """
        # Merge HTTP params: prefer args overrides
        base_url = args.get("url", self.spec.url)
        method = (args.get("method") or self.spec.method or "GET").upper()
        
        # Build headers
        headers: Dict[str, str] = {"Accept": "application/json, */*;q=0.8"}
        if self.spec.headers:
            headers.update(self.spec.headers)
        if args.get("headers"):
            headers.update(args.get("headers"))
        
        # Build query string
        combined_qs: Dict[str, str] = {}
        if self.spec.query_params:
            combined_qs.update(self.spec.query_params)
        if args.get("query_params"):
            combined_qs.update(args.get("query_params"))
        
        # Merge query params into URL
        parsed = urlparse(base_url)
        existing_qs = dict(parse_qsl(parsed.query))
        existing_qs.update(combined_qs)
        final_query = urlencode(existing_qs, doseq=True) if existing_qs else ""
        final_url = urlunparse((
            parsed.scheme, parsed.netloc, parsed.path,
            parsed.params, final_query, parsed.fragment
        ))
        
        # Prepare body
        body = args.get("body", self.spec.body)
        json_data = None
        if method != "GET" and body is not None:
            if isinstance(body, (dict, list)):
                json_data = body
                if "Content-Type" not in {k.title(): v for k, v in headers.items()}:
                    headers["Content-Type"] = "application/json"
            elif isinstance(body, str):
                # Try to parse as JSON, otherwise send as text
                try:
                    json_data = json.loads(body)
                except json.JSONDecodeError:
                    # Will be sent as text data
                    pass
        
        # Get retry settings from spec
        max_retries = self.spec.retry.max_retries if self.spec.retry.enabled else 0
        retry_delay = self.spec.retry.base_delay_ms / 1000 if self.spec.retry.enabled else 1.0
        backoff_multiplier = self.spec.retry.backoff_multiplier if self.spec.retry.enabled else 2.0
        
        # Execute with retry
        last_error: Optional[Exception] = None
        last_response: Optional[Dict[str, Any]] = None
        
        for attempt in range(max_retries + 1):
            try:
                session = await self._get_session()
                request_timeout = aiohttp.ClientTimeout(total=timeout)
                
                async with session.request(
                    method,
                    final_url,
                    headers=headers,
                    json=json_data if json_data else None,
                    data=body if not json_data and body and isinstance(body, str) else None,
                    timeout=request_timeout,
                ) as response:
                    # Parse response
                    content_type = response.headers.get("Content-Type", "")
                    
                    if "json" in content_type.lower():
                        try:
                            data = await response.json()
                        except Exception:
                            data = await response.text()
                    else:
                        # Try JSON anyway, fallback to text
                        try:
                            data = await response.json()
                        except Exception:
                            data = await response.text()
                    
                    http_response = {
                        "status_code": response.status,
                        "response": data,
                        "headers": dict(response.headers),
                    }
                    
                    # Check if we should retry
                    if response.status in self._retry_on_status:
                        last_response = http_response
                        if attempt < max_retries:
                            delay = retry_delay * (backoff_multiplier ** attempt)
                            await asyncio.sleep(delay)
                            continue
                    
                    return {
                        "status_code": response.status,
                        "response": data,
                        "args": args,
                    }
                    
            except asyncio.TimeoutError:
                last_error = asyncio.TimeoutError(f"Request timed out after {timeout}s")
                if attempt < max_retries:
                    delay = retry_delay * (backoff_multiplier ** attempt)
                    await asyncio.sleep(delay)
                    continue
                    
            except aiohttp.ClientError as e:
                last_error = e
                if attempt < max_retries:
                    delay = retry_delay * (backoff_multiplier ** attempt)
                    await asyncio.sleep(delay)
                    continue
                    
            except Exception as e:
                last_error = e
                break
        
        # All retries exhausted
        if last_response:
            return last_response
        
        raise last_error or Exception("HTTP request failed with unknown error")
    
    async def __aenter__(self) -> "AioHttpExecutor":
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, *args) -> None:
        """Async context manager exit."""
        await self.close()

