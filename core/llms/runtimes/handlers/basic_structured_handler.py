"""
Basic Structured Output Handler.

Provides comprehensive structured output handling with validation and retry logic.
"""

from typing import Optional, Type
from pydantic import BaseModel
from ...interfaces.llm_interfaces import IStructuredOutputHandler, Parameters
from ...spec.llm_output_config import OutputConfig, OutputFormat, ParseResult
from utils.converters import pydantic_to_openai_schema, parse_structured_response
from utils.logging.LoggerAdaptor import LoggerAdaptor


class BasicStructuredHandler(IStructuredOutputHandler):
    """
    Basic implementation of IStructuredOutputHandler.
    
    Handles:
    - Pydantic model validation
    - JSON dict validation
    - Response mode handling (STRICT, IMMEDIATE, BEST_EFFORT)
    - Retry logic for validation failures
    
    Usage:
        handler = BasicStructuredHandler()
        params = handler.prepare_request(params, output_config)
        result = handler.validate_output(content, output_config)
    """
    
    def __init__(self):
        """Initialize handler."""
        self.logger = LoggerAdaptor.get_logger("llm.handler.structured")
        self._response_schema: Optional[Type[BaseModel]] = None
    
    def prepare_request(
        self,
        params: Parameters,
        output_config: OutputConfig
    ) -> Parameters:
        """
        Prepare request parameters for structured output.
        
        Converts Pydantic models to OpenAI schema format.
        
        Args:
            params: Request parameters
            output_config: Output configuration
            
        Returns:
            Modified parameters with response_format
        """
        if not output_config.expects_structured_output:
            return params
        
        result = params.copy()
        response_format = output_config.response_format
        
        # If it's a Pydantic model class, convert to OpenAI schema
        if isinstance(response_format, type) and issubclass(response_format, BaseModel):
            self.logger.info(
                "Converting Pydantic model to OpenAI schema",
                model_name=response_format.__name__
            )
            self._response_schema = response_format
            result["response_format"] = pydantic_to_openai_schema(
                response_format,
                strict=output_config.strict_schema
            )
        elif isinstance(response_format, dict):
            # Already in OpenAI format
            result["response_format"] = response_format
            self.logger.debug("Using provided response_format dict")
        
        return result
    
    def validate_output(
        self,
        content: str,
        output_config: OutputConfig
    ) -> ParseResult:
        """
        Validate response content against output configuration.
        
        Args:
            content: Response content
            output_config: Output configuration with schema
            
        Returns:
            ParseResult with validation status and parsed output
        """
        if not output_config.expects_structured_output:
            return ParseResult(
                success=True,
                parsed_output=content,
                raw_content=content
            )
        
        output_type = output_config.output_format_type
        
        try:
            if output_type == OutputFormat.PYDANTIC:
                schema = self._response_schema or output_config.response_format
                if isinstance(schema, type) and issubclass(schema, BaseModel):
                    validated_obj = parse_structured_response(
                        content,
                        schema,
                        partial=False
                    )
                    
                    self.logger.info(
                        "Structured output validated successfully",
                        schema=schema.__name__
                    )
                    
                    return ParseResult(
                        success=True,
                        parsed_output=validated_obj,
                        raw_content=content
                    )
            
            elif output_type == OutputFormat.JSON:
                validated_obj = parse_structured_response(
                    content,
                    model_class=None,
                    partial=False
                )
                
                self.logger.info("JSON output validated successfully")
                
                return ParseResult(
                    success=True,
                    parsed_output=validated_obj,
                    raw_content=content
                )
            
            # TEXT format - return as-is
            return ParseResult(
                success=True,
                parsed_output=content,
                raw_content=content
            )
            
        except Exception as e:
            self.logger.error(
                "Structured output validation failed",
                error=str(e),
                content_preview=content[:200] if content else ""
            )
            
            return ParseResult(
                success=False,
                parsed_output=None,
                raw_content=content,
                error=str(e)
            )
    
    def handle_validation_failure(
        self,
        error: Exception,
        output_config: OutputConfig,
        attempt: int
    ) -> bool:
        """
        Handle validation failure and decide whether to retry.
        
        Args:
            error: Validation error
            output_config: Output configuration
            attempt: Current attempt number (1-indexed)
            
        Returns:
            True if should retry, False otherwise
        """
        # Check if retries are configured
        if not output_config.should_retry_on_parse_failure:
            return False
        
        # Check if we've exceeded max retries
        if attempt >= output_config.max_retries + 1:
            self.logger.warning(
                "Max retries exceeded for structured output",
                attempt=attempt,
                max_retries=output_config.max_retries
            )
            return False
        
        self.logger.info(
            f"Retrying structured output validation (attempt {attempt + 1})",
            error=str(error)
        )
        return True
    
    def get_response_schema(self) -> Optional[Type[BaseModel]]:
        """Get the current response schema."""
        return self._response_schema
    
    def reset(self) -> None:
        """Reset handler state."""
        self._response_schema = None

