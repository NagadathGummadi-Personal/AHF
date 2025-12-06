"""
Human Input Node Implementation Module.

This module provides a node that pauses workflow execution to wait for
human input or approval. Essential for Human-in-the-Loop (HITL) workflows.
"""

import logging
from typing import Any, Dict, List, Optional

from ..interfaces import IWorkflowContext
from ..enum import NodeType, DataFormat, DataType, WorkflowState
from ..spec import NodeSpec, IOSpec, IOFieldSpec
from ..exceptions import NodeExecutionError
from .base_node import BaseNode

logger = logging.getLogger(__name__)


class HumanInputNode(BaseNode):
    """
    A node that pauses workflow for human input or approval.
    
    This node supports various HITL scenarios:
    - Collecting required information from user (e.g., service name, guest name)
    - Requesting approval for actions
    - Clarification requests
    - Multi-turn conversations
    
    Configuration:
        prompt: Prompt/question to show the user
        required_fields: List of field names that must be provided
        field_prompts: Dict mapping field names to specific prompts
        field_types: Dict mapping field names to expected types
        timeout_seconds: How long to wait for input (0 = no timeout)
        approval_mode: If True, expects yes/no approval
        retry_on_invalid: Whether to retry if validation fails
        max_retries: Maximum retry attempts
        
    Input Spec:
        - context_data: Context to show user (any, optional)
        - existing_values: Already collected values (object, optional)
        
    Output Spec:
        - user_input: The input provided by user (any)
        - fields: Extracted field values (object)
        - approved: If approval_mode, whether user approved (boolean)
        - complete: Whether all required fields are filled (boolean)
    """
    
    DEFAULT_INPUT_SPEC = IOSpec(
        fields=[
            IOFieldSpec(
                name="context_data",
                data_type=DataType.ANY,
                required=False,
                description="Context information to show user"
            ),
            IOFieldSpec(
                name="existing_values",
                data_type=DataType.OBJECT,
                required=False,
                description="Already collected field values"
            ),
        ],
        format=DataFormat.JSON,
        description="Input for Human Input node"
    )
    
    DEFAULT_OUTPUT_SPEC = IOSpec(
        fields=[
            IOFieldSpec(
                name="user_input",
                data_type=DataType.ANY,
                required=True,
                description="Raw input from user"
            ),
            IOFieldSpec(
                name="fields",
                data_type=DataType.OBJECT,
                required=True,
                description="Extracted field values"
            ),
            IOFieldSpec(
                name="approved",
                data_type=DataType.BOOLEAN,
                required=False,
                description="Whether user approved (if approval_mode)"
            ),
            IOFieldSpec(
                name="complete",
                data_type=DataType.BOOLEAN,
                required=True,
                description="Whether all required fields are provided"
            ),
            IOFieldSpec(
                name="missing_fields",
                data_type=DataType.ARRAY,
                required=False,
                description="List of still-missing required fields"
            ),
        ],
        format=DataFormat.JSON,
        description="Output from Human Input node"
    )
    
    def __init__(self, spec: NodeSpec):
        """
        Initialize the human input node.
        
        Args:
            spec: Node specification.
        """
        if spec.node_type != NodeType.HUMAN_INPUT:
            spec.node_type = NodeType.HUMAN_INPUT
        
        if not spec.input_spec:
            spec.input_spec = self.DEFAULT_INPUT_SPEC
        if not spec.output_spec:
            spec.output_spec = self.DEFAULT_OUTPUT_SPEC
        
        super().__init__(spec)
        
        self._prompt = self._config.get("prompt", "Please provide input:")
        self._required_fields = self._config.get("required_fields", [])
        self._field_prompts = self._config.get("field_prompts", {})
        self._field_types = self._config.get("field_types", {})
        self._approval_mode = self._config.get("approval_mode", False)
        self._retry_on_invalid = self._config.get("retry_on_invalid", True)
        self._max_retries = self._config.get("max_retries", 3)
        self._extraction_prompt = self._config.get("extraction_prompt")
    
    async def execute(
        self,
        input_data: Any,
        context: IWorkflowContext,
    ) -> Any:
        """
        Execute the human input request.
        
        This node will signal to the workflow engine that execution should
        pause and wait for human input. The actual waiting is handled by
        the workflow engine, not this node.
        
        Args:
            input_data: Input containing context and existing values.
            context: Workflow execution context.
            
        Returns:
            Output with prompt and required fields info.
        """
        logger.info(f"Executing human input node: {self._name}")
        
        # Resolve input
        resolved_input = self._resolve_input(context, input_data)
        
        # Get existing values
        existing_values = resolved_input.get("existing_values", {})
        if not isinstance(existing_values, dict):
            existing_values = {}
        
        # Merge with any values already in context
        for field in self._required_fields:
            if field not in existing_values:
                ctx_value = context.get(field)
                if ctx_value is not None:
                    existing_values[field] = ctx_value
        
        # Find missing required fields
        missing_fields = [
            field for field in self._required_fields
            if field not in existing_values or existing_values.get(field) is None
        ]
        
        # Check if we have user input waiting in context (from resumed workflow)
        pending_input = context.get(f"_hitl_input_{self._id}")
        
        if pending_input is not None:
            # Process the user input
            return await self._process_user_input(
                pending_input,
                existing_values,
                missing_fields,
                context
            )
        
        # No input yet - signal workflow to pause
        prompt_to_show = self._build_prompt(missing_fields, resolved_input)
        
        # Store state for when we resume
        context.set(f"_hitl_state_{self._id}", {
            "existing_values": existing_values,
            "missing_fields": missing_fields,
            "retry_count": 0,
        })
        
        # Signal that we're waiting for input
        context.set("_waiting_for_input", True)
        context.set("_waiting_node_id", self._id)
        
        result = {
            "status": "waiting",
            "prompt": prompt_to_show,
            "required_fields": self._required_fields,
            "missing_fields": missing_fields,
            "field_prompts": {
                field: self._field_prompts.get(field, f"Please provide {field}")
                for field in missing_fields
            },
            "approval_mode": self._approval_mode,
            "existing_values": existing_values,
        }
        
        logger.info(f"Human input node {self._name}: waiting for input, missing: {missing_fields}")
        return result
    
    async def _process_user_input(
        self,
        user_input: Any,
        existing_values: Dict[str, Any],
        missing_fields: List[str],
        context: IWorkflowContext,
    ) -> Dict[str, Any]:
        """Process input received from user."""
        # Clear the pending input
        context.set(f"_hitl_input_{self._id}", None)
        
        # Extract fields from user input
        extracted_fields = await self._extract_fields(user_input, missing_fields, context)
        
        # Merge with existing values
        all_fields = dict(existing_values)
        all_fields.update(extracted_fields)
        
        # Store extracted values in context
        for field, value in extracted_fields.items():
            context.set(field, value)
        
        # Check what's still missing
        still_missing = [
            field for field in self._required_fields
            if field not in all_fields or all_fields.get(field) is None
        ]
        
        # Handle approval mode
        approved = None
        if self._approval_mode:
            approved = self._check_approval(user_input)
        
        # Determine if complete
        is_complete = len(still_missing) == 0
        if self._approval_mode:
            is_complete = is_complete and approved is not None
        
        result = {
            "user_input": user_input,
            "fields": all_fields,
            "complete": is_complete,
            "missing_fields": still_missing,
        }
        
        if self._approval_mode:
            result["approved"] = approved
        
        # Clear waiting state
        context.set("_waiting_for_input", False)
        context.set("_waiting_node_id", None)
        
        logger.info(
            f"Human input node {self._name}: processed input, "
            f"complete={is_complete}, still_missing={still_missing}"
        )
        
        return result
    
    async def _extract_fields(
        self,
        user_input: Any,
        target_fields: List[str],
        context: IWorkflowContext,
    ) -> Dict[str, Any]:
        """Extract field values from user input."""
        extracted = {}
        
        # If input is already a dict, use direct mapping
        if isinstance(user_input, dict):
            for field in target_fields:
                if field in user_input:
                    extracted[field] = user_input[field]
            return extracted
        
        # If we have an LLM for extraction, use it
        llm = context.get("llm")
        if llm and self._extraction_prompt and isinstance(user_input, str):
            try:
                extraction_result = await self._llm_extract(
                    llm, user_input, target_fields
                )
                extracted.update(extraction_result)
            except Exception as e:
                logger.warning(f"LLM extraction failed: {e}")
        
        # Simple heuristic extraction for single field
        if len(target_fields) == 1 and not extracted:
            extracted[target_fields[0]] = user_input
        
        return extracted
    
    async def _llm_extract(
        self,
        llm: Any,
        user_input: str,
        target_fields: List[str],
    ) -> Dict[str, Any]:
        """Use LLM to extract fields from text."""
        import json
        
        fields_desc = ", ".join(target_fields)
        prompt = self._extraction_prompt or (
            f"Extract the following fields from the user's message: {fields_desc}\n"
            f"User message: {user_input}\n"
            f"Return a JSON object with the extracted values. Use null for missing values."
        )
        
        messages = [{"role": "user", "content": prompt}]
        response = await llm.generate(messages, response_format={"type": "json_object"})
        
        try:
            content = response.content if hasattr(response, "content") else str(response)
            return json.loads(content)
        except json.JSONDecodeError:
            return {}
    
    def _check_approval(self, user_input: Any) -> Optional[bool]:
        """Check if user input indicates approval."""
        if isinstance(user_input, bool):
            return user_input
        
        if isinstance(user_input, dict):
            return user_input.get("approved", user_input.get("confirm"))
        
        if isinstance(user_input, str):
            lower_input = user_input.lower().strip()
            if lower_input in ("yes", "y", "approve", "confirm", "ok", "true", "1"):
                return True
            if lower_input in ("no", "n", "reject", "deny", "cancel", "false", "0"):
                return False
        
        return None
    
    def _build_prompt(
        self,
        missing_fields: List[str],
        input_data: Dict[str, Any],
    ) -> str:
        """Build the prompt to show the user."""
        if self._approval_mode:
            return self._prompt
        
        if not missing_fields:
            return self._prompt
        
        # Build field-specific prompts
        field_prompts = []
        for field in missing_fields:
            field_prompt = self._field_prompts.get(field)
            if field_prompt:
                field_prompts.append(field_prompt)
            else:
                field_prompts.append(f"What is the {field.replace('_', ' ')}?")
        
        if len(field_prompts) == 1:
            return field_prompts[0]
        
        return self._prompt + "\n" + "\n".join(f"- {p}" for p in field_prompts)
    
    async def validate(self, context: IWorkflowContext) -> List[str]:
        """Validate human input node configuration."""
        errors = await super().validate(context)
        
        if not self._prompt and not self._required_fields:
            errors.append(
                f"Human input node {self._name}: Must specify prompt or required_fields"
            )
        
        return errors
    
    def provide_input(self, context: IWorkflowContext, user_input: Any) -> None:
        """
        Provide user input to a waiting node.
        
        Called by the workflow engine when input is received.
        """
        context.set(f"_hitl_input_{self._id}", user_input)
        context.set("_waiting_for_input", False)


