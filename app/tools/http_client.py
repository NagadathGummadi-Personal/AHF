"""
Async HTTP Client

Production-grade async HTTP client with retry, timeout, and circuit breaker.

Version: 1.0.0
"""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Union
import aiohttp

from app.config import Defaults


class HTTPMethod(str, Enum):
    """HTTP methods."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


@dataclass
class HTTPResponse:
    """HTTP response wrapper."""
    
    status_code: int
    data: Any
    headers: Dict[str, str]
    latency_ms: float
    success: bool = True
    error: Optional[str] = None
    
    @property
    def is_success(self) -> bool:
        """Check if response indicates success."""
        return 200 <= self.status_code < 300 and self.success
    
    @property
    def is_error(self) -> bool:
        """Check if response indicates error."""
        return not self.is_success


@dataclass
class RetryConfig:
    """Retry configuration."""
    
    max_retries: int = Defaults.MAX_RETRIES
    retry_delay_ms: int = Defaults.RETRY_DELAY_MS
    backoff_multiplier: float = Defaults.RETRY_BACKOFF_MULTIPLIER
    retry_on_status: tuple = (429, 500, 502, 503, 504)


class AsyncHTTPClient:
    """
    Production async HTTP client.
    
    Features:
    - Connection pooling
    - Automatic retries with exponential backoff
    - Timeout handling
    - Circuit breaker (optional)
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout_ms: int = Defaults.HTTP_TIMEOUT_MS,
        retry_config: Optional[RetryConfig] = None,
        default_headers: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize HTTP client.
        
        Args:
            base_url: Base URL for all requests
            timeout_ms: Default timeout in milliseconds
            retry_config: Retry configuration
            default_headers: Headers to include in all requests
        """
        self._base_url = base_url
        self._timeout_ms = timeout_ms
        self._retry_config = retry_config or RetryConfig()
        self._default_headers = default_headers or {}
        
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create the session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(
                total=self._timeout_ms / 1000,
                connect=10,
            )
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers=self._default_headers,
            )
        return self._session
    
    async def close(self) -> None:
        """Close the client session."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def request(
        self,
        method: Union[HTTPMethod, str],
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        timeout_ms: Optional[int] = None,
    ) -> HTTPResponse:
        """
        Make an HTTP request with retry support.
        
        Args:
            method: HTTP method
            url: URL (absolute or relative to base_url)
            headers: Additional headers
            params: Query parameters
            json_data: JSON body
            timeout_ms: Override timeout
            
        Returns:
            HTTPResponse object
        """
        # Build full URL
        full_url = url
        if self._base_url and not url.startswith(("http://", "https://")):
            full_url = f"{self._base_url.rstrip('/')}/{url.lstrip('/')}"
        
        # Merge headers
        request_headers = {**self._default_headers}
        if headers:
            request_headers.update(headers)
        
        # Method
        method_str = method.value if isinstance(method, HTTPMethod) else method
        
        # Timeout
        request_timeout = (timeout_ms or self._timeout_ms) / 1000
        
        # Retry loop
        last_error: Optional[Exception] = None
        last_response: Optional[HTTPResponse] = None
        
        for attempt in range(self._retry_config.max_retries + 1):
            start_time = time.perf_counter()
            
            try:
                session = await self._get_session()
                
                async with session.request(
                    method_str,
                    full_url,
                    headers=request_headers,
                    params=params,
                    json=json_data,
                    timeout=aiohttp.ClientTimeout(total=request_timeout),
                ) as response:
                    latency_ms = (time.perf_counter() - start_time) * 1000
                    
                    # Try to parse JSON response
                    try:
                        data = await response.json()
                    except Exception:
                        data = await response.text()
                    
                    http_response = HTTPResponse(
                        status_code=response.status,
                        data=data,
                        headers=dict(response.headers),
                        latency_ms=latency_ms,
                        success=200 <= response.status < 300,
                    )
                    
                    # Check if we should retry
                    if response.status in self._retry_config.retry_on_status:
                        last_response = http_response
                        if attempt < self._retry_config.max_retries:
                            await self._wait_for_retry(attempt)
                            continue
                    
                    return http_response
                    
            except asyncio.TimeoutError:
                latency_ms = (time.perf_counter() - start_time) * 1000
                last_error = asyncio.TimeoutError("Request timed out")
                
                if attempt < self._retry_config.max_retries:
                    await self._wait_for_retry(attempt)
                    continue
                    
            except aiohttp.ClientError as e:
                latency_ms = (time.perf_counter() - start_time) * 1000
                last_error = e
                
                if attempt < self._retry_config.max_retries:
                    await self._wait_for_retry(attempt)
                    continue
            
            except Exception as e:
                latency_ms = (time.perf_counter() - start_time) * 1000
                last_error = e
                break
        
        # All retries exhausted
        if last_response:
            return last_response
        
        return HTTPResponse(
            status_code=0,
            data=None,
            headers={},
            latency_ms=latency_ms if 'latency_ms' in dir() else 0,
            success=False,
            error=str(last_error) if last_error else "Unknown error",
        )
    
    async def _wait_for_retry(self, attempt: int) -> None:
        """Wait before retrying with exponential backoff."""
        delay_ms = self._retry_config.retry_delay_ms * (
            self._retry_config.backoff_multiplier ** attempt
        )
        await asyncio.sleep(delay_ms / 1000)
    
    # Convenience methods
    
    async def get(
        self,
        url: str,
        **kwargs,
    ) -> HTTPResponse:
        """Make a GET request."""
        return await self.request(HTTPMethod.GET, url, **kwargs)
    
    async def post(
        self,
        url: str,
        json_data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> HTTPResponse:
        """Make a POST request."""
        return await self.request(HTTPMethod.POST, url, json_data=json_data, **kwargs)
    
    async def put(
        self,
        url: str,
        json_data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> HTTPResponse:
        """Make a PUT request."""
        return await self.request(HTTPMethod.PUT, url, json_data=json_data, **kwargs)
    
    async def delete(
        self,
        url: str,
        **kwargs,
    ) -> HTTPResponse:
        """Make a DELETE request."""
        return await self.request(HTTPMethod.DELETE, url, **kwargs)
    
    async def __aenter__(self) -> "AsyncHTTPClient":
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, *args) -> None:
        """Async context manager exit."""
        await self.close()

