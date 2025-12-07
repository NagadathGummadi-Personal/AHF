"""
Enumerations for Prompt Registry Subsystem.
"""

from enum import Enum
from .constants import (
    STATUS_DRAFT,
    STATUS_ACTIVE,
    STATUS_DEPRECATED,
    STATUS_ARCHIVED,
    CATEGORY_SYSTEM,
    CATEGORY_USER,
    CATEGORY_ASSISTANT,
    CATEGORY_FUNCTION,
    CATEGORY_TOOL,
    CATEGORY_TEMPLATE,
    CATEGORY_EXAMPLE,
    ENV_PROD,
    ENV_STAGING,
    ENV_DEV,
    ENV_TEST,
    PROMPT_TYPE_SYSTEM,
    PROMPT_TYPE_USER,
)


class PromptStatus(str, Enum):
    """Status of a prompt."""
    DRAFT = STATUS_DRAFT
    ACTIVE = STATUS_ACTIVE
    DEPRECATED = STATUS_DEPRECATED
    ARCHIVED = STATUS_ARCHIVED


class PromptCategory(str, Enum):
    """Category of a prompt."""
    SYSTEM = CATEGORY_SYSTEM
    USER = CATEGORY_USER
    ASSISTANT = CATEGORY_ASSISTANT
    FUNCTION = CATEGORY_FUNCTION
    TOOL = CATEGORY_TOOL
    TEMPLATE = CATEGORY_TEMPLATE
    EXAMPLE = CATEGORY_EXAMPLE


class PromptEnvironment(str, Enum):
    """
    Environment for a prompt.
    
    Prompts can be scoped to specific environments. During retrieval,
    the system will attempt to find a prompt for the requested environment
    and fallback to lower environments if not found.
    
    Priority: prod > staging > dev > test
    """
    PROD = ENV_PROD
    STAGING = ENV_STAGING
    DEV = ENV_DEV
    TEST = ENV_TEST


class PromptType(str, Enum):
    """
    Type of prompt - system or user.
    
    - SYSTEM: Instructions/persona for the LLM (system message)
    - USER: User-facing prompts or templates
    """
    SYSTEM = PROMPT_TYPE_SYSTEM
    USER = PROMPT_TYPE_USER

