"""
Mock implementations for testing tool executors.

This module provides test doubles (mocks) for all tool interfaces to enable
comprehensive testing without external dependencies. Includes mock implementations
for memory, metrics, tracing, rate limiting, validation, and security.

Mock Classes:
=============
- MockMemory: In-memory key-value storage with locking support
- MockMetrics: Metrics collector tracking increments, observations, and timings
- MockTracer: Distributed tracing with span tracking
- MockLimiter: Rate limiting simulation with configurable delays
- MockValidator: Parameter validation with configurable pass/fail behavior
- MockSecurity: Authorization and egress checks with configurable behavior

Usage:
    from tests.tools.mocks import MockMemory, MockMetrics, MockTracer
    
    # Create mock instances
    memory = MockMemory()
    metrics = MockMetrics()
    tracer = MockTracer()
    
    # Use in ToolContext
    context = ToolContext(
        user_id="test-user",
        memory=memory,
        metrics=metrics,
        tracer=tracer
    )
    
    # Execute tool and verify interactions
    result = await executor.execute(args, context)
    assert metrics.get_incr_count('tool.executions') > 0

Note:
    These mocks are designed for testing only and should not be used in
    production environments. They provide simplified implementations that
    track method calls and allow verification of tool executor behavior.
"""

from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager
import asyncio

# Local imports
from core.tools.interfaces.tool_interfaces import (
    IToolMemory,
    IToolMetrics,
    IToolTracer,
    IToolLimiter,
    IToolValidator,
    IToolSecurity,
)
from core.tools.spec.tool_types import ToolSpec
from core.tools.spec.tool_context import ToolContext


class MockMemory(IToolMemory):
    """
    Mock in-memory storage for testing.
    
    Provides a simple in-memory key-value store with locking support for testing
    tool executors that use memory for caching, idempotency, or state management.
    
    Attributes:
        storage: Dictionary storing key-value pairs
        locks: Dictionary storing asyncio locks by key
    
    Methods:
        get: Retrieve value by key
        set: Store value with optional TTL
        set_if_absent: Store value only if key doesn't exist
        delete: Remove key from storage
        lock: Acquire an async lock for a key
    """
    
    def __init__(self):
        """Initialize empty storage and lock dictionaries."""
        self.storage: Dict[str, Any] = {}
        self.locks: Dict[str, asyncio.Lock] = {}
    
    async def get(self, key: str) -> Any:
        """Get value from memory"""
        return self.storage.get(key)
    
    async def set(self, key: str, value: Any, ttl_s: Optional[int] = None) -> None:
        """Set value in memory (ttl_s is ignored in mock)"""
        self.storage[key] = value
    
    async def set_if_absent(self, key: str, value: Any, ttl_s: Optional[int] = None) -> bool:
        """Set if absent"""
        if key not in self.storage:
            self.storage[key] = value
            return True
        return False
    
    async def delete(self, key: str) -> None:
        """Delete from memory"""
        self.storage.pop(key, None)
    
    @asynccontextmanager
    async def lock(self, key: str, ttl_s: int = 10):
        """Acquire a lock"""
        if key not in self.locks:
            self.locks[key] = asyncio.Lock()
        
        async with self.locks[key]:
            yield


class MockMetrics(IToolMetrics):
    """Mock metrics collector for testing"""
    
    def __init__(self):
        self.increments: List[Dict[str, Any]] = []
        self.observations: List[Dict[str, Any]] = []
        self.timings: List[Dict[str, Any]] = []
    
    async def incr(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None) -> None:
        """Record increment"""
        self.increments.append({
            'name': name,
            'value': value,
            'tags': tags or {}
        })
    
    async def observe(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record observation"""
        self.observations.append({
            'name': name,
            'value': value,
            'tags': tags or {}
        })
    
    async def timing_ms(self, name: str, value_ms: int, tags: Optional[Dict[str, str]] = None) -> None:
        """Record timing"""
        self.timings.append({
            'name': name,
            'value_ms': value_ms,
            'tags': tags or {}
        })
    
    def get_incr_count(self, name: str, tags: Optional[Dict[str, str]] = None) -> int:
        """Get total count for a metric"""
        matching = [
            m for m in self.increments 
            if m['name'] == name and (tags is None or m['tags'] == tags)
        ]
        return sum(m['value'] for m in matching)


class MockTracer(IToolTracer):
    """Mock distributed tracer for testing"""
    
    def __init__(self):
        self.spans: List[Dict[str, Any]] = []
        self._span_counter = 0
    
    @asynccontextmanager
    async def span(self, name: str, attrs: Optional[Dict[str, Any]] = None):
        """Create a trace span"""
        self._span_counter += 1
        span_id = f"span-{self._span_counter}"
        
        span_info = {
            'span_id': span_id,
            'name': name,
            'attrs': attrs or {}
        }
        self.spans.append(span_info)
        
        try:
            yield span_id
        finally:
            pass


class MockLimiter(IToolLimiter):
    """Mock rate limiter for testing"""
    
    def __init__(self, delay_ms: int = 0):
        self.acquisitions: List[Dict[str, Any]] = []
        self.delay_ms = delay_ms
    
    @asynccontextmanager
    async def acquire(self, key: str, limit: Optional[int] = None):
        """Acquire rate limit slot"""
        self.acquisitions.append({
            'key': key,
            'limit': limit
        })
        
        if self.delay_ms > 0:
            await asyncio.sleep(self.delay_ms / 1000.0)
        
        yield


class MockValidator(IToolValidator):
    """Mock parameter validator for testing"""
    
    def __init__(self, should_fail: bool = False, failure_msg: str = "Validation failed"):
        self.validations: List[Dict[str, Any]] = []
        self.should_fail = should_fail
        self.failure_msg = failure_msg
    
    async def validate(self, args: Dict[str, Any], spec: ToolSpec) -> None:
        """Validate parameters"""
        self.validations.append({
            'args': args,
            'spec_id': spec.id,
            'tool_name': spec.tool_name
        })
        
        if self.should_fail:
            raise ValueError(self.failure_msg)


class MockSecurity(IToolSecurity):
    """Mock security checker for testing"""
    
    def __init__(
        self, 
        should_fail_auth: bool = False,
        should_fail_egress: bool = False,
        auth_failure_msg: str = "Authorization failed",
        egress_failure_msg: str = "Egress check failed"
    ):
        self.authorizations: List[Dict[str, Any]] = []
        self.egress_checks: List[Dict[str, Any]] = []
        self.should_fail_auth = should_fail_auth
        self.should_fail_egress = should_fail_egress
        self.auth_failure_msg = auth_failure_msg
        self.egress_failure_msg = egress_failure_msg
    
    async def authorize(self, ctx: ToolContext, spec: ToolSpec) -> None:
        """Check authorization"""
        self.authorizations.append({
            'user_id': ctx.user_id,
            'spec_id': spec.id,
            'tool_name': spec.tool_name
        })
        
        if self.should_fail_auth:
            raise PermissionError(self.auth_failure_msg)
    
    async def check_egress(self, args: Dict[str, Any], spec: ToolSpec) -> None:
        """Check egress permissions"""
        self.egress_checks.append({
            'args': args,
            'spec_id': spec.id,
            'tool_name': spec.tool_name
        })
        
        if self.should_fail_egress:
            raise PermissionError(self.egress_failure_msg)

