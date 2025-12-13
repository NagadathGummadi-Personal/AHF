"""
Configuration Module

Provides centralized configuration with environment variable support.

Usage:
    from air.config import get_settings, Defaults, get_tool_urls
    
    # Get application settings
    settings = get_settings()
    
    # Get environment-aware tool URLs
    urls = get_tool_urls()
    handover_url = urls.handover_url
    
    # Check environment
    from air.config import Environment
    if Environment.is_development():
        print("Running in development mode")
"""

from .settings import Settings, get_settings
from .defaults import Defaults, Environment, ToolURLs, get_tool_urls

__all__ = [
    "Settings",
    "get_settings",
    "Defaults",
    "Environment",
    "ToolURLs",
    "get_tool_urls",
]

