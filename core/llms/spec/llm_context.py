"""
LLM Context.

This module defines the context object that carries execution metadata,
configuration, and optional services through LLM operations.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
import uuid

from ..constants import (
    CONTEXT_REQUEST_ID,
    CONTEXT_USER_ID,
    CONTEXT_SESSION_ID,
    CONTEXT_TENANT_ID,
    CONTEXT_TRACE_ID,
    CONTEXT_LOCALE,
    CONTEXT_METADATA,
    CONTEXT_CONFIG,
    DEFAULT_LOCALE,
    DEFAULT_TIMEZONE,
    PREFIX_REQUEST,
    PREFIX_TEST_USER,
    PREFIX_TEST_SESSION,
    PREFIX_TEST_TENANT,
    TEST_ENVIRONMENT_KEY,
    TEST_ENVIRONMENT_VALUE,
)


class LLMContext(BaseModel):
    """
    Context for LLM execution.
    
    Carries metadata, configuration, and optional service references
    through LLM operations. Similar to ToolContext for tools.
    
    Attributes:
        request_id: Unique request identifier
        user_id: User making the request
        session_id: Session identifier
        tenant_id: Tenant/organization identifier
        trace_id: Distributed tracing ID
        locale: User locale/language
        timezone: User timezone
        metadata: Additional context metadata
        config: Runtime configuration overrides
        
    Example:
        context = LLMContext(
            user_id="user-123",
            session_id="session-456",
            metadata={"app": "chatbot"}
        )
    """
    
    # Identifiers
    request_id: str = Field(
        default_factory=lambda: f"{PREFIX_REQUEST}{uuid.uuid4()}",
        description="Unique request identifier"
    )
    user_id: Optional[str] = Field(
        default=None,
        description="User making the request"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Session identifier"
    )
    tenant_id: Optional[str] = Field(
        default=None,
        description="Tenant/organization identifier"
    )
    trace_id: Optional[str] = Field(
        default=None,
        description="Distributed tracing ID"
    )
    
    # Localization
    locale: str = Field(
        default=DEFAULT_LOCALE,
        description="User locale/language"
    )
    timezone: str = Field(
        default=DEFAULT_TIMEZONE,
        description="User timezone"
    )
    
    # Additional data
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context metadata"
    )
    config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Runtime configuration overrides"
    )
    
    model_config = {
        "arbitrary_types_allowed": True,
        "json_schema_extra": {
            "examples": [
                {
                    CONTEXT_REQUEST_ID: f"{PREFIX_REQUEST}12345",
                    CONTEXT_USER_ID: "user-001",
                    CONTEXT_SESSION_ID: "session-abc",
                    CONTEXT_LOCALE: DEFAULT_LOCALE,
                    CONTEXT_METADATA: {
                        "app": "chatbot",
                        "version": "1.0"
                    }
                }
            ]
        }
    }
    
    def with_metadata(self, **kwargs) -> 'LLMContext':
        """
        Create a new context with additional metadata.
        
        Args:
            **kwargs: Metadata key-value pairs to add
            
        Returns:
            New LLMContext with merged metadata
            
        Example:
            new_ctx = context.with_metadata(model="gpt-4", temperature=0.7)
        """
        new_metadata = self.metadata.copy()
        new_metadata.update(kwargs)
        return self.model_copy(update={CONTEXT_METADATA: new_metadata})
    
    def with_config(self, **kwargs) -> 'LLMContext':
        """
        Create a new context with additional config.
        
        Args:
            **kwargs: Config key-value pairs to add
            
        Returns:
            New LLMContext with merged config
            
        Example:
            new_ctx = context.with_config(timeout=60, max_retries=5)
        """
        new_config = self.config.copy()
        new_config.update(kwargs)
        return self.model_copy(update={CONTEXT_CONFIG: new_config})
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """
        Get a metadata value.
        
        Args:
            key: Metadata key
            default: Default value if key not found
            
        Returns:
            Metadata value or default
        """
        return self.metadata.get(key, default)
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Get a config value.
        
        Args:
            key: Config key
            default: Default value if key not found
            
        Returns:
            Config value or default
        """
        return self.config.get(key, default)
    
    def to_log_dict(self) -> Dict[str, Any]:
        """
        Convert context to a dictionary suitable for logging.
        
        Returns:
            Dictionary with loggable context data
        """
        return {
            CONTEXT_REQUEST_ID: self.request_id,
            CONTEXT_USER_ID: self.user_id,
            CONTEXT_SESSION_ID: self.session_id,
            CONTEXT_TENANT_ID: self.tenant_id,
            CONTEXT_TRACE_ID: self.trace_id,
            CONTEXT_LOCALE: self.locale,
        }


# Helper functions

def create_context(
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    **kwargs
) -> LLMContext:
    """
    Helper to create an LLMContext.
    
    Args:
        user_id: Optional user ID
        session_id: Optional session ID
        **kwargs: Additional context fields
        
    Returns:
        LLMContext instance
    """
    return LLMContext(
        user_id=user_id,
        session_id=session_id,
        **kwargs
    )


if __name__ == "__main__":
    test_context = create_context(
        user_id=PREFIX_TEST_USER,
        session_id=PREFIX_TEST_SESSION,
        tenant_id=PREFIX_TEST_TENANT,
        metadata={TEST_ENVIRONMENT_KEY: TEST_ENVIRONMENT_VALUE}
    )
    print(test_context)
