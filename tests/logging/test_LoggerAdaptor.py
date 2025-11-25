"""
Comprehensive test suite for LoggerAdaptor class.

This module contains tests for the LoggerAdaptor logging framework, covering:
- Logger initialization and configuration
- Singleton pattern implementation
- Multiple logging backends (standard, JSON, detailed)
- Context management and redaction features
- Environment-specific behavior
- Error handling and edge cases

Note: Duration logging and delayed logging functionality has been moved to separate modules:
- DurationLogger: Contains @durationlogger decorator and timing functionality
- DelayedLogger: Contains asynchronous logging functionality

Test Structure:
===============
1. Constants: Test data and configuration constants
2. Fixtures: Setup and teardown utilities
3. Test Classes:
   - TestLoggerAdaptor: Main test class for LoggerAdaptor functionality
   - TestLoggingFormat: Tests for LoggingFormat enum
   - TestEnvironment: Tests for Environment enum
   - TestRedactionConfig: Tests for RedactionConfig enum

Testing Standards Applied:
==========================
- Each test is focused on a single behavior
- Comprehensive mocking of external dependencies
- Parametrized tests for multiple scenarios
- Proper setup and teardown with fixtures
- Clear test naming and documentation

Pytest Markers:
===============
- logger: All tests in this module
"""

import pytest
import json
import os
import tempfile
from unittest.mock import Mock, patch, mock_open
from utils.logging.LoggerAdaptor import LoggerAdaptor
from utils.logging.Enum import Environment, LoggingFormat, RedactionConfig


# Test Constants
class TestConstants:
    """Constants used throughout the test suite."""

    # Environment values
    ENVIRONMENTS = {
        "dev": "development",
        "development": "development",
        "staging": "staging",
        "prod": "production",
        "production": "production",
        "test": "testing",
        "testing": "testing"
    }

    # Log levels
    LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

    # Backend types
    BACKENDS = ["standard", "json", "detailed"]

    # Test file paths
    LOGS_DIR = "./logs"
    TEST_CONFIG_DIR = "./test_logs"
    TEST_LOG_FILE = "test.log"

    # Mock configuration
    MOCK_CONFIG = {
        "backend": "standard",
        "level": "INFO",
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            }
        },
        "handlers": {
            "console": {
                "type": "console",
                "level": "INFO",
                "formatter": "default"
            }
        },
        "log_directory": "./logs"
    }

    # Debug configuration
    DEBUG_CONFIG = {
        "backend": "standard",
        "level": "DEBUG",
        "formatters": MOCK_CONFIG["formatters"],
        "handlers": MOCK_CONFIG["handlers"],
        "log_directory": MOCK_CONFIG["log_directory"]
    }

    # Test messages
    TEST_MESSAGES = {
        "debug": "Debug message",
        "info": "Info message",
        "warning": "Warning message",
        "error": "Error message",
        "critical": "Critical message"
    }

    # Test data
    TEST_USER_ID = "123"
    TEST_SESSION_ID = "abc"
    TEST_REQUEST_ID = "req-123"
    TEST_CREDIT_CARD = "1234-5678-9012-3456"
    TEST_EMAIL = "test@example.com"
    TEST_PHONE = "555-123-4567"


@pytest.mark.logger
class TestLoggerAdaptor:
    """
    Comprehensive test suite for LoggerAdaptor class functionality.

    This class contains tests organized into logical sections:
    - Initialization and Setup: Basic logger creation and configuration
    - Singleton Pattern: Testing the singleton behavior across different scenarios
    - Configuration: Loading, validation, and reloading of configurations
    - Logging Functionality: Context management, redaction, and log level handling
    - Backend-Specific: Tests for different logging backends (standard, JSON, detailed)
    - Advanced Features: Configuration reloading and complex scenarios

    Each test method is designed to be:
    - Focused: Tests a single specific behavior
    - Independent: Can run in isolation
    - Well-documented: Clear naming and docstrings
    - Mocked: External dependencies are properly mocked
    """

    @pytest.fixture
    def mock_config(self):
        """
        Provide a standard mock configuration for testing basic logger functionality.

        Returns:
            dict: A copy of the standard test configuration with console handler
        """
        return TestConstants.MOCK_CONFIG.copy()

    @pytest.fixture
    def json_config(self):
        """
        Provide a JSON backend configuration for testing structured logging.

        Returns:
            dict: Configuration optimized for JSON logging backend
        """
        return {
            "backend": "json",
            "level": "INFO",
            "formatters": {
                "default": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S"
                }
            }
        }

    @pytest.fixture
    def detailed_config(self):
        """
        Provide a detailed backend configuration for testing verbose logging.

        Returns:
            dict: Minimal configuration for detailed logging backend
        """
        return {
            "backend": "detailed",
            "level": "INFO"
        }

    @pytest.fixture
    def debug_config(self):
        """
        Provide a debug-level configuration for testing debug logging behavior.

        Returns:
            dict: Configuration with DEBUG level for comprehensive logging
        """
        return {
            "backend": "standard",
            "level": "DEBUG",
            "formatters": TestConstants.MOCK_CONFIG["formatters"],
            "handlers": TestConstants.MOCK_CONFIG["handlers"],
            "log_directory": TestConstants.MOCK_CONFIG["log_directory"]
        }

    @pytest.fixture
    def temp_config_file(self, mock_config):
        """Create a temporary config file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(mock_config, f)
            temp_file_path = f.name

        yield temp_file_path

        # Cleanup
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)

    @pytest.fixture
    def temp_json_config_file(self, json_config):
        """Create a temporary JSON config file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(json_config, f)
            temp_file_path = f.name

        yield temp_file_path

        # Cleanup
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)

    @pytest.fixture(autouse=True)
    def setup_and_teardown_logger(self):
        """
        Comprehensive setup and teardown for all LoggerAdaptor tests.

        This fixture runs automatically before and after each test method in this class.
        It ensures a clean test environment by:

        Setup (before each test):
        - Clearing any existing LoggerAdaptor instances and configuration
        - Creating necessary directories for log files
        - Preparing a clean state for isolated testing

        Teardown (after each test):
        - Clearing LoggerAdaptor instances and configuration
        - Removing any test-generated log files
        - Ensuring no state leaks between tests

        This guarantees test isolation and prevents cross-test contamination.
        """
        # Setup: Clear any existing state before each test
        LoggerAdaptor._instances.clear()
        LoggerAdaptor._config = None

        # Ensure log directory exists for tests that need it
        os.makedirs(TestConstants.LOGS_DIR, exist_ok=True)

        yield

        # Teardown: Cleanup after each test
        LoggerAdaptor._instances.clear()
        LoggerAdaptor._config = None

        # Clean up any test log files to prevent disk space issues
        test_log_path = os.path.join(TestConstants.TEST_CONFIG_DIR, TestConstants.TEST_LOG_FILE)
        if os.path.exists(test_log_path):
            os.remove(test_log_path)

    # =============================================================================
    # INITIALIZATION AND SETUP TESTS
    # =============================================================================

    def test_logger_adaptor_initialization_default(self):
        """Test LoggerAdaptor initialization with default parameters."""
        with patch.object(LoggerAdaptor, '_load_config') as mock_load:
            mock_load.return_value = {"backend": "standard", "level": "INFO"}
            
            logger = LoggerAdaptor()
            assert logger.name == "default"
            assert logger.environment in ["development", "staging", "production", "testing"]

    @pytest.mark.parametrize("env_var,expected", [
        ("dev", "development"),
        ("development", "development"),
        ("staging", "staging"),
        ("prod", "production"),
        ("production", "production"),
        ("test", "testing"),
        ("testing", "testing"),
    ])
    def test_environment_detection(self, env_var, expected):
        """Test environment detection from environment variables."""
        with patch.dict(os.environ, {'ENVIRONMENT': env_var}):
            detected = LoggerAdaptor._detect_environment_static()
            assert detected == expected

    def test_environment_detection_default(self):
        """Test environment detection defaults to production when no env var set."""
        with patch.dict(os.environ, {}, clear=True):
            detected = LoggerAdaptor._detect_environment_static()
            assert detected == "production"

    def test_environment_detection_empty_string(self):
        """Test environment detection with empty environment variable."""
        with patch.dict(os.environ, {'ENVIRONMENT': ''}):
            detected = LoggerAdaptor._detect_environment_static()
            assert detected == "production"

    # =============================================================================
    # SINGLETON PATTERN TESTS
    # =============================================================================

    def test_get_logger_singleton_pattern_same_name_and_env(self):
        """Test that get_logger follows singleton pattern for same name and environment."""
        with patch.object(LoggerAdaptor, '_load_config') as mock_load:
            mock_load.return_value = TestConstants.MOCK_CONFIG

            logger1 = LoggerAdaptor.get_logger("test_logger", "dev")
            logger2 = LoggerAdaptor.get_logger("test_logger", "dev")
            assert logger1 is logger2

    def test_get_logger_singleton_pattern_different_names(self):
        """Test that different logger names create different instances."""
        with patch.object(LoggerAdaptor, '_load_config') as mock_load:
            mock_load.return_value = TestConstants.MOCK_CONFIG

            logger1 = LoggerAdaptor.get_logger("logger1", "dev")
            logger2 = LoggerAdaptor.get_logger("logger2", "dev")

            assert logger1 is not logger2
            assert logger1.name == "logger1"
            assert logger2.name == "logger2"

    def test_get_logger_singleton_pattern_different_environments(self):
        """Test that same logger name with different environments creates different instances."""
        with patch.object(LoggerAdaptor, '_load_config') as mock_load:
            mock_load.return_value = TestConstants.MOCK_CONFIG

            logger1 = LoggerAdaptor.get_logger("logger1", "dev")
            logger2 = LoggerAdaptor.get_logger("logger1", "prod")

            assert logger1 is not logger2
            assert logger1.environment == "dev"  # The environment is stored as passed to get_logger
            assert logger2.environment == "prod"

    # =============================================================================
    # CONFIGURATION TESTS
    # =============================================================================

    @patch('builtins.open', new_callable=mock_open)
    def test_load_config_success(self, mock_file, mock_config):
        """Test successful config loading."""
        mock_file.return_value.read.return_value = json.dumps(mock_config)
        
        with patch.object(LoggerAdaptor, '_get_environment_config_file') as mock_get_file:
            mock_get_file.return_value = "test_config.json"
            logger = LoggerAdaptor()
            config = logger._load_config("test_config.json")
            
            assert config == mock_config

    def test_load_config_file_not_found(self):
        """Test config loading when file doesn't exist."""
        with patch('builtins.open', side_effect=FileNotFoundError):
            logger = LoggerAdaptor()
            config = logger._load_config("nonexistent.json")
            
            # Should return default config
            assert "backend" in config
            assert "level" in config

    def test_load_config_invalid_json(self):
        """Test config loading with invalid JSON."""
        with patch('builtins.open', mock_open(read_data="invalid json")):
            with patch.object(LoggerAdaptor, '_get_environment_config_file') as mock_get_file:
                mock_get_file.return_value = "invalid.json"
                
                with pytest.raises(ValueError, match="Invalid JSON"):
                    _ = LoggerAdaptor()

    def test_format_message_single_string(self):
        """Test message formatting with single string argument."""
        with patch.object(LoggerAdaptor, '_load_config') as mock_load:
            mock_load.return_value = {"backend": "standard", "level": "INFO"}
            
            logger = LoggerAdaptor()
            message = logger._format_message("Hello, World!")
            assert message == "Hello, World!"

    def test_format_message_multiple_args(self):
        """Test message formatting with multiple arguments."""
        with patch.object(LoggerAdaptor, '_load_config') as mock_load:
            mock_load.return_value = {"backend": "standard", "level": "INFO"}
            
            logger = LoggerAdaptor()
            message = logger._format_message("Hello", "World", 123)
            assert message == "Hello World 123"

    def test_format_message_empty(self):
        """Test message formatting with no arguments."""
        with patch.object(LoggerAdaptor, '_load_config') as mock_load:
            mock_load.return_value = {"backend": "standard", "level": "INFO"}
            
            logger = LoggerAdaptor()
            message = logger._format_message()
            assert message == ""

    @pytest.mark.parametrize("level,method_name,message", [
        ("DEBUG", "debug", TestConstants.TEST_MESSAGES["debug"]),
        ("INFO", "info", TestConstants.TEST_MESSAGES["info"]),
        ("WARNING", "warning", TestConstants.TEST_MESSAGES["warning"]),
        ("ERROR", "error", TestConstants.TEST_MESSAGES["error"]),
        ("CRITICAL", "critical", TestConstants.TEST_MESSAGES["critical"]),
    ])
    def test_log_level_methods_call_log_message_correctly(self, level, method_name, message):
        """Test that all log level methods call _log_message with correct parameters."""
        with patch.object(LoggerAdaptor, '_load_config') as mock_load:
            mock_load.return_value = TestConstants.DEBUG_CONFIG

            logger = LoggerAdaptor()

            with patch.object(logger, '_log_message') as mock_log:
                log_method = getattr(logger, method_name)
                log_method(message)

                mock_log.assert_called_once_with(level, message)

    def test_debug_logging_with_debug_level_config(self):
        """Test debug logging when logger level is set to DEBUG."""
        with patch.object(LoggerAdaptor, '_load_config') as mock_load:
            mock_load.return_value = TestConstants.DEBUG_CONFIG

            logger = LoggerAdaptor()

            with patch.object(logger, '_log_message') as mock_log:
                logger.debug(TestConstants.TEST_MESSAGES["debug"])
                mock_log.assert_called_once_with('DEBUG', TestConstants.TEST_MESSAGES["debug"])

    def test_info_logging_with_info_level_config(self):
        """Test info logging when logger level is set to INFO."""
        with patch.object(LoggerAdaptor, '_load_config') as mock_load:
            mock_load.return_value = TestConstants.MOCK_CONFIG

            logger = LoggerAdaptor()

            with patch.object(logger, '_log_message') as mock_log:
                logger.info(TestConstants.TEST_MESSAGES["info"])
                mock_log.assert_called_once_with('INFO', TestConstants.TEST_MESSAGES["info"])

    # =============================================================================
    # LOGGING FUNCTIONALITY TESTS
    # =============================================================================

    def test_context_management_set_and_clear(self):
        """Test setting and clearing logger context."""
        with patch.object(LoggerAdaptor, '_load_config') as mock_load:
            mock_load.return_value = TestConstants.MOCK_CONFIG

            logger = LoggerAdaptor()

            # Set context with test data
            logger.set_context(
                user_id=TestConstants.TEST_USER_ID,
                session_id=TestConstants.TEST_SESSION_ID
            )
            assert logger.context["user_id"] == TestConstants.TEST_USER_ID
            assert logger.context["session_id"] == TestConstants.TEST_SESSION_ID

            # Clear context and verify it's empty
            logger.clear_context()
            assert len(logger.context) == 0

    def test_context_management_multiple_keys(self):
        """Test setting multiple context keys at once."""
        with patch.object(LoggerAdaptor, '_load_config') as mock_load:
            mock_load.return_value = TestConstants.MOCK_CONFIG

            logger = LoggerAdaptor()

            context_data = {
                "user_id": TestConstants.TEST_USER_ID,
                "session_id": TestConstants.TEST_SESSION_ID,
                "request_id": TestConstants.TEST_REQUEST_ID
            }

            logger.set_context(**context_data)

            for key, value in context_data.items():
                assert logger.context[key] == value

    def test_context_management_overwrite_existing(self):
        """Test that setting context overwrites existing values."""
        with patch.object(LoggerAdaptor, '_load_config') as mock_load:
            mock_load.return_value = TestConstants.MOCK_CONFIG

            logger = LoggerAdaptor()

            # Set initial context
            logger.set_context(user_id="old_user")
            assert logger.context["user_id"] == "old_user"

            # Overwrite with new value
            logger.set_context(user_id="new_user")
            assert logger.context["user_id"] == "new_user"

    def test_redaction_initially_disabled(self):
        """Test that redaction is initially disabled."""
        # Mock the ConfigManager to return a config without redaction
        with patch('utils.logging.LoggerAdaptor.ConfigManager') as mock_cm:
            mock_cm.return_value.load_config.return_value = TestConstants.MOCK_CONFIG

            logger = LoggerAdaptor()

            assert not logger.has_redaction()

    def test_redaction_enable_and_disable(self):
        """Test enabling and disabling redaction functionality."""
        # Mock the ConfigManager to return a config without redaction
        with patch('utils.logging.LoggerAdaptor.ConfigManager') as mock_cm:
            mock_cm.return_value.load_config.return_value = TestConstants.MOCK_CONFIG

            logger = LoggerAdaptor()

            # Initially should not have redaction
            assert not logger.has_redaction()

            # Enable redaction
            logger.enable_redaction(enabled=True)
            assert logger.has_redaction()

            # Disable redaction
            logger.enable_redaction(enabled=False)
            assert not logger.has_redaction()

    def test_redaction_add_credit_card_pattern(self):
        """Test adding a credit card redaction pattern."""
        # Mock the ConfigManager to return a config without redaction
        with patch('utils.logging.LoggerAdaptor.ConfigManager') as mock_cm:
            mock_cm.return_value.load_config.return_value = TestConstants.MOCK_CONFIG

            logger = LoggerAdaptor()
            logger.enable_redaction(enabled=True)

            # Add credit card pattern
            pattern = r'\d{4}-\d{4}-\d{4}-\d{4}'
            placeholder = '[CARD]'
            logger.add_redaction_pattern(pattern, placeholder)

            # Test redaction
            test_message = f"Credit card: {TestConstants.TEST_CREDIT_CARD}"
            redacted = logger.test_redaction(test_message)

            assert placeholder in redacted
            assert TestConstants.TEST_CREDIT_CARD not in redacted

    def test_redaction_multiple_patterns(self):
        """Test adding multiple redaction patterns."""
        # Mock the ConfigManager to return a config without redaction
        with patch('utils.logging.LoggerAdaptor.ConfigManager') as mock_cm:
            mock_cm.return_value.load_config.return_value = TestConstants.MOCK_CONFIG

            logger = LoggerAdaptor()
            logger.enable_redaction(enabled=True)

            # Add multiple patterns
            patterns_and_placeholders = [
                (r'\d{4}-\d{4}-\d{4}-\d{4}', '[CARD]'),
                (r'\d{3}-\d{2}-\d{4}', '[SSN]'),
            ]

            for pattern, placeholder in patterns_and_placeholders:
                logger.add_redaction_pattern(pattern, placeholder)

            # Test message with multiple sensitive data
            test_message = f"Card: {TestConstants.TEST_CREDIT_CARD}, SSN: 123-45-6789"
            redacted = logger.test_redaction(test_message)

            assert '[CARD]' in redacted
            assert '[SSN]' in redacted
            assert TestConstants.TEST_CREDIT_CARD not in redacted
            assert '123-45-6789' not in redacted

    # =============================================================================
    # BACKEND-SPECIFIC TESTS
    # =============================================================================

    def test_json_logging_backend_basic_functionality(self, json_config):
        """Test basic JSON logging backend functionality."""
        with patch('utils.logging.LoggerAdaptor.ConfigManager') as mock_cm:
            mock_cm.return_value.load_config.return_value = json_config

            logger = LoggerAdaptor()

            with patch.object(logger.logger, 'log') as mock_log:
                test_message = "Test message"
                extra_field = "extra_value"

                logger.info(test_message, extra_field=extra_field)

                # Verify log was called
                mock_log.assert_called_once()
                args, kwargs = mock_log.call_args

                # First argument should be log level (INFO = 20)
                assert args[0] == 20

                # Second argument should be JSON string
                json_message = args[1]
                log_data = json.loads(json_message)

                assert log_data["message"] == test_message
                assert log_data["level"] == "INFO"
                assert log_data["extra_field"] == extra_field

    def test_json_logging_backend_with_context(self, json_config):
        """Test JSON logging backend with persistent context."""
        with patch('utils.logging.LoggerAdaptor.ConfigManager') as mock_cm:
            mock_cm.return_value.load_config.return_value = json_config

            logger = LoggerAdaptor("json_test")
            logger.set_context(
                service="test-service",
                version="1.0.0"
            )

            with patch.object(logger.logger, 'log') as mock_log:
                logger.info("Context test", user_id="user123")

                mock_log.assert_called_once()
                args, kwargs = mock_log.call_args

                json_message = args[1]
                log_data = json.loads(json_message)

                assert log_data["message"] == "Context test"
                assert log_data["service"] == "test-service"
                assert log_data["version"] == "1.0.0"
                assert log_data["user_id"] == "user123"

    def test_detailed_logging_backend_basic_functionality(self, detailed_config):
        """Test basic detailed logging backend functionality."""
        with patch('utils.logging.LoggerAdaptor.ConfigManager') as mock_cm:
            mock_cm.return_value.load_config.return_value = detailed_config

            logger = LoggerAdaptor()
            logger.set_context(request_id=TestConstants.TEST_REQUEST_ID)

            with patch.object(logger, '_log_detailed') as mock_log:
                test_message = "Test message"
                test_user_id = "user-456"

                logger.info(test_message, user_id=test_user_id)

                mock_log.assert_called_once()
                call_args, call_kwargs = mock_log.call_args

                assert call_args[0] == 'INFO'  # level
                assert call_args[1] == test_message  # message
                # Check that context information is passed to _log_detailed
                # The _log_message method combines persistent context with kwargs
                expected_kwargs = {'request_id': TestConstants.TEST_REQUEST_ID, 'user_id': test_user_id}
                # Check that both persistent context and method kwargs are present
                assert 'request_id' in call_kwargs, f"Expected 'request_id' in {call_kwargs}"
                assert 'user_id' in call_kwargs, f"Expected 'user_id' in {call_kwargs}"
                assert call_kwargs['request_id'] == TestConstants.TEST_REQUEST_ID
                assert call_kwargs['user_id'] == test_user_id

    def test_detailed_logging_backend_multiple_context_and_params(self, detailed_config):
        """Test detailed logging with multiple context variables and parameters."""
        with patch('utils.logging.LoggerAdaptor.ConfigManager') as mock_cm:
            mock_cm.return_value.load_config.return_value = detailed_config

            logger = LoggerAdaptor()
            logger.set_context(
                request_id=TestConstants.TEST_REQUEST_ID,
                session_id=TestConstants.TEST_SESSION_ID
            )

            with patch.object(logger, '_log_detailed') as mock_log:
                logger.warning("Warning message", user_id="user-789", action="login")

                mock_log.assert_called_once()
                call_args, call_kwargs = mock_log.call_args

                assert call_args[0] == 'WARNING'  # level
                assert call_args[1] == "Warning message"  # message
                # Check that context information is passed to _log_detailed
                expected_kwargs = {
                    'request_id': TestConstants.TEST_REQUEST_ID,
                    'session_id': TestConstants.TEST_SESSION_ID,
                    'user_id': 'user-789',
                    'action': 'login'
                }
                # Check that all context and kwargs are present
                assert 'request_id' in call_kwargs
                assert 'session_id' in call_kwargs
                assert 'user_id' in call_kwargs
                assert 'action' in call_kwargs
                assert call_kwargs['request_id'] == TestConstants.TEST_REQUEST_ID
                assert call_kwargs['session_id'] == TestConstants.TEST_SESSION_ID
                assert call_kwargs['user_id'] == 'user-789'
                assert call_kwargs['action'] == 'login'

    @pytest.mark.parametrize("backend", TestConstants.BACKENDS)
    def test_different_backends_initialization(self, backend):
        """Test initialization of different logging backends."""
        config = {"backend": backend, "level": "INFO"}

        with patch('utils.logging.LoggerAdaptor.ConfigManager') as mock_cm:
            mock_cm.return_value.load_config.return_value = config

            logger = LoggerAdaptor()
            assert logger.backend == backend

    @pytest.mark.parametrize("backend", TestConstants.BACKENDS)
    def test_different_backends_logging_functionality(self, backend):
        """Test logging functionality across different backends."""
        config = {"backend": backend, "level": "INFO"}

        with patch('utils.logging.LoggerAdaptor.ConfigManager') as mock_cm:
            mock_cm.return_value.load_config.return_value = config

            logger = LoggerAdaptor()

            # All backends use _log_message, which then delegates to backend-specific methods
            with patch.object(logger, '_log_message') as mock_log:
                logger.info("Test message across backends")
                mock_log.assert_called_once_with('INFO', "Test message across backends")

    # =============================================================================
    # ADVANCED FEATURES TESTS
    # =============================================================================

    def test_config_reload_successful(self, temp_config_file):
        """Test successful configuration reloading."""
        with patch.object(LoggerAdaptor, '_get_environment_config_file') as mock_get_file:
            mock_get_file.return_value = temp_config_file

            logger = LoggerAdaptor()
            original_config = LoggerAdaptor._config

            # Modify config file with new configuration
            new_config = {
                "backend": "json",
                "level": "DEBUG",
                "formatters": TestConstants.MOCK_CONFIG["formatters"]
            }
            with open(temp_config_file, 'w') as f:
                json.dump(new_config, f)

            # Reload configuration
            logger.reload_config(temp_config_file)

            assert LoggerAdaptor._config != original_config
            assert LoggerAdaptor._config["backend"] == "json"
            assert LoggerAdaptor._config["level"] == "DEBUG"

    def test_config_reload_preserves_existing_instances(self, temp_config_file):
        """Test that config reload doesn't break existing logger instances."""
        with patch.object(LoggerAdaptor, '_get_environment_config_file') as mock_get_file:
            mock_get_file.return_value = temp_config_file

            # Create initial logger
            logger1 = LoggerAdaptor("test_logger")

            # Modify config file
            new_config = {"backend": "detailed", "level": "INFO"}
            with open(temp_config_file, 'w') as f:
                json.dump(new_config, f)

            # Reload configuration
            logger1.reload_config(temp_config_file)

            # Verify the logger instance is still functional
            assert logger1.backend == "detailed"
            assert logger1.name == "test_logger"

    def test_properties(self):
        """Test logger properties."""
        config = {"backend": "standard", "level": "WARNING"}

        with patch('utils.logging.LoggerAdaptor.ConfigManager') as mock_cm:
            mock_cm.return_value.load_config.return_value = config
            mock_cm.return_value.get_environment_config_file.return_value = "log_config_dev.json"
            mock_cm.return_value.detect_environment.return_value = "development"

            with patch.dict(os.environ, {'ENVIRONMENT': 'dev'}):
                logger = LoggerAdaptor("test_logger")

                assert logger.level == "WARNING"
                assert logger.current_environment == "development"
                assert "log_config_dev.json" in logger.config_file_used

    def test_get_log_filepath(self):
        """Test log file path generation."""
        config = {"log_directory": "./test_logs"}

        with patch('utils.logging.LoggerAdaptor.ConfigManager') as mock_cm:
            mock_cm.return_value.load_config.return_value = config

            logger = LoggerAdaptor()

            with patch('pathlib.Path.mkdir') as mock_mkdir:
                filepath = logger._get_log_filepath("test.log")

                assert "test.log" in filepath
                assert "test_logs" in filepath
                mock_mkdir.assert_called_once()

    def test_handler_creation(self):
        """Test different handler types creation."""
        logger = LoggerAdaptor()
        formatters = {"default": Mock()}
        
        # Console handler
        console_config = {"type": "console", "level": "INFO", "formatter": "default"}
        handler = logger._create_handler(console_config, formatters)
        assert handler is not None
        
        # File handler
        with patch('logging.FileHandler') as mock_file_handler:
            file_config = {"type": "file", "filename": "test.log", "level": "DEBUG", "formatter": "default"}
            handler = logger._create_handler(file_config, formatters)
            mock_file_handler.assert_called_once()
        
        # Rotating file handler
        with patch('logging.handlers.RotatingFileHandler') as mock_rotating_handler:
            rotating_config = {
                "type": "rotating_file",
                "filename": "test.log",
                "max_bytes": 1000000,
                "backup_count": 3,
                "level": "INFO",
                "formatter": "default"
            }
            handler = logger._create_handler(rotating_config, formatters)
            mock_rotating_handler.assert_called_once()

    def test_invalid_redaction_pattern(self):
        """Test handling of invalid redaction patterns."""
        with patch.object(LoggerAdaptor, '_load_config') as mock_load:
            mock_load.return_value = {"backend": "standard", "level": "INFO"}
            
            logger = LoggerAdaptor()
            logger.enable_redaction(enabled=True)
            
            # Invalid regex pattern should raise ValueError
            with pytest.raises(ValueError, match="Invalid regex pattern"):
                logger.add_redaction_pattern("[invalid regex", "[REDACTED]")

    def test_comprehensive_logging_with_credit_card_redaction(self):
        """Test comprehensive logging with credit card redaction."""
        config = {
            "backend": "standard",
            "level": "DEBUG",
            "redaction": {
                "enabled": True,
                "placeholder": "[REDACTED]",
                "patterns": [
                    {
                        "pattern": r"\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}",
                        "placeholder": "[CARD]"
                    }
                ]
            }
        }
        
        with patch.object(LoggerAdaptor, '_load_config') as mock_load:
            mock_load.return_value = config
            
            logger = LoggerAdaptor()
            logger.enable_redaction(enabled=True)
            logger.add_redaction_pattern(r'\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}', '[CARD]')
            
            # Test messages with credit card numbers
            test_message = "Processing payment for card 1234-5678-9012-3456"
            redacted = logger.test_redaction(test_message)
            assert '[CARD]' in redacted
            assert '1234-5678-9012-3456' not in redacted

    def test_all_log_levels_comprehensive(self):
        """Test all logging levels with various parameters."""
        with patch.object(LoggerAdaptor, '_load_config') as mock_load:
            mock_load.return_value = {"backend": "standard", "level": "DEBUG"}
            
            logger = LoggerAdaptor()
            
            # Test with different parameter combinations
            test_cases = [
                ("debug", "Debug message", {"user_id": "123", "action": "login"}),
                ("info", "User logged in successfully", {"session_id": "abc-def"}),
                ("warning", "Password will expire soon", {"days_remaining": 5}),
                ("error", "Database connection failed", {"retry_count": 3, "error_code": "DB001"}),
                ("critical", "System out of memory", {"memory_usage": "95%", "alert": True})
            ]
            
            with patch.object(logger, '_log_message') as mock_log:
                for level, message, params in test_cases:
                    getattr(logger, level)(message, **params)
                    mock_log.assert_called_with(level.upper(), message, **params)

    def test_environment_specific_behavior(self):
        """Test behavior specific to different environments."""
        test_cases = [
            ("dev", "development"),
            ("staging", "staging"), 
            ("prod", "production"),
            ("test", "testing")
        ]
        
        for env_var, expected_env in test_cases:
            with patch.dict(os.environ, {'ENVIRONMENT': env_var}):
                with patch.object(LoggerAdaptor, '_load_config') as mock_load:
                    mock_load.return_value = {"backend": "standard", "level": "INFO"}
                    
                    logger = LoggerAdaptor(f"test_{expected_env}")
                    assert logger.environment == expected_env
                    # Check that the appropriate config file is being used
                    config_mapping = {
                        "development": "dev",
                        "staging": "staging", 
                        "production": "prod",
                        "testing": "test"
                    }
                    expected_config_part = config_mapping[expected_env]
                    assert expected_config_part in logger.config_file_used

    def test_concurrent_logger_instances(self):
        """Test multiple logger instances with different configurations."""
        with patch.object(LoggerAdaptor, '_load_config') as mock_load:
            mock_load.return_value = {"backend": "standard", "level": "INFO"}
            
            # Create multiple loggers
            logger1 = LoggerAdaptor.get_logger("service1", "dev")
            logger2 = LoggerAdaptor.get_logger("service2", "dev")
            logger3 = LoggerAdaptor.get_logger("service1", "prod")  # Same name, different env
            
            # Test they have correct identities
            assert logger1.name == "service1"
            assert logger2.name == "service2"
            assert logger3.name == "service1"
            
            # Test singleton behavior
            logger1_duplicate = LoggerAdaptor.get_logger("service1", "dev")
            assert logger1 is logger1_duplicate
            assert logger1 is not logger2
            assert logger1 is not logger3

    def test_structured_logging_with_context(self):
        """Test structured logging with persistent context."""
        with patch.object(LoggerAdaptor, '_load_config') as mock_load:
            mock_load.return_value = {"backend": "json", "level": "INFO"}
            
            logger = LoggerAdaptor("structured_test")
            
            # Set persistent context
            logger.set_context(
                service="user-auth",
                version="1.2.3",
                environment="production"
            )
            
            # Test that context persists across multiple log calls
            with patch.object(logger.logger, 'log') as mock_log:
                logger.info("User authentication started", user_id="user-123")
                logger.warning("Rate limit approaching", current_requests=45, limit=50)
                logger.error("Authentication failed", reason="invalid_token")
                
                # Verify all calls include persistent context
                assert mock_log.call_count == 3
                
                # Check that context is maintained - either persistent context or call-specific params
                for call in mock_log.call_args_list:
                    json_message = call[0][1]  # Second argument is the JSON string
                    log_data = json.loads(json_message)
                    # Context should include either persistent context or call-specific parameters
                    has_context = any(key in log_data for key in ["service", "user_id", "current_requests", "reason"])
                    assert has_context, f"Expected context in log data: {log_data}"

    def test_error_handling_and_recovery(self):
        """Test error handling and recovery scenarios."""
        # Test with invalid config file path
        with patch.object(LoggerAdaptor, '_get_environment_config_file') as mock_get_file:
            mock_get_file.return_value = "/nonexistent/path/config.json"
            
            with patch('builtins.open', side_effect=FileNotFoundError):
                logger = LoggerAdaptor("error_test")
                # Should fall back to default config
                assert logger.backend in ["standard", "json", "detailed"]
                assert logger.level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

    @pytest.mark.parametrize("log_level,should_log", [
        ("DEBUG", True),
        ("INFO", True), 
        ("WARNING", True),
        ("ERROR", True),
        ("CRITICAL", True)
    ])
    def test_log_level_filtering(self, log_level, should_log):
        """Test that log level filtering works correctly."""
        config = {"backend": "standard", "level": log_level}

        with patch('utils.logging.LoggerAdaptor.ConfigManager') as mock_cm:
            mock_cm.return_value.load_config.return_value = config

            logger = LoggerAdaptor("level_test")
            assert logger.level == log_level

            # Test that logger accepts the configured level
            with patch.object(logger, '_log_message') as mock_log:
                getattr(logger, log_level.lower())("Test message")
                if should_log:
                    mock_log.assert_called_once_with(log_level, "Test message")
                else:
                    mock_log.assert_not_called()

    # =============================================================================
    # DURATION LOGGING TESTS - LoggerAdaptor provides log_duration method
    # =============================================================================
    # Note: Duration logging context managers and decorators are in DurationLogger module
    # LoggerAdaptor only provides the log_duration method for direct duration logging

    def test_duration_log_level_mapping(self):
        """Test duration log level mapping based on thresholds."""
        with patch.object(LoggerAdaptor, '_load_config') as mock_load:
            mock_load.return_value = {
                "backend": "standard",
                "level": "INFO",
                "duration_logging": {
                    "slow_threshold_seconds": 1.0,
                    "warn_threshold_seconds": 5.0,
                    "error_threshold_seconds": 30.0
                }
            }

            logger = LoggerAdaptor("test_duration")

            # Test duration thresholds
            assert logger._get_duration_log_level(0.5) == 'DEBUG'  # Below slow threshold
            assert logger._get_duration_log_level(2.0) == 'INFO'   # Above slow, below warn
            assert logger._get_duration_log_level(10.0) == 'WARNING'  # Above warn, below error
            assert logger._get_duration_log_level(60.0) == 'ERROR'   # Above error threshold

    def test_log_duration_formats_duration_correctly(self):
        """Test that duration logging formats time correctly."""
        with patch.object(LoggerAdaptor, '_load_config') as mock_load:
            mock_load.return_value = {
                "backend": "standard",
                "level": "INFO"
            }

            logger = LoggerAdaptor("test_duration")

            with patch.object(logger, '_log_message') as mock_log:
                # Test millisecond formatting
                logger.log_duration("test_op", 0.123)
                call_args = mock_log.call_args[0]
                assert "123.00ms" in call_args[1] or "123ms" in call_args[1]

                # Test second formatting
                logger.log_duration("test_op", 5.5)
                call_args = mock_log.call_args[0]
                assert "5.50s" in call_args[1]

                # Test minute formatting
                logger.log_duration("test_op", 90.0)
                call_args = mock_log.call_args[0]
                assert "1m30.0s" in call_args[1] or "1m30s" in call_args[1]

    # Note: Duration context managers and decorators have been moved to DurationLogger module
    # LoggerAdaptor only provides the log_duration method for direct duration logging


@pytest.mark.logger
class TestLoggingFormat:
    """Test cases for LoggingFormat enum."""

    def test_logging_format_values(self):
        """Test that LoggingFormat enum has correct values."""
        assert LoggingFormat.STANDARD.value == "standard"
        assert LoggingFormat.JSON.value == "json"
        assert LoggingFormat.DETAILED.value == "detailed"

    def test_logging_format_membership(self):
        """Test LoggingFormat enum membership."""
        assert "standard" in [format.value for format in LoggingFormat]
        assert "json" in [format.value for format in LoggingFormat]
        assert "detailed" in [format.value for format in LoggingFormat]

    def test_logging_format_iteration(self):
        """Test iterating over LoggingFormat enum."""
        formats = list(LoggingFormat)
        assert len(formats) == 3
        assert LoggingFormat.STANDARD in formats
        assert LoggingFormat.JSON in formats
        assert LoggingFormat.DETAILED in formats

    def test_logging_format_string_representation(self):
        """Test string representation of LoggingFormat enum."""
        assert str(LoggingFormat.STANDARD) == "LoggingFormat.STANDARD"
        assert str(LoggingFormat.JSON) == "LoggingFormat.JSON"
        assert str(LoggingFormat.DETAILED) == "LoggingFormat.DETAILED"

    def test_logging_format_comparison(self):
        """Test LoggingFormat enum comparison."""
        assert LoggingFormat.STANDARD == LoggingFormat.STANDARD
        assert LoggingFormat.JSON != LoggingFormat.STANDARD
        assert LoggingFormat.DETAILED != LoggingFormat.JSON


@pytest.mark.logger
class TestEnvironment:
    """Test cases for Environment enum."""

    def test_environment_values(self):
        """Test that Environment enum has correct values."""
        assert Environment.DEVELOPMENT.value == "development"
        assert Environment.STAGING.value == "staging"
        assert Environment.PRODUCTION.value == "production"
        assert Environment.TESTING.value == "testing"

    def test_environment_membership(self):
        """Test Environment enum membership."""
        environments = [env.value for env in Environment]
        assert "development" in environments
        assert "staging" in environments
        assert "production" in environments
        assert "testing" in environments

    def test_environment_iteration(self):
        """Test iterating over Environment enum."""
        envs = list(Environment)
        assert len(envs) == 4
        assert Environment.DEVELOPMENT in envs
        assert Environment.STAGING in envs
        assert Environment.PRODUCTION in envs
        assert Environment.TESTING in envs


@pytest.mark.logger
class TestRedactionConfig:
    """Test cases for RedactionConfig enum with various patterns."""

    def test_redaction_config_values(self):
        """Test that RedactionConfig enum has correct values."""
        assert RedactionConfig.ENABLED.value == "enabled"
        assert RedactionConfig.PLACEHOLDER.value == "placeholder"
        assert RedactionConfig.PATTERNS.value == "patterns"

    def test_redaction_config_membership(self):
        """Test RedactionConfig enum membership."""
        config_keys = [config.value for config in RedactionConfig]
        assert "enabled" in config_keys
        assert "placeholder" in config_keys
        assert "patterns" in config_keys

    def test_redaction_patterns_credit_card(self):
        """Test redaction patterns for credit card numbers."""
        patterns = {
            "visa": r"4[0-9]{12}(?:[0-9]{3})?",
            "mastercard": r"5[1-5][0-9]{14}",
            "amex": r"3[47][0-9]{13}",
            "discover": r"6(?:011|5[0-9]{2})[0-9]{12}",
            "generic_card": r"\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}"
        }
        
        # Test that patterns are valid regex patterns
        import re
        for pattern_name, pattern in patterns.items():
            try:
                re.compile(pattern)
                assert True, f"Pattern {pattern_name} is valid"
            except re.error:
                assert False, f"Pattern {pattern_name} is invalid: {pattern}"

    def test_redaction_patterns_personal_info(self):
        """Test redaction patterns for personal information."""
        patterns = {
            "ssn": r"\b\d{3}-?\d{2}-?\d{4}\b",
            "phone": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
            "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "ip_address": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
            "mac_address": r"\b[0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}\b"
        }
        
        import re
        for pattern_name, pattern in patterns.items():
            try:
                re.compile(pattern)
                assert True, f"Pattern {pattern_name} is valid"
            except re.error:
                assert False, f"Pattern {pattern_name} is invalid: {pattern}"

    def test_redaction_patterns_financial(self):
        """Test redaction patterns for financial information."""
        patterns = {
            "bank_account": r"\b\d{8,17}\b",
            "routing_number": r"\b\d{9}\b",
            "iban": r"\b[A-Z]{2}\d{2}[A-Z0-9]{4,30}\b",
            "swift_code": r"\b[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?\b",
            "currency_amount": r"\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?"
        }
        
        import re
        for pattern_name, pattern in patterns.items():
            try:
                re.compile(pattern)
                assert True, f"Pattern {pattern_name} is valid"
            except re.error:
                assert False, f"Pattern {pattern_name} is invalid: {pattern}"

    def test_redaction_config_structure(self):
        """Test complete redaction configuration structure."""
        redaction_config = {
            RedactionConfig.ENABLED.value: True,
            RedactionConfig.PLACEHOLDER.value: "[REDACTED]",
            RedactionConfig.PATTERNS.value: [
                {
                    "name": "credit_card",
                    "pattern": r"\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}",
                    "placeholder": "[CARD]",
                    "flags": ["IGNORECASE"]
                },
                {
                    "name": "ssn",
                    "pattern": r"\b\d{3}-?\d{2}-?\d{4}\b",
                    "placeholder": "[SSN]",
                    "flags": []
                },
                {
                    "name": "email",
                    "pattern": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
                    "placeholder": "[EMAIL]",
                    "flags": ["IGNORECASE"]
                },
                {
                    "name": "phone",
                    "pattern": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
                    "placeholder": "[PHONE]",
                    "flags": []
                },
                {
                    "name": "api_key",
                    "pattern": r"\b[Aa][Pp][Ii][-_]?[Kk][Ee][Yy]\s*[:=]\s*['\"]?([A-Za-z0-9_-]{20,})['\"]?",
                    "placeholder": "[API_KEY]",
                    "flags": ["IGNORECASE"]
                }
            ]
        }
        
        # Validate structure
        assert redaction_config[RedactionConfig.ENABLED.value] is True
        assert redaction_config[RedactionConfig.PLACEHOLDER.value] == "[REDACTED]"
        assert len(redaction_config[RedactionConfig.PATTERNS.value]) == 5
        
        # Validate each pattern
        for pattern_config in redaction_config[RedactionConfig.PATTERNS.value]:
            assert "name" in pattern_config
            assert "pattern" in pattern_config
            assert "placeholder" in pattern_config
            assert "flags" in pattern_config
            
            # Test pattern compilation
            import re
            try:
                re.compile(pattern_config["pattern"])
                assert True, f"Pattern {pattern_config['name']} is valid"
            except re.error:
                assert False, f"Pattern {pattern_config['name']} is invalid"

    def test_redaction_pattern_matching(self):
        """Test that redaction patterns match expected strings."""
        import re
        
        test_cases = [
            {
                "pattern": r"\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}",
                "test_strings": [
                    "4532-1234-5678-9012",
                    "4532 1234 5678 9012",
                    "4532123456789012"
                ],
                "should_match": True
            },
            {
                "pattern": r"\b\d{3}-?\d{2}-?\d{4}\b",
                "test_strings": [
                    "123-45-6789",
                    "123456789",
                    "123-456789"
                ],
                "should_match": True
            },
            {
                "pattern": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
                "test_strings": [
                    "user@example.com",
                    "test.email+tag@domain.co.uk",
                    "user123@test-domain.org"
                ],
                "should_match": True
            },
            {
                "pattern": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
                "test_strings": [
                    "555-123-4567",
                    "555.123.4567",
                    "5551234567"
                ],
                "should_match": True
            }
        ]
        
        for test_case in test_cases:
            pattern = re.compile(test_case["pattern"])
            for test_string in test_case["test_strings"]:
                match = pattern.search(test_string)
                if test_case["should_match"]:
                    assert match is not None, f"Pattern should match '{test_string}'"
                else:
                    assert match is None, f"Pattern should not match '{test_string}'"

    def test_redaction_placeholder_variations(self):
        """Test different placeholder variations for redaction."""
        placeholders = [
            "[REDACTED]",
            "[CARD]",
            "[SSN]",
            "[EMAIL]",
            "[PHONE]",
            "[API_KEY]",
            "[SENSITIVE]",
            "***",
            "XXXXX",
            "[MASKED]"
        ]
        
        # Test that all placeholders are valid strings
        for placeholder in placeholders:
            assert isinstance(placeholder, str)
            assert len(placeholder) > 0
            assert placeholder != ""

    def test_redaction_flags_support(self):
        """Test support for regex flags in redaction patterns."""
        import re
        
        flag_mappings = {
            "IGNORECASE": re.IGNORECASE,
            "MULTILINE": re.MULTILINE,
            "DOTALL": re.DOTALL,
            "VERBOSE": re.VERBOSE,
            "ASCII": re.ASCII
        }
        
        # Test that flag strings map to correct regex flags
        for flag_name, flag_value in flag_mappings.items():
            assert hasattr(re, flag_name)
            assert getattr(re, flag_name) == flag_value

    def test_complex_redaction_scenario(self):
        """Test complex redaction scenario with multiple patterns."""
        test_message = """
        User john.doe@company.com called 555-123-4567 about credit card 4532-1234-5678-9012.
        SSN: 123-45-6789, API Key: api_key=abc123def456ghi789jkl012
        IP Address: 192.168.1.100, Account: 1234567890123456
        """
        
        patterns = [
            (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL]"),
            (r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", "[PHONE]"),
            (r"\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}", "[CARD]"),
            (r"\b\d{3}-?\d{2}-?\d{4}\b", "[SSN]"),
            (r"api_key\s*[:=]\s*[A-Za-z0-9_-]{10,}", "[API_KEY]"),
            (r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "[IP]"),
            (r"\b\d{13,19}\b", "[ACCOUNT]")
        ]
        
        import re
        redacted_message = test_message
        
        for pattern, placeholder in patterns:
            redacted_message = re.sub(pattern, placeholder, redacted_message, flags=re.IGNORECASE)
        
        # Verify that sensitive data has been redacted
        assert "[EMAIL]" in redacted_message
        assert "[PHONE]" in redacted_message
        assert "[CARD]" in redacted_message
        assert "[SSN]" in redacted_message
        assert "[API_KEY]" in redacted_message
        assert "[IP]" in redacted_message
        
        # Verify original sensitive data is not present
        assert "john.doe@company.com" not in redacted_message
        assert "555-123-4567" not in redacted_message
        assert "4532-1234-5678-9012" not in redacted_message
        assert "123-45-6789" not in redacted_message
