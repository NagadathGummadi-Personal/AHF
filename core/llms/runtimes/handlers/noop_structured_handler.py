"""
No-Op Structured Output Handler.

Returns content without validation (for debugging/testing).
"""

from typing import Any, Dict
from ...interfaces.llm_interfaces import IStructuredOutputHandler, Parameters
from ...spec.llm_output_config import OutputConfig, ParseResult


class NoOpStructuredHandler(IStructuredOutputHandler):
    """
    No-op implementation of IStructuredOutputHandler.
    
    Returns content without validation. Useful for:
    - Debugging
    - Testing
    - Bypassing structured output validation
    
    Usage:
        handler = NoOpStructuredHandler()
        result = handler.validate_output(content, output_config)  # Always succeeds
    """
    
    def prepare_request(
        self,
        params: Parameters,
        output_config: OutputConfig
    ) -> Parameters:
        """Return parameters unchanged."""
        return params.copy()
    
    def validate_output(
        self,
        content: str,
        output_config: OutputConfig
    ) -> ParseResult:
        """Return content without validation."""
        return ParseResult(
            success=True,
            parsed_output=content,
            raw_content=content
        )
    
    def handle_validation_failure(
        self,
        error: Exception,
        output_config: OutputConfig,
        attempt: int
    ) -> bool:
        """Never retry in noop mode."""
        return False

