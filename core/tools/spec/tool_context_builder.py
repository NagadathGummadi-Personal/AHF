"""
ToolContext Builder for simplified context creation.

Provides a fluent interface for building ToolContext instances with all dependencies.
"""

from typing import Any, Dict, Optional
from .tool_context import ToolContext
from ..interfaces.tool_interfaces import (
    IToolMemory,
    IToolMetrics,
    IToolTracer,
    IToolLimiter,
    IToolValidator,
    IToolSecurity,
)


class ToolContextBuilder:
    """
    Builder for creating ToolContext instances with fluent interface.
    
    Provides a convenient way to construct ToolContext with all dependencies
    using method chaining.
    
    Usage:
        # Simple context
        context = (ToolContextBuilder()
            .with_user("user-123")
            .with_session("session-456")
            .build())
        
        # Full context with all dependencies
        context = (ToolContextBuilder()
            .with_user("user-123")
            .with_session("session-456")
            .with_memory(MemoryFactory.get_memory('redis'))
            .with_metrics(MetricsFactory.get_metrics('prometheus'))
            .with_tracer(TracerFactory.get_tracer('opentelemetry'))
            .with_limiter(LimiterFactory.get_limiter('redis'))
            .with_validator(ValidatorFactory.get_validator('basic'))
            .with_security(SecurityFactory.get_security('oauth'))
            .build())
        
        # Using factory names (requires factories to be imported)
        context = (ToolContextBuilder()
            .with_user("user-123")
            .with_memory_by_name('redis')
            .with_metrics_by_name('prometheus')
            .build())
    """
    
    def __init__(self):
        """Initialize builder with default values."""
        self._tenant_id: Optional[str] = None
        self._user_id: Optional[str] = None
        self._session_id: Optional[str] = None
        self._trace_id: Optional[str] = None
        self._span_id: Optional[str] = None
        self._parent_span_id: Optional[str] = None
        self._locale: Optional[str] = None
        self._timezone: Optional[str] = None
        self._deadline_ts: Optional[float] = None
        self._auth: Dict[str, Any] = {}
        self._extras: Dict[str, Any] = {}
        self._run_id: Optional[str] = None
        self._idempotency_key: Optional[str] = None
        self._memory: Optional[IToolMemory] = None
        self._metrics: Optional[IToolMetrics] = None
        self._tracer: Optional[IToolTracer] = None
        self._limiter: Optional[IToolLimiter] = None
        self._validator: Optional[IToolValidator] = None
        self._security: Optional[IToolSecurity] = None
    
    def with_tenant(self, tenant_id: str) -> "ToolContextBuilder":
        """Set tenant ID."""
        self._tenant_id = tenant_id
        return self
    
    def with_user(self, user_id: str) -> "ToolContextBuilder":
        """Set user ID."""
        self._user_id = user_id
        return self
    
    def with_session(self, session_id: str) -> "ToolContextBuilder":
        """Set session ID."""
        self._session_id = session_id
        return self
    
    def with_trace(self, trace_id: str, span_id: Optional[str] = None, parent_span_id: Optional[str] = None) -> "ToolContextBuilder":
        """Set tracing IDs."""
        self._trace_id = trace_id
        self._span_id = span_id
        self._parent_span_id = parent_span_id
        return self
    
    def with_locale(self, locale: str) -> "ToolContextBuilder":
        """Set locale."""
        self._locale = locale
        return self
    
    def with_timezone(self, timezone: str) -> "ToolContextBuilder":
        """Set timezone."""
        self._timezone = timezone
        return self
    
    def with_deadline(self, deadline_ts: float) -> "ToolContextBuilder":
        """Set execution deadline timestamp."""
        self._deadline_ts = deadline_ts
        return self
    
    def with_auth(self, auth: Dict[str, Any]) -> "ToolContextBuilder":
        """Set authentication data."""
        self._auth = auth
        return self
    
    def with_extras(self, extras: Dict[str, Any]) -> "ToolContextBuilder":
        """Set extra context data."""
        self._extras = extras
        return self
    
    def with_run_id(self, run_id: str) -> "ToolContextBuilder":
        """Set run ID."""
        self._run_id = run_id
        return self
    
    def with_idempotency_key(self, idempotency_key: str) -> "ToolContextBuilder":
        """Set idempotency key."""
        self._idempotency_key = idempotency_key
        return self
    
    def with_memory(self, memory: IToolMemory) -> "ToolContextBuilder":
        """Set memory/cache implementation."""
        self._memory = memory
        return self
    
    def with_metrics(self, metrics: IToolMetrics) -> "ToolContextBuilder":
        """Set metrics collector."""
        self._metrics = metrics
        return self
    
    def with_tracer(self, tracer: IToolTracer) -> "ToolContextBuilder":
        """Set distributed tracer."""
        self._tracer = tracer
        return self
    
    def with_limiter(self, limiter: IToolLimiter) -> "ToolContextBuilder":
        """Set rate limiter."""
        self._limiter = limiter
        return self
    
    def with_validator(self, validator: IToolValidator) -> "ToolContextBuilder":
        """Set parameter validator."""
        self._validator = validator
        return self
    
    def with_security(self, security: IToolSecurity) -> "ToolContextBuilder":
        """Set security checker."""
        self._security = security
        return self
    
    def with_memory_by_name(self, name: str) -> "ToolContextBuilder":
        """
        Set memory implementation by factory name.
        
        Args:
            name: Memory implementation name (e.g., 'noop', 'redis')
            
        Requires:
            MemoryFactory to be available
        """
        from ..runtimes.memory.memory_factory import MemoryFactory
        self._memory = MemoryFactory.get_memory(name)
        return self
    
    def with_metrics_by_name(self, name: str) -> "ToolContextBuilder":
        """
        Set metrics implementation by factory name.
        
        Args:
            name: Metrics implementation name (e.g., 'noop', 'prometheus')
            
        Requires:
            MetricsFactory to be available
        """
        from ..runtimes.metrics.metrics_factory import MetricsFactory
        self._metrics = MetricsFactory.get_metrics(name)
        return self
    
    def with_tracer_by_name(self, name: str) -> "ToolContextBuilder":
        """
        Set tracer implementation by factory name.
        
        Args:
            name: Tracer implementation name (e.g., 'noop', 'opentelemetry')
            
        Requires:
            TracerFactory to be available
        """
        from ..runtimes.tracers.tracer_factory import TracerFactory
        self._tracer = TracerFactory.get_tracer(name)
        return self
    
    def with_limiter_by_name(self, name: str) -> "ToolContextBuilder":
        """
        Set limiter implementation by factory name.
        
        Args:
            name: Limiter implementation name (e.g., 'noop', 'redis')
            
        Requires:
            LimiterFactory to be available
        """
        from ..runtimes.limiters.limiter_factory import LimiterFactory
        self._limiter = LimiterFactory.get_limiter(name)
        return self
    
    def with_validator_by_name(self, name: str) -> "ToolContextBuilder":
        """
        Set validator implementation by factory name.
        
        Args:
            name: Validator implementation name (e.g., 'basic', 'noop')
            
        Requires:
            ValidatorFactory to be available
        """
        from ..runtimes.validators.validator_factory import ValidatorFactory
        self._validator = ValidatorFactory.get_validator(name)
        return self
    
    def with_security_by_name(self, name: str) -> "ToolContextBuilder":
        """
        Set security implementation by factory name.
        
        Args:
            name: Security implementation name (e.g., 'basic', 'noop')
            
        Requires:
            SecurityFactory to be available
        """
        from ..runtimes.security.security_factory import SecurityFactory
        self._security = SecurityFactory.get_security(name)
        return self
    
    def with_emitter_by_name(self, name: str) -> "ToolContextBuilder":
        """
        Set emitter implementation by factory name.
        
        Note: ToolContext doesn't have an emitter field yet, but this is included
        for completeness and future compatibility.
        
        Args:
            name: Emitter implementation name (e.g., 'noop', 'eventbridge')
            
        Requires:
            EmitterFactory to be available
        """
        from ..runtimes.emitters.emitter_factory import EmitterFactory
        # Store in extras since ToolContext doesn't have emitter field yet
        self._extras['emitter'] = EmitterFactory.get_emitter(name)
        return self
    
    def with_defaults(self, profile: str = 'noop') -> "ToolContextBuilder":
        """
        Set all dependencies to default implementations.
        
        Args:
            profile: Profile name ('noop', 'basic', 'full')
                - 'noop': All no-op implementations
                - 'basic': Basic implementations where available
                - 'full': Full implementations (requires custom setup)
        """
        if profile == 'noop':
            self.with_memory_by_name('noop')
            self.with_metrics_by_name('noop')
            self.with_tracer_by_name('noop')
            self.with_limiter_by_name('noop')
            self.with_validator_by_name('noop')
            self.with_security_by_name('noop')
        elif profile == 'basic':
            self.with_memory_by_name('noop')
            self.with_metrics_by_name('noop')
            self.with_tracer_by_name('noop')
            self.with_limiter_by_name('noop')
            self.with_validator_by_name('basic')
            self.with_security_by_name('basic')
        return self
    
    def build(self) -> ToolContext:
        """
        Build and return the ToolContext instance.
        
        Returns:
            Configured ToolContext instance
        """
        return ToolContext(
            tenant_id=self._tenant_id,
            user_id=self._user_id,
            session_id=self._session_id,
            trace_id=self._trace_id,
            span_id=self._span_id,
            parent_span_id=self._parent_span_id,
            locale=self._locale,
            timezone=self._timezone,
            deadline_ts=self._deadline_ts,
            auth=self._auth,
            extras=self._extras,
            run_id=self._run_id,
            idempotency_key=self._idempotency_key,
            memory=self._memory,
            metrics=self._metrics,
            tracer=self._tracer,
            limiter=self._limiter,
            validator=self._validator,
            security=self._security,
        )

