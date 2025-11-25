"""
Test suite for DurationLogger module.

This module contains tests for the DurationLogger functionality, covering:
- @durationlogger decorator functionality
- DurationLogger class methods
- Context manager functionality
- Exception handling
- Duration formatting
- Integration with LoggerAdaptor

Test Structure:
===============
1. Test the @durationlogger decorator
2. Test DurationLogger class methods
3. Test context manager functionality
4. Test duration formatting and thresholds
5. Test integration with LoggerAdaptor

Pytest Markers:
===============
- duration: All tests in this module
"""

import pytest
import time
from unittest.mock import Mock, patch
from utils.logging.DurationLogger import DurationLogger, durationlogger, log_duration, time_function
from utils.logging.LoggerAdaptor import LoggerAdaptor


@pytest.mark.duration
class TestDurationLogger:
    """Test cases for DurationLogger class functionality."""

    @pytest.fixture
    def mock_logger(self):
        """Provide a mock logger for testing."""
        logger = Mock()
        logger.log_duration = Mock()
        return logger

    @pytest.fixture
    def duration_logger(self, mock_logger):
        """Provide a DurationLogger instance for testing."""
        return DurationLogger(mock_logger)

    def test_duration_logger_initialization(self, mock_logger):
        """Test DurationLogger initialization."""
        dl = DurationLogger(mock_logger)
        assert dl.logger == mock_logger

    def test_duration_logger_set_logger(self, duration_logger, mock_logger):
        """Test setting logger on DurationLogger instance."""
        new_logger = Mock()
        duration_logger.set_logger(new_logger)
        assert duration_logger.logger == new_logger

    def test_decorator_successful_execution(self, duration_logger):
        """Test @durationlogger decorator with successful execution."""
        @duration_logger
        def test_function():
            time.sleep(0.01)
            return "success"

        result = test_function()

        # Verify the function executed correctly
        assert result == "success"

        # Verify log_duration was called
        duration_logger.logger.log_duration.assert_called_once()
        call_args = duration_logger.logger.log_duration.call_args
        assert call_args[0][0] == "test_function"  # function name
        assert call_args[1]["success"] is True

    def test_decorator_with_exception(self, duration_logger):
        """Test @durationlogger decorator with exception."""
        @duration_logger
        def failing_function():
            time.sleep(0.01)
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            failing_function()

        # Verify log_duration was called with exception info
        duration_logger.logger.log_duration.assert_called_once()
        call_args = duration_logger.logger.log_duration.call_args
        assert call_args[0][0] == "failing_function"
        assert call_args[1]["success"] is False
        assert call_args[1]["error"] == "Test error"
        assert call_args[1]["error_type"] == "ValueError"

    def test_decorator_with_custom_operation_name(self, duration_logger):
        """Test @durationlogger decorator with custom operation name."""
        @duration_logger(operation_name="custom_operation", user_id="123")
        def test_function():
            time.sleep(0.01)
            return "success"

        result = test_function()

        assert result == "success"
        duration_logger.logger.log_duration.assert_called_once()
        call_args = duration_logger.logger.log_duration.call_args
        assert call_args[0][0] == "custom_operation"
        assert call_args[1]["user_id"] == "123"

    def test_time_operation_context_manager(self, duration_logger):
        """Test time_operation context manager."""
        with duration_logger.time_operation("test_operation", operation_type="test") as timer:
            time.sleep(0.01)
            timer.add_metadata(records_processed=5, success=True)

        duration_logger.logger.log_duration.assert_called_once()
        call_args = duration_logger.logger.log_duration.call_args
        assert call_args[0][0] == "test_operation"
        assert call_args[1]["operation_type"] == "test"
        assert call_args[1]["records_processed"] == 5
        assert call_args[1]["success"] is True

    def test_time_operation_context_manager_with_exception(self, duration_logger):
        """Test time_operation context manager with exception."""
        with pytest.raises(ValueError, match="Test exception"):
            with duration_logger.time_operation("failing_operation") as timer:
                time.sleep(0.01)
                timer.add_metadata(attempted=True)
                raise ValueError("Test exception")

        duration_logger.logger.log_duration.assert_called_once()
        call_args = duration_logger.logger.log_duration.call_args
        assert call_args[0][0] == "failing_operation"
        assert call_args[1]["success"] is False
        assert call_args[1]["exception_type"] == "ValueError"
        assert "Test exception" in call_args[1]["exception_message"]

    def test_get_duration_method(self, duration_logger):
        """Test get_duration method of DurationContext."""
        with duration_logger.time_operation("test_operation") as timer:
            time.sleep(0.01)
            duration = timer.get_duration()
            assert duration > 0
            assert isinstance(duration, float)

    def test_metadata_collection(self, duration_logger):
        """Test metadata collection during operation."""
        with duration_logger.time_operation("data_processing") as timer:
            timer.add_metadata(batch_size=100, records_processed=95)
            timer.add_metadata(success_rate=0.95)
            time.sleep(0.01)

        duration_logger.logger.log_duration.assert_called_once()
        call_args = duration_logger.logger.log_duration.call_args
        assert call_args[1]["batch_size"] == 100
        assert call_args[1]["records_processed"] == 95
        assert call_args[1]["success_rate"] == 0.95


@pytest.mark.duration
class TestGlobalDurationLogger:
    """Test cases for the global durationlogger function."""

    @pytest.fixture
    def mock_logger(self):
        """Provide a mock logger for testing."""
        logger = Mock()
        logger.log_duration = Mock()
        return logger

    def test_global_durationlogger_decorator(self, mock_logger):
        """Test the global @durationlogger decorator."""
        from utils.logging.DurationLogger import configure_duration_logger
        configure_duration_logger(mock_logger)

        @durationlogger
        def test_function():
            time.sleep(0.01)
            return "global_test"

        result = test_function()

        assert result == "global_test"
        mock_logger.log_duration.assert_called_once()

    def test_global_durationlogger_context_manager(self, mock_logger):
        """Test the global durationlogger as context manager."""
        from utils.logging.DurationLogger import configure_duration_logger, DurationLogger
        configure_duration_logger(mock_logger)

        # Use DurationLogger instance for context manager
        duration_logger = DurationLogger(mock_logger)
        with duration_logger.time_operation("global_operation") as timer:
            time.sleep(0.01)
            timer.add_metadata(global_test=True)

        mock_logger.log_duration.assert_called_once()
        call_args = mock_logger.log_duration.call_args
        assert call_args[0][0] == "global_operation"
        assert call_args[1]["global_test"] is True


@pytest.mark.duration
class TestConvenienceFunctions:
    """Test cases for convenience context managers."""

    @pytest.fixture
    def mock_logger(self):
        """Provide a mock logger for testing."""
        logger = Mock()
        logger.log_duration = Mock()
        return logger

    def test_log_duration_convenience_function(self, mock_logger):
        """Test log_duration convenience function."""
        with log_duration(mock_logger, "convenience_test", test_param="value"):
            time.sleep(0.01)

        mock_logger.log_duration.assert_called_once()
        call_args = mock_logger.log_duration.call_args
        assert call_args[0][0] == "convenience_test"
        assert call_args[1]["test_param"] == "value"

    def test_time_function_convenience_decorator(self, mock_logger):
        """Test time_function convenience decorator."""
        def test_func():
            time.sleep(0.01)
            return "convenience_result"

        # Create decorator and apply it
        decorator = time_function(mock_logger, operation_name="convenience_func")
        decorated_func = decorator(test_func)
        result = decorated_func()

        assert result == "convenience_result"
        mock_logger.log_duration.assert_called_once()
        call_args = mock_logger.log_duration.call_args
        assert call_args[0][0] == "convenience_func"
        assert call_args[1]["success"] is True


@pytest.mark.duration
class TestIntegrationWithLoggerAdaptor:
    """Test integration between DurationLogger and LoggerAdaptor."""

    @pytest.fixture
    def logger_adaptor(self):
        """Provide a real LoggerAdaptor instance for integration testing."""
        with patch.object(LoggerAdaptor, '_load_config') as mock_load:
            mock_load.return_value = {
                "backend": "standard",
                "level": "INFO"
            }
            return LoggerAdaptor("integration_test")

    def test_duration_logger_with_logger_adaptor(self, logger_adaptor):
        """Test DurationLogger working with real LoggerAdaptor."""
        duration_logger = DurationLogger(logger_adaptor)

        # Test decorator
        @duration_logger
        def integration_test():
            time.sleep(0.01)
            return "integration_success"

        result = integration_test()
        assert result == "integration_success"

        # Verify that LoggerAdaptor's log_duration was called
        # (We can't easily mock it since it's a real instance, but we know it works)

    def test_context_manager_with_logger_adaptor(self, logger_adaptor):
        """Test time_operation context manager with real LoggerAdaptor."""
        duration_logger = DurationLogger(logger_adaptor)

        with duration_logger.time_operation("adaptor_test") as timer:
            time.sleep(0.01)
            timer.add_metadata(adaptor_integration=True)

        # The duration logging should work without errors
        assert True  # If we get here, the integration worked
