"""
Simple config access for the tools package.

Reads environment variables and exposes a minimal API for environment checks.
"""

import os
from .defaults import DEFAULT_ENVIRONMENT
from .constants import ENVIRONMENT


def get_environment() -> str:
    """Return current environment name, defaulting to DEFAULT_ENVIRONMENT.

    ENVIRONMENT takes precedence, falls back to DEFAULT_ENVIRONMENT.
    """
    return (os.getenv(ENVIRONMENT) or DEFAULT_ENVIRONMENT).lower()


def is_dev() -> bool:
    return get_environment().startswith(DEFAULT_ENVIRONMENT)


