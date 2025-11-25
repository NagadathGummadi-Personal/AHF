"""
DurationLogger - Standalone duration logging functionality with @durationlogger decorator.

This module provides duration logging capabilities that can be used with any logger
that supports duration logging. It includes context managers, decorators, and
convenience functions for timing operations and logging their performance.

Usage:
    from utils.logging.DurationLogger import durationlogger

    # As a decorator
    @durationlogger
    def my_function():
        return do_something()

    # As a context manager
    with durationlogger.time_operation("database_query") as timer:
        result = query_database()
        timer.add_metadata(rows_affected=len(result))
"""

import time
import functools
from contextlib import contextmanager
from typing import Any, Callable, ContextManager


class DurationContext(ContextManager):
    """
    Context manager for timing operations and automatically logging their duration.

    This class provides a convenient way to time operations using Python's `with` statement.
    When the context exits, it automatically logs the duration using the associated logger.

    Example:
        with durationlogger.time_operation("database_query", table="users") as timer:
            # Perform the operation
            result = query_database()
            timer.add_metadata(rows_affected=len(result))

        # Duration is automatically logged when exiting the context
    """

    def __init__(self, logger: Any, operation_name: str, **kwargs):
        """
        Initialize the duration context.

        Args:
            logger: Logger instance that has a log_duration method
            operation_name: Name/description of the operation
            **kwargs: Additional context for the log entry
        """
        self.logger = logger
        self.operation_name = operation_name
        self.kwargs = kwargs
        self.start_time = None
        self.metadata = {}

    def __enter__(self):
        """Start timing the operation."""
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timing and log the duration."""
        if self.start_time is not None:
            duration = time.perf_counter() - self.start_time

            # Add exception info if an exception occurred
            if exc_type is not None:
                self.kwargs.update({
                    'exception_type': exc_type.__name__,
                    'exception_message': str(exc_val),
                    'success': False
                })
            else:
                self.kwargs['success'] = True

            # Add any metadata collected during the operation
            if self.metadata:
                self.kwargs.update(self.metadata)

            # Log the duration
            self.logger.log_duration(self.operation_name, duration, **self.kwargs)

    def add_metadata(self, **metadata):
        """
        Add metadata to be included in the duration log.

        Args:
            **metadata: Key-value pairs to add to the log context
        """
        self.metadata.update(metadata)

    def get_duration(self) -> float:
        """
        Get the current duration (or 0 if timing hasn't started).

        Returns:
            float: Duration in seconds since timing started
        """
        if self.start_time is None:
            return 0.0
        return time.perf_counter() - self.start_time


class DurationLogger:
    """
    Standalone duration logger that provides timing functionality with decorators and context managers.

    This class can be used as a decorator (@durationlogger) or as a context manager
    for timing operations. It requires a logger instance that has a log_duration method.
    """

    def __init__(self, logger: Any = None):
        """
        Initialize the duration logger.

        Args:
            logger: Logger instance that has a log_duration method
        """
        self.logger = logger

    def __call__(self, func_or_operation_name: Callable | str = None, **kwargs):
        """
        Use as a decorator or function call.

        Args:
            func_or_operation_name: Function to decorate or operation name
            **kwargs: Additional context for the log entry

        Returns:
            Callable or DurationContext: Decorated function or context manager
        """
        if func_or_operation_name is None:
            # Used as @durationlogger
            return lambda func: self.time_function(**kwargs)(func)
        elif callable(func_or_operation_name):
            # Used as @durationlogger(func)
            return self.time_function(**kwargs)(func_or_operation_name)
        else:
            # Used as durationlogger.time_operation(operation_name)
            return self.time_operation(str(func_or_operation_name), **kwargs)

    def time_function(self, **kwargs):
        """
        Decorator to time a function execution.

        Args:
            operation_name: Optional name for the operation (defaults to function name)
            **kwargs: Additional context for the log entry

        Returns:
            Callable: Decorated function
        """
        def decorator(func: Callable) -> Callable:
            operation_name = kwargs.pop('operation_name', None)
            actual_operation_name = operation_name or func.__name__

            @functools.wraps(func)
            def wrapper(*args, **func_kwargs):
                start_time = time.perf_counter()

                try:
                    result = func(*args, **func_kwargs)
                    duration = time.perf_counter() - start_time

                    # Log successful execution
                    self.logger.log_duration(actual_operation_name, duration, success=True, **kwargs)
                    return result

                except Exception as e:
                    duration = time.perf_counter() - start_time

                    # Log failed execution
                    self.logger.log_duration(
                        actual_operation_name,
                        duration,
                        success=False,
                        error=str(e),
                        error_type=type(e).__name__,
                        **kwargs
                    )
                    raise

            return wrapper
        return decorator

    def time_operation(self, operation_name: str, **kwargs) -> DurationContext:
        """
        Create a context manager to time an operation.

        Args:
            operation_name: Name/description of the operation
            **kwargs: Additional context for the log entry

        Returns:
            DurationContext: Context manager that will log duration on exit
        """
        if self.logger is None:
            raise ValueError("Logger not set. Use DurationLogger(logger) or set logger attribute.")
        return DurationContext(self.logger, operation_name, **kwargs)

    def set_logger(self, logger: Any):
        """
        Set the logger instance to use for logging durations.

        Args:
            logger: Logger instance that has a log_duration method
        """
        self.logger = logger


# Global instance for convenient usage
_duration_logger = DurationLogger()


def durationlogger(func_or_operation_name: Callable | str = None, **kwargs):
    """
    Global duration logger function/decorator.

    Can be used in multiple ways:
    1. As a decorator: @durationlogger
    2. As a function: durationlogger("operation_name")
    3. As a context manager: with durationlogger.time_operation("op"):

    Args:
        func_or_operation_name: Function to decorate or operation name
        **kwargs: Additional context for the log entry

    Returns:
        Callable or DurationContext: Decorated function or context manager
    """
    return _duration_logger(func_or_operation_name, **kwargs)


# Convenience context managers for common use cases
@contextmanager
def log_duration(logger: Any, operation_name: str, **kwargs):
    """
    Context manager for timing operations with automatic logging.

    Args:
        logger: Logger instance with log_duration method
        operation_name: Name/description of the operation
        **kwargs: Additional context for the log entry

    Example:
        with log_duration(logger, "file_processing", file_path="data.csv") as timer:
            process_file()
    """
    with DurationContext(logger, operation_name, **kwargs):
        yield


def time_function(logger: Any, **kwargs):
    """
    Decorator factory for timing functions.

    Args:
        logger: Logger instance with log_duration method
        func_name: Optional function name override
        operation_name: Optional operation name override
        **kwargs: Additional context for the log entry

    Example:
        @time_function(logger, user_id="123")
        def my_function():
            return do_something()
    """
    def decorator(func):
        func_name = kwargs.pop('func_name', None)
        operation_name = kwargs.pop('operation_name', None)
        actual_name = func_name or operation_name or func.__name__

        @functools.wraps(func)
        def wrapper(*args, **func_kwargs):
            start_time = time.perf_counter()

            try:
                result = func(*args, **func_kwargs)
                duration = time.perf_counter() - start_time

                # Log successful execution
                logger.log_duration(actual_name, duration, success=True, **kwargs)
                return result

            except Exception as e:
                duration = time.perf_counter() - start_time

                # Log failed execution
                logger.log_duration(
                    actual_name,
                    duration,
                    success=False,
                    error=str(e),
                    error_type=type(e).__name__,
                    **kwargs
                )
                raise

        return wrapper

    return decorator


# Set up the global duration logger to be used without explicit logger
def configure_duration_logger(logger: Any):
    """
    Configure the global duration logger instance.

    Args:
        logger: Logger instance that has a log_duration method
    """
    global _duration_logger
    _duration_logger.set_logger(logger)
