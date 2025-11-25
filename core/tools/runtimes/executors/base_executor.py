"""
Base Executor for Tools Specification System.

This module provides the base class with common functionality shared across
all tool executor implementations. It handles cross-cutting concerns like
idempotency key generation, usage calculation, and result creation.

Classes:
========
- BaseToolExecutor: Abstract base class for all tool executors

Responsibilities:
=================
- Idempotency key generation from arguments and context
- Usage statistics calculation (bytes, tokens, cost, etc.)
- Standardized ToolResult creation
- Common utility methods for all executors

Usage:
    from core.tools.executors.base_executor import BaseToolExecutor
    
    class MyExecutor(BaseToolExecutor):
        def __init__(self, spec):
            super().__init__(spec)
        
        async def execute(self, args, ctx):
            # Use inherited methods
            key = self._generate_idempotency_key(args, ctx)
            usage = self._calculate_usage(start_time, args, result)
            return self._create_result(content, usage)

Note:
    This is an abstract base class. Concrete executors should inherit from
    this and implement their specific execution logic while leveraging the
    common functionality provided here.
"""

# Standard library
import json
from typing import Any, Dict, List, Optional

# Local imports
from ...interfaces.tool_interfaces import IToolExecutor
from ...spec.tool_types import ToolSpec
from ...spec.tool_context import ToolContext, ToolUsage
from ...spec.tool_result import ToolResult
from ...constants import UTF_8
from ..usage_calculators.token_calculators import calculate_tokens_in, calculate_tokens_out
from ..usage_calculators.cost_calculator import calculate_cost_usd
from ..usage_calculators.generic_calculator import (
    calculate_attempts,
    calculate_retries,
    check_cached_hit,
    check_idempotency_reused,
    check_circuit_opened,
)


class BaseToolExecutor(IToolExecutor):
    """
    Base utility class for tool executors with common functionality.
    
    Provides shared utility methods for idempotency, usage tracking, and result
    creation that are used by all executor implementations. This class implements
    IToolExecutor's contract through its subclass hierarchy:
    
    - BaseFunctionExecutor implements execute() and defines abstract _execute_function()
    - BaseHttpExecutor implements execute() and defines abstract _execute_http_request()
    - BaseDbExecutor implements execute() and defines abstract _execute_db_operation()
    
    Attributes:
        spec: Tool specification containing configuration and metadata
    
    Utility Methods:
        _generate_idempotency_key: Generate unique key for idempotent operations
        _calculate_usage: Calculate usage statistics for execution
        _create_result: Create standardized ToolResult object
    
    Subclass Hierarchy:
        BaseToolExecutor (utility methods only)
        ├── BaseFunctionExecutor (implements execute, abstract _execute_function)
        │   └── FunctionToolExecutor (implements _execute_function)
        ├── BaseHttpExecutor (implements execute, abstract _execute_http_request)
        │   └── HttpToolExecutor (implements _execute_http_request)
        └── BaseDbExecutor (implements execute, abstract _execute_db_operation)
            └── DynamoDBExecutor (implements _execute_db_operation)
    
    Note:
        This class provides only utility methods. The execute() method is implemented
        by the intermediate classes (BaseFunctionExecutor, BaseHttpExecutor, BaseDbExecutor).
        Direct instantiation is possible but not useful - always use concrete executors.
    """

    def __init__(self, spec: ToolSpec):
        """
        Initialize the base executor with a tool specification.
        
        Args:
            spec: Tool specification containing configuration
        """
        self.spec = spec

    def _generate_idempotency_key(self, args: Dict[str, Any], ctx: ToolContext) -> str:
        """
        Generate idempotency key from arguments and context using configured strategy.
        
        Creates a unique key that identifies this specific tool execution. The key
        generation strategy can be customized by setting spec.idempotency_key_generator.
        
        Args:
            args: Tool execution arguments
            ctx: Tool execution context containing user/session information
            
        Returns:
            String key representing this unique execution
            
        Note:
            - Uses custom generator if spec.idempotency_key_generator is set
            - Falls back to DefaultIdempotencyKeyGenerator if not set
            - Key generation is deterministic - same inputs produce same key
        
        Example:
            # Using custom generator
            from core.tools.runtimes.idempotency import FieldBasedIdempotencyKeyGenerator
            spec.idempotency_key_generator = FieldBasedIdempotencyKeyGenerator()
        """
        # Use custom generator if specified, otherwise use default
        if self.spec.idempotency_key_generator:
            return self.spec.idempotency_key_generator.generate_key(args, ctx, self.spec)
        
        # Default implementation (for backward compatibility)
        from ..idempotency.default_idempotency_key_gen import DefaultIdempotencyKeyGenerator
        default_generator = DefaultIdempotencyKeyGenerator()
        return default_generator.generate_key(args, ctx, self.spec)

    def _calculate_usage(self, start_time: float, input_args: Dict[str, Any], output_content: Any) -> ToolUsage:
        """
        Calculate usage statistics for the tool execution.
        
        Computes various metrics about the execution including data sizes,
        token counts, costs, and operational metadata.
        
        Args:
            start_time: Execution start timestamp (from time.time())
            input_args: Input arguments to the tool
            output_content: Output content from the tool execution
            
        Returns:
            ToolUsage object containing all usage metrics
            
        Note:
            Token and cost calculations are environment-aware and may return
            mock values in development mode.
        """
        # Calculate byte sizes
        input_bytes = len(json.dumps(input_args).encode(UTF_8))
        output_bytes = len(json.dumps(output_content).encode(UTF_8)) if output_content else 0

        return ToolUsage(
            input_bytes=input_bytes,
            output_bytes=output_bytes,
            tokens_in=calculate_tokens_in(),
            tokens_out=calculate_tokens_out(),
            cost_usd=calculate_cost_usd(),
            attempts=calculate_attempts(),
            retries=calculate_retries(),
            cached_hit=check_cached_hit(),
            idempotency_reused=check_idempotency_reused(),
            circuit_opened=check_circuit_opened(),
        )

    def _create_result(
        self,
        content: Any,
        usage: Optional[ToolUsage] = None,
        warnings: Optional[List[str]] = None,
        logs: Optional[List[str]] = None,
        artifacts: Optional[Dict[str, bytes]] = None
    ) -> ToolResult:
        """
        Create a standardized ToolResult.
        
        Constructs a ToolResult object with all required fields populated from
        the spec and provided parameters.
        
        Args:
            content: The main result content (can be any serializable type)
            usage: Optional usage statistics for this execution
            warnings: Optional list of warning messages
            logs: Optional list of log messages
            artifacts: Optional dictionary of binary artifacts (e.g., files, images)
            
        Returns:
            ToolResult object ready to be returned to the caller
            
        Example:
            result = self._create_result(
                content={'status': 'success', 'value': 42},
                usage=usage_stats,
                warnings=['Deprecated parameter used']
            )
        """
        return ToolResult(
            return_type=self.spec.return_type,
            return_target=self.spec.return_target,
            content=content,
            artifacts=artifacts,
            usage=usage,
            warnings=warnings or [],
            logs=logs or []
        )
    
    


