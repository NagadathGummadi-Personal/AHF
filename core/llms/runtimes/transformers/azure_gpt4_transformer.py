"""
Azure GPT-4 Parameter Transformer.

Transforms standard parameters to Azure GPT-4.x specific format.
"""

from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel
from ...interfaces.llm_interfaces import IParameterTransformer, Parameters
from ...spec.llm_schema import ModelMetadata
from ...constants import (
    PARAM_MAX_TOKENS,
    PARAM_MAX_COMPLETION_TOKENS,
    PARAM_TEMPERATURE,
)
from utils.converters import pydantic_to_openai_schema
from utils.logging.LoggerAdaptor import LoggerAdaptor


class AzureGPT4Transformer(IParameterTransformer):
    """
    Parameter transformer for Azure GPT-4.x models.
    
    Handles GPT-4.1 specific transformations:
    - max_tokens → max_completion_tokens
    - Temperature removal (if not supported)
    - Response format conversion (Pydantic → OpenAI schema)
    
    Usage:
        transformer = AzureGPT4Transformer()
        params = transformer.transform(params, metadata)
    """
    
    def __init__(
        self,
        remove_temperature: bool = True,
        convert_response_format: bool = True
    ):
        """
        Initialize transformer.
        
        Args:
            remove_temperature: Whether to remove temperature parameter
            convert_response_format: Whether to convert Pydantic models to schema
        """
        self.remove_temperature = remove_temperature
        self.convert_response_format = convert_response_format
        self.logger = LoggerAdaptor.get_logger("llm.transformer.azure_gpt4")
        self._response_schema: Optional[Type[BaseModel]] = None
    
    def transform(
        self,
        params: Parameters,
        metadata: ModelMetadata
    ) -> Parameters:
        """
        Transform parameters for Azure GPT-4.x models.
        
        Transformations:
        1. max_tokens → max_completion_tokens
        2. Remove temperature (if configured)
        3. Convert Pydantic model to OpenAI schema (if configured)
        
        Args:
            params: Standard parameters
            metadata: Model metadata
            
        Returns:
            Transformed parameters
        """
        transformed = params.copy()
        
        # 1. Transform max_tokens to max_completion_tokens
        if PARAM_MAX_TOKENS in transformed:
            transformed[PARAM_MAX_COMPLETION_TOKENS] = transformed.pop(PARAM_MAX_TOKENS)
            self.logger.debug(
                "Transformed max_tokens to max_completion_tokens",
                value=transformed[PARAM_MAX_COMPLETION_TOKENS]
            )
        
        # 2. Remove temperature if configured
        if self.remove_temperature and PARAM_TEMPERATURE in transformed:
            self.logger.warning(
                "Temperature parameter removed (not supported)",
                requested_temperature=transformed[PARAM_TEMPERATURE]
            )
            del transformed[PARAM_TEMPERATURE]
        
        # 3. Handle response_format (structured output)
        if self.convert_response_format and "response_format" in transformed:
            response_format = transformed["response_format"]
            
            # If it's a Pydantic model class, convert to OpenAI schema
            if isinstance(response_format, type) and issubclass(response_format, BaseModel):
                self.logger.info(
                    "Converting Pydantic model to OpenAI schema",
                    model_name=response_format.__name__
                )
                self._response_schema = response_format
                transformed["response_format"] = pydantic_to_openai_schema(response_format)
                self.logger.debug(
                    "Structured output schema configured",
                    schema_name=response_format.__name__
                )
            elif isinstance(response_format, dict):
                self.logger.debug("Using provided response_format dict")
                if "json_schema" in response_format:
                    schema_info = response_format["json_schema"]
                    self.logger.debug(
                        "Response format configured",
                        schema_name=schema_info.get("name", "unknown")
                    )
        
        return transformed
    
    def get_supported_parameters(self) -> List[str]:
        """
        Get list of parameters this transformer handles.
        
        Returns:
            List of parameter names
        """
        return [
            PARAM_MAX_TOKENS,
            PARAM_MAX_COMPLETION_TOKENS,
            PARAM_TEMPERATURE,
            "response_format",
        ]
    
    def get_response_schema(self) -> Optional[Type[BaseModel]]:
        """
        Get the response schema if a Pydantic model was converted.
        
        Returns:
            Pydantic model class or None
        """
        return self._response_schema
    
    def reset(self) -> None:
        """Reset transformer state."""
        self._response_schema = None

