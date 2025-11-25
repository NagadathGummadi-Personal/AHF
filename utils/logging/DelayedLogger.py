"""
DelayedLogger - Asynchronous logging functionality for improved performance.

This module provides delayed/asynchronous logging capabilities to improve performance
in high-throughput scenarios. It supports queuing log messages and processing them
in a background thread.

WARNING: LAMBDA COMPATIBILITY
=============================
This module has significant complications when running on AWS Lambda:

1. BACKGROUND THREADS: Lambda doesn't support long-running background threads
2. EXECUTION TIMEOUT: Lambda functions have limited execution time (15 minutes max)
3. NO CLEAN SHUTDOWN: shutdown() method may not be called reliably
4. CONTAINER REUSE: Unpredictable behavior across Lambda container reuse
5. MEMORY CONSTRAINTS: Limited memory for queues in Lambda environment
6. COLD START DELAYS: Background thread startup adds to cold start time

RECOMMENDATIONS FOR LAMBDA:
- Set delayed_logging.enabled: false in Lambda environment
- Use immediate logging for Lambda functions
- Consider Lambda Powertools for structured logging instead
- Use CloudWatch Logs for centralized log management

Usage:
    from utils.logging.DelayedLogger import DelayedLogger

    delayed_logger = DelayedLogger(logger)
    delayed_logger.info_delayed("Processing started", user_id="123")
    delayed_logger.flush_delayed_logs()  # Manual flush
"""

import os
import threading
from datetime import datetime
from queue import Queue, Empty
from typing import Any, Dict, Optional
from utils.logging.Enum import LoggingFormat


class DelayedLogger:
    """
    Delayed/asynchronous logger that queues log messages for batch processing.

    This logger provides performance benefits in high-throughput scenarios by
    batching log entries and processing them asynchronously.
    """

    def __init__(self, logger: Any):
        """
        Initialize the delayed logger.

        Args:
            logger: Base logger instance that has standard logging methods
        """
        self.logger = logger
        self.delayed_logging_enabled = False
        self.delayed_logging_size_kb = 0  # 0 = immediate
        self.delayed_logging_flush_on_exception = True
        self.delayed_logging_flush_on_completion = True

        # Check if running on Lambda and disable delayed logging if so
        if self._is_running_on_lambda():
            self.delayed_logging_enabled = False
            self.delayed_logging_size_kb = 0

        if self.delayed_logging_enabled:
            self._initialize_queue()

    def configure(self, config: Dict[str, Any]):
        """
        Configure delayed logging from configuration dictionary.

        Args:
            config: Configuration dictionary with delayed_logging settings
        """
        delayed_config = config.get('delayed_logging', {})

        self.delayed_logging_enabled = delayed_config.get('enabled', False)
        self.delayed_logging_size_kb = delayed_config.get('queue_size_kb', 0)
        self.delayed_logging_flush_on_exception = delayed_config.get('flush_on_exception', True)
        self.delayed_logging_flush_on_completion = delayed_config.get('flush_on_completion', True)

        # Check if running on Lambda
        if self._is_running_on_lambda():
            if self.delayed_logging_enabled:
                print("WARNING: Delayed logging disabled - not compatible with Lambda environment")
            self.delayed_logging_enabled = False
            self.delayed_logging_size_kb = 0
        elif not self.delayed_logging_enabled:
            # When disabled, set queue size to 0
            self.delayed_logging_size_kb = 0

        if self.delayed_logging_enabled:
            self._initialize_queue()
        else:
            self._shutdown_queue()

    def _is_running_on_lambda(self) -> bool:
        """Check if running in AWS Lambda environment."""
        return (
            os.getenv('AWS_LAMBDA_FUNCTION_NAME') is not None or
            os.getenv('AWS_LAMBDA_FUNCTION_VERSION') is not None or
            os.getenv('LAMBDA_TASK_ROOT') is not None
        )

    def _initialize_queue(self):
        """Initialize the log queue and worker thread."""
        self._log_queue: Queue = Queue()
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_worker = threading.Event()
        self._start_worker_thread()

    def _shutdown_queue(self):
        """Shutdown the log queue and worker thread."""
        if hasattr(self, '_stop_worker') and self._stop_worker:
            self._stop_worker.set()

        if hasattr(self, '_log_queue') and self._log_queue:
            try:
                self._log_queue.put(None)  # Shutdown signal
            except Exception:
                pass

        if hasattr(self, '_worker_thread') and self._worker_thread and self._worker_thread.is_alive():
            try:
                self._worker_thread.join(timeout=5.0)
            except Exception:
                pass

    def _start_worker_thread(self):
        """Start the background worker thread for processing log queue."""
        if not self.delayed_logging_enabled:
            return

        self._worker_thread = threading.Thread(
            target=self._process_log_queue,
            name=f"DelayedLoggerWorker-{id(self)}",
            daemon=True
        )
        self._worker_thread.start()

    def _process_log_queue(self):
        """Background worker to process queued log entries."""
        while not self._stop_worker.is_set():
            try:
                # Wait for log entries with timeout
                log_entry = self._log_queue.get(timeout=1.0)

                if log_entry is None:  # Shutdown signal
                    break

                # Process the log entry
                self._process_delayed_log_entry(log_entry)

            except Empty:
                # Timeout occurred, check if we should continue
                continue
            except Exception as e:
                # Log any errors that occur during processing
                try:
                    self.logger.error(f"Error processing delayed log entry: {e}")
                except Exception:
                    pass  # Avoid infinite recursion

    def _process_delayed_log_entry(self, log_entry: Dict[str, Any]):
        """Process a single delayed log entry."""
        try:
            level = log_entry['level']
            message = log_entry['message']
            kwargs = log_entry.get('kwargs', {})
            backend = log_entry.get('backend', 'standard')

            # Apply redaction if enabled (assuming logger has redaction_manager)
            if hasattr(self.logger, 'redaction_manager') and self.logger.redaction_manager:
                message = self.logger.redaction_manager.redact_message(message)
                # Redact kwargs values if they are strings
                kwargs = {k: (self.logger.redaction_manager.redact_message(v) if isinstance(v, str) else v) 
                         for k, v in kwargs.items()}

            # Log using the appropriate backend
            if backend == LoggingFormat.JSON.value:
                self.logger._log_json(level, message, **kwargs)
            elif backend == LoggingFormat.DETAILED.value:
                self.logger._log_detailed(level, message, **kwargs)
            else:
                self.logger._log_standard(level, message, **kwargs)

        except Exception as e:
            # Log processing errors
            try:
                self.logger.error(f"Failed to process delayed log entry: {e}")
            except Exception:
                pass

    def _log_message_delayed(self, level: str, *args, **kwargs):
        """Log message with delayed processing if enabled."""
        if not self.delayed_logging_enabled:
            # Fall back to immediate logging
            self._log_message_immediate(level, *args, **kwargs)
            return

        # Create log entry
        message = self._format_message(*args)
        log_entry = {
            'level': level,
            'message': message,
            'kwargs': kwargs,
            'backend': getattr(self.logger, 'backend', 'standard'),
            'timestamp': datetime.utcnow().isoformat(),
            'context': getattr(self.logger, 'context', {}).copy()
        }

        # Add to queue
        self._log_queue.put(log_entry)

        # Check if we should flush based on size
        if self.delayed_logging_size_kb > 0:
            current_size = self._get_queue_size_kb()
            if current_size >= self.delayed_logging_size_kb:
                self.flush_delayed_logs()

    def _log_message_immediate(self, level: str, *args, **kwargs):
        """Log message immediately using the underlying logger."""
        if hasattr(self.logger, '_log_message'):
            self.logger._log_message(level, *args, **kwargs)
        else:
            # Fallback to direct method calls
            getattr(self.logger, level.lower())(*args, **kwargs)

    def _format_message(self, *args) -> str:
        """Format message from multiple arguments."""
        if not args:
            return ""

        # If only one argument and it's a string, use it as the message
        if len(args) == 1 and isinstance(args[0], str):
            message = args[0]
        else:
            # Format multiple arguments similar to print()
            message = " ".join(str(arg) for arg in args)

        return message

    def _get_queue_size_kb(self) -> float:
        """Get approximate size of queue in KB."""
        total_size = 0
        try:
            # Sample a few entries to estimate size
            queue_size = self._log_queue.qsize()
            sample_size = min(10, queue_size)

            for _ in range(sample_size):
                try:
                    entry = self._log_queue.get(timeout=0.1)
                    entry_size = len(str(entry).encode('utf-8'))
                    total_size += entry_size
                    self._log_queue.put(entry)  # Put it back
                except Empty:
                    break

            # Extrapolate for full queue
            if sample_size > 0:
                estimated_size = (total_size / sample_size) * queue_size
                return estimated_size / 1024  # Convert to KB
        except Exception:
            pass

        return 0.0

    def flush_delayed_logs(self):
        """Force flush all delayed log entries."""
        if not self.delayed_logging_enabled:
            return

        # Process all entries in queue
        while True:
            try:
                log_entry = self._log_queue.get_nowait()
                self._process_delayed_log_entry(log_entry)
            except Empty:
                break

    def flush_on_exception(self):
        """Flush delayed logs when an exception occurs."""
        if self.delayed_logging_enabled and self.delayed_logging_flush_on_exception:
            self.flush_delayed_logs()

    def flush_on_completion(self):
        """Flush delayed logs when operation completes."""
        if self.delayed_logging_enabled and self.delayed_logging_flush_on_completion:
            self.flush_delayed_logs()

    def shutdown(self):
        """Shutdown the delayed logger and flush any pending logs."""
        # Flush any delayed logs
        self.flush_delayed_logs()

        # Stop worker thread
        self._shutdown_queue()

    # Delayed logging methods
    def debug_delayed(self, *args, **kwargs):
        """Log debug message with delayed processing."""
        self._log_message_delayed('DEBUG', *args, **kwargs)

    def info_delayed(self, *args, **kwargs):
        """Log info message with delayed processing."""
        self._log_message_delayed('INFO', *args, **kwargs)

    def warning_delayed(self, *args, **kwargs):
        """Log warning message with delayed processing."""
        self._log_message_delayed('WARNING', *args, **kwargs)

    def error_delayed(self, *args, **kwargs):
        """Log error message with delayed processing."""
        self._log_message_delayed('ERROR', *args, **kwargs)

    def critical_delayed(self, *args, **kwargs):
        """Log critical message with delayed processing."""
        self._log_message_delayed('CRITICAL', *args, **kwargs)

    def log_delayed(self, level: str, *args, **kwargs):
        """Log message with delayed processing at specified level."""
        self._log_message_delayed(level.upper(), *args, **kwargs)
