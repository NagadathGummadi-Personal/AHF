"""
Azure OpenAI Base LLM Implementation.

This module provides the base LLM implementation for Azure OpenAI Service.
Uses pluggable components for validation, transformation, parsing, and structured output handling.

Pluggable Components:
- ILLMValidator: Message and parameter validation
- IParameterTransformer: Parameter transformations
- IResponseParser: Response parsing
- IStructuredOutputHandler: Structured output handling

Model-specific implementations can override components or hook methods.
"""

import json
import time
from typing import Any, Dict, List, AsyncIterator, Optional

from ..base.implementation import BaseLLM
from ...spec.llm_result import LLMResponse, LLMStreamChunk, LLMUsage
from ...spec.llm_context import LLMContext
from ...spec.llm_output_config import OutputConfig, ResponseMode
from ...enum import FinishReason
from ...interfaces.llm_interfaces import (
    ILLMValidator,
    IParameterTransformer,
    IResponseParser,
    IStructuredOutputHandler,
)
from ...runtimes.validators import LLMValidatorFactory
from ...runtimes.transformers import TransformerFactory
from ...runtimes.parsers import AzureResponseParser
from ...runtimes.handlers import StructuredHandlerFactory
from ...constants import (
    OPENAI_FIELD_MESSAGES,
    STREAM_DATA_PREFIX,
    STREAM_DATA_PREFIX_LENGTH,
    STREAM_DONE_TOKEN,
    STREAM_PARAM_TRUE,
    PARAM_MAX_TOKENS,
    PARAM_MAX_COMPLETION_TOKENS,
)
from utils.logging.LoggerAdaptor import LoggerAdaptor


class AzureBaseLLM(BaseLLM):
    """
    Azure OpenAI base LLM implementation with pluggable components.
    
    Uses pluggable components for all operations:
    - Validator: Message and parameter validation
    - Transformer: Parameter transformations
    - Parser: Response parsing
    - StructuredHandler: Structured output handling
    
    Default components are used if not specified. Model-specific implementations
    can provide custom components or override hook methods.
    
    Example:
        # Use default components
        llm = GPT41MiniLLM(connector)
        
        # Use custom validator
        llm = GPT41MiniLLM(
            connector,
            validator=LLMValidatorFactory.get_validator('noop')
        )
        
        # Use custom transformer
        llm = GPT41MiniLLM(
            connector,
            transformer=MyCustomTransformer()
        )
    """
    
    def __init__(
        self,
        metadata,
        connector,
        validator: Optional[ILLMValidator] = None,
        transformer: Optional[IParameterTransformer] = None,
        parser: Optional[IResponseParser] = None,
        structured_handler: Optional[IStructuredOutputHandler] = None,
    ):
        """
        Initialize Azure Base LLM with pluggable components.
        
        Args:
            metadata: Model metadata
            connector: Azure connector instance
            validator: Custom validator (default: BasicLLMValidator)
            transformer: Custom transformer (default: NoOpTransformer)
            parser: Custom parser (default: AzureResponseParser)
            structured_handler: Custom handler (default: BasicStructuredHandler)
        """
        super().__init__(metadata=metadata, connector=connector)
        self.logger = LoggerAdaptor.get_logger("llm.azure-base")
        
        # Initialize pluggable components with defaults
        self.validator = validator or LLMValidatorFactory.get_validator("basic")
        self.transformer = transformer or TransformerFactory.get_transformer("noop")
        self.parser = parser or AzureResponseParser(
            deployment_name=getattr(connector, 'deployment_name', None)
        )
        self.structured_handler = structured_handler or StructuredHandlerFactory.get_handler("basic")
        
        # State
        self._output_config: Optional[OutputConfig] = None
    
    # ============================================================================
    # MAIN API METHODS
    # ============================================================================
    
    async def get_answer(
        self,
        messages: List[Dict[str, Any]],
        ctx: LLMContext,
        output_config: Optional[OutputConfig] = None,
        **kwargs: Any
    ) -> LLMResponse:
        """
        Get complete response from Azure OpenAI.
        
        Uses pluggable components for validation, transformation, and parsing.
        If prompt_id is set in context and a prompt registry is configured,
        usage metrics are automatically recorded.
        
        Args:
            messages: List of message dicts
            ctx: LLM context (can include prompt_id for metrics tracking)
            output_config: Output configuration (optional)
            **kwargs: Additional parameters
            
        Returns:
            LLMResponse with content and usage
        """
        start_time = time.time()
        success = True
        llm_response = None
        
        try:
            # 1. Check output support
            self._check_text_output_support()
            
            # 2. Setup output configuration
            self._setup_output_config(output_config, kwargs)
            
            # 3. Validate using pluggable validator
            await self.validator.validate_messages(messages, self.metadata)
            await self.validator.validate_parameters(kwargs, self.metadata)
            
            # 4. Model-specific validation hook
            self._validate_model_specific(messages, kwargs)
            
            # 5. Merge and transform parameters using pluggable transformer
            params = self._merge_parameters(kwargs)
            params = self.transformer.transform(params, self.metadata)
            params = self._transform_parameters(params)  # Model-specific hook
            
            # 6. Prepare for structured output
            if self._output_config and self._output_config.expects_structured_output:
                params = self.structured_handler.prepare_request(params, self._output_config)
            
            # 7. Validate token limits
            max_tokens = params.get(PARAM_MAX_COMPLETION_TOKENS) or params.get(PARAM_MAX_TOKENS, self.metadata.max_output_tokens)
            await self.validator.validate_token_limits(messages, max_tokens, self.metadata)
            
            # 8. Apply parameter mappings
            mapped_params = self._apply_parameter_mappings(params)
            
            # 9. Build payload
            payload = self._build_azure_payload(messages, mapped_params)
            payload = self._build_model_payload(payload)  # Model-specific hook
            
            # 10. Execute with retry logic
            llm_response = await self._execute_with_retry(messages, payload, start_time)
            
            return llm_response
            
        except Exception:
            success = False
            raise
            
        finally:
            # 11. Record prompt usage if registry is set
            latency_ms = (time.time() - start_time) * 1000
            await self._record_prompt_usage(ctx, llm_response, latency_ms, success)
            
            # 12. Reset state
            self._reset_output_state()
    
    async def stream_answer(
        self,
        messages: List[Dict[str, Any]],
        ctx: LLMContext,
        output_config: Optional[OutputConfig] = None,
        **kwargs: Any
    ) -> AsyncIterator[LLMStreamChunk]:
        """
        Get streaming response from Azure OpenAI.
        
        If prompt_id is set in context and a prompt registry is configured,
        usage metrics are automatically recorded after streaming completes.
        
        Args:
            messages: List of message dicts
            ctx: LLM context (can include prompt_id for metrics tracking)
            output_config: Output configuration (optional)
            **kwargs: Additional parameters
            
        Yields:
            LLMStreamChunk objects
        """
        start_time = time.time()
        success = True
        final_usage = None
        
        try:
            # 1. Check output support
            self._check_text_output_support()
            
            # 2. Setup output configuration
            self._setup_output_config(output_config, kwargs)
            
            # 3. Validate
            await self.validator.validate_messages(messages, self.metadata)
            await self.validator.validate_parameters(kwargs, self.metadata)
            self._validate_model_specific(messages, kwargs)
            
            # 4. Transform parameters
            params = self._merge_parameters(kwargs)
            params = self.transformer.transform(params, self.metadata)
            params = self._transform_parameters(params)
            
            # 5. Prepare for structured output
            if self._output_config and self._output_config.expects_structured_output:
                params = self.structured_handler.prepare_request(params, self._output_config)
            
            # 6. Validate token limits
            max_tokens = params.get(PARAM_MAX_COMPLETION_TOKENS) or params.get(PARAM_MAX_TOKENS, self.metadata.max_output_tokens)
            await self.validator.validate_token_limits(messages, max_tokens, self.metadata)
            
            # 7. Build streaming payload
            mapped_params = self._apply_parameter_mappings(params)
            payload = self._build_azure_payload(messages, mapped_params)
            payload = self._build_model_payload(payload)
            payload[STREAM_PARAM_TRUE] = True
            
            # 8. Stream with structured output handling if needed
            if self._output_config and self._output_config.expects_structured_output:
                async for chunk in self._stream_with_structured_output(messages, payload, start_time):
                    if chunk.is_final and chunk.usage:
                        final_usage = chunk.usage
                    yield chunk
            else:
                async for chunk in self._stream_azure_response(messages, payload, start_time):
                    if chunk.is_final and chunk.usage:
                        final_usage = chunk.usage
                    yield chunk
                    
        except Exception:
            success = False
            raise
            
        finally:
            # 9. Record prompt usage if registry is set
            latency_ms = (time.time() - start_time) * 1000
            # Build a minimal response for metrics recording
            if final_usage:
                from ...spec.llm_result import LLMResponse
                mock_response = LLMResponse(content="", usage=final_usage)
                await self._record_prompt_usage(ctx, mock_response, latency_ms, success)
            else:
                await self._record_prompt_usage(ctx, None, latency_ms, success)
            
            # 10. Reset state
            self._reset_output_state()
    
    # ============================================================================
    # HOOK METHODS - Override in model-specific implementations
    # ============================================================================
    
    def _transform_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Additional model-specific parameter transformations.
        
        Override in subclasses for model-specific transformations.
        Called after the pluggable transformer.
        
        Args:
            params: Parameters (already transformed by pluggable transformer)
            
        Returns:
            Further transformed parameters
        """
        return params
    
    def _validate_model_specific(
        self,
        messages: List[Dict[str, Any]],
        params: Dict[str, Any]
    ) -> None:
        """
        Additional model-specific validations.
        
        Override in subclasses for model-specific validation.
        Called after pluggable validator.
        
        Args:
            messages: Messages to validate
            params: Parameters to validate
        """
        pass
    
    def _build_model_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Additional model-specific payload modifications.
        
        Override in subclasses for model-specific payload changes.
        
        Args:
            payload: Base payload
            
        Returns:
            Modified payload
        """
        return payload
    
    # ============================================================================
    # OUTPUT CONFIGURATION
    # ============================================================================
    
    def _setup_output_config(
        self,
        output_config: Optional[OutputConfig],
        kwargs: Dict[str, Any]
    ) -> None:
        """Setup output configuration."""
        if output_config:
            self._output_config = output_config
            if output_config.response_format:
                kwargs["response_format"] = output_config.response_format
        elif "response_format" in kwargs:
            self._output_config = OutputConfig(
                response_format=kwargs["response_format"],
                max_retries=0,
                response_mode=ResponseMode.BEST_EFFORT
            )
    
    def _reset_output_state(self) -> None:
        """Reset output configuration state."""
        self._output_config = None
        if hasattr(self.structured_handler, 'reset'):
            self.structured_handler.reset()
        if hasattr(self.transformer, 'reset'):
            self.transformer.reset()
    
    # ============================================================================
    # RETRY LOGIC
    # ============================================================================
    
    async def _execute_with_retry(
        self,
        messages: List[Dict[str, Any]],
        payload: Dict[str, Any],
        start_time: float
    ) -> LLMResponse:
        """Execute request with retry logic for structured output."""
        max_attempts = 1
        if self._output_config and self._output_config.should_retry_on_parse_failure:
            max_attempts = self._output_config.max_retries + 1
        
        last_error = None
        last_response = None
        
        for attempt in range(max_attempts):
            try:
                response = await self.connector.request("chat/completions", payload)
                llm_response = self.parser.parse_response(response, start_time, self.metadata)
                last_response = llm_response
                
                # Validate structured output
                if self._output_config and self._output_config.expects_structured_output:
                    parse_result = self.structured_handler.validate_output(
                        llm_response.content,
                        self._output_config
                    )
                    
                    if parse_result.success:
                        llm_response.metadata["structured_output"] = parse_result.parsed_output
                        llm_response.metadata["validation_status"] = "success"
                        llm_response.metadata["parse_attempts"] = attempt + 1
                    else:
                        raise ValueError(parse_result.error or "Validation failed")
                
                return llm_response
                
            except Exception as e:
                last_error = e
                self.logger.warning(f"Attempt {attempt + 1}/{max_attempts} failed", error=str(e))
                
                if self._output_config and self.structured_handler.handle_validation_failure(
                    e, self._output_config, attempt + 1
                ):
                    continue
                
                return self._handle_final_parse_failure(last_response, last_error)
        
        return self._handle_final_parse_failure(last_response, last_error)
    
    def _handle_final_parse_failure(
        self,
        llm_response: Optional[LLMResponse],
        error: Exception
    ) -> LLMResponse:
        """Handle final parsing failure based on response mode."""
        if not self._output_config:
            raise error
        
        response_mode = self._output_config.response_mode
        
        if response_mode == ResponseMode.STRICT:
            raise error
        
        if llm_response:
            llm_response.metadata["structured_output"] = None
            llm_response.metadata["validation_status"] = "failed"
            llm_response.metadata["validation_error"] = str(error)
            return llm_response
        
        raise error
    
    # ============================================================================
    # STREAMING
    # ============================================================================
    
    async def _stream_with_structured_output(
        self,
        messages: List[Dict[str, Any]],
        payload: Dict[str, Any],
        start_time: float
    ) -> AsyncIterator[LLMStreamChunk]:
        """Stream with structured output validation at the end."""
        accumulated_content = []
        final_chunk = None
        
        async for chunk in self._stream_azure_response(messages, payload, start_time):
            if chunk.content:
                accumulated_content.append(chunk.content)
            
            if chunk.is_final:
                final_chunk = chunk
            else:
                yield chunk
        
        if final_chunk and accumulated_content:
            full_content = "".join(accumulated_content)
            
            if self._output_config:
                parse_result = self.structured_handler.validate_output(
                    full_content,
                    self._output_config
                )
                
                if final_chunk.metadata is None:
                    final_chunk.metadata = {}
                
                if parse_result.success:
                    final_chunk.metadata["structured_output"] = parse_result.parsed_output
                    final_chunk.metadata["validation_status"] = "success"
                else:
                    final_chunk.metadata["structured_output"] = None
                    final_chunk.metadata["validation_status"] = "failed"
                    final_chunk.metadata["validation_error"] = parse_result.error
        
        if final_chunk:
            yield final_chunk
    
    async def _stream_azure_response(
        self,
        messages: List[Dict[str, Any]],
        payload: Dict[str, Any],
        start_time: float
    ) -> AsyncIterator[LLMStreamChunk]:
        """Stream Azure OpenAI response."""
        accumulated_content = []
        
        async for line in self.connector.stream_request("chat/completions", payload):
            line = line.strip()
            if not line:
                continue
            
            if line.startswith(STREAM_DATA_PREFIX):
                line = line[STREAM_DATA_PREFIX_LENGTH:]
            
            if line == STREAM_DONE_TOKEN:
                duration_ms = int((time.time() - start_time) * 1000)
                yield LLMStreamChunk(
                    content="",
                    is_final=True,
                    finish_reason=FinishReason.STOP,
                    usage=LLMUsage(
                        prompt_tokens=self._estimate_tokens(messages),
                        completion_tokens=self._estimate_tokens([{"content": "".join(accumulated_content)}]),
                        duration_ms=duration_ms
                    )
                )
                break
            
            try:
                chunk_data = json.loads(line)
                chunk = self.parser.parse_stream_chunk(chunk_data, self.metadata)
                
                if chunk:
                    if chunk.content:
                        accumulated_content.append(chunk.content)
                    
                    if chunk.is_final:
                        duration_ms = int((time.time() - start_time) * 1000)
                        chunk.usage = LLMUsage(
                            prompt_tokens=self._estimate_tokens(messages),
                            completion_tokens=self._estimate_tokens([{"content": "".join(accumulated_content)}]),
                            duration_ms=duration_ms
                        )
                    
                    yield chunk
                    
            except json.JSONDecodeError:
                continue
    
    # ============================================================================
    # HELPER METHODS
    # ============================================================================
    
    def _build_azure_payload(
        self,
        messages: List[Dict[str, Any]],
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build standard Azure OpenAI request payload."""
        return {
            OPENAI_FIELD_MESSAGES: messages,
            **params
        }
    
    # ============================================================================
    # COMPONENT ACCESS
    # ============================================================================
    
    def set_validator(self, validator: ILLMValidator) -> None:
        """Set a custom validator."""
        self.validator = validator
    
    def set_transformer(self, transformer: IParameterTransformer) -> None:
        """Set a custom transformer."""
        self.transformer = transformer
    
    def set_parser(self, parser: IResponseParser) -> None:
        """Set a custom parser."""
        self.parser = parser
    
    def set_structured_handler(self, handler: IStructuredOutputHandler) -> None:
        """Set a custom structured output handler."""
        self.structured_handler = handler
