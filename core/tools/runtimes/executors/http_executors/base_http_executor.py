"""
Base HTTP Executor for Tools Specification System.

This module provides the base class for all HTTP tool executors. It handles
common HTTP execution patterns including validation, authorization, request
building, response handling, and metrics collection.

Classes:
========
- BaseHttpExecutor: Abstract base class for all HTTP executors

Inheritance Hierarchy:
======================
BaseToolExecutor (from base_executor.py)
└── BaseHttpExecutor (this file)
    ├── HttpToolExecutor (standard REST)
    ├── GraphQLExecutor (future)
    ├── WebSocketExecutor (future)
    └── [Your Custom Executors]

Responsibilities:
=================
- HTTP-specific logging setup
- Common validation/auth flow for HTTP requests
- Request building and execution
- Response parsing and formatting
- Retry logic for transient failures
- Metrics and tracing integration
- Delegates actual HTTP logic to subclasses

Usage:
    class MyHttpExecutor(BaseHttpExecutor):
        async def _execute_http_request(self, args, ctx, timeout):
            # Your specific HTTP logic
            response = await self._make_request(
                method='GET',
                url=f"{self.spec.base_url}/endpoint",
                headers={'Authorization': 'Bearer token'}
            )
            return response

Note:
    Subclasses must implement _execute_http_request() method.
"""

from __future__ import annotations

# Standard library
import time
import asyncio
from abc import abstractmethod
from typing import Any, Dict, Optional, TYPE_CHECKING

# Local imports
from ..base_executor import BaseToolExecutor
from ....spec.tool_types import ToolSpec
from ....spec.tool_context import ToolContext
from ....spec.tool_result import ToolResult
from ....constants import (
    LOG_STARTING_EXECUTION, LOG_PARAMETERS, LOG_VALIDATING, LOG_VALIDATION_PASSED,
    LOG_VALIDATION_SKIPPED, LOG_AUTH_CHECK, LOG_AUTH_PASSED, LOG_AUTH_SKIPPED,
    LOG_EGRESS_CHECK, LOG_EGRESS_PASSED, LOG_EGRESS_SKIPPED, LOG_IDEMPOTENCY_CACHE_HIT,
    LOG_EXECUTION_COMPLETED, LOG_EXECUTION_FAILED, IDEMPOTENCY_CACHE_PREFIX,
    TOOL_EXECUTION_TIME, TOOL_EXECUTIONS, STATUS, SUCCESS, TOOL, ERROR, EXECUTION_FAILED,
)
from ....defaults import DEFAULT_TOOL_CONTEXT_DATA
from utils.logging.LoggerAdaptor import LoggerAdaptor


class BaseHttpExecutor(BaseToolExecutor):
    """
    Base executor for HTTP-based tools.
    
    Provides common functionality for making HTTP requests
    with observability, error handling, and metrics collection using
    the Template Method pattern.
    """
    
    def __init__(self, spec: ToolSpec):
        """
        Initialize the base HTTP executor.
        
        Args:
            spec: Tool specification
        """
        super().__init__(spec)
        self.logger = LoggerAdaptor.get_logger(f"{TOOL}.{spec.tool_name}")
    
    async def execute(self, args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
        """
        Execute the HTTP tool with full lifecycle management.
        
        This is the Template Method that provides the complete execution flow:
        1. Log execution start
        2. Validate parameters (if validator available)
        3. Authorize execution (if security available)
        4. Check egress permissions (if security available)
        5. Check idempotency cache (if enabled)
        6. Execute HTTP request (via _execute_http_request) with timeout/rate limiting
        7. Record metrics and logs
        8. Cache result (if idempotency enabled)
        9. Handle errors gracefully
        
        Args:
            args: HTTP request arguments
            ctx: Tool execution context
            
        Returns:
            ToolResult containing HTTP response and metadata
        """
        start_time = time.time()
        context_data = DEFAULT_TOOL_CONTEXT_DATA(self.spec, ctx)
        self.logger.info(LOG_STARTING_EXECUTION, **context_data)
        self.logger.debug(LOG_PARAMETERS, parameters=args, **context_data)
        
        try:
            if ctx.validator:
                self.logger.info(LOG_VALIDATING, **context_data)
                await ctx.validator.validate(args, self.spec)
                self.logger.info(LOG_VALIDATION_PASSED, **context_data)
            else:
                self.logger.warning(LOG_VALIDATION_SKIPPED, **context_data)
            
            if ctx.security:
                self.logger.info(LOG_AUTH_CHECK, **context_data)
                await ctx.security.authorize(ctx, self.spec)
                self.logger.info(LOG_AUTH_PASSED, **context_data)
            else:
                self.logger.warning(LOG_AUTH_SKIPPED, **context_data)
            
            if ctx.security:
                self.logger.info(LOG_EGRESS_CHECK, **context_data)
                await ctx.security.check_egress(args, self.spec)
                self.logger.info(LOG_EGRESS_PASSED, **context_data)
            else:
                self.logger.warning(LOG_EGRESS_SKIPPED, **context_data)
            
            bypass_idempotency = False
            if self.spec.idempotency.enabled and ctx.memory:
                if self.spec.idempotency.key_fields and self.spec.idempotency.bypass_on_missing_key:
                    missing = [k for k in self.spec.idempotency.key_fields if k not in args]
                    if missing:
                        bypass_idempotency = True
                if not bypass_idempotency:
                    idempotency_key = self._generate_idempotency_key(args, ctx)
                    ctx.idempotency_key = idempotency_key
                    if self.spec.idempotency.persist_result:
                        cached_result = await ctx.memory.get(f"{IDEMPOTENCY_CACHE_PREFIX}:{idempotency_key}")
                        if cached_result:
                            self.logger.info(
                                LOG_IDEMPOTENCY_CACHE_HIT,
                                idempotency_key=idempotency_key,
                                **context_data
                            )
                            return ToolResult(**cached_result)
            
            timeout = self.spec.timeout_s or 30
            result_content = await self._execute_http_request(args, ctx, timeout)
            
            execution_time = time.time() - start_time
            self.logger.info(LOG_EXECUTION_COMPLETED,
                result=str(result_content),
                execution_time_ms=round(execution_time * 1000, 2),
                **context_data)
            
            if ctx.metrics:
                TAGS = {TOOL: self.spec.tool_name, STATUS: SUCCESS}
                await ctx.metrics.timing_ms(TOOL_EXECUTION_TIME, int(execution_time * 1000), tags=TAGS)
                await ctx.metrics.incr(TOOL_EXECUTIONS, tags=TAGS)
            
            usage = self._calculate_usage(start_time, args, result_content)
            result = self._create_result(result_content, usage)
            
            if (
                self.spec.idempotency.enabled
                and ctx.memory
                and self.spec.idempotency.persist_result
                and not bypass_idempotency
                and getattr(ctx, "idempotency_key", None)
            ):
                await ctx.memory.set(
                    f"{IDEMPOTENCY_CACHE_PREFIX}:{ctx.idempotency_key}",
                    result.model_dump(),
                    ttl_s=self.spec.idempotency.ttl_s
                )
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(LOG_EXECUTION_FAILED,
                error=str(e),
                execution_time_ms=round(execution_time * 1000, 2),
                **context_data)
            
            if ctx.metrics:
                await ctx.metrics.incr(TOOL_EXECUTIONS, tags={TOOL: self.spec.tool_name, STATUS: ERROR})
            
            usage = self._calculate_usage(start_time, args, None)
            error_result = self._create_result(
                content={ERROR: str(e)},
                usage=usage,
                warnings=[f"{EXECUTION_FAILED}: {str(e)}"]
            )
            return error_result
    
    @abstractmethod
    async def _execute_http_request(
        self,
        args: Dict[str, Any],
        ctx: ToolContext,
        timeout: float
    ) -> Any:
        """
        Execute the actual HTTP request.
        
        This method must be implemented by subclasses to define
        how the HTTP request is made.
        
        This is the only method that concrete HTTP executors need to implement.
        The base class handles all validation, security, idempotency, and metrics.
        
        Args:
            args: Input arguments
            ctx: Tool context
            timeout: Timeout in seconds
            
        Returns:
            HTTP response data (can be any structure: dict, list, etc.)
            
        Raises:
            Exception: Any error from HTTP request
        """
        pass

