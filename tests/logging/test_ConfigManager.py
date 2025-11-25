"""
Test suite for ConfigManager module.

This module contains tests for the ConfigManager functionality, covering:
- Configuration loading from files
- Environment detection
- Default configuration handling
- Configuration validation
- Path handling for log files
- Nested configuration access

Test Structure:
===============
1. Test ConfigManager class initialization
2. Test environment detection
3. Test configuration file loading
4. Test default configuration
5. Test configuration validation
6. Test nested configuration access
7. Test log file path generation

Pytest Markers:
===============
- config: All tests in this module
"""

import pytest
import json
import os
import tempfile
from unittest.mock import patch, mock_open
from utils.logging.ConfigManager import ConfigManager
from utils.logging.Enum import Environment


@pytest.mark.config
class TestConfigManager:
    """Test cases for ConfigManager class functionality."""

    @pytest.fixture
    def config_manager(self):
        """Provide a ConfigManager instance for testing."""
        return ConfigManager()

    @pytest.fixture
    def temp_config_file(self):
        """Create a temporary config file for testing."""
        config_data = {
            "backend": "json",
            "level": "DEBUG",
            "log_directory": "./test_logs",
            "redaction": {
                "enabled": True,
                "placeholder": "[REDACTED]"
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_file_path = f.name

        yield temp_file_path

        # Cleanup
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)

    def test_config_manager_initialization(self):
        """Test ConfigManager initialization."""
        cm = ConfigManager()
        assert cm.config is None
        assert cm.config_file is None

    def test_environment_detection(self, config_manager):
        """Test environment detection from environment variables."""
        # Test development environment
        with patch.dict(os.environ, {'ENVIRONMENT': 'dev'}):
            env = config_manager.detect_environment()
            assert env == Environment.DEVELOPMENT.value

        # Test production environment
        with patch.dict(os.environ, {'ENVIRONMENT': 'prod'}):
            env = config_manager.detect_environment()
            assert env == Environment.PRODUCTION.value

        # Test default to production
        with patch.dict(os.environ, {}, clear=True):
            env = config_manager.detect_environment()
            assert env == Environment.PRODUCTION.value

    @pytest.mark.parametrize("env_var,expected", [
        ("dev", "development"),
        ("development", "development"),
        ("staging", "staging"),
        ("prod", "production"),
        ("production", "production"),
        ("test", "testing"),
        ("testing", "testing"),
    ])
    def test_environment_detection_parametrized(self, config_manager, env_var, expected):
        """Test environment detection with various environment variables."""
        with patch.dict(os.environ, {'ENVIRONMENT': env_var}):
            detected = config_manager.detect_environment()
            assert detected == expected

    def test_get_environment_config_file(self, config_manager):
        """Test getting environment-specific config files."""
        # Test development
        config_file = config_manager.get_environment_config_file("development")
        assert "log_config_dev.json" in config_file

        # Test production
        config_file = config_manager.get_environment_config_file("production")
        assert "log_config_prod.json" in config_file

        # Test unknown environment defaults to production
        config_file = config_manager.get_environment_config_file("unknown")
        assert "log_config_prod.json" in config_file

    def test_load_config_success(self, config_manager, temp_config_file):
        """Test successful config loading."""
        config = config_manager.load_config(temp_config_file)

        assert config["backend"] == "json"
        assert config["level"] == "DEBUG"
        assert config["log_directory"] == "./test_logs"
        assert config["redaction"]["enabled"] is True

    def test_load_config_file_not_found(self, config_manager):
        """Test config loading when file doesn't exist."""
        config = config_manager.load_config("nonexistent.json")

        # Should return default config
        assert "backend" in config
        assert "level" in config
        assert "handlers" in config

    def test_load_config_invalid_json(self, config_manager):
        """Test config loading with invalid JSON."""
        with patch('builtins.open', mock_open(read_data="invalid json")):
            with pytest.raises(ValueError, match="Invalid JSON"):
                config_manager.load_config("invalid.json")

    def test_get_default_config(self, config_manager):
        """Test getting default configuration."""
        default_config = config_manager.get_default_config()

        assert default_config["backend"] == "standard"
        assert default_config["level"] == "INFO"
        assert "formatters" in default_config
        assert "handlers" in default_config

    def test_validate_config_valid(self, config_manager):
        """Test configuration validation with valid config."""
        valid_config = {
            "backend": "json",
            "level": "INFO",
            "handlers": {"console": {"type": "console"}}
        }

        assert config_manager.validate_config(valid_config) is True

    def test_validate_config_invalid(self, config_manager):
        """Test configuration validation with invalid config."""
        invalid_config = {
            "backend": "json"
            # Missing required 'level' and 'handlers'
        }

        assert config_manager.validate_config(invalid_config) is False

    def test_get_config_value_simple(self, config_manager):
        """Test getting simple configuration values."""
        config_manager.config = {
            "backend": "json",
            "level": "DEBUG",
            "nested": {"key": "value"}
        }

        assert config_manager.get_config_value("backend") == "json"
        assert config_manager.get_config_value("level") == "DEBUG"
        assert config_manager.get_config_value("nonexistent", "default") == "default"

    def test_get_config_value_nested(self, config_manager):
        """Test getting nested configuration values."""
        config_manager.config = {
            "database": {
                "host": "localhost",
                "port": 5432,
                "credentials": {
                    "username": "admin",
                    "password": "secret"
                }
            }
        }

        assert config_manager.get_config_value("database.host") == "localhost"
        assert config_manager.get_config_value("database.port") == 5432
        assert config_manager.get_config_value("database.credentials.username") == "admin"
        assert config_manager.get_config_value("database.nonexistent.key", "default") == "default"

    def test_set_config_value_simple(self, config_manager):
        """Test setting simple configuration values."""
        config_manager.set_config_value("backend", "json")
        assert config_manager.config["backend"] == "json"

    def test_set_config_value_nested(self, config_manager):
        """Test setting nested configuration values."""
        config_manager.set_config_value("database.host", "localhost")
        config_manager.set_config_value("database.port", 5432)
        config_manager.set_config_value("database.credentials.username", "admin")

        assert config_manager.config["database"]["host"] == "localhost"
        assert config_manager.config["database"]["port"] == 5432
        assert config_manager.config["database"]["credentials"]["username"] == "admin"

    def test_reload_config(self, config_manager, temp_config_file):
        """Test configuration reloading."""
        # Load initial config
        initial_config = config_manager.load_config(temp_config_file)
        assert initial_config["backend"] == "json"

        # Modify the config file
        new_config_data = {
            "backend": "standard",
            "level": "WARNING"
        }

        with open(temp_config_file, 'w') as f:
            json.dump(new_config_data, f)

        # Reload configuration
        config_manager.reload_config(temp_config_file)

        assert config_manager.config["backend"] == "standard"
        assert config_manager.config["level"] == "WARNING"

    def test_get_log_filepath(self, config_manager):
        """Test log file path generation."""
        config_manager.config = {
            "log_directory": "./test_logs"
        }

        filepath = config_manager.get_log_filepath("test.log")

        assert "test.log" in filepath
        assert "test_logs" in filepath

    def test_get_log_filepath_with_tilde(self, config_manager):
        """Test log file path generation with ~ expansion."""
        config_manager.config = {
            "log_directory": "~/logs"
        }

        with patch('pathlib.Path.mkdir') as mock_mkdir:
            filepath = config_manager.get_log_filepath("test.log")

            assert "test.log" in filepath
            assert "logs" in filepath
            mock_mkdir.assert_called_once()

    def test_get_log_filepath_with_relative_path(self, config_manager):
        """Test log file path generation with relative path."""
        config_manager.config = {
            "log_directory": "./logs"
        }

        with patch('pathlib.Path.mkdir') as mock_mkdir:
            filepath = config_manager.get_log_filepath("test.log")

            assert "test.log" in filepath
            assert "logs" in filepath
            mock_mkdir.assert_called_once()

    def test_get_duration_config(self, config_manager):
        """Test getting duration logging configuration."""
        config_manager.config = {
            "duration_logging": {
                "slow_threshold_seconds": 1.0,
                "warn_threshold_seconds": 5.0,
                "error_threshold_seconds": 30.0
            }
        }

        duration_config = config_manager.get_duration_config()

        assert duration_config["slow_threshold_seconds"] == 1.0
        assert duration_config["warn_threshold_seconds"] == 5.0
        assert duration_config["error_threshold_seconds"] == 30.0

    def test_get_duration_config_defaults(self, config_manager):
        """Test getting duration logging configuration with defaults."""
        config_manager.config = {}  # No duration_logging config

        duration_config = config_manager.get_duration_config()

        assert duration_config["slow_threshold_seconds"] == 1.0
        assert duration_config["warn_threshold_seconds"] == 5.0
        assert duration_config["error_threshold_seconds"] == 30.0

    def test_get_delayed_logging_config(self, config_manager):
        """Test getting delayed logging configuration."""
        config_manager.config = {
            "delayed_logging": {
                "enabled": True,
                "queue_size_kb": 10,
                "flush_on_exception": True,
                "flush_on_completion": True
            }
        }

        delayed_config = config_manager.get_delayed_logging_config()

        assert delayed_config["enabled"] is True
        assert delayed_config["queue_size_kb"] == 10
        assert delayed_config["flush_on_exception"] is True
        assert delayed_config["flush_on_completion"] is True

    def test_get_delayed_logging_config_defaults(self, config_manager):
        """Test getting delayed logging configuration with defaults."""
        config_manager.config = {}  # No delayed_logging config

        delayed_config = config_manager.get_delayed_logging_config()

        assert delayed_config["enabled"] is False
        assert delayed_config["queue_size_kb"] == 0
        assert delayed_config["flush_on_exception"] is True
        assert delayed_config["flush_on_completion"] is True

    def test_get_redaction_config(self, config_manager):
        """Test getting redaction configuration."""
        config_manager.config = {
            "redaction": {
                "enabled": True,
                "placeholder": "[REDACTED]",
                "patterns": [
                    {"pattern": "test_pattern", "placeholder": "[TEST]"}
                ]
            }
        }

        redaction_config = config_manager.get_redaction_config()

        assert redaction_config["enabled"] is True
        assert redaction_config["placeholder"] == "[REDACTED]"
        assert len(redaction_config["patterns"]) == 1

    def test_get_redaction_config_defaults(self, config_manager):
        """Test getting redaction configuration with defaults."""
        config_manager.config = {}  # No redaction config

        redaction_config = config_manager.get_redaction_config()

        assert redaction_config["enabled"] is False
        assert redaction_config["placeholder"] == "[REDACTED]"
        assert redaction_config["patterns"] == []


@pytest.mark.config
class TestConfigManagerIntegration:
    """Test integration scenarios for ConfigManager."""

    @pytest.fixture
    def config_manager(self):
        """Provide a ConfigManager instance for testing."""
        return ConfigManager()

    def test_full_config_loading_workflow(self, config_manager):
        """Test the complete configuration loading workflow."""
        # Test with a temporary config file
        config_data = {
            "backend": "json",
            "level": "INFO",
            "log_directory": "./test_logs",
            "duration_logging": {
                "slow_threshold_seconds": 0.5,
                "warn_threshold_seconds": 2.0,
                "error_threshold_seconds": 10.0
            },
            "delayed_logging": {
                "enabled": True,
                "queue_size_kb": 5
            },
            "redaction": {
                "enabled": True,
                "placeholder": "[HIDDEN]"
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_file_path = f.name

        try:
            # Load the configuration
            config = config_manager.load_config(temp_file_path)

            # Verify all sections are loaded correctly
            assert config["backend"] == "json"
            assert config["level"] == "INFO"
            assert config["log_directory"] == "./test_logs"

            # Test nested access
            assert config_manager.get_config_value("duration_logging.slow_threshold_seconds") == 0.5
            assert config_manager.get_config_value("delayed_logging.enabled") is True
            assert config_manager.get_config_value("redaction.placeholder") == "[HIDDEN]"

            # Test specific config getters
            duration_config = config_manager.get_duration_config()
            assert duration_config["slow_threshold_seconds"] == 0.5
            assert duration_config["warn_threshold_seconds"] == 2.0

            delayed_config = config_manager.get_delayed_logging_config()
            assert delayed_config["enabled"] is True
            assert delayed_config["queue_size_kb"] == 5

            redaction_config = config_manager.get_redaction_config()
            assert redaction_config["enabled"] is True
            assert redaction_config["placeholder"] == "[HIDDEN]"

        finally:
            # Cleanup
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    def test_environment_specific_config_loading(self, config_manager):
        """Test loading different configs based on environment."""
        # Test development environment
        with patch.dict(os.environ, {'ENVIRONMENT': 'dev'}):
            config_file = config_manager.get_environment_config_file("development")
            assert "log_config_dev.json" in config_file

            # Verify the config file path structure
            assert "utils/logging/Config" in config_file or "logging/Config" in config_file

        # Test production environment
        with patch.dict(os.environ, {'ENVIRONMENT': 'prod'}):
            config_file = config_manager.get_environment_config_file("production")
            assert "log_config_prod.json" in config_file
