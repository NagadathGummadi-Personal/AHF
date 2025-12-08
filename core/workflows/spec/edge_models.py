"""
Edge Specification Models

Defines the structure for workflow edges including conditions,
metadata, routing logic, pass-through fields, and LLM-based evaluation.

An edge connects two nodes and can include:
- Simple expression conditions
- Dynamic variable conditions
- LLM-based semantic conditions
- Custom function conditions
- Pass-through fields that are extracted and passed to target nodes

Version: 1.0.0
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field, PrivateAttr

from ..enum import (
    EdgeType,
    WorkflowStatus,
    ConditionOperator,
    ConditionJoinOperator,
    EdgeConditionType,
    PassThroughExtractionStrategy,
    LLMEvaluationMode,
)
from ..defaults import (
    DEFAULT_EDGE_VERSION,
    DEFAULT_EDGE_STATUS,
    DEFAULT_EDGE_TYPE,
    DEFAULT_EDGE_PRIORITY,
    DEFAULT_EDGE_WEIGHT,
    DEFAULT_EDGE_CONDITION_TYPE,
    DEFAULT_LLM_EVAL_MODE,
    DEFAULT_LLM_SCORE_THRESHOLD,
    DEFAULT_PASS_THROUGH_EXTRACTION_STRATEGY,
    DEFAULT_PASS_THROUGH_REQUIRED,
    DEFAULT_PASS_THROUGH_ASK_ON_MISSING,
)
from ..constants import (
    ARBITRARY_TYPES_ALLOWED,
    POPULATE_BY_NAME,
    ERROR_VERSION_EXISTS,
    ERROR_INVALID_CONDITION,
    ERROR_LLM_CONDITION_EVALUATION_FAILED,
)


# =============================================================================
# PASS-THROUGH FIELD MODELS
# =============================================================================


class PassThroughField(BaseModel):
    """
    A field to extract and pass through when edge condition is met.
    
    Pass-through fields are extracted from the context or conversation
    and passed to the target node. If the field cannot be found in context,
    an LLM can be used to extract it, or the user can be prompted.
    
    Example:
        Edge condition: "transfer if user's intent is booking"
        Pass-through field: service_name
        - First looks in context for service_name
        - If not found, uses LLM to extract from conversation
        - If still not found, asks user: "Which service would you like to book?"
    
    Attributes:
        name: Field name (e.g., "service_name", "booking_date")
        description: What this field represents (used for LLM extraction and user prompting)
        required: Whether this field must be present to proceed
        default_value: Default value if field cannot be extracted
        source_path: Dot-notation path to look for value in context
        extraction_strategy: Strategy for extracting the field value
        llm_extraction_prompt: Custom prompt for LLM extraction
        ask_user_prompt: Custom prompt when asking user for the value
        validation_regex: Optional regex pattern for validating extracted value
        transform_expr: Optional Python expression to transform the value
    """
    name: str = Field(..., description="Field name to pass through")
    description: str = Field(
        default="",
        description="Description of what this field represents (used for extraction)"
    )
    required: bool = Field(
        default=DEFAULT_PASS_THROUGH_REQUIRED,
        description="Whether this field is required to proceed"
    )
    default_value: Optional[Any] = Field(
        default=None,
        description="Default value if extraction fails"
    )
    source_path: Optional[str] = Field(
        default=None,
        description="Dot-notation path to look for value in context (e.g., 'user.preferences.service')"
    )
    extraction_strategy: PassThroughExtractionStrategy = Field(
        default=PassThroughExtractionStrategy(DEFAULT_PASS_THROUGH_EXTRACTION_STRATEGY),
        description="Strategy for extracting field value"
    )
    ask_on_missing: bool = Field(
        default=DEFAULT_PASS_THROUGH_ASK_ON_MISSING,
        description="Whether to ask user if field cannot be extracted"
    )
    llm_extraction_prompt: Optional[str] = Field(
        default=None,
        description="Custom prompt for LLM extraction (uses description if not set)"
    )
    ask_user_prompt: Optional[str] = Field(
        default=None,
        description="Custom prompt when asking user (generated from description if not set)"
    )
    validation_regex: Optional[str] = Field(
        default=None,
        description="Regex pattern for validating extracted value"
    )
    transform_expr: Optional[str] = Field(
        default=None,
        description="Python expression to transform extracted value (e.g., 'value.strip().lower()')"
    )
    
    model_config = {ARBITRARY_TYPES_ALLOWED: True}
    
    def get_extraction_prompt(self) -> str:
        """Get the prompt for LLM extraction."""
        if self.llm_extraction_prompt:
            return self.llm_extraction_prompt
        return f"Extract the {self.name}: {self.description}"
    
    def get_ask_user_prompt(self) -> str:
        """Get the prompt for asking user."""
        if self.ask_user_prompt:
            return self.ask_user_prompt
        if self.description:
            return f"Please provide {self.description}"
        return f"Please provide the {self.name}"


class PassThroughConfig(BaseModel):
    """
    Configuration for pass-through field extraction.
    
    Attributes:
        fields: List of fields to pass through
        llm_ref: Reference to LLM for extraction (if needed)
        llm_instance: Direct LLM instance
        extraction_context_keys: Keys from context to include for LLM extraction
        fail_on_missing_required: Whether to fail if required fields can't be extracted
    """
    fields: List[PassThroughField] = Field(
        default_factory=list,
        description="Fields to pass through"
    )
    llm_ref: Optional[str] = Field(
        default=None,
        description="Reference to LLM for extraction"
    )
    llm_instance: Optional[Any] = Field(
        default=None,
        description="Direct LLM instance",
        exclude=True
    )
    extraction_context_keys: List[str] = Field(
        default_factory=lambda: ["messages", "conversation_history", "user_input"],
        description="Context keys to include for LLM extraction"
    )
    fail_on_missing_required: bool = Field(
        default=True,
        description="Whether to fail if required fields cannot be extracted"
    )
    
    model_config = {ARBITRARY_TYPES_ALLOWED: True}


# =============================================================================
# LLM CONDITION MODELS
# =============================================================================


class LLMConditionConfig(BaseModel):
    """
    Configuration for LLM-based edge condition evaluation.
    
    LLM conditions allow semantic evaluation of edge conditions using natural language.
    
    Example:
        condition_prompt: "Check if the user's intent is to book a service"
        This will be:
        - Added to agent's prompt as transfer rule (if source is AGENT)
        - Evaluated by LLM after tool execution (if source is TOOL)
    
    Attributes:
        condition_prompt: Natural language description of the condition
        evaluation_mode: How to evaluate (binary, score, classification)
        llm_ref: Reference to LLM for evaluation (required if source is TOOL)
        llm_instance: Direct LLM instance
        score_threshold: Threshold for score-based evaluation
        classification_options: Valid classification options
        include_context_keys: Context keys to include in evaluation
        system_prompt: Custom system prompt for evaluation
        few_shot_examples: Examples for better evaluation accuracy
    """
    condition_prompt: str = Field(
        ...,
        description="Natural language description of the condition to evaluate"
    )
    evaluation_mode: LLMEvaluationMode = Field(
        default=LLMEvaluationMode(DEFAULT_LLM_EVAL_MODE),
        description="How to evaluate the condition"
    )
    llm_ref: Optional[str] = Field(
        default=None,
        description="Reference to LLM for evaluation (required if source node is TOOL)"
    )
    llm_instance: Optional[Any] = Field(
        default=None,
        description="Direct LLM instance",
        exclude=True
    )
    score_threshold: float = Field(
        default=DEFAULT_LLM_SCORE_THRESHOLD,
        ge=0.0,
        le=1.0,
        description="Threshold for score-based evaluation (condition met if score >= threshold)"
    )
    classification_options: List[str] = Field(
        default_factory=list,
        description="Valid classification options (for CLASSIFICATION mode)"
    )
    expected_classification: Optional[str] = Field(
        default=None,
        description="Expected classification for condition to be met"
    )
    include_context_keys: List[str] = Field(
        default_factory=lambda: ["messages", "last_output", "variables"],
        description="Context keys to include in evaluation"
    )
    system_prompt: Optional[str] = Field(
        default=None,
        description="Custom system prompt for evaluation"
    )
    few_shot_examples: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Few-shot examples for better accuracy"
    )
    
    model_config = {ARBITRARY_TYPES_ALLOWED: True}
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for LLM evaluation."""
        if self.system_prompt:
            return self.system_prompt
        
        if self.evaluation_mode == LLMEvaluationMode.BINARY:
            return (
                "You are a condition evaluator. Analyze the given context and determine "
                "if the specified condition is met. Respond with only 'YES' or 'NO'."
            )
        elif self.evaluation_mode == LLMEvaluationMode.SCORE:
            return (
                "You are a condition evaluator. Analyze the given context and determine "
                "how well the specified condition is met. Respond with a score from 0.0 to 1.0, "
                "where 0.0 means condition is not met at all and 1.0 means fully met."
            )
        else:  # CLASSIFICATION
            options = ", ".join(self.classification_options) if self.classification_options else "the appropriate category"
            return (
                f"You are a classifier. Analyze the given context and classify it into "
                f"one of these categories: {options}. Respond with only the category name."
            )
    
    def to_transfer_rule_prompt(self, target_node_name: str) -> str:
        """
        Convert this LLM condition to a transfer rule for agent prompts.
        
        This is used when the source node is an AGENT - the condition
        becomes part of the agent's instructions about when to transfer.
        
        Args:
            target_node_name: Name of the target node for the transfer
            
        Returns:
            str: Transfer rule text to include in agent prompt
        """
        return f"Transfer to '{target_node_name}' when: {self.condition_prompt}"


# =============================================================================
# EDGE CONDITION MODELS
# =============================================================================


class EdgeCondition(BaseModel):
    """
    A single condition for edge evaluation.
    
    Supports multiple condition types:
    - EXPRESSION: Traditional field comparison (field == value)
    - DYNAMIC: Runtime variable evaluation
    - LLM: Semantic evaluation using LLM
    - FUNCTION: Custom function evaluation
    
    Attributes:
        condition_type: Type of condition evaluation
        field: Field/variable to evaluate (for EXPRESSION/DYNAMIC types)
        operator: Comparison operator (for EXPRESSION type)
        value: Value to compare against (for EXPRESSION type)
        custom_func: Custom evaluation function (for FUNCTION type)
        llm_config: LLM evaluation configuration (for LLM type)
        negate: Whether to negate the result
        description: Human-readable description of this condition
    """
    condition_type: EdgeConditionType = Field(
        default=EdgeConditionType(DEFAULT_EDGE_CONDITION_TYPE),
        description="Type of condition evaluation"
    )
    
    # For EXPRESSION and DYNAMIC types
    field: Optional[str] = Field(
        default=None,
        description="Field to evaluate (dot notation supported)"
    )
    operator: ConditionOperator = Field(
        default=ConditionOperator.EQUALS,
        description="Comparison operator"
    )
    value: Optional[Any] = Field(
        default=None,
        description="Value to compare against"
    )
    
    # For FUNCTION type
    custom_func: Optional[Callable[[Any, Dict[str, Any]], bool]] = Field(
        default=None,
        description="Custom evaluation function (field_value, context) -> bool"
    )
    
    # For LLM type
    llm_config: Optional[LLMConditionConfig] = Field(
        default=None,
        description="LLM evaluation configuration"
    )
    
    # Common attributes
    negate: bool = Field(default=False, description="Negate the condition result")
    description: str = Field(default="", description="Human-readable description")
    
    model_config = {ARBITRARY_TYPES_ALLOWED: True}
    
    def evaluate(self, context: Dict[str, Any]) -> bool:
        """
        Evaluate this condition against the given context.
        
        Note: LLM conditions require async evaluation and should use evaluate_async instead.
        For LLM conditions, this method returns False and logs a warning.
        
        Args:
            context: Dictionary containing workflow variables and node outputs
            
        Returns:
            bool: Whether the condition is met
            
        Raises:
            ValueError: If condition is invalid or evaluation fails
        """
        try:
            if self.condition_type == EdgeConditionType.LLM:
                # LLM conditions require async evaluation
                # Return pending flag in context for workflow engine to handle
                context.setdefault("_pending_llm_conditions", []).append(self)
                return False  # Will be evaluated asynchronously
            
            if self.condition_type == EdgeConditionType.FUNCTION:
                result = self._evaluate_function(context)
            elif self.condition_type in (EdgeConditionType.EXPRESSION, EdgeConditionType.DYNAMIC):
                result = self._evaluate_expression(context)
            else:
                raise ValueError(f"Unknown condition type: {self.condition_type}")
            
            return not result if self.negate else result
            
        except Exception as e:
            raise ValueError(
                ERROR_INVALID_CONDITION.format(
                    condition=f"{self.condition_type.value}: {self.field} {getattr(self.operator, 'value', '')} {self.value}: {e}"
                )
            )
    
    async def evaluate_async(
        self,
        context: Dict[str, Any],
        llm: Optional[Any] = None
    ) -> bool:
        """
        Asynchronously evaluate this condition (required for LLM conditions).
        
        Args:
            context: Dictionary containing workflow variables and node outputs
            llm: LLM instance for LLM condition evaluation
            
        Returns:
            bool: Whether the condition is met
        """
        try:
            if self.condition_type == EdgeConditionType.LLM:
                result = await self._evaluate_llm(context, llm)
            elif self.condition_type == EdgeConditionType.FUNCTION:
                result = self._evaluate_function(context)
            else:
                result = self._evaluate_expression(context)
            
            return not result if self.negate else result
            
        except Exception as e:
            raise ValueError(
                ERROR_LLM_CONDITION_EVALUATION_FAILED.format(error=str(e))
            )
    
    def _evaluate_expression(self, context: Dict[str, Any]) -> bool:
        """Evaluate expression-based condition."""
        if not self.field:
            raise ValueError("Field is required for EXPRESSION/DYNAMIC conditions")
        
        field_value = self._get_nested_value(context, self.field)
        return self._evaluate_operator(field_value)
    
    def _evaluate_function(self, context: Dict[str, Any]) -> bool:
        """Evaluate function-based condition."""
        if not self.custom_func:
            raise ValueError("Custom function is required for FUNCTION conditions")
        
        field_value = None
        if self.field:
            field_value = self._get_nested_value(context, self.field)
        
        return self.custom_func(field_value, context)
    
    async def _evaluate_llm(
        self,
        context: Dict[str, Any],
        llm: Optional[Any] = None
    ) -> bool:
        """Evaluate LLM-based condition."""
        if not self.llm_config:
            raise ValueError("LLM config is required for LLM conditions")
        
        # Get LLM instance
        effective_llm = llm or self.llm_config.llm_instance
        if not effective_llm:
            raise ValueError(
                "LLM instance required for LLM condition evaluation. "
                "Provide llm_ref or llm_instance in LLMConditionConfig."
            )
        
        # Build context for evaluation
        eval_context = {}
        for key in self.llm_config.include_context_keys:
            if key in context:
                eval_context[key] = context[key]
        
        # Build messages for LLM
        messages = [
            {"role": "system", "content": self.llm_config.get_system_prompt()},
            {
                "role": "user",
                "content": f"Context:\n{eval_context}\n\nCondition to evaluate:\n{self.llm_config.condition_prompt}"
            }
        ]
        
        # Add few-shot examples if provided
        if self.llm_config.few_shot_examples:
            for example in self.llm_config.few_shot_examples:
                messages.insert(1, {"role": "user", "content": example.get("input", "")})
                messages.insert(2, {"role": "assistant", "content": example.get("output", "")})
        
        # Call LLM
        from core.llms import LLMContext
        response = await effective_llm.get_answer(messages, LLMContext())
        result_text = response.content.strip().upper()
        
        # Parse result based on evaluation mode
        if self.llm_config.evaluation_mode == LLMEvaluationMode.BINARY:
            return result_text in ("YES", "TRUE", "1")
        elif self.llm_config.evaluation_mode == LLMEvaluationMode.SCORE:
            try:
                score = float(result_text)
                return score >= self.llm_config.score_threshold
            except ValueError:
                return False
        else:  # CLASSIFICATION
            return result_text.lower() == (self.llm_config.expected_classification or "").lower()
    
    def _get_nested_value(self, obj: Dict[str, Any], path: str) -> Any:
        """Get nested value using dot notation."""
        keys = path.split(".")
        value = obj
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        return value
    
    def _evaluate_operator(self, field_value: Any) -> bool:
        """Evaluate the operator against the field value."""
        op = self.operator
        
        if op == ConditionOperator.EQUALS:
            return field_value == self.value
        elif op == ConditionOperator.NOT_EQUALS:
            return field_value != self.value
        elif op == ConditionOperator.GREATER_THAN:
            return field_value is not None and field_value > self.value
        elif op == ConditionOperator.LESS_THAN:
            return field_value is not None and field_value < self.value
        elif op == ConditionOperator.GREATER_THAN_OR_EQUALS:
            return field_value is not None and field_value >= self.value
        elif op == ConditionOperator.LESS_THAN_OR_EQUALS:
            return field_value is not None and field_value <= self.value
        elif op == ConditionOperator.CONTAINS:
            return self.value in field_value if field_value else False
        elif op == ConditionOperator.NOT_CONTAINS:
            return self.value not in field_value if field_value else True
        elif op == ConditionOperator.STARTS_WITH:
            return str(field_value).startswith(str(self.value)) if field_value else False
        elif op == ConditionOperator.ENDS_WITH:
            return str(field_value).endswith(str(self.value)) if field_value else False
        elif op == ConditionOperator.MATCHES:
            import re
            return bool(re.match(str(self.value), str(field_value))) if field_value else False
        elif op == ConditionOperator.IN:
            return field_value in self.value if self.value else False
        elif op == ConditionOperator.NOT_IN:
            return field_value not in self.value if self.value else True
        elif op == ConditionOperator.IS_NULL:
            return field_value is None
        elif op == ConditionOperator.IS_NOT_NULL:
            return field_value is not None
        elif op == ConditionOperator.IS_EMPTY:
            return not field_value if field_value is not None else True
        elif op == ConditionOperator.IS_NOT_EMPTY:
            return bool(field_value)
        elif op == ConditionOperator.CUSTOM:
            if self.custom_func:
                return self.custom_func(field_value, {})
            return False
        else:
            raise ValueError(f"Unknown operator: {op}")
    
    def to_transfer_rule(self, target_name: str) -> Optional[str]:
        """
        Convert this condition to a transfer rule for agent prompts.
        
        Only applicable for LLM conditions.
        
        Args:
            target_name: Name of the target node
            
        Returns:
            Optional[str]: Transfer rule text or None if not applicable
        """
        if self.condition_type == EdgeConditionType.LLM and self.llm_config:
            return self.llm_config.to_transfer_rule_prompt(target_name)
        elif self.description:
            return f"Transfer to '{target_name}' when: {self.description}"
        return None


class EdgeConditionGroup(BaseModel):
    """
    A group of conditions joined by AND/OR.
    
    Supports nested condition groups for complex logic.
    
    Attributes:
        conditions: List of conditions in this group
        join_operator: How to join conditions (AND/OR)
        nested_groups: Nested condition groups
    """
    conditions: List[EdgeCondition] = Field(
        default_factory=list,
        description="Conditions in this group"
    )
    join_operator: ConditionJoinOperator = Field(
        default=ConditionJoinOperator.AND,
        description="How to join conditions"
    )
    nested_groups: List[EdgeConditionGroup] = Field(
        default_factory=list,
        description="Nested condition groups"
    )
    
    def evaluate(self, context: Dict[str, Any]) -> bool:
        """
        Evaluate all conditions in this group (synchronous).
        
        Note: LLM conditions will be marked as pending and return False.
        Use evaluate_async for full support of LLM conditions.
        
        Args:
            context: Dictionary containing workflow variables
            
        Returns:
            bool: Whether the condition group is satisfied
        """
        results = []
        
        # Evaluate individual conditions
        for condition in self.conditions:
            results.append(condition.evaluate(context))
        
        # Evaluate nested groups
        for group in self.nested_groups:
            results.append(group.evaluate(context))
        
        if not results:
            return True  # No conditions = always pass
        
        if self.join_operator == ConditionJoinOperator.AND:
            return all(results)
        else:  # OR
            return any(results)
    
    async def evaluate_async(
        self,
        context: Dict[str, Any],
        llm: Optional[Any] = None
    ) -> bool:
        """
        Asynchronously evaluate all conditions (supports LLM conditions).
        
        Args:
            context: Dictionary containing workflow variables
            llm: LLM instance for LLM condition evaluation
            
        Returns:
            bool: Whether the condition group is satisfied
        """
        results = []
        
        # Evaluate individual conditions
        for condition in self.conditions:
            result = await condition.evaluate_async(context, llm)
            results.append(result)
        
        # Evaluate nested groups
        for group in self.nested_groups:
            result = await group.evaluate_async(context, llm)
            results.append(result)
        
        if not results:
            return True  # No conditions = always pass
        
        if self.join_operator == ConditionJoinOperator.AND:
            return all(results)
        else:  # OR
            return any(results)
    
    def has_llm_conditions(self) -> bool:
        """Check if this group contains any LLM conditions."""
        for condition in self.conditions:
            if condition.condition_type == EdgeConditionType.LLM:
                return True
        for group in self.nested_groups:
            if group.has_llm_conditions():
                return True
        return False
    
    def get_transfer_rules(self, target_name: str) -> List[str]:
        """
        Get all transfer rules for agent prompts.
        
        Args:
            target_name: Name of the target node
            
        Returns:
            List[str]: List of transfer rule texts
        """
        rules = []
        for condition in self.conditions:
            rule = condition.to_transfer_rule(target_name)
            if rule:
                rules.append(rule)
        for group in self.nested_groups:
            rules.extend(group.get_transfer_rules(target_name))
        return rules


# =============================================================================
# EDGE METADATA AND CONFIG
# =============================================================================


class EdgeMetadata(BaseModel):
    """
    Metadata for an edge.
    
    Attributes:
        version: Edge version string
        status: Current status (draft, published, etc.)
        created_at: Creation timestamp
        updated_at: Last update timestamp
        created_by: User who created the edge
        tags: Tags for categorization
    """
    version: str = Field(default=DEFAULT_EDGE_VERSION, description="Edge version")
    status: WorkflowStatus = Field(default=WorkflowStatus(DEFAULT_EDGE_STATUS), description="Edge status")
    created_at: Optional[datetime] = Field(default=None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")
    created_by: Optional[str] = Field(default=None, description="Creator user ID")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")


class EdgeConfig(BaseModel):
    """
    Configuration for edge behavior.
    
    Attributes:
        priority: Edge priority (lower = higher priority)
        weight: Weight for weighted routing
        timeout_ms: Timeout for condition evaluation
    """
    priority: int = Field(
        default=DEFAULT_EDGE_PRIORITY,
        description="Edge priority (lower = higher priority)"
    )
    weight: float = Field(
        default=DEFAULT_EDGE_WEIGHT,
        description="Weight for weighted routing"
    )
    timeout_ms: Optional[int] = Field(
        default=None,
        description="Timeout for condition evaluation"
    )


# =============================================================================
# EDGE SPECIFICATION
# =============================================================================


class EdgeSpec(BaseModel):
    """
    Complete specification for a workflow edge.
    
    An edge connects two nodes and determines routing based on conditions.
    Supports multiple condition types and pass-through field extraction.
    
    When source node is an AGENT:
    - LLM conditions become transfer rules in the agent's prompt
    - The agent decides when to transfer based on these rules
    
    When source node is a TOOL:
    - Conditions are evaluated after tool execution
    - LLM conditions require llm_ref/llm_instance for evaluation
    
    Attributes:
        id: Unique identifier
        name: Human-readable name
        description: Edge description
        edge_type: Type of edge (DEFAULT, CONDITIONAL, ERROR, etc.)
        
        # Connection
        source_node_id: ID of the source node
        target_node_id: ID of the target node
        
        # Conditions
        conditions: Condition group for evaluation
        
        # Pass-through fields
        pass_through: Pass-through field configuration
        
        # Configuration
        metadata: Edge metadata
        config: Edge configuration
        
        # Data transformation
        data_mapping: Mapping of source fields to target fields
    """
    # Identity
    id: str = Field(..., description="Unique edge identifier")
    name: str = Field(default="", description="Human-readable name")
    description: str = Field(default="", description="Edge description")
    edge_type: EdgeType = Field(default=EdgeType(DEFAULT_EDGE_TYPE), description="Type of edge")
    
    # Connection
    source_node_id: str = Field(..., description="ID of source node")
    target_node_id: str = Field(..., description="ID of target node")
    
    # Conditions (only for CONDITIONAL type)
    conditions: Optional[EdgeConditionGroup] = Field(
        default=None,
        description="Conditions for traversing this edge"
    )
    
    # Pass-through fields configuration
    pass_through: Optional[PassThroughConfig] = Field(
        default=None,
        description="Configuration for pass-through fields"
    )
    
    # Metadata and config
    metadata: EdgeMetadata = Field(default_factory=EdgeMetadata, description="Edge metadata")
    config: EdgeConfig = Field(default_factory=EdgeConfig, description="Edge configuration")
    
    # Data transformation between nodes
    data_mapping: Dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of source output fields to target input fields"
    )
    
    # Additional properties for extensibility
    properties: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional custom properties"
    )
    
    model_config = {
        ARBITRARY_TYPES_ALLOWED: True,
        POPULATE_BY_NAME: True,
    }
    
    def should_traverse(self, context: Dict[str, Any]) -> bool:
        """
        Determine if this edge should be traversed based on conditions (synchronous).
        
        Note: For LLM conditions, use should_traverse_async.
        
        Args:
            context: Workflow context including variables and node outputs
            
        Returns:
            bool: Whether to traverse this edge
        """
        # Default edges always traverse
        if self.edge_type == EdgeType.DEFAULT:
            return True
        
        # Error edges only traverse on error
        if self.edge_type == EdgeType.ERROR:
            return context.get("_error", False)
        
        # Timeout edges only traverse on timeout
        if self.edge_type == EdgeType.TIMEOUT:
            return context.get("_timeout", False)
        
        # Conditional edges evaluate conditions
        if self.edge_type == EdgeType.CONDITIONAL:
            if self.conditions:
                return self.conditions.evaluate(context)
            return True  # No conditions = always pass
        
        # Fallback edges traverse if primary path failed
        if self.edge_type == EdgeType.FALLBACK:
            return context.get("_fallback_needed", False)
        
        return True
    
    async def should_traverse_async(
        self,
        context: Dict[str, Any],
        llm: Optional[Any] = None
    ) -> bool:
        """
        Asynchronously determine if this edge should be traversed (supports LLM conditions).
        
        Args:
            context: Workflow context including variables and node outputs
            llm: LLM instance for LLM condition evaluation
            
        Returns:
            bool: Whether to traverse this edge
        """
        # Default edges always traverse
        if self.edge_type == EdgeType.DEFAULT:
            return True
        
        # Error edges only traverse on error
        if self.edge_type == EdgeType.ERROR:
            return context.get("_error", False)
        
        # Timeout edges only traverse on timeout
        if self.edge_type == EdgeType.TIMEOUT:
            return context.get("_timeout", False)
        
        # Conditional edges evaluate conditions
        if self.edge_type == EdgeType.CONDITIONAL:
            if self.conditions:
                effective_llm = llm
                if not effective_llm and self.pass_through and self.pass_through.llm_instance:
                    effective_llm = self.pass_through.llm_instance
                return await self.conditions.evaluate_async(context, effective_llm)
            return True  # No conditions = always pass
        
        # Fallback edges traverse if primary path failed
        if self.edge_type == EdgeType.FALLBACK:
            return context.get("_fallback_needed", False)
        
        return True
    
    def has_llm_conditions(self) -> bool:
        """Check if this edge has any LLM-based conditions."""
        if self.conditions:
            return self.conditions.has_llm_conditions()
        return False
    
    def requires_llm_for_evaluation(self) -> bool:
        """Check if this edge requires an LLM for condition evaluation."""
        return self.has_llm_conditions()
    
    def get_transfer_rules(self) -> List[str]:
        """
        Get transfer rules for agent prompts.
        
        When the source node is an AGENT, these rules should be
        added to the agent's system prompt.
        
        Returns:
            List[str]: Transfer rule texts
        """
        rules = []
        if self.conditions:
            rules.extend(self.conditions.get_transfer_rules(self.target_node_id))
        return rules
    
    def get_transfer_rules_prompt(self, target_name: Optional[str] = None) -> str:
        """
        Get formatted transfer rules for agent prompt injection.
        
        Args:
            target_name: Optional override for target node name
            
        Returns:
            str: Formatted transfer rules section for agent prompt
        """
        _ = target_name  # Reserved for future use with target node name display
        rules = self.get_transfer_rules()
        
        if not rules:
            return ""
        
        rules_text = "\n".join(f"- {rule}" for rule in rules)
        
        # Include pass-through field instructions if present
        if self.pass_through and self.pass_through.fields:
            fields_info = []
            for field in self.pass_through.fields:
                desc = field.description or field.name
                required = " (required)" if field.required else ""
                fields_info.append(f"  - {field.name}: {desc}{required}")
            
            fields_text = "\n".join(fields_info)
            return f"""
## Transfer Rules
{rules_text}

When transferring, extract and include these fields:
{fields_text}
"""
        
        return f"""
## Transfer Rules
{rules_text}
"""
    
    async def extract_pass_through_fields(
        self,
        context: Dict[str, Any],
        llm: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Extract pass-through field values from context.
        
        Follows the extraction strategy for each field:
        1. Look in context at source_path
        2. Use LLM to extract from conversation
        3. Ask user if still not found
        
        Args:
            context: Workflow context
            llm: LLM instance for extraction
            
        Returns:
            Dict[str, Any]: Extracted field values
        """
        if not self.pass_through or not self.pass_through.fields:
            return {}
        
        result = {}
        missing_required = []
        ask_user_fields = []
        
        effective_llm = llm or (self.pass_through.llm_instance if self.pass_through else None)
        
        for field in self.pass_through.fields:
            value = None
            
            # Strategy 1: Look in context
            if field.source_path:
                value = self._get_nested_value(context, field.source_path)
            
            if value is None and field.name in context:
                value = context[field.name]
            
            # Strategy 2: Try LLM extraction
            if value is None and effective_llm and field.extraction_strategy in (
                PassThroughExtractionStrategy.LLM,
                PassThroughExtractionStrategy.CONTEXT
            ):
                value = await self._extract_with_llm(field, context, effective_llm)
            
            # Strategy 3: Mark for user prompt
            if value is None and field.ask_on_missing:
                ask_user_fields.append(field)
            
            # Apply default value if still None
            if value is None and field.default_value is not None:
                value = field.default_value
            
            # Apply transformation if specified
            if value is not None and field.transform_expr:
                try:
                    value = eval(field.transform_expr, {"value": value})
                except Exception:
                    pass  # Keep original value on transform failure
            
            # Validate if regex specified
            if value is not None and field.validation_regex:
                import re
                if not re.match(field.validation_regex, str(value)):
                    value = None  # Invalid value
            
            if value is not None:
                result[field.name] = value
            elif field.required:
                missing_required.append(field.name)
        
        # Store fields that need user input in context
        if ask_user_fields:
            context["_ask_user_fields"] = [
                {
                    "name": f.name,
                    "prompt": f.get_ask_user_prompt(),
                    "required": f.required
                }
                for f in ask_user_fields
                if f.name not in result
            ]
        
        # Check for missing required fields
        if missing_required and self.pass_through.fail_on_missing_required:
            context["_missing_required_fields"] = missing_required
        
        return result
    
    async def _extract_with_llm(
        self,
        field: PassThroughField,
        context: Dict[str, Any],
        llm: Any
    ) -> Optional[Any]:
        """Extract a field value using LLM."""
        try:
            # Build extraction context
            extraction_context = {}
            if self.pass_through:
                for key in self.pass_through.extraction_context_keys:
                    if key in context:
                        extraction_context[key] = context[key]
            
            messages = [
                {
                    "role": "system",
                    "content": (
                        f"Extract the '{field.name}' from the conversation. "
                        f"Description: {field.description or field.name}. "
                        f"Respond with only the extracted value, or 'NOT_FOUND' if not present."
                    )
                },
                {
                    "role": "user",
                    "content": f"Context:\n{extraction_context}\n\nExtract: {field.name}"
                }
            ]
            
            from core.llms import LLMContext
            response = await llm.get_answer(messages, LLMContext())
            result = response.content.strip()
            
            if result.upper() == "NOT_FOUND":
                return None
            
            return result
            
        except Exception:
            return None
    
    def apply_data_mapping(self, source_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply data mapping to transform source output for target input.
        
        Args:
            source_output: Output from source node
            
        Returns:
            Dict: Transformed data for target node input
        """
        if not self.data_mapping:
            return source_output
        
        result = {}
        for target_field, source_field in self.data_mapping.items():
            value = self._get_nested_value(source_output, source_field)
            self._set_nested_value(result, target_field, value)
        
        return result
    
    def _get_nested_value(self, obj: Dict[str, Any], path: str) -> Any:
        """Get nested value using dot notation."""
        keys = path.split(".")
        value = obj
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        return value
    
    def _set_nested_value(self, obj: Dict[str, Any], path: str, value: Any) -> None:
        """Set nested value using dot notation."""
        keys = path.split(".")
        for key in keys[:-1]:
            obj = obj.setdefault(key, {})
        obj[keys[-1]] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return self.model_dump(exclude={"pass_through": {"llm_instance"}})
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EdgeSpec:
        """Create from dictionary."""
        return cls(**data)


# =============================================================================
# EDGE VERSIONING
# =============================================================================


class EdgeVersion(BaseModel):
    """
    A specific version of an edge.
    
    Versions are immutable once published.
    """
    version: str = Field(..., description="Version string")
    spec: EdgeSpec = Field(..., description="Edge specification")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation time")
    is_published: bool = Field(default=False, description="Whether version is published")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "version": self.version,
            "spec": self.spec.to_dict(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_published": self.is_published,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EdgeVersion:
        """Create from dictionary."""
        spec_data = data.get("spec", {})
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        return cls(
            version=data["version"],
            spec=EdgeSpec.from_dict(spec_data),
            created_at=created_at or datetime.utcnow(),
            is_published=data.get("is_published", False),
        )


class EdgeEntry(BaseModel):
    """
    Entry containing all versions of an edge.
    
    Similar to NodeEntry, manages multiple versions.
    """
    id: str = Field(..., description="Edge ID")
    versions: Dict[str, EdgeVersion] = Field(default_factory=dict, description="Version map")
    
    # Private attrs for tracking
    _latest_version: str = PrivateAttr(default="")
    
    def model_post_init(self, __context: Any) -> None:
        """Initialize after model creation."""
        if self.versions:
            versions = sorted(self.versions.keys(), key=lambda v: [int(x) for x in v.split(".")])
            self._latest_version = versions[-1] if versions else ""
    
    def get_version(self, version: str) -> Optional[EdgeVersion]:
        """Get a specific version."""
        return self.versions.get(version)
    
    def get_latest_version(self) -> Optional[str]:
        """Get the latest version string."""
        return self._latest_version or None
    
    def get_latest(self) -> Optional[EdgeVersion]:
        """Get the latest version entry."""
        if self._latest_version:
            return self.versions.get(self._latest_version)
        return None
    
    def version_exists(self, version: str) -> bool:
        """Check if version exists."""
        return version in self.versions
    
    def add_version(self, edge_version: EdgeVersion) -> None:
        """Add a new version."""
        if self.version_exists(edge_version.version):
            raise ValueError(
                ERROR_VERSION_EXISTS.format(
                    version=edge_version.version,
                    entity_type="edge",
                    id=self.id
                )
            )
        self.versions[edge_version.version] = edge_version
        
        versions = sorted(self.versions.keys(), key=lambda v: [int(x) for x in v.split(".")])
        self._latest_version = versions[-1]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "versions": {v: ev.to_dict() for v, ev in self.versions.items()},
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EdgeEntry:
        """Create from dictionary."""
        versions = {
            v: EdgeVersion.from_dict(ev_data)
            for v, ev_data in data.get("versions", {}).items()
        }
        return cls(id=data["id"], versions=versions)
