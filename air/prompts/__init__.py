"""
Prompts Module

System prompts and templates for agent nodes.
"""

from .greeting_prompt import GREETING_AGENT_PROMPT, build_greeting_prompt
from .service_check_prompt import SERVICE_CHECK_PROMPT, build_service_check_prompt
from .guidelines_prompt import GUIDELINES_PROMPT, build_guidelines_prompt
from .fallback_prompt import FALLBACK_PROMPT, build_fallback_prompt

__all__ = [
    "GREETING_AGENT_PROMPT",
    "build_greeting_prompt",
    "SERVICE_CHECK_PROMPT",
    "build_service_check_prompt",
    "GUIDELINES_PROMPT",
    "build_guidelines_prompt",
    "FALLBACK_PROMPT",
    "build_fallback_prompt",
]

