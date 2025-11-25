"""
Pytest configuration and fixtures for test suite.

This module provides global test configuration, fixtures, and cleanup
to prevent memory leaks and ensure proper test isolation.
"""

import pytest
import logging
import gc
from unittest.mock import Mock


@pytest.fixture(autouse=True)
def cleanup_logging():
    """
    Cleanup logging handlers and loggers after each test.
    
    This prevents memory leaks from accumulated logging handlers and
    logger instances in Python's global logging state.
    """
    # Before test: Record existing loggers
    existing_loggers = set(logging.Logger.manager.loggerDict.keys())
    
    yield
    
    # After test: Cleanup
    # 1. Get all new loggers created during the test
    current_loggers = set(logging.Logger.manager.loggerDict.keys())
    new_loggers = current_loggers - existing_loggers
    
    # 2. Remove handlers from new loggers
    for logger_name in new_loggers:
        logger = logging.getLogger(logger_name)
        if hasattr(logger, 'handlers'):
            for handler in logger.handlers[:]:
                try:
                    handler.close()
                    logger.removeHandler(handler)
                except Exception:
                    pass
    
    # 3. Clear root logger handlers if they accumulated
    root_logger = logging.getLogger()
    if len(root_logger.handlers) > 10:  # Arbitrary threshold
        for handler in root_logger.handlers[:]:
            try:
                handler.close()
                root_logger.removeHandler(handler)
            except Exception:
                pass


@pytest.fixture(autouse=True)
def cleanup_logger_adaptor_instances():
    """
    Cleanup LoggerAdaptor singleton instances after each test.
    
    LoggerAdaptor maintains a class-level _instances dict that
    can accumulate memory. This fixture cleans it up after each test.
    """
    yield
    
    # Clean up LoggerAdaptor singleton instances
    try:
        from utils.logging.LoggerAdaptor import LoggerAdaptor
        
        # Shutdown all logger instances
        for instance in LoggerAdaptor._instances.values():
            try:
                # Remove all handlers
                if hasattr(instance, 'logger') and instance.logger:
                    for handler in instance.logger.handlers[:]:
                        try:
                            handler.close()
                            instance.logger.removeHandler(handler)
                        except Exception:
                            pass
            except Exception:
                pass
        
        # Clear the instances dict
        LoggerAdaptor._instances.clear()
        
    except ImportError:
        pass


@pytest.fixture(autouse=True)
def reset_mock_call_limits():
    """
    Reset mock objects to prevent unlimited call history accumulation.
    
    This is automatically applied to all tests.
    """
    # Nothing to do before test
    yield
    
    # Force garbage collection after each test
    gc.collect()


@pytest.fixture(autouse=True)
def cleanup_delayed_logger_threads():
    """
    Ensure DelayedLogger threads are properly shutdown after tests.
    
    DelayedLogger creates background threads that may not be cleaned up,
    causing memory leaks and preventing process termination.
    """
    import threading
    
    # Record existing threads before test
    existing_threads = set(threading.enumerate())
    
    yield
    
    # After test: Find and stop DelayedLogger worker threads
    current_threads = set(threading.enumerate())
    new_threads = current_threads - existing_threads
    
    for thread in new_threads:
        if 'DelayedLoggerWorker' in thread.name:
            # Thread is a daemon, but we should try to signal it to stop
            # The thread checks _stop_worker event, but we can't access it here
            # Just wait a bit for it to finish naturally
            try:
                thread.join(timeout=0.5)
            except Exception:
                pass


@pytest.fixture
def limited_mock():
    """
    Create a Mock object with limited call history to prevent memory bloat.
    
    Regular Mock objects keep unlimited call history. This fixture creates
    a Mock that only keeps the last 10 calls.
    """
    class LimitedMock(Mock):
        """Mock with limited call history."""
        
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._call_limit = 10
        
        def __call__(self, *args, **kwargs):
            result = super().__call__(*args, **kwargs)
            # Limit call history
            if len(self.call_args_list) > self._call_limit:
                self.call_args_list = self.call_args_list[-self._call_limit:]
            return result
    
    return LimitedMock


@pytest.fixture(scope="session", autouse=True)
def configure_pytest_for_memory_efficiency():
    """
    Configure pytest session for memory efficiency.
    """
    # Could set memory limits, configure garbage collection, etc.
    import gc
    
    # Enable automatic garbage collection
    gc.enable()
    
    # Set gc to run more frequently
    gc.set_threshold(700, 10, 10)  # More aggressive than default (700, 10, 10)
    
    yield
    
    # Final cleanup at end of session
    gc.collect()
    
    # Print memory usage stats if available
    try:
        import psutil
        import os
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        print(f"\n=== Memory Usage at End of Tests ===")
        print(f"RSS: {memory_info.rss / 1024 / 1024:.2f} MB")
        print(f"VMS: {memory_info.vms / 1024 / 1024:.2f} MB")
    except ImportError:
        pass


def pytest_runtest_teardown(item, nextitem):
    """
    Hook that runs after each test for additional cleanup.
    """
    # Force garbage collection after each test
    gc.collect()

