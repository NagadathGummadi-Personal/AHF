"""
HTTP Executors for Tools Specification System.

This module provides executors for HTTP-based tools that make HTTP requests
with full observability and control, following a modular architecture.

Strategy Pattern Implementation:
=================================
All executors extend BaseHttpExecutor, providing consistent HTTP request execution
with full observability and control.

Available Components:
=====================
- BaseHttpExecutor: Base implementation with common patterns
- HttpToolExecutor: Standard HTTP executor with full observability

Architecture:
=============
BaseHttpExecutor (Base implementation)
└── HttpToolExecutor (Standard implementation)

Usage:
    from core.tools.runtimes.executors.http_executors import HttpToolExecutor
    from core.tools.spec.tool_types import HttpToolSpec
    
    # Create HTTP tool spec
    spec = HttpToolSpec(
        id="github-api-v1",
        tool_name="get_repo",
        description="Get GitHub repository information",
        base_url="https://api.github.com",
        method="GET",
        endpoint="/repos/{owner}/{repo}",
        parameters=[...]
    )
    
    # Create executor
    executor = HttpToolExecutor(spec)
    
    # Execute
    result = await executor.execute({
        'owner': 'octocat',
        'repo': 'Hello-World'
    }, ctx)

Extending with Custom Executors:
==================================
To add a custom HTTP executor:

1. Implement the executor by inheriting from BaseHttpExecutor:

    from core.tools.runtimes.executors.http_executors import BaseHttpExecutor
    from core.tools.spec.tool_types import ToolSpec
    from core.tools.spec.tool_context import ToolContext
    from core.tools.spec.tool_result import ToolResult
    from typing import Dict, Any
    import aiohttp
    
    class GraphQLExecutor(BaseHttpExecutor):
        def __init__(self, spec: ToolSpec):
            self.spec = spec
        
        async def execute(self, args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
            # Custom GraphQL request logic
            query = args.get('query')
            variables = args.get('variables', {})
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.spec.base_url,
                    json={'query': query, 'variables': variables}
                ) as response:
                    data = await response.json()
                    return ToolResult(
                        content=data,
                        tool_name=self.spec.tool_name
                    )

2. Use it:

    executor = GraphQLExecutor(spec)
    result = await executor.execute({
        'query': 'query GetUser($id: ID!) { user(id: $id) { name email } }',
        'variables': {'id': '123'}
    }, ctx)

Note:
    HTTP executors handle validation, authorization, retries, and metrics
    automatically through the base executor implementation.
"""

from .base_http_executor import BaseHttpExecutor
from .http_executor import HttpToolExecutor

__all__ = [
    "BaseHttpExecutor",
    "HttpToolExecutor",
]


