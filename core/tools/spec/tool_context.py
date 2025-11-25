"""
Core Data Types for Tools Specification System (v1.2.0)

This module defines the core data types, enumerations, and model classes
that form the foundation of the tools specification system.
"""

from __future__ import annotations
from typing import Any, Dict, Optional
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
#Tool Interfaces
from ..interfaces.tool_interfaces import IToolMemory, IToolMetrics, IToolTracer, IToolLimiter, IToolValidator, IToolSecurity
from ..constants import ARBITRARY_TYPES_ALLOWED
class ToolUsage(TypedDict, total=False):
    """Usage statistics for tool execution"""
    input_bytes: int
    output_bytes: int
    tokens_in: int
    tokens_out: int
    cost_usd: float
    attempts: int
    retries: int
    cached_hit: bool
    idempotency_reused: bool
    circuit_opened: bool

class ToolContext(BaseModel):
    """Execution context with tracing, auth, and dependencies"""

    model_config = {ARBITRARY_TYPES_ALLOWED: True}
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None

    # Tracing
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    parent_span_id: Optional[str] = None

    # Execution control
    locale: Optional[str] = None
    timezone: Optional[str] = None
    deadline_ts: Optional[float] = None

    # Auth and arbitrary extensions
    auth: Dict[str, Any] = Field(default_factory=dict)
    extras: Dict[str, Any] = Field(default_factory=dict)

    # Idempotency / run metadata
    run_id: Optional[str] = None
    idempotency_key: Optional[str] = None

    # Injected dependencies (optional but recommended)
    memory: Optional[IToolMemory] = None
    metrics: Optional[IToolMetrics] = None
    tracer: Optional[IToolTracer] = None
    limiter: Optional[IToolLimiter] = None
    validator: Optional[IToolValidator] = None
    security: Optional[IToolSecurity] = None