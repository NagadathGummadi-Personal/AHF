"""
Interrupt Configuration.

Defines configuration for interrupt handling behavior.

Version: 1.0.0
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class InterruptConfig(BaseModel):
    """
    Configuration for interrupt handling.
    
    Attributes:
        enabled: Whether interrupts are enabled for this component
        wait_for_followup_ms: Time to wait for follow-up message after interrupt (ms)
        stash_partial_response: Whether to stash partial response on interrupt
        include_conversation_history: Include full conversation history in continuation
        max_history_messages: Max messages to include from conversation history
        continuation_prompt_template: Template for creating continuation prompts
        auto_combine_responses: Automatically combine stashed + new response
    """
    enabled: bool = Field(
        default=False,
        description="Whether interrupts are enabled for this component"
    )
    
    wait_for_followup_ms: int = Field(
        default=500,
        ge=0,
        le=10000,
        description="Time to wait for follow-up message after interrupt (ms)"
    )
    
    stash_partial_response: bool = Field(
        default=True,
        description="Whether to stash partial response on interrupt"
    )
    
    include_conversation_history: bool = Field(
        default=True,
        description="Include full conversation history in continuation"
    )
    
    max_history_messages: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Max messages to include from conversation history"
    )
    
    continuation_prompt_template: str = Field(
        default=(
            "The user interrupted while you were saying:\n"
            '"{stashed_response}"\n\n'
            "The user now says: {new_message}\n\n"
            "Please provide a response that:\n"
            "1. Acknowledges what you were saying if relevant\n"
            "2. Addresses the user's new message\n"
            "3. Maintains context from the conversation"
        ),
        description="Template for creating continuation prompts"
    )
    
    auto_combine_responses: bool = Field(
        default=True,
        description="Automatically combine stashed + new response using LLM"
    )
    
    interrupt_on_tool_call: bool = Field(
        default=False,
        description="Allow interrupts during tool execution"
    )
    
    preserve_tool_state: bool = Field(
        default=True,
        description="Preserve tool state when interrupted"
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'InterruptConfig':
        """Create from dictionary."""
        return cls(**data)
    
    def merge_with(self, other: Optional['InterruptConfig']) -> 'InterruptConfig':
        """
        Merge with another config, preferring other's non-default values.
        
        Args:
            other: Config to merge with
            
        Returns:
            New merged config
        """
        if not other:
            return self
        
        data = self.model_dump()
        other_data = other.model_dump()
        
        # Merge, preferring other's values if explicitly set
        for key, value in other_data.items():
            if value is not None:
                data[key] = value
        
        return InterruptConfig(**data)


# Default configuration
DEFAULT_INTERRUPT_CONFIG = InterruptConfig(
    enabled=False,
    wait_for_followup_ms=500,
    stash_partial_response=True,
    include_conversation_history=True,
    max_history_messages=20,
    auto_combine_responses=True,
)


# Preset configurations
INTERACTIVE_INTERRUPT_CONFIG = InterruptConfig(
    enabled=True,
    wait_for_followup_ms=500,
    stash_partial_response=True,
    include_conversation_history=True,
    max_history_messages=30,
    auto_combine_responses=True,
)

VOICE_INTERRUPT_CONFIG = InterruptConfig(
    enabled=True,
    wait_for_followup_ms=300,  # Shorter wait for voice
    stash_partial_response=True,
    include_conversation_history=True,
    max_history_messages=10,
    auto_combine_responses=True,
    interrupt_on_tool_call=False,
)

STREAMING_INTERRUPT_CONFIG = InterruptConfig(
    enabled=True,
    wait_for_followup_ms=1000,  # Longer wait for streaming
    stash_partial_response=True,
    include_conversation_history=True,
    max_history_messages=20,
    auto_combine_responses=True,
)

