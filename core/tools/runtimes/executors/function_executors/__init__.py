"""
Function Executors for Tools Specification System.

This module provides executors for function-based tools that execute user-provided
async functions with full observability and control, following a modular architecture.

Strategy Pattern Implementation:
=================================
All executors extend BaseFunctionExecutor, providing consistent function execution
with full observability and control.

Available Components:
=====================
- BaseFunctionExecutor: Base implementation with common patterns
- FunctionToolExecutor: Standard function executor with full observability

Architecture:
=============
BaseFunctionExecutor (Base implementation)
└── FunctionToolExecutor (Standard implementation)

Usage:
    from core.tools.runtimes.executors.function_executors import FunctionToolExecutor
    from core.tools.spec.tool_types import FunctionToolSpec
    
    # Define your async function
    async def my_function(args):
        result = args['x'] + args['y']
        return {'result': result}
    
    # Create tool spec
    spec = FunctionToolSpec(
        id="add-numbers-v1",
        tool_name="add",
        description="Add two numbers",
        parameters=[...]
    )
    
    # Create executor
    executor = FunctionToolExecutor(spec, my_function)
    
    # Execute
    result = await executor.execute({'x': 10, 'y': 20}, ctx)

Extending with Custom Executors:
==================================
To add a custom function executor:

1. Implement the executor by inheriting from BaseFunctionExecutor:

    from core.tools.runtimes.executors.function_executors import BaseFunctionExecutor
    from core.tools.spec.tool_types import ToolSpec
    from core.tools.spec.tool_context import ToolContext
    from core.tools.spec.tool_result import ToolResult
    from typing import Dict, Any, Callable, Awaitable
    
    class CachedFunctionExecutor(BaseFunctionExecutor):
        def __init__(self, spec: ToolSpec, func: Callable[[Dict[str, Any]], Awaitable[Any]]):
            self.spec = spec
            self.func = func
            self.cache = {}
        
        async def execute(self, args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
            # Check cache
            cache_key = str(args)
            if cache_key in self.cache:
                return self.cache[cache_key]
            
            # Execute function
            result = await self.func(args)
            
            # Cache result
            tool_result = ToolResult(content=result, tool_name=self.spec.tool_name)
            self.cache[cache_key] = tool_result
            return tool_result

2. Use it:

    executor = CachedFunctionExecutor(spec, my_function)
    result = await executor.execute(args, ctx)

Note:
    Function executors handle validation, authorization, idempotency, and metrics
    automatically through the base executor implementation.
"""

from .base_function_executor import BaseFunctionExecutor
from .function_executor import FunctionToolExecutor

__all__ = [
    "BaseFunctionExecutor",
    "FunctionToolExecutor",
]


