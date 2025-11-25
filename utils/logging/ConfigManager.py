"""
ConfigManager - Configuration management for logging system.

This module handles loading, validating, and managing logging configuration
from JSON files and environment variables.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict
from utils.logging.Enum import Environment


class ConfigManager:
    """
    Manages logging configuration loading and validation.

    This class handles loading configuration from environment-specific files,
    provides default configurations, and validates configuration structure.
    """

    def __init__(self, config_file: str = None):
        """
        Initialize the configuration manager.

        Args:
            config_file: Optional specific config file to load
        """
        self.config_file = config_file
        self.config = None

    @staticmethod
    def detect_environment() -> str:
        """
        Detect current environment from env variables.

        Defaults to 'prod' if not set.

        Returns:
            str: Detected environment
        """
        env = os.getenv('ENVIRONMENT', os.getenv('ENV', 'prod')).lower()
        env_mapping = {
            'dev': Environment.DEVELOPMENT.value,
            'development': Environment.DEVELOPMENT.value,
            'stage': Environment.STAGING.value,
            'staging': Environment.STAGING.value,
            'prod': Environment.PRODUCTION.value,
            'production': Environment.PRODUCTION.value,
            'test': Environment.TESTING.value,
            'testing': Environment.TESTING.value
        }
        return env_mapping.get(env, Environment.PRODUCTION.value)

    @staticmethod
    def get_environment_config_file(environment: str) -> str:
        """
        Get configuration file based on environment.

        Args:
            environment: Environment name

        Returns:
            str: Path to configuration file
        """
        config_dir = "utils/logging/Config"
        config_files = {
            Environment.DEVELOPMENT.value: f"{config_dir}/log_config_dev.json",
            Environment.STAGING.value: f"{config_dir}/log_config_staging.json",
            Environment.PRODUCTION.value: f"{config_dir}/log_config_prod.json",
            Environment.TESTING.value: f"{config_dir}/log_config_test.json"
        }
        config_file = config_files.get(environment, f"{config_dir}/log_config_prod.json")

        # Check if environment-specific config exists, otherwise use prod
        if not os.path.exists(config_file):
            config_file = f"{config_dir}/log_config_prod.json"
        return config_file

    def load_config(self, config_file: str = None) -> Dict[str, Any]:
        """
        Load logging configuration from file.

        Args:
            config_file: Optional config file path

        Returns:
            Dict[str, Any]: Configuration dictionary
        """
        if config_file:
            self.config_file = config_file

        if not self.config_file:
            # Auto-detect based on environment
            environment = self.detect_environment()
            self.config_file = self.get_environment_config_file(environment)

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            return self.config
        except FileNotFoundError:
            # Return default configuration if file not found
            return self.get_default_config()
        except json.JSONDecodeError as e:
            msg = f"Invalid JSON in configuration file {self.config_file}: {e}"
            raise ValueError(msg) from e

    @staticmethod
    def get_default_config() -> Dict[str, Any]:
        """
        Get default logging configuration.

        Returns:
            Dict[str, Any]: Default configuration
        """
        return {
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
            }
        }

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate configuration structure.

        Args:
            config: Configuration dictionary to validate

        Returns:
            bool: True if valid, False otherwise
        """
        required_keys = ['backend', 'level', 'handlers']
        return all(key in config for key in required_keys)

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.

        Args:
            key: Configuration key (supports dot notation for nested keys)
            default: Default value if key not found

        Returns:
            Any: Configuration value
        """
        if not self.config:
            return default

        if '.' in key:
            # Handle nested keys like "handlers.console.level"
            keys = key.split('.')
            value = self.config
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            return value
        else:
            return self.config.get(key, default)

    def set_config_value(self, key: str, value: Any):
        """
        Set a configuration value.

        Args:
            key: Configuration key (supports dot notation for nested keys)
            value: Value to set
        """
        if not self.config:
            self.config = {}

        if '.' in key:
            # Handle nested keys like "handlers.console.level"
            keys = key.split('.')
            config = self.config
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]
            config[keys[-1]] = value
        else:
            self.config[key] = value

    def reload_config(self, config_file: str = None):
        """
        Reload configuration from file.

        Args:
            config_file: Optional config file path
        """
        self.load_config(config_file)

    def get_log_filepath(self, filename: str) -> str:
        """
        Get the full filepath for log files based on configuration.

        Args:
            filename: Log filename

        Returns:
            str: Full path to log file
        """
        if not self.config:
            return filename

        # Get log directory from config, default to ./logs
        log_directory = self.config.get('log_directory', './logs')

        # Handle different path types
        if log_directory.startswith('~/'):
            # Expand ~ to user's home directory
            home_dir = Path.home()
            log_dir = home_dir / log_directory[2:]  # Remove ~/
        elif log_directory.startswith('./'):
            # Relative to current working directory
            log_dir = Path.cwd() / log_directory[2:]  # Remove ./
        else:
            # Absolute path or relative path
            log_dir = Path(log_directory)

        # Create log directory if it doesn't exist
        log_dir.mkdir(parents=True, exist_ok=True)

        return str(log_dir / filename)

    def get_duration_config(self) -> Dict[str, Any]:
        """
        Get duration logging configuration.

        Returns:
            Dict[str, Any]: Duration logging configuration
        """
        return self.config.get('duration_logging', {
            'slow_threshold_seconds': 1.0,
            'warn_threshold_seconds': 5.0,
            'error_threshold_seconds': 30.0
        })

    def get_delayed_logging_config(self) -> Dict[str, Any]:
        """
        Get delayed logging configuration.

        Returns:
            Dict[str, Any]: Delayed logging configuration
        """
        return self.config.get('delayed_logging', {
            'enabled': False,
            'queue_size_kb': 0,
            'flush_on_exception': True,
            'flush_on_completion': True
        })

    def get_redaction_config(self) -> Dict[str, Any]:
        """
        Get redaction configuration.

        Returns:
            Dict[str, Any]: Redaction configuration
        """
        return self.config.get('redaction', {
            'enabled': False,
            'placeholder': '[REDACTED]',
            'patterns': []
        })
