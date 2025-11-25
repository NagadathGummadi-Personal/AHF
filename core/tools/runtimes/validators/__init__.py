"""
Validators for Tools Specification System.

This module provides pluggable validation strategies for parameter validation,
allowing runtime selection of the appropriate validation approach for each tool.

Strategy Pattern Implementation:
=================================
All validators implement IValidator, allowing runtime selection of the
appropriate validation strategy for each tool.

Available Strategies:
=====================
- BasicValidator: Comprehensive parameter validation with type checking, constraints, etc.
- NoOpValidator: Disables validation (for development/testing)

Usage:
    from core.tools.executors.validators import BasicValidator
    
    # Use basic validator
    validator = BasicValidator()
    await validator.validate(args, spec)
    
    # Or use factory
    from core.tools.executors.validators import ValidatorFactory
    validator = ValidatorFactory.get_validator('basic')
    spec.validator = validator

Extending:
==========
Create custom validator by implementing IValidator:

    class CustomValidator:
        async def validate(self, args: Dict[str, Any], spec: ToolSpec) -> None:
            # Your validation logic
            pass
    
    # Register custom validator
    ValidatorFactory.register('custom', CustomValidator())
    validator = ValidatorFactory.get_validator('custom')

Note:
    Validators should raise ToolError with ERROR_VALIDATION code when validation fails.
"""

from .basic_validator import BasicValidator
from .noop_validator import NoOpValidator
from .validator_factory import ValidatorFactory

__all__ = [
    "BasicValidator",
    "NoOpValidator",
    "ValidatorFactory",
]

