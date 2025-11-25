"""
Demo: Factory Pattern and ToolContextBuilder

This example demonstrates the new factory pattern for all runtime components
and the ToolContextBuilder for easy context creation.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from core.tools.spec import ToolContextBuilder, ToolContext
from core.tools.runtimes import (
    MemoryFactory,
    MetricsFactory,
    TracerFactory,
    LimiterFactory,
    EmitterFactory,
    SecurityFactory,
    ValidatorFactory,
    PolicyFactory,
)


def demo_factories():
    """Demonstrate factory pattern for all components."""
    print("\n=== Factory Pattern Demo ===\n")
    
    # 1. Memory Factory
    print("1. Memory Factory:")
    memory = MemoryFactory.get_memory('noop')
    print(f"   Created: {type(memory).__name__}")
    
    # 2. Metrics Factory
    print("\n2. Metrics Factory:")
    metrics = MetricsFactory.get_metrics('noop')
    print(f"   Created: {type(metrics).__name__}")
    
    # 3. Tracer Factory
    print("\n3. Tracer Factory:")
    tracer = TracerFactory.get_tracer('noop')
    print(f"   Created: {type(tracer).__name__}")
    
    # 4. Limiter Factory
    print("\n4. Limiter Factory:")
    limiter = LimiterFactory.get_limiter('noop')
    print(f"   Created: {type(limiter).__name__}")
    
    # 5. Emitter Factory
    print("\n5. Emitter Factory:")
    emitter = EmitterFactory.get_emitter('noop')
    print(f"   Created: {type(emitter).__name__}")
    
    # 6. Security Factory
    print("\n6. Security Factory:")
    security_basic = SecurityFactory.get_security('basic')
    security_noop = SecurityFactory.get_security('noop')
    print(f"   Basic: {type(security_basic).__name__}")
    print(f"   NoOp: {type(security_noop).__name__}")
    
    # 7. Validator Factory
    print("\n7. Validator Factory:")
    validator_basic = ValidatorFactory.get_validator('basic')
    validator_noop = ValidatorFactory.get_validator('noop')
    print(f"   Basic: {type(validator_basic).__name__}")
    print(f"   NoOp: {type(validator_noop).__name__}")
    
    # 8. Policy Factory
    print("\n8. Policy Factory:")
    policy = PolicyFactory.get_policy('noop')
    print(f"   Created: {type(policy).__name__}")


def demo_context_builder_basic():
    """Demonstrate basic ToolContextBuilder usage."""
    print("\n\n=== ToolContextBuilder: Basic Usage ===\n")
    
    # Simple context with just user info
    context = (ToolContextBuilder()
        .with_user("user-123")
        .with_session("session-456")
        .build())
    
    print(f"User ID: {context.user_id}")
    print(f"Session ID: {context.session_id}")
    print(f"Memory: {context.memory}")  # None
    print(f"Metrics: {context.metrics}")  # None


def demo_context_builder_with_defaults():
    """Demonstrate ToolContextBuilder with preset profiles."""
    print("\n\n=== ToolContextBuilder: With Defaults ===\n")
    
    # Context with all NoOp implementations
    context_noop = (ToolContextBuilder()
        .with_user("user-123")
        .with_tenant("tenant-abc")
        .with_defaults('noop')
        .build())
    
    print("NoOp Profile:")
    print(f"  User: {context_noop.user_id}")
    print(f"  Tenant: {context_noop.tenant_id}")
    print(f"  Memory: {type(context_noop.memory).__name__}")
    print(f"  Metrics: {type(context_noop.metrics).__name__}")
    print(f"  Tracer: {type(context_noop.tracer).__name__}")
    print(f"  Limiter: {type(context_noop.limiter).__name__}")
    print(f"  Validator: {type(context_noop.validator).__name__}")
    print(f"  Security: {type(context_noop.security).__name__}")
    
    # Context with Basic implementations
    context_basic = (ToolContextBuilder()
        .with_user("user-456")
        .with_defaults('basic')
        .build())
    
    print("\nBasic Profile:")
    print(f"  User: {context_basic.user_id}")
    print(f"  Validator: {type(context_basic.validator).__name__}")
    print(f"  Security: {type(context_basic.security).__name__}")


def demo_context_builder_custom():
    """Demonstrate ToolContextBuilder with custom configuration."""
    print("\n\n=== ToolContextBuilder: Custom Configuration ===\n")
    
    context = (ToolContextBuilder()
        .with_user("user-789")
        .with_tenant("tenant-xyz")
        .with_session("session-abc")
        .with_trace("trace-123", "span-456")
        .with_locale("en-US")
        .with_timezone("America/New_York")
        .with_auth({"role": "admin", "permissions": ["read", "write"]})
        .with_extras({"department": "engineering", "level": "senior"})
        .with_memory_by_name('noop')
        .with_metrics_by_name('noop')
        .with_tracer_by_name('noop')
        .with_validator_by_name('basic')
        .with_security_by_name('basic')
        .build())
    
    print(f"User ID: {context.user_id}")
    print(f"Tenant ID: {context.tenant_id}")
    print(f"Session ID: {context.session_id}")
    print(f"Trace ID: {context.trace_id}")
    print(f"Span ID: {context.span_id}")
    print(f"Locale: {context.locale}")
    print(f"Timezone: {context.timezone}")
    print(f"Auth: {context.auth}")
    print(f"Extras: {context.extras}")
    print(f"Validator: {type(context.validator).__name__}")
    print(f"Security: {type(context.security).__name__}")


def demo_factory_registration():
    """Demonstrate registering custom implementations."""
    print("\n\n=== Factory Registration: Custom Implementations ===\n")
    
    # Create a simple custom memory implementation
    from core.tools.interfaces.tool_interfaces import IToolMemory
    from typing import Any, Optional
    from contextlib import asynccontextmanager
    
    class SimpleMemory(IToolMemory):
        def __init__(self):
            self.storage = {}
        
        async def get(self, key: str) -> Any:
            return self.storage.get(key)
        
        async def set(self, key: str, value: Any, ttl_s: Optional[int] = None) -> None:
            self.storage[key] = value
        
        async def set_if_absent(self, key: str, value: Any, ttl_s: Optional[int] = None) -> bool:
            if key not in self.storage:
                self.storage[key] = value
                return True
            return False
        
        async def delete(self, key: str) -> None:
            self.storage.pop(key, None)
        
        @asynccontextmanager
        async def lock(self, key: str, ttl_s: int = 10):
            yield
    
    # Register custom implementation
    MemoryFactory.register('simple', SimpleMemory())
    print("[OK] Registered custom 'simple' memory implementation")
    
    # Use custom implementation
    custom_memory = MemoryFactory.get_memory('simple')
    print(f"[OK] Retrieved custom memory: {type(custom_memory).__name__}")
    
    # Use in builder
    context = (ToolContextBuilder()
        .with_user("user-custom")
        .with_memory_by_name('simple')
        .build())
    
    print(f"[OK] Used in context: {type(context.memory).__name__}")


async def demo_interface_compliance():
    """Demonstrate that all implementations properly implement their interfaces."""
    print("\n\n=== Interface Compliance Demo ===\n")
    
    from core.tools.interfaces.tool_interfaces import (
        IToolMemory, IToolMetrics, IToolTracer, IToolLimiter,
        IToolEmitter, IToolValidator, IToolSecurity, IToolPolicy
    )
    
    # Get implementations
    memory = MemoryFactory.get_memory('noop')
    metrics = MetricsFactory.get_metrics('noop')
    tracer = TracerFactory.get_tracer('noop')
    limiter = LimiterFactory.get_limiter('noop')
    emitter = EmitterFactory.get_emitter('noop')
    validator = ValidatorFactory.get_validator('basic')
    security = SecurityFactory.get_security('basic')
    policy = PolicyFactory.get_policy('noop')
    
    # Verify interface compliance
    print("Interface Compliance Checks:")
    print(f"  NoOpMemory implements IToolMemory: {isinstance(memory, IToolMemory)}")
    print(f"  NoOpMetrics implements IToolMetrics: {isinstance(metrics, IToolMetrics)}")
    print(f"  NoOpTracer implements IToolTracer: {isinstance(tracer, IToolTracer)}")
    print(f"  NoOpLimiter implements IToolLimiter: {isinstance(limiter, IToolLimiter)}")
    print(f"  NoOpEmitter implements IToolEmitter: {isinstance(emitter, IToolEmitter)}")
    print(f"  BasicValidator implements IToolValidator: {isinstance(validator, IToolValidator)}")
    print(f"  BasicSecurity implements IToolSecurity: {isinstance(security, IToolSecurity)}")
    print(f"  NoOpPolicy implements IToolPolicy: {isinstance(policy, IToolPolicy)}")
    
    # Test actual interface methods
    print("\nInterface Method Tests:")
    
    # Memory
    await memory.set("test_key", "test_value")
    value = await memory.get("test_key")
    print(f"  Memory.get/set: [OK]")
    
    # Metrics
    await metrics.incr("test.metric")
    await metrics.observe("test.observation", 1.5)
    await metrics.timing_ms("test.timing", 100)
    print(f"  Metrics.incr/observe/timing_ms: [OK]")
    
    # Tracer
    async with tracer.span("test.span") as span_id:
        print(f"  Tracer.span: [OK] (span_id: '{span_id}')")
    
    # Limiter
    async with limiter.acquire("test.rate"):
        print(f"  Limiter.acquire: [OK]")
    
    # Emitter
    await emitter.emit("test.event", {"data": "value"})
    print(f"  Emitter.emit: [OK]")
    
    print("\n[OK] All interface methods work correctly!")


def main():
    """Run all demos."""
    print("=" * 70)
    print("Factory Pattern and ToolContextBuilder Demo")
    print("=" * 70)
    
    # Run synchronous demos
    demo_factories()
    demo_context_builder_basic()
    demo_context_builder_with_defaults()
    demo_context_builder_custom()
    demo_factory_registration()
    
    # Run async demos
    asyncio.run(demo_interface_compliance())
    
    print("\n" + "=" * 70)
    print("Demo Complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()

