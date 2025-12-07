"""
Basic Prompt Validator Implementation.

Provides basic validation with configurable rules for content,
variables, labels, and metadata.
"""

import re
from typing import Any, Dict, List, Optional, Set, TYPE_CHECKING

from ...interfaces.prompt_registry_interfaces import (
    IPromptValidator,
    ValidationResult,
)

if TYPE_CHECKING:
    from ...spec.prompt_models import PromptMetadata


class BasicPromptValidator(IPromptValidator):
    """
    Basic Prompt Validator with configurable rules.
    
    Provides validation for:
    - Content length limits
    - Blocked patterns (potential injection attempts)
    - Label format validation
    - Variable value validation
    
    Usage:
        validator = BasicPromptValidator(
            max_content_length=50000,
            max_variable_length=1000,
            blocked_patterns=[
                r'ignore.*previous.*instructions',
                r'system:\\s*',
                r'<\\|.*\\|>'
            ],
            label_pattern=r'^[a-z][a-z0-9_\\.]*$'
        )
        
        result = validator.validate_content(user_provided_content)
        if not result.is_valid:
            raise ValidationError(result.errors)
    """
    
    # Default blocked patterns for prompt injection detection
    DEFAULT_BLOCKED_PATTERNS = [
        r'ignore\s+(all\s+)?previous\s+instructions',
        r'disregard\s+(all\s+)?previous',
        r'forget\s+(everything|all)',
        r'new\s+instructions?\s*:',
        r'system\s*:\s*',
        r'<\|.*\|>',  # Special tokens
        r'\[INST\]',  # Instruction markers
        r'\[/INST\]',
        r'<<SYS>>',
        r'<</SYS>>',
    ]
    
    def __init__(
        self,
        max_content_length: int = 100000,
        max_variable_length: int = 10000,
        max_label_length: int = 200,
        blocked_patterns: Optional[List[str]] = None,
        label_pattern: str = r'^[a-zA-Z][a-zA-Z0-9_\.\-]*$',
        case_insensitive: bool = True,
        sanitize_html: bool = True,
    ):
        """
        Initialize validator with configuration.
        
        Args:
            max_content_length: Maximum allowed content length
            max_variable_length: Maximum allowed variable value length
            max_label_length: Maximum allowed label length
            blocked_patterns: Regex patterns to block (defaults to injection patterns)
            label_pattern: Regex pattern for valid labels
            case_insensitive: Whether pattern matching is case-insensitive
            sanitize_html: Whether to escape HTML in sanitization
        """
        self.max_content_length = max_content_length
        self.max_variable_length = max_variable_length
        self.max_label_length = max_label_length
        self.label_pattern = re.compile(label_pattern)
        self.case_insensitive = case_insensitive
        self.sanitize_html = sanitize_html
        
        # Compile blocked patterns
        patterns = blocked_patterns if blocked_patterns is not None else self.DEFAULT_BLOCKED_PATTERNS
        flags = re.IGNORECASE if case_insensitive else 0
        self.blocked_patterns = [re.compile(p, flags) for p in patterns]
    
    def validate_content(self, content: str) -> ValidationResult:
        """Validate prompt content."""
        errors = []
        warnings = []
        
        # Check length
        if len(content) > self.max_content_length:
            errors.append(
                f"Content exceeds maximum length of {self.max_content_length} characters"
            )
        
        # Check for blocked patterns
        for pattern in self.blocked_patterns:
            if pattern.search(content):
                errors.append(
                    f"Content contains blocked pattern: {pattern.pattern}"
                )
        
        # Check for potential issues (warnings)
        if content.count('{') != content.count('}'):
            warnings.append("Unbalanced curly braces in content")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            sanitized_value=self.sanitize_content(content) if len(errors) == 0 else None,
            warnings=warnings
        )
    
    def validate_variables(
        self,
        variables: Dict[str, Any],
        allowed_keys: Optional[Set[str]] = None
    ) -> ValidationResult:
        """Validate variables before template substitution."""
        errors = []
        warnings = []
        sanitized = {}
        
        for key, value in variables.items():
            # Check if key is allowed
            if allowed_keys is not None and key not in allowed_keys:
                errors.append(f"Variable '{key}' is not in allowed keys")
                continue
            
            # Validate string values
            if isinstance(value, str):
                # Check length
                if len(value) > self.max_variable_length:
                    errors.append(
                        f"Variable '{key}' exceeds maximum length of {self.max_variable_length}"
                    )
                    continue
                
                # Check for blocked patterns
                for pattern in self.blocked_patterns:
                    if pattern.search(value):
                        errors.append(
                            f"Variable '{key}' contains blocked pattern"
                        )
                        break
                else:
                    sanitized[key] = self.sanitize_variable_value(value)
            else:
                # Non-string values pass through (could add type-specific validation)
                sanitized[key] = value
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            sanitized_value=sanitized if len(errors) == 0 else None,
            warnings=warnings
        )
    
    def validate_label(self, label: str) -> ValidationResult:
        """Validate a prompt label."""
        errors = []
        
        # Check length
        if len(label) > self.max_label_length:
            errors.append(
                f"Label exceeds maximum length of {self.max_label_length}"
            )
        
        # Check format
        if not self.label_pattern.match(label):
            errors.append(
                f"Label does not match required pattern: {self.label_pattern.pattern}"
            )
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            sanitized_value=label if len(errors) == 0 else None
        )
    
    def validate_metadata(self, metadata: 'PromptMetadata') -> ValidationResult:
        """Validate prompt metadata."""
        errors = []
        warnings = []
        
        # Validate tags
        if metadata.tags:
            for tag in metadata.tags:
                if len(tag) > 100:
                    errors.append(f"Tag '{tag[:50]}...' exceeds maximum length")
        
        # Validate description
        if metadata.description and len(metadata.description) > 5000:
            errors.append("Description exceeds maximum length of 5000")
        
        # Validate eval scores
        if metadata.llm_eval_score is not None:
            if not 0.0 <= metadata.llm_eval_score <= 1.0:
                errors.append("LLM eval score must be between 0.0 and 1.0")
        
        if metadata.human_eval_score is not None:
            if not 0.0 <= metadata.human_eval_score <= 1.0:
                errors.append("Human eval score must be between 0.0 and 1.0")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            sanitized_value=metadata if len(errors) == 0 else None,
            warnings=warnings
        )
    
    def sanitize_content(self, content: str) -> str:
        """Sanitize prompt content."""
        result = content
        
        # Optionally escape HTML
        if self.sanitize_html:
            # Only escape in non-template parts (preserve {variables})
            pass  # Basic implementation leaves content as-is
        
        return result
    
    def sanitize_variable_value(self, value: Any) -> Any:
        """Sanitize a single variable value."""
        if isinstance(value, str):
            result = value
            
            # Escape HTML if enabled
            if self.sanitize_html:
                result = (
                    result
                    .replace('&', '&amp;')
                    .replace('<', '&lt;')
                    .replace('>', '&gt;')
                    .replace('"', '&quot;')
                    .replace("'", '&#x27;')
                )
            
            return result
        
        return value

