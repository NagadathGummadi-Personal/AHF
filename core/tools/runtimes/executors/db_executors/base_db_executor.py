"""
Base Database Executor for Tools Specification System.

This module provides the base class for all database tool executors. It handles
common database execution patterns including validation, authorization, egress
checks, idempotency, tracing, rate limiting, and metrics.

Classes:
========
- BaseDbExecutor: Abstract base class for all database executors

Inheritance Hierarchy:
======================
BaseToolExecutor (from base_executor.py)
└── BaseDbExecutor (this file)
    ├── DynamoDBExecutor
    ├── PostgreSQLExecutor
    ├── MySQLExecutor
    └── SQLiteExecutor

Responsibilities:
=================
- Database-specific logging setup
- Common validation/auth/egress flow
- Idempotency handling for database operations
- Metrics and tracing integration
- Error handling and result formatting
- Delegates actual DB operations to subclasses

Usage:
    class MyDbExecutor(BaseDbExecutor):
        async def _execute_db_operation(self, args, ctx, timeout):
            # Your specific DB logic here
            return {
                'operation': 'query',
                'rows_affected': 5,
                'status': 'success'
            }

Note:
    Subclasses must implement _execute_db_operation() method.
"""

# Standard library
import time
import asyncio
from abc import abstractmethod
from typing import Any, Dict

# Local imports
from ..base_executor import BaseToolExecutor
from ....spec.tool_types import DbToolSpec
from ....spec.tool_context import ToolContext
from ....spec.tool_result import ToolResult
from ....constants import (
    LOG_DB_STARTING,
    LOG_DB_COMPLETED,
    LOG_DB_FAILED,
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
    IDEMPOTENCY_CACHE_PREFIX,
    TOOL_EXECUTION_TIME,
    TOOL_EXECUTIONS,
    STATUS,
    SUCCESS,
    TOOL,
    ERROR,
    DB,
    TABLE_NAME,
    DATABASE,
    DRIVER,
    ROWS_AFFECTED,
    ROW_COUNT,
    IDEMPOTENCY_KEY
)
from ....defaults import (
    DEFAULT_DB_CONTEXT_DATA,
    DB_DEFAULT_ERROR_STATUS_WARNING,
)
from utils.logging.LoggerAdaptor import LoggerAdaptor


class BaseDbExecutor(BaseToolExecutor):
    """
    Base class for database tool executors.
    
    Provides common database execution patterns including validation, security,
    idempotency, and metrics. Subclasses implement database-specific operations.
    
    Attributes:
        spec: Database tool specification (DbToolSpec)
        logger: Logger instance for this executor
    
    Methods:
        execute: Main execution method (implements common patterns)
        _execute_db_operation: Abstract method for database-specific logic
    
    Subclasses Must Implement:
        _execute_db_operation(args, ctx, timeout) -> Dict[str, Any]
    
    Example:
        class PostgreSQLExecutor(BaseDbExecutor):
            async def _execute_db_operation(self, args, ctx, timeout):
                # PostgreSQL-specific implementation
                return {'operation': 'select', 'rows': [...], 'status': 'success'}
    """
    
    def __init__(self, spec: DbToolSpec):
        """
        Initialize the database executor.
        
        Args:
            spec: Database tool specification
        """
        super().__init__(spec)
        self.spec: DbToolSpec = spec
        # Initialize logger for DB tool execution
        self.logger = LoggerAdaptor.get_logger(f"{DB}.{spec.tool_name}") if LoggerAdaptor else None
    
    @abstractmethod
    async def _execute_db_operation(
        self,
        args: Dict[str, Any],
        ctx: ToolContext,
        timeout: float | None
    ) -> Dict[str, Any]:
        """
        Execute the database-specific operation.
        
        This method must be implemented by subclasses to perform the actual
        database operation (query, insert, update, etc.).
        
        Args:
            args: Tool execution arguments
            ctx: Tool execution context
            timeout: Optional timeout in seconds
            
        Returns:
            Dictionary containing operation results with keys:
                - operation: Type of operation performed
                - status: 'success' or error status
                - Additional operation-specific data
        
        Raises:
            Exception: Database-specific errors
        
        Example:
            async def _execute_db_operation(self, args, ctx, timeout):
                # Connect to database
                # Execute query
                # Return results
                return {
                    'operation': 'select',
                    'rows': query_results,
                    'row_count': len(query_results),
                    'status': 'success'
                }
        """
        pass
    
    async def execute(self, args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
        """
        Execute the database tool with common patterns.
        
        This method implements the common execution flow for all database tools:
        1. Validation (if validator available)
        2. Authorization (if security available)
        3. Egress checks (if security available)
        4. Idempotency check (if enabled)
        5. Execute database operation (via _execute_db_operation)
        6. Record metrics and logs
        7. Cache result (if idempotency enabled)
        8. Handle errors gracefully
        
        Args:
            args: Tool execution arguments
            ctx: Tool execution context
            
        Returns:
            ToolResult containing operation results and metadata
        """
        start_time = time.time()
        
        # Set up logging context
        context_data = DEFAULT_DB_CONTEXT_DATA(self.spec, ctx)
        
        # Log execution start
        self.logger.info(LOG_DB_STARTING, **context_data)
        
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
            
            # Idempotency handling
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
                            self.logger.info(LOG_IDEMPOTENCY_CACHE_HIT, idempotency_key=idempotency_key, **context_data)
                            return ToolResult(**cached_result)
            
            # Execute using database-specific implementation
            timeout = float(self.spec.timeout_s) if self.spec.timeout_s else None
            
            async def _invoke_db() -> Dict[str, Any]:
                if ctx.tracer:
                    # Handle both table_name (DynamoDB) and database (PostgreSQL, MySQL, etc.)
                    db_name = getattr(self.spec, TABLE_NAME, None) or getattr(self.spec, DATABASE, None)
                    async with ctx.tracer.span(
                        f"{self.spec.tool_name}.{DB}",
                        {DRIVER: self.spec.driver, DATABASE: db_name}
                    ):
                        return await self._execute_db_operation(args, ctx, timeout)
                return await self._execute_db_operation(args, ctx, timeout)
            
            if ctx.limiter:
                async with ctx.limiter.acquire(self.spec.tool_name):
                    if timeout:
                        result_content = await asyncio.wait_for(_invoke_db(), timeout=timeout)
                    else:
                        result_content = await _invoke_db()
            else:
                if timeout:
                    result_content = await asyncio.wait_for(_invoke_db(), timeout=timeout)
                else:
                    result_content = await _invoke_db()
            
            execution_time = time.time() - start_time
            
            # Log successful completion
            rows_affected = result_content.get(ROWS_AFFECTED) or result_content.get(ROW_COUNT, 1)
            self.logger.info(LOG_DB_COMPLETED,
                rows_affected=rows_affected,
                execution_time_ms=round(execution_time * 1000, 2),
                **context_data)
            
            # Metrics
            if ctx.metrics:
                TAGS = {TOOL: self.spec.tool_name, STATUS: SUCCESS}
                await ctx.metrics.timing_ms(TOOL_EXECUTION_TIME, int(execution_time * 1000), tags=TAGS)
                await ctx.metrics.incr(TOOL_EXECUTIONS, tags=TAGS)
            
            usage = self._calculate_usage(start_time, args, result_content)
            result = self._create_result(result_content, usage)
            
            # Cache result if idempotency is enabled and not bypassed
            if (
                self.spec.idempotency.enabled
                and ctx.memory
                and self.spec.idempotency.persist_result
                and not bypass_idempotency
                and getattr(ctx, IDEMPOTENCY_KEY, None)
            ):
                await ctx.memory.set(
                    f"{IDEMPOTENCY_CACHE_PREFIX}:{ctx.idempotency_key}",
                    result.model_dump(),
                    ttl_s=self.spec.idempotency.ttl_s,
                )
            
            return result
        
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(LOG_DB_FAILED,
                error=str(e),
                execution_time_ms=round(execution_time * 1000, 2),
                **context_data)
            
            # Log error metrics if available
            if ctx.metrics:
                await ctx.metrics.incr(TOOL_EXECUTIONS, tags={TOOL: self.spec.tool_name, STATUS: ERROR})
            
            usage = self._calculate_usage(start_time, args, None)
            error_result = self._create_result(
                content={ERROR: str(e)},
                usage=usage,
                warnings=[DB_DEFAULT_ERROR_STATUS_WARNING(self.spec, str(e))]
            )
            return error_result


