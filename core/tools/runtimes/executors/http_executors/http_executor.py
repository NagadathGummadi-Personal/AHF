"""
HTTP Tool Executor for Tools Specification System.

This module provides the executor for HTTP-based tools that make HTTP requests
with full observability and control.
"""

# Standard library
import json
import time
import asyncio
from typing import Any, Dict, Optional
from urllib.parse import urlencode, urlparse, urlunparse, parse_qsl
from urllib.request import Request, urlopen

# Local imports
from ..base_executor import BaseToolExecutor
from .base_http_executor import BaseHttpExecutor
from ....spec.tool_types import HttpToolSpec
from ....spec.tool_context import ToolContext
from ....spec.tool_result import ToolResult
from ....constants import (
    LOG_HTTP_STARTING,
    LOG_HTTP_COMPLETED,
    LOG_HTTP_FAILED,
    LOG_VALIDATING,
    LOG_VALIDATION_PASSED,
    LOG_VALIDATION_SKIPPED,
    LOG_AUTH_CHECK,
    LOG_AUTH_PASSED,
    LOG_AUTH_SKIPPED,
    LOG_EGRESS_CHECK,
    LOG_EGRESS_PASSED,
    LOG_EGRESS_SKIPPED,
    LOG_IDEMPOTENCY_CACHE_HIT,
    UTF_8,
    IDEMPOTENCY_CACHE_PREFIX,
    TOOL_EXECUTION_TIME,
    TOOL_EXECUTIONS,
    STATUS,
    SUCCESS,
    TOOL,
    ERROR,
    HTTP,
)
from ....defaults import DEFAULT_HTTP_CONTEXT_DATA, HTTP_DEFAULT_ERROR_STATUS_WARNING
from utils.logging.LoggerAdaptor import LoggerAdaptor


class HttpToolExecutor(BaseHttpExecutor):
    """
    Executor for HTTP-based tools.
    
    Makes HTTP requests with full lifecycle management including validation,
    authorization, idempotency, metrics, and error handling.
    
    Attributes:
        spec: HTTP tool specification
        logger: Logger instance
    
    Methods:
        execute: Main execution method with full lifecycle management
    """
    
    def __init__(self, spec: HttpToolSpec):
        """
        Initialize HTTP tool executor.
        
        Args:
            spec: HTTP tool specification
        """
        super().__init__(spec)
        self.spec: HttpToolSpec = spec
        self.logger = LoggerAdaptor.get_logger(f"{HTTP}.{spec.tool_name}") if LoggerAdaptor else None

    async def _execute_http_request(
        self,
        args: Dict[str, Any],
        ctx: ToolContext,
        timeout: float
    ) -> Any:
        """
        Execute the actual HTTP request using Python's urllib.
        
        This is the only method that concrete HTTP executors need to implement.
        The base class handles all validation, security, idempotency, and metrics.
        """
        # Merge HTTP params: prefer args overrides
        base_url = args.get("url", self.spec.url)
        method = (args.get("method") or self.spec.method or "GET").upper()
        headers: Dict[str, str] = {}
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

        parsed = urlparse(base_url)
        existing_qs = dict(parse_qsl(parsed.query))
        existing_qs.update(combined_qs)
        final_query = urlencode(existing_qs, doseq=True)
        final_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, final_query, parsed.fragment))

        # Prepare body
        body = args.get("body", self.spec.body)
        data_bytes: Optional[bytes] = None
        if method != "GET" and body is not None:
            if isinstance(body, (dict, list)):
                if "Content-Type" not in {k.title(): v for k, v in headers.items()}:
                    headers["Content-Type"] = "application/json"
                data_bytes = json.dumps(body).encode(UTF_8)
            elif isinstance(body, (str, bytes)):
                data_bytes = body.encode(UTF_8) if isinstance(body, str) else body
            else:
                data_bytes = json.dumps(body).encode(UTF_8)

        # Accept header default
        if "Accept" not in {k.title(): v for k, v in headers.items()}:
            headers.setdefault("Accept", "application/json, */*;q=0.8")

        def _do_request() -> Dict[str, Any]:
            req = Request(final_url, data=data_bytes, headers=headers, method=method)
            with urlopen(req, timeout=timeout) as resp:
                status_code = getattr(resp, "status", None) or resp.getcode()
                raw = resp.read()
                content_type = resp.headers.get("Content-Type", "")
                # Try JSON parse
                parsed_body: Any
                if "json" in content_type.lower():
                    try:
                        parsed_body = json.loads(raw.decode(UTF_8))
                    except Exception:
                        parsed_body = raw.decode(UTF_8, errors="ignore")
                else:
                    # attempt json anyway, else fallback to text
                    try:
                        parsed_body = json.loads(raw.decode(UTF_8))
                    except Exception:
                        parsed_body = raw.decode(UTF_8, errors="ignore")
                return {
                    "status_code": status_code,
                    "response": parsed_body,
                }

        async def _invoke_http() -> Dict[str, Any]:
            if ctx.tracer:
                async with ctx.tracer.span(f"{self.spec.tool_name}.http", {"method": method, "url": final_url}):
                    return await asyncio.to_thread(_do_request)
            return await asyncio.to_thread(_do_request)

        if ctx.limiter:
            async with ctx.limiter.acquire(self.spec.tool_name):
                if timeout:
                    http_result = await asyncio.wait_for(_invoke_http(), timeout=timeout)
                else:
                    http_result = await _invoke_http()
        else:
            if timeout:
                http_result = await asyncio.wait_for(_invoke_http(), timeout=timeout)
            else:
                http_result = await _invoke_http()

        return {
            "status_code": http_result["status_code"],
            "response": http_result["response"],
            "args": args,
        }

