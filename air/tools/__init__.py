"""
Tools Module

HTTP tools and utilities for the voice agent workflow.
Uses core.tools.AioHttpExecutor for HTTP operations.

All tools extend BaseHttpTool which provides:
- Connection pooling via shared aiohttp session
- Automatic retries with exponential backoff
- Full integration with core.tools validation and metrics

Usage:
    from air.tools import HandoverTool, PricingInfoTool
    
    handover = HandoverTool()
    result = await handover.execute({"reason": "User requested"}, session)
"""

from .base import BaseTool, BaseHttpTool, ToolResult
from .handover import HandoverTool
from .pricing import PricingInfoTool
from .therapist import TherapistTool
from .kb_search import KBSearchTool

__all__ = [
    # Base classes
    "BaseTool",
    "BaseHttpTool",
    "ToolResult",
    # Tools
    "HandoverTool",
    "PricingInfoTool",
    "TherapistTool",
    "KBSearchTool",
]
