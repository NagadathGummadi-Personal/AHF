"""
Continuation Context and Prompt Generation.

Handles creating continuation contexts and prompts when combining
stashed responses with new user messages after interrupts.

Version: 1.0.0
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .state import StashedResponse


class ContinuationContext(BaseModel):
    """
    Context for continuing after an interrupt.
    
    Contains all the information needed to generate a continuation
    response that combines the stashed partial response with the
    new user message.
    
    Attributes:
        stashed_response: The stashed partial response
        new_message: The new user message
        conversation_history: Prior conversation history
        continuation_prompt: The generated continuation prompt
        metadata: Additional context metadata
    """
    stashed_response: Optional[StashedResponse] = Field(
        default=None,
        description="The stashed partial response from interrupt"
    )
    new_message: Optional[str] = Field(
        default=None,
        description="New message from user after interrupt"
    )
    conversation_history: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Conversation history before interrupt"
    )
    continuation_prompt: Optional[str] = Field(
        default=None,
        description="Generated continuation prompt"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    
    def has_stashed_content(self) -> bool:
        """Check if there's stashed content to continue from."""
        return (
            self.stashed_response is not None and 
            bool(self.stashed_response.content)
        )
    
    def has_new_message(self) -> bool:
        """Check if there's a new user message."""
        return bool(self.new_message)
    
    def should_combine(self) -> bool:
        """Check if we should combine stashed response with new message."""
        return self.has_stashed_content() and self.has_new_message()
    
    def get_stashed_content(self) -> str:
        """Get the stashed response content."""
        if self.stashed_response:
            return self.stashed_response.content
        return ""
    
    def to_messages(self) -> List[Dict[str, Any]]:
        """
        Convert continuation context to message list for LLM.
        
        Returns:
            List of messages including history and continuation prompt
        """
        messages = list(self.conversation_history)
        
        if self.continuation_prompt:
            messages.append({
                "role": "user",
                "content": self.continuation_prompt,
            })
        elif self.new_message:
            messages.append({
                "role": "user",
                "content": self.new_message,
            })
        
        return messages


# Default continuation prompt template
DEFAULT_CONTINUATION_TEMPLATE = (
    "The user interrupted while you were saying:\n"
    '"{stashed_response}"\n\n'
    "The user now says: {new_message}\n\n"
    "Please provide a response that:\n"
    "1. Acknowledges what you were saying if relevant\n"
    "2. Addresses the user's new message\n"
    "3. Maintains context from the conversation"
)

# Simple continuation template (for shorter responses)
SIMPLE_CONTINUATION_TEMPLATE = (
    "[Interrupted response: \"{stashed_response}\"]\n\n"
    "User's new message: {new_message}\n\n"
    "Please respond to the user's new message, considering the interrupted context."
)

# Acknowledgment-focused template
ACKNOWLEDGMENT_CONTINUATION_TEMPLATE = (
    "You were responding with: \"{stashed_response}\"\n"
    "The user interrupted with: {new_message}\n\n"
    "Briefly acknowledge the interruption and address the user's new message."
)


def create_continuation_prompt(
    stashed_response: Optional[str] = None,
    new_message: Optional[str] = None,
    template: Optional[str] = None,
    max_stashed_length: int = 1000,
    **kwargs,
) -> str:
    """
    Create a continuation prompt combining stashed response and new message.
    
    Args:
        stashed_response: The stashed partial response content
        new_message: The new user message
        template: Optional custom template (uses default if not provided)
        max_stashed_length: Maximum length for stashed response in prompt
        **kwargs: Additional template variables
        
    Returns:
        Formatted continuation prompt
        
    Example:
        prompt = create_continuation_prompt(
            stashed_response="I was explaining that Python...",
            new_message="Actually, can you show me an example?",
        )
    """
    # Use default template if none provided
    if template is None:
        template = DEFAULT_CONTINUATION_TEMPLATE
    
    # Prepare stashed response (truncate if needed)
    stashed = stashed_response or ""
    if len(stashed) > max_stashed_length:
        stashed = stashed[:max_stashed_length - 3] + "..."
    
    # Prepare new message
    message = new_message or ""
    
    # Format template
    try:
        prompt = template.format(
            stashed_response=stashed,
            new_message=message,
            **kwargs,
        )
    except KeyError:
        # Fallback if template has unexpected variables
        prompt = (
            f"[Previous partial response: {stashed}]\n\n"
            f"User's message: {message}"
        )
    
    return prompt


def create_continuation_context(
    stashed_response: Optional[StashedResponse] = None,
    new_message: Optional[str] = None,
    conversation_history: Optional[List[Dict[str, Any]]] = None,
    template: Optional[str] = None,
    max_stashed_length: int = 1000,
    metadata: Optional[Dict[str, Any]] = None,
) -> ContinuationContext:
    """
    Create a full continuation context.
    
    Args:
        stashed_response: The stashed partial response
        new_message: The new user message
        conversation_history: Prior conversation history
        template: Optional custom template for continuation prompt
        max_stashed_length: Maximum length for stashed response in prompt
        metadata: Additional metadata
        
    Returns:
        ContinuationContext with generated continuation prompt
    """
    # Generate continuation prompt if we have both stashed and new message
    continuation_prompt = None
    if stashed_response and stashed_response.content and new_message:
        continuation_prompt = create_continuation_prompt(
            stashed_response=stashed_response.content,
            new_message=new_message,
            template=template,
            max_stashed_length=max_stashed_length,
        )
    
    return ContinuationContext(
        stashed_response=stashed_response,
        new_message=new_message,
        conversation_history=conversation_history or [],
        continuation_prompt=continuation_prompt,
        metadata=metadata or {},
    )

