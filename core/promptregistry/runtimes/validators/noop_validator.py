"""
NoOp Prompt Validator Implementation.

A validator that passes all validation. Use for development/testing
or when validation is handled externally.
"""

from typing import Any, Dict, Optional, Set, TYPE_CHECKING

from ...interfaces.prompt_registry_interfaces import (
    IPromptValidator,
    ValidationResult,
)

if TYPE_CHECKING:
    from ...spec.prompt_models import PromptMetadata


class NoOpPromptValidator(IPromptValidator):
    """
    NoOp (No Operation) Prompt Validator.
    
    Passes all validation without any checks.
    Use for development, testing, or when validation is handled elsewhere.
    
    Usage:
        validator = NoOpPromptValidator()
        
        # Always returns valid
        result = validator.validate_content("any content")
        assert result.is_valid
        
        # Variables passed through unchanged
        result = validator.validate_variables({"key": "value"})
        assert result.sanitized_value == {"key": "value"}
    """
    
    def validate_content(self, content: str) -> ValidationResult:
        """Always returns valid."""
        return ValidationResult(
            is_valid=True,
            errors=[],
            sanitized_value=content
        )
    
    def validate_variables(
        self,
        variables: Dict[str, Any],
        allowed_keys: Optional[Set[str]] = None
    ) -> ValidationResult:
        """Always returns valid with variables unchanged."""
        return ValidationResult(
            is_valid=True,
            errors=[],
            sanitized_value=variables
        )
    
    def validate_label(self, label: str) -> ValidationResult:
        """Always returns valid."""
        return ValidationResult(
            is_valid=True,
            errors=[],
            sanitized_value=label
        )
    
    def validate_metadata(self, metadata: 'PromptMetadata') -> ValidationResult:
        """Always returns valid."""
        return ValidationResult(
            is_valid=True,
            errors=[],
            sanitized_value=metadata
        )
    
    def sanitize_content(self, content: str) -> str:
        """Returns content unchanged."""
        return content
    
    def sanitize_variable_value(self, value: Any) -> Any:
        """Returns value unchanged."""
        return value

