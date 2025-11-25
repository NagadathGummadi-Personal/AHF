"""
Base Function Executor for Tools Specification System.

This module provides the base class for all function tool executors. It handles
common function execution patterns including validation, authorization, function
wrapping, error handling, and metrics collection.

Classes:
========
- BaseFunctionExecutor: Abstract base class for all function executors

Inheritance Hierarchy:
======================
BaseToolExecutor (from base_executor.py)
└── BaseFunctionExecutor (this file)
    ├── FunctionToolExecutor (standard)
    ├── CachedFunctionExecutor (future)
    ├── StreamingFunctionExecutor (future)
    └── [Your Custom Executors]

Responsibilities:
=================
- Function-specific logging setup
- Common validation/auth flow for functions
- Function invocation with error handling
- Result formatting and wrapping
- Metrics and tracing integration
- Delegates actual function execution to subclasses

Usage:
    class MyFunctionExecutor(BaseFunctionExecutor):
        def __init__(self, spec: ToolSpec, func: Callable):
            super().__init__(spec)
            self.func = func
        
        async def _execute_function(self, args, ctx, timeout):
            # Your specific function execution logic
            result = await asyncio.wait_for(
                self.func(args, ctx),
                timeout=timeout
            )
            return result

Note:
    Subclasses must implement _execute_function() method.
"""

# Standard library
import time
import asyncio
from abc import abstractmethod
from typing import Any, Dict, Callable, Awaitable

# Local imports
from ..base_executor import BaseToolExecutor
from ....spec.tool_types import ToolSpec
from ....spec.tool_context import ToolContext
from ....spec.tool_result import ToolResult
from ....constants import (
    LOG_STARTING_EXECUTION,
    LOG_PARAMETERS,
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
    LOG_EXECUTION_COMPLETED,
    LOG_EXECUTION_FAILED,
    IDEMPOTENCY_CACHE_PREFIX,
    TOOL_EXECUTION_TIME,
    TOOL_EXECUTIONS,
    STATUS,
    SUCCESS,
    TOOL,
    ERROR,
    EXECUTION_FAILED,
)
from ....defaults import DEFAULT_TOOL_CONTEXT_DATA
from utils.logging.LoggerAdaptor import LoggerAdaptor


class BaseFunctionExecutor(BaseToolExecutor):
    """
    Base executor for function-based tools.
    
    Provides common functionality for executing user-provided functions
    with observability, error handling, and metrics collection.
    
    Attributes:
        spec: Tool specification
        func: The async function to execute
    """
    
    def __init__(self, spec: ToolSpec, func: Callable[[Dict[str, Any]], Awaitable[Any]]):
        """
        Initialize the base function executor.
        
        Args:
            spec: Tool specification
            func: Async function to execute. Must accept (args: Dict) and return Any
        
        Raises:
            TypeError: If func is not callable
        """
        super().__init__(spec)
        
        if not callable(func):
            raise TypeError(f"Function must be callable, got {type(func)}")
        
        self.func = func
        self.logger = LoggerAdaptor.get_logger(f"{TOOL}.{spec.tool_name}")
    
    async def execute(self, args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
        """
        Execute the function tool with full lifecycle management.
        
        This is the Template Method that provides the complete execution flow:
        1. Log execution start
        2. Validate parameters (if validator available)
        3. Authorize execution (if security available)
        4. Check egress permissions (if security available)
        5. Check idempotency cache (if enabled)
        6. Execute user function (via _execute_function) with timeout/rate limiting
        7. Record metrics and logs
        8. Cache result (if idempotency enabled)
        9. Handle errors gracefully
        
        Args:
            args: Function arguments
            ctx: Tool execution context
            
        Returns:
            ToolResult containing function output and metadata
        """
        start_time = time.time()
        
        # Set up logging context
        context_data = DEFAULT_TOOL_CONTEXT_DATA(self.spec, ctx)
        
        # Log execution start with context
        self.logger.info(LOG_STARTING_EXECUTION, **context_data)
        
        # Log parameter details
        self.logger.debug(LOG_PARAMETERS, parameters=args, **context_data)
        
        try:
            # Validate parameters if validator is available
            if ctx.validator:
                self.logger.info(LOG_VALIDATING, **context_data)
                await ctx.validator.validate(args, self.spec)
                self.logger.info(LOG_VALIDATION_PASSED, **context_data)
            else:
                self.logger.warning(LOG_VALIDATION_SKIPPED, **context_data)
            
            # Authorize execution if security is available
            if ctx.security:
                self.logger.info(LOG_AUTH_CHECK, **context_data)
                await ctx.security.authorize(ctx, self.spec)
                self.logger.info(LOG_AUTH_PASSED, **context_data)
            else:
                self.logger.warning(LOG_AUTH_SKIPPED, **context_data)
            
            # Check egress permissions if security is available
            if ctx.security:
                self.logger.info(LOG_EGRESS_CHECK, **context_data)
                await ctx.security.check_egress(args, self.spec)
                self.logger.info(LOG_EGRESS_PASSED, **context_data)
            else:
                self.logger.warning(LOG_EGRESS_SKIPPED, **context_data)
            
            # Check idempotency if enabled
            bypass_idempotency = False
            if self.spec.idempotency.enabled and ctx.memory:
                # If key_fields are defined and bypass_on_missing_key is True, and any key is missing, bypass idempotency
                if self.spec.idempotency.key_fields and self.spec.idempotency.bypass_on_missing_key:
                    missing = [k for k in self.spec.idempotency.key_fields if k not in args]
                    if missing:
                        bypass_idempotency = True
                if not bypass_idempotency:
                    idempotency_key = self._generate_idempotency_key(args, ctx)
                    ctx.idempotency_key = idempotency_key
                    # Try to get cached result
                    if self.spec.idempotency.persist_result:
                        cached_result = await ctx.memory.get(f"{IDEMPOTENCY_CACHE_PREFIX}:{idempotency_key}")
                        if cached_result:
                            self.logger.info(
                                LOG_IDEMPOTENCY_CACHE_HIT,
                                idempotency_key=idempotency_key,
                                **context_data
                            )
                            return ToolResult(**cached_result)
            
            # Execute the actual function (delegate to subclass implementation)
            timeout = self.spec.timeout_s or 30
            result_content = await self._execute_function(args, ctx, timeout)
            
            execution_time = time.time() - start_time
            
            # Log successful completion
            self.logger.info(LOG_EXECUTION_COMPLETED,
                result=str(result_content),
                execution_time_ms=round(execution_time * 1000, 2),
                **context_data)
            
            # Log metrics if available
            if ctx.metrics:
                TAGS = {TOOL: self.spec.tool_name, STATUS: SUCCESS}
                await ctx.metrics.timing_ms(TOOL_EXECUTION_TIME, int(execution_time * 1000), tags=TAGS)
                await ctx.metrics.incr(TOOL_EXECUTIONS, tags=TAGS)
            
            # Calculate usage metrics
            usage = self._calculate_usage(start_time, args, result_content)
            
            # Create result
            result = self._create_result(result_content, usage)
            
            # Cache result if idempotency is enabled and not bypassed
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
            
            # Log error metrics if available
            if ctx.metrics:
                await ctx.metrics.incr(TOOL_EXECUTIONS, tags={TOOL: self.spec.tool_name, STATUS: ERROR})
            
            # Create error result
            usage = self._calculate_usage(start_time, args, None)
            error_result = self._create_result(
                content={ERROR: str(e)},
                usage=usage,
                warnings=[f"{EXECUTION_FAILED}: {str(e)}"]
            )
            return error_result
    
    @abstractmethod
    async def _execute_function(
        self,
        args: Dict[str, Any],
        ctx: ToolContext,
        timeout: float
    ) -> Any:
        """
        Execute the actual function.
        
        This method must be implemented by subclasses to define
        how the function is invoked.
        
        Args:
            args: Input arguments
            ctx: Tool context
            timeout: Timeout in seconds
            
        Returns:
            Function execution result
            
        Raises:
            Exception: Any error from function execution
        """
        pass
    
    async def _format_result(
        self,
        result: Any,
        ctx: ToolContext
    ) -> ToolResult:
        """
        Format the function result into a ToolResult.
        
        Args:
            result: Raw function result
            ctx: Tool context
            
        Returns:
            Formatted ToolResult
        """
        # If result is already a dict, use it as content
        if isinstance(result, dict):
            content = result
        else:
            # Wrap non-dict results
            content = {"result": result}
        
        return ToolResult(
            return_type=self.spec.return_type,
            return_target=self.spec.return_target,
            content=content,
            metadata={
                "tool_name": self.spec.tool_name,
                "executor": "BaseFunctionExecutor"
            }
        )
    
    def _is_retryable_error(self, error: Exception) -> bool:
        """
        Determine if an error is retryable.
        
        Args:
            error: The exception that occurred
            
        Returns:
            True if the error should be retried
        """
        # Network errors, timeouts, and temporary failures are retryable
        retryable_types = (
            asyncio.TimeoutError,
            ConnectionError,
            TimeoutError,
        )
        
        return isinstance(error, retryable_types)

