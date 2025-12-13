"""
HTTP Session Manager for Fargate/Containerized Deployments.

This module provides a centralized session manager for aiohttp connections
with proper lifecycle management for containerized environments like Fargate.

Features:
=========
- Shared connection pooling across executors
- Graceful shutdown with SIGTERM handling
- Connection limits and timeouts
- Health check support
- Properly async singleton pattern (no module-level locks)

Usage:
======
    from core.tools.runtimes.executors.http_executors import (
        HttpSessionManager,
        get_session_manager,
    )
    
    # Get the singleton manager
    manager = await get_session_manager()
    
    # Get a shared session
    session = await manager.get_session()
    
    # On shutdown (automatically called on SIGTERM)
    await manager.shutdown()

For Fargate:
============
    # In your FastAPI lifespan
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        manager = await get_session_manager()
        await manager.startup()
        yield
        await manager.shutdown()

Version: 1.1.0
"""

import asyncio
import atexit
import signal
import sys
import threading
from typing import Optional, Dict, Any
from weakref import WeakSet
import logging

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False


logger = logging.getLogger("ahf.http.session_manager")


class HttpSessionManager:
    """
    Centralized HTTP session manager for connection pooling.
    
    Designed for containerized deployments (Fargate, ECS, K8s) where:
    - Connections should be pooled for efficiency
    - Resources must be cleaned up on shutdown
    - SIGTERM must be handled gracefully
    
    Attributes:
        _session: Shared aiohttp ClientSession
        _connector: TCP connector with connection limits
        _executors: Weak references to executors using this manager
        _shutdown_event: Event signaling shutdown in progress
    """
    
    # Default connection settings for Fargate
    DEFAULT_LIMIT = 100  # Max concurrent connections
    DEFAULT_LIMIT_PER_HOST = 10  # Max connections per host
    DEFAULT_TIMEOUT_TOTAL = 30  # Total request timeout
    DEFAULT_TIMEOUT_CONNECT = 10  # Connection timeout
    DEFAULT_KEEPALIVE_TIMEOUT = 30  # Keep-alive timeout
    
    def __init__(
        self,
        limit: int = DEFAULT_LIMIT,
        limit_per_host: int = DEFAULT_LIMIT_PER_HOST,
        timeout_total: float = DEFAULT_TIMEOUT_TOTAL,
        timeout_connect: float = DEFAULT_TIMEOUT_CONNECT,
        keepalive_timeout: float = DEFAULT_KEEPALIVE_TIMEOUT,
        enable_cleanup_closed: bool = True,
    ):
        """
        Initialize the session manager.
        
        Args:
            limit: Maximum number of concurrent connections
            limit_per_host: Maximum connections per host
            timeout_total: Total request timeout in seconds
            timeout_connect: Connection timeout in seconds
            keepalive_timeout: Keep-alive timeout for idle connections
            enable_cleanup_closed: Enable cleanup of closed connections
        """
        if not AIOHTTP_AVAILABLE:
            raise ImportError(
                "aiohttp is required for HttpSessionManager. "
                "Install it with: pip install aiohttp"
            )
        
        self._limit = limit
        self._limit_per_host = limit_per_host
        self._timeout_total = timeout_total
        self._timeout_connect = timeout_connect
        self._keepalive_timeout = keepalive_timeout
        self._enable_cleanup_closed = enable_cleanup_closed
        
        self._session: Optional[aiohttp.ClientSession] = None
        self._connector: Optional[aiohttp.TCPConnector] = None
        self._executors: WeakSet = WeakSet()
        self._shutdown_event: Optional[asyncio.Event] = None  # Lazily created
        self._is_started = False
        self._is_shutting_down = False
        self._lock: Optional[asyncio.Lock] = None  # Lazily created
        self._sync_lock = threading.Lock()  # Thread-safe for lazy init
    
    def _get_lock(self) -> asyncio.Lock:
        """Get or create the async lock (lazy initialization)."""
        if self._lock is None:
            with self._sync_lock:
                if self._lock is None:
                    self._lock = asyncio.Lock()
        return self._lock
    
    def _get_shutdown_event(self) -> asyncio.Event:
        """Get or create the shutdown event (lazy initialization)."""
        if self._shutdown_event is None:
            with self._sync_lock:
                if self._shutdown_event is None:
                    self._shutdown_event = asyncio.Event()
        return self._shutdown_event
    
    async def startup(self) -> None:
        """
        Initialize the session manager.
        
        Call this during application startup (e.g., FastAPI lifespan).
        """
        async with self._get_lock():
            if self._is_started:
                return
            
            self._connector = aiohttp.TCPConnector(
                limit=self._limit,
                limit_per_host=self._limit_per_host,
                keepalive_timeout=self._keepalive_timeout,
                enable_cleanup_closed=self._enable_cleanup_closed,
                force_close=False,
            )
            
            timeout = aiohttp.ClientTimeout(
                total=self._timeout_total,
                connect=self._timeout_connect,
            )
            
            self._session = aiohttp.ClientSession(
                connector=self._connector,
                timeout=timeout,
            )
            
            self._is_started = True
            self._get_shutdown_event().clear()
            
            logger.info(
                "HTTP Session Manager started",
                extra={
                    "limit": self._limit,
                    "limit_per_host": self._limit_per_host,
                    "timeout": self._timeout_total,
                }
            )
    
    async def shutdown(self, timeout: float = 5.0) -> None:
        """
        Gracefully shutdown the session manager.
        
        Args:
            timeout: Maximum time to wait for pending requests
        """
        async with self._get_lock():
            if not self._is_started or self._is_shutting_down:
                return
            
            self._is_shutting_down = True
            self._get_shutdown_event().set()
            
            logger.info("HTTP Session Manager shutting down...")
            
            # Close all executor sessions first
            for executor in list(self._executors):
                try:
                    if hasattr(executor, 'close'):
                        await asyncio.wait_for(executor.close(), timeout=1.0)
                except Exception as e:
                    logger.warning(f"Error closing executor: {e}")
            
            # Wait briefly for pending requests
            if self._connector:
                # Give pending requests time to complete
                await asyncio.sleep(min(0.5, timeout / 2))
            
            # Close the shared session
            if self._session and not self._session.closed:
                await self._session.close()
            
            # Close the connector
            if self._connector and not self._connector.closed:
                await self._connector.close()
            
            self._session = None
            self._connector = None
            self._is_started = False
            self._is_shutting_down = False
            
            logger.info("HTTP Session Manager shutdown complete")
    
    async def get_session(self) -> aiohttp.ClientSession:
        """
        Get the shared HTTP session.
        
        Creates a session if one doesn't exist.
        
        Returns:
            Shared aiohttp ClientSession
            
        Raises:
            RuntimeError: If manager is shutting down
        """
        if self._is_shutting_down:
            raise RuntimeError("Session manager is shutting down")
        
        if not self._is_started:
            await self.startup()
        
        if self._session is None or self._session.closed:
            await self.startup()
        
        return self._session
    
    def register_executor(self, executor: Any) -> None:
        """
        Register an executor for lifecycle management.
        
        Registered executors will be closed during shutdown.
        
        Args:
            executor: Executor instance with close() method
        """
        self._executors.add(executor)
    
    def unregister_executor(self, executor: Any) -> None:
        """
        Unregister an executor.
        
        Args:
            executor: Executor to unregister
        """
        self._executors.discard(executor)
    
    @property
    def is_healthy(self) -> bool:
        """Check if the session manager is healthy."""
        return (
            self._is_started
            and not self._is_shutting_down
            and self._session is not None
            and not self._session.closed
        )
    
    @property
    def stats(self) -> Dict[str, Any]:
        """Get session manager statistics."""
        if not self._connector:
            return {"status": "not_started"}
        
        return {
            "status": "healthy" if self.is_healthy else "unhealthy",
            "is_started": self._is_started,
            "is_shutting_down": self._is_shutting_down,
            "active_connections": len(self._connector._acquired) if hasattr(self._connector, '_acquired') else 0,
            "limit": self._limit,
            "limit_per_host": self._limit_per_host,
            "registered_executors": len(self._executors),
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check.
        
        Returns:
            Health check result with status and details
        """
        return {
            "healthy": self.is_healthy,
            "details": self.stats,
        }


# =============================================================================
# Singleton Instance with Proper Async Safety
# =============================================================================

_session_manager: Optional[HttpSessionManager] = None
_sync_lock = threading.Lock()  # Thread-safe lock for initialization


async def get_session_manager(**kwargs) -> HttpSessionManager:
    """
    Get the global HTTP session manager (singleton).
    
    Uses thread-safe initialization to avoid module-level asyncio.Lock issues.
    The Lock() is created lazily when first needed within an event loop context.
    
    Args:
        **kwargs: Arguments passed to HttpSessionManager on first call
        
    Returns:
        Global HttpSessionManager instance
    """
    global _session_manager
    
    if _session_manager is None:
        # Use threading lock for synchronization (safe across event loops)
        with _sync_lock:
            if _session_manager is None:
                _session_manager = HttpSessionManager(**kwargs)
    
    return _session_manager


def get_session_manager_sync(**kwargs) -> HttpSessionManager:
    """
    Get the session manager synchronously (for signal handlers).
    
    Thread-safe initialization without requiring an event loop.
    
    Args:
        **kwargs: Arguments passed to HttpSessionManager on first call
        
    Returns:
        HttpSessionManager instance
    """
    global _session_manager
    
    with _sync_lock:
        if _session_manager is None:
            _session_manager = HttpSessionManager(**kwargs)
    
    return _session_manager


async def shutdown_session_manager() -> None:
    """Shutdown the global session manager."""
    global _session_manager
    
    if _session_manager is not None:
        await _session_manager.shutdown()
        with _sync_lock:
            _session_manager = None


def reset_session_manager() -> None:
    """Reset the session manager (for testing)."""
    global _session_manager
    with _sync_lock:
        _session_manager = None


# =============================================================================
# Signal Handlers for Graceful Shutdown
# =============================================================================

def _handle_sigterm(signum: int, frame: Any) -> None:
    """
    Handle SIGTERM for graceful shutdown in Fargate.
    
    Fargate sends SIGTERM before SIGKILL, so we need to clean up.
    """
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    
    # Get or create event loop
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # Schedule shutdown
    if _session_manager is not None:
        try:
            loop.run_until_complete(shutdown_session_manager())
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


def install_signal_handlers() -> None:
    """
    Install signal handlers for graceful shutdown.
    
    Call this during application startup for Fargate deployments.
    """
    # Only install on Unix-like systems
    if sys.platform != 'win32':
        signal.signal(signal.SIGTERM, _handle_sigterm)
        signal.signal(signal.SIGINT, _handle_sigterm)
        logger.info("Signal handlers installed for graceful shutdown")


# Register cleanup on interpreter exit
def _atexit_cleanup() -> None:
    """Cleanup on interpreter exit."""
    if _session_manager is not None:
        try:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(shutdown_session_manager())
            loop.close()
        except Exception:
            pass


atexit.register(_atexit_cleanup)

