"""
LLM Node Implementation Module.

This module provides a node that directly invokes a language model.
Unlike agent nodes, LLM nodes make a single LLM call without tools or memory.
"""

import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from ..interfaces import IWorkflowContext
from ..enum import NodeType, DataFormat, DataType
from ..spec import NodeSpec, IOSpec, IOFieldSpec
from ..exceptions import NodeExecutionError
from .base_node import BaseNode

if TYPE_CHECKING:
    from core.llms.interfaces.llm_interfaces import ILLM

logger = logging.getLogger(__name__)


class LLMNode(BaseNode):
    """
    A node that invokes a language model directly.
    
    Configuration:
        llm_id: ID of a registered LLM to use
        llm: Direct LLM instance (alternative to llm_id)
        system_prompt: System prompt for the LLM
        user_prompt_template: Template for user message (supports {variable} substitution)
        temperature: LLM temperature (0.0 - 1.0)
        max_tokens: Maximum tokens in response
        response_format: Expected response format (text, json, etc.)
        output_schema: JSON schema for structured output
        
    Input Spec:
        - message: The user message/prompt (string, required)
        - context: Additional context to include (object, optional)
        - variables: Variables for template substitution (object, optional)
    
    Output Spec:
        - content: LLM response content (string)
        - usage: Token usage statistics (object, optional)
        - model: Model used (string, optional)
    """
    
    # Default I/O specifications
    DEFAULT_INPUT_SPEC = IOSpec(
        fields=[
            IOFieldSpec(
                name="message",
                data_type=DataType.STRING,
                required=True,
                description="The user message or prompt"
            ),
            IOFieldSpec(
                name="context",
                data_type=DataType.OBJECT,
                required=False,
                description="Additional context for the prompt"
            ),
            IOFieldSpec(
                name="variables",
                data_type=DataType.OBJECT,
                required=False,
                description="Variables for template substitution"
            ),
        ],
        format=DataFormat.JSON,
        description="Input for LLM node"
    )
    
    DEFAULT_OUTPUT_SPEC = IOSpec(
        fields=[
            IOFieldSpec(
                name="content",
                data_type=DataType.STRING,
                required=True,
                description="LLM response content"
            ),
            IOFieldSpec(
                name="usage",
                data_type=DataType.OBJECT,
                required=False,
                description="Token usage statistics"
            ),
            IOFieldSpec(
                name="model",
                data_type=DataType.STRING,
                required=False,
                description="Model identifier used"
            ),
        ],
        format=DataFormat.JSON,
        description="Output from LLM node"
    )
    
    def __init__(
        self,
        spec: NodeSpec,
        llm: Optional["ILLM"] = None,
        llm_factory: Optional[Any] = None,
    ):
        """
        Initialize the LLM node.
        
        Args:
            spec: Node specification.
            llm: Optional direct LLM instance.
            llm_factory: Optional factory for creating LLMs.
        """
        if spec.node_type != NodeType.LLM:
            spec.node_type = NodeType.LLM
        
        # Set default I/O specs if not provided
        if not spec.input_spec:
            spec.input_spec = self.DEFAULT_INPUT_SPEC
        if not spec.output_spec:
            spec.output_spec = self.DEFAULT_OUTPUT_SPEC
        
        super().__init__(spec)
        
        self._llm = llm
        self._llm_factory = llm_factory
        self._system_prompt = spec.system_prompt or self._config.get("system_prompt")
        self._user_prompt_template = self._config.get("user_prompt_template")
        self._temperature = self._config.get("temperature", 0.7)
        self._max_tokens = self._config.get("max_tokens")
        self._response_format = self._config.get("response_format", "text")
        self._output_schema = self._config.get("output_schema")
    
    async def execute(
        self,
        input_data: Any,
        context: IWorkflowContext,
    ) -> Any:
        """
        Execute the LLM call.
        
        Args:
            input_data: Input containing message and optional context.
            context: Workflow execution context.
            
        Returns:
            LLM response with content and metadata.
        """
        logger.info(f"Executing LLM node: {self._name}")
        
        # Get or create the LLM
        llm = await self._get_llm(context)
        if not llm:
            raise NodeExecutionError(
                f"No LLM available for node {self._name}",
                node_id=self._id,
                node_type=self._node_type.value,
            )
        
        # Resolve input
        resolved_input = self._resolve_input(context, input_data)
        
        # Build the prompt
        user_message = self._build_user_message(resolved_input)
        
        # Build messages
        messages = []
        if self._system_prompt:
            messages.append({"role": "system", "content": self._system_prompt})
        messages.append({"role": "user", "content": user_message})
        
        try:
            # Build generation kwargs
            gen_kwargs = {
                "temperature": self._temperature,
            }
            if self._max_tokens:
                gen_kwargs["max_tokens"] = self._max_tokens
            if self._output_schema:
                gen_kwargs["response_format"] = {"type": "json_object"}
            
            # Call LLM
            response = await llm.generate(messages, **gen_kwargs)
            
            # Extract result
            output = {
                "content": response.content if hasattr(response, "content") else str(response),
                "model": getattr(response, "model", None),
            }
            
            # Add usage if available
            if hasattr(response, "usage") and response.usage:
                output["usage"] = {
                    "prompt_tokens": getattr(response.usage, "prompt_tokens", 0),
                    "completion_tokens": getattr(response.usage, "completion_tokens", 0),
                    "total_tokens": getattr(response.usage, "total_tokens", 0),
                }
            
            logger.debug(f"LLM node {self._name} completed successfully")
            return output
            
        except Exception as e:
            logger.error(f"LLM node {self._name} failed: {e}")
            raise NodeExecutionError(
                f"LLM execution failed: {e}",
                node_id=self._id,
                node_type=self._node_type.value,
                details={"error": str(e)},
            ) from e
    
    def _build_user_message(self, input_data: Dict[str, Any]) -> str:
        """Build the user message from input and template."""
        # Get base message
        message = input_data.get("message", "")
        if isinstance(message, dict):
            message = str(message)
        
        # If template provided, use it
        if self._user_prompt_template:
            variables = input_data.get("variables", {})
            variables["message"] = message
            
            # Add context if available
            if "context" in input_data:
                variables["context"] = input_data["context"]
            
            try:
                return self._user_prompt_template.format(**variables)
            except KeyError as e:
                logger.warning(f"Template variable not found: {e}, using raw message")
                return message
        
        # Include context in message if provided
        if "context" in input_data and input_data["context"]:
            context_str = str(input_data["context"])
            return f"Context:\n{context_str}\n\nMessage:\n{message}"
        
        return message
    
    async def _get_llm(self, context: IWorkflowContext) -> Optional["ILLM"]:
        """Get or create the LLM instance."""
        if self._llm:
            return self._llm
        
        # Try to get from factory by ID
        llm_id = self._config.get("llm_id")
        if llm_id and self._llm_factory:
            try:
                return self._llm_factory.create(llm_id)
            except Exception as e:
                logger.warning(f"Failed to create LLM {llm_id}: {e}")
        
        # Try to get from context
        llm = context.get("llm")
        if llm:
            return llm
        
        return None
    
    async def validate(self, context: IWorkflowContext) -> List[str]:
        """Validate LLM node configuration."""
        errors = await super().validate(context)
        
        if not self._llm:
            if not self._config.get("llm_id") and not self._llm_factory:
                # Check if context might have LLM
                if not context.get("llm"):
                    errors.append(
                        f"LLM node {self._name}: Must specify llm, llm_id, or provide LLM in context"
                    )
        
        return errors
    
    def set_llm(self, llm: "ILLM") -> None:
        """Set the LLM instance directly."""
        self._llm = llm
    
    def set_system_prompt(self, prompt: str) -> None:
        """Set/update the system prompt."""
        self._system_prompt = prompt


