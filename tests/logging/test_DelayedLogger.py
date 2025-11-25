"""
Test suite for DelayedLogger module.

This module contains tests for the DelayedLogger functionality, covering:
- Delayed logging initialization and configuration
- Queue management and background processing
- Lambda environment detection
- Integration with LoggerAdaptor
- Flush behavior and error handling

Test Structure:
===============
1. Test DelayedLogger class initialization
2. Test queue management functionality
3. Test background thread processing
4. Test Lambda environment detection
5. Test integration with LoggerAdaptor

Pytest Markers:
===============
- delayed: All tests in this module
"""

import pytest
from unittest.mock import Mock, patch
from queue import Empty
from utils.logging.DelayedLogger import DelayedLogger
from utils.logging.LoggerAdaptor import LoggerAdaptor


@pytest.mark.delayed
class TestDelayedLogger:
    """Test cases for DelayedLogger class functionality."""

    @pytest.fixture
    def mock_logger(self):
        """Provide a mock logger for testing."""
        logger = Mock()
        logger._log_message = Mock()
        logger._log_standard = Mock()
        logger._log_json = Mock()
        logger._log_detailed = Mock()
        return logger

    @pytest.fixture
    def delayed_logger(self, mock_logger):
        """Provide a DelayedLogger instance for testing."""
        dl = DelayedLogger(mock_logger)
        yield dl
        # Cleanup: shutdown the delayed logger to stop threads and clear queue
        try:
            dl.shutdown()
            # Explicitly wait for thread to stop
            if hasattr(dl, '_worker_thread') and dl._worker_thread and dl._worker_thread.is_alive():
                dl._worker_thread.join(timeout=2.0)
            # Clear the queue
            if hasattr(dl, '_log_queue'):
                while not dl._log_queue.empty():
                    try:
                        dl._log_queue.get_nowait()
                    except Exception:
                        break
        except Exception:
            pass

    def test_delayed_logger_initialization(self, mock_logger):
        """Test DelayedLogger initialization."""
        dl = DelayedLogger(mock_logger)
        assert dl.logger == mock_logger
        assert dl.delayed_logging_enabled is False  # Disabled by default

    def test_configure_delayed_logging_enabled(self, mock_logger):
        """Test configuring delayed logging as enabled."""
        dl = DelayedLogger(mock_logger)

        config = {
            "delayed_logging": {
                "enabled": True,
                "queue_size_kb": 10,
                "flush_on_exception": True,
                "flush_on_completion": True
            }
        }

        dl.configure(config)
        assert dl.delayed_logging_enabled is True
        assert dl.delayed_logging_size_kb == 10
        assert dl.delayed_logging_flush_on_exception is True
        assert dl.delayed_logging_flush_on_completion is True

    def test_configure_delayed_logging_disabled(self, mock_logger):
        """Test configuring delayed logging as disabled."""
        dl = DelayedLogger(mock_logger)

        config = {
            "delayed_logging": {
                "enabled": False,
                "queue_size_kb": 5,
                "flush_on_exception": False,
                "flush_on_completion": False
            }
        }

        dl.configure(config)
        assert dl.delayed_logging_enabled is False
        assert dl.delayed_logging_size_kb == 0

    def test_lambda_environment_detection(self, mock_logger):
        """Test that delayed logging is disabled in Lambda environment."""
        dl = DelayedLogger(mock_logger)

        # Test with Lambda environment variable
        with patch.dict('os.environ', {'AWS_LAMBDA_FUNCTION_NAME': 'test-function'}):
            config = {
                "delayed_logging": {
                    "enabled": True,
                    "queue_size_kb": 10
                }
            }

            dl.configure(config)
            assert dl.delayed_logging_enabled is False
            assert dl.delayed_logging_size_kb == 0

    def test_non_lambda_environment_allows_delayed_logging(self, mock_logger):
        """Test that delayed logging works in non-Lambda environments."""
        dl = DelayedLogger(mock_logger)

        with patch.dict('os.environ', {}, clear=True):
            config = {
                "delayed_logging": {
                    "enabled": True,
                    "queue_size_kb": 10,
                    "flush_on_exception": True,
                    "flush_on_completion": True
                }
            }

            dl.configure(config)
            assert dl.delayed_logging_enabled is True
            assert dl.delayed_logging_size_kb == 10

    def test_delayed_logging_methods_exist(self, delayed_logger):
        """Test that delayed logging methods exist."""
        assert hasattr(delayed_logger, 'debug_delayed')
        assert hasattr(delayed_logger, 'info_delayed')
        assert hasattr(delayed_logger, 'warning_delayed')
        assert hasattr(delayed_logger, 'error_delayed')
        assert hasattr(delayed_logger, 'critical_delayed')
        assert hasattr(delayed_logger, 'flush_delayed_logs')
        assert hasattr(delayed_logger, 'flush_on_exception')
        assert hasattr(delayed_logger, 'flush_on_completion')

    def test_delayed_logging_fallback_to_immediate(self, mock_logger):
        """Test that delayed logging falls back to immediate when disabled."""
        dl = DelayedLogger(mock_logger)
        dl.delayed_logging_enabled = False

        with patch.object(dl, '_log_message_immediate') as mock_immediate:
            dl.info_delayed("Test message", user_id="123")

            mock_immediate.assert_called_once_with('INFO', "Test message", user_id="123")

    def test_delayed_logging_queue_processing(self, mock_logger):
        """Test that delayed logging processes queued messages."""
        dl = DelayedLogger(mock_logger)
        dl.delayed_logging_enabled = True
        dl.delayed_logging_size_kb = 100  # Large size to avoid auto-flush
        dl._initialize_queue()  # Initialize the queue

        # Mock queue methods
        with patch.object(dl, '_log_queue') as mock_queue:
            with patch.object(dl, '_get_queue_size_kb', return_value=0.1):
                dl.info_delayed("Test message", user_id="123")

                # Verify queue operations
                mock_queue.put.assert_called_once()

    def test_flush_delayed_logs(self, mock_logger):
        """Test manual flush of delayed logs."""
        dl = DelayedLogger(mock_logger)
        dl.delayed_logging_enabled = True
        dl._initialize_queue()  # Initialize the queue

        with patch.object(dl, '_log_queue') as mock_queue:
            with patch.object(dl, '_process_delayed_log_entry') as mock_process:
                mock_queue.get_nowait.side_effect = [
                    {"level": "INFO", "message": "test", "kwargs": {}},
                    Empty
                ]

                dl.flush_delayed_logs()

                # Should have called process once with the log entry
                mock_process.assert_called_once_with({"level": "INFO", "message": "test", "kwargs": {}})

    def test_flush_on_exception(self, mock_logger):
        """Test flush on exception behavior."""
        dl = DelayedLogger(mock_logger)
        dl.delayed_logging_enabled = True
        dl.delayed_logging_flush_on_exception = True

        with patch.object(dl, 'flush_delayed_logs') as mock_flush:
            dl.flush_on_exception()

            mock_flush.assert_called_once()

    def test_flush_on_completion(self, mock_logger):
        """Test flush on completion behavior."""
        dl = DelayedLogger(mock_logger)
        dl.delayed_logging_enabled = True
        dl.delayed_logging_flush_on_completion = True

        with patch.object(dl, 'flush_delayed_logs') as mock_flush:
            dl.flush_on_completion()

            mock_flush.assert_called_once()

    def test_shutdown_behavior(self, mock_logger):
        """Test shutdown behavior."""
        dl = DelayedLogger(mock_logger)
        dl.delayed_logging_enabled = True

        with patch.object(dl, 'flush_delayed_logs') as mock_flush:
            dl.shutdown()

            mock_flush.assert_called_once()


@pytest.mark.delayed
class TestDelayedLoggerIntegration:
    """Test integration between DelayedLogger and LoggerAdaptor."""

    @pytest.fixture
    def logger_adaptor(self):
        """Provide a real LoggerAdaptor instance for integration testing."""
        with patch.object(LoggerAdaptor, '_load_config') as mock_load:
            mock_load.return_value = {
                "backend": "standard",
                "level": "INFO"
            }
            return LoggerAdaptor("integration_test")

    def test_delayed_logger_with_logger_adaptor(self, logger_adaptor):
        """Test DelayedLogger working with real LoggerAdaptor."""
        dl = DelayedLogger(logger_adaptor)

        # Configure delayed logging
        config = {
            "delayed_logging": {
                "enabled": True,
                "queue_size_kb": 10,
                "flush_on_exception": True,
                "flush_on_completion": True
            }
        }

        dl.configure(config)
        assert dl.delayed_logging_enabled is True

        # Test delayed logging method
        with patch.object(logger_adaptor, '_log_message') as mock_log:
            dl.info_delayed("Integration test message")

            # Should not call immediately (should be queued)
            mock_log.assert_not_called()

    def test_delayed_logger_disabled_with_logger_adaptor(self, logger_adaptor):
        """Test DelayedLogger disabled state with real LoggerAdaptor."""
        dl = DelayedLogger(logger_adaptor)

        # Configure as disabled
        config = {
            "delayed_logging": {
                "enabled": False
            }
        }

        dl.configure(config)
        assert dl.delayed_logging_enabled is False

        # Test that it falls back to immediate logging
        with patch.object(logger_adaptor, '_log_message') as mock_log:
            dl.info_delayed("Fallback test message")

            mock_log.assert_called_once_with('INFO', "Fallback test message")


@pytest.mark.delayed
class TestDelayedLoggerThreading:
    """Test threading behavior of DelayedLogger."""

    @pytest.fixture
    def mock_logger(self):
        """Provide a mock logger for testing."""
        logger = Mock()
        logger._log_message = Mock()
        logger._log_standard = Mock()
        logger._log_json = Mock()
        logger._log_detailed = Mock()
        return logger

    def test_background_thread_creation(self, mock_logger):
        """Test that background thread is created when delayed logging is enabled."""
        dl = DelayedLogger(mock_logger)

        config = {
            "delayed_logging": {
                "enabled": True,
                "queue_size_kb": 10
            }
        }

        dl.configure(config)

        # Check that worker thread was created
        assert hasattr(dl, '_worker_thread')
        assert dl._worker_thread is not None
        assert dl._worker_thread.is_alive()

    def test_background_thread_not_created_when_disabled(self, mock_logger):
        """Test that background thread is not created when delayed logging is disabled."""
        dl = DelayedLogger(mock_logger)

        config = {
            "delayed_logging": {
                "enabled": False
            }
        }

        dl.configure(config)

        # Check that worker thread was not created
        assert not hasattr(dl, '_worker_thread') or dl._worker_thread is None

    def test_queue_processing_with_real_entries(self, mock_logger):
        """Test queue processing with real log entries."""
        dl = DelayedLogger(mock_logger)
        dl.delayed_logging_enabled = True
        dl._initialize_queue()  # Initialize the queue

        try:
            # Configure the mock logger to not have redaction (to avoid mock complications)
            mock_logger.redaction_manager = None
            
            # Create a real log entry
            log_entry = {
                'level': 'INFO',
                'message': 'Test message',
                'kwargs': {'user_id': '123'},
                'backend': 'standard'
            }

            # Add entry to the REAL queue (not mocked)
            dl._log_queue.put(log_entry)
            
            # Verify the queue has one item
            assert dl._log_queue.qsize() == 1

            # Reset the mock to clear any previous calls
            mock_logger._log_standard.reset_mock()

                # Process the queue
            dl.flush_delayed_logs()

            # Verify the queue is now empty
            assert dl._log_queue.qsize() == 0
            
            # Verify the log was processed
            assert mock_logger._log_standard.called
            assert mock_logger._log_standard.call_count == 1
            
            # Check the first call's arguments
            call_args = mock_logger._log_standard.call_args_list[0]
            # Call args format: ((level, message), {kwargs})
            assert call_args[0][0] == 'INFO'
            assert call_args[0][1] == 'Test message'
            # Check kwargs contain user_id
            assert call_args[1].get('user_id') == '123'
        finally:
            # Cleanup
            try:
                dl.shutdown()
                if hasattr(dl, '_worker_thread') and dl._worker_thread:
                    dl._worker_thread.join(timeout=2.0)
            except Exception:
                pass
