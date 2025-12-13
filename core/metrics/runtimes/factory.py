"""
Metrics Store Factory.

Provides singleton access to the metrics store for the application.
Uses core.memory.metrics_store for actual storage implementations.
"""

import threading
from typing import Optional

from core.memory import IMetricsStore, create_metrics_store as _create_store


# =============================================================================
# Singleton Instance
# =============================================================================

_instance: Optional[IMetricsStore] = None
_lock = threading.Lock()
_store_type: str = "memory"  # "memory" or "dynamodb"
_store_kwargs: dict = {}


def configure_metrics_store(
    store_type: str = "memory",
    **kwargs,
) -> None:
    """
    Configure the metrics store type and options.
    
    Call this before first use of get_metrics_store() to configure.
    
    Args:
        store_type: "memory" or "dynamodb"
        **kwargs: Store-specific options (table_name, ttl_days, etc.)
    """
    global _store_type, _store_kwargs
    _store_type = store_type
    _store_kwargs = kwargs


async def get_metrics_store(**kwargs) -> IMetricsStore:
    """
    Get the global metrics store (singleton).
    
    Uses core.memory.metrics_store for storage.
    
    Args:
        **kwargs: Override store options (only used on first call)
        
    Returns:
        IMetricsStore instance
    """
    global _instance
    
    if _instance is None:
        with _lock:
            if _instance is None:
                # Merge configured kwargs with overrides
                final_kwargs = {**_store_kwargs, **kwargs}
                _instance = _create_store(_store_type, **final_kwargs)
    
    return _instance


async def shutdown_metrics_store() -> None:
    """Shutdown the global metrics store."""
    global _instance
    
    with _lock:
        if _instance is not None:
            if hasattr(_instance, 'clear'):
                # Don't clear on shutdown, just release reference
                pass
            _instance = None


def reset_metrics_store() -> None:
    """Reset the metrics store (for testing)."""
    global _instance
    
    with _lock:
        _instance = None

