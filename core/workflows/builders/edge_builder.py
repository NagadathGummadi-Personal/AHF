"""
Edge Builder

Fluent builder for creating workflow edges with support for:
- Expression-based conditions
- LLM-based semantic conditions
- Custom function conditions
- Pass-through fields with LLM extraction

Version: 2.0.0
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from ..spec.edge_models import (
    EdgeSpec,
    EdgeMetadata,
    EdgeConfig,
    EdgeCondition,
    EdgeConditionGroup,
    PassThroughField,
    PassThroughConfig,
    LLMConditionConfig,
)
from ..enum import (
    EdgeType,
    WorkflowStatus,
    ConditionOperator,
    ConditionJoinOperator,
    EdgeConditionType,
    PassThroughExtractionStrategy,
    LLMEvaluationMode,
)
from ..defaults import DEFAULT_EDGE_VERSION


class EdgeBuilder:
    """
    Fluent builder for creating EdgeSpec instances.
    
    Usage:
        # Create a simple default edge
        edge = (EdgeBuilder()
            .with_id("edge-1")
            .from_node("node-a")
            .to_node("node-b")
            .build())
        
        # Create a conditional edge with expression
        edge = (EdgeBuilder()
            .with_id("edge-2")
            .with_name("Success Path")
            .from_node("node-a")
            .to_node("node-success")
            .as_conditional()
            .with_condition("result.success", ConditionOperator.EQUALS, True)
            .build())
        
        # Create an edge with LLM condition
        edge = (EdgeBuilder()
            .with_id("edge-3")
            .from_node("booking-agent")
            .to_node("service-lookup")
            .as_conditional()
            .with_llm_condition(
                "Check if the user's intent is to book a service"
            )
            .with_pass_through_field(
                name="service_name",
                description="The service the user wants to book"
            )
            .build())
        
        # Create an error edge
        edge = (EdgeBuilder()
            .with_id("edge-4")
            .from_node("node-a")
            .to_node("node-error")
            .as_error_handler()
            .build())
    """
    
    def __init__(self):
        """Initialize the builder."""
        self._id: Optional[str] = None
        self._name: str = ""
        self._description: str = ""
        self._edge_type: EdgeType = EdgeType.DEFAULT
        
        # Connection
        self._source_node_id: Optional[str] = None
        self._target_node_id: Optional[str] = None
        
        # Conditions
        self._conditions: List[EdgeCondition] = []
        self._condition_join: ConditionJoinOperator = ConditionJoinOperator.AND
        
        # Pass-through fields
        self._pass_through_fields: List[PassThroughField] = []
        self._pass_through_llm_ref: Optional[str] = None
        self._pass_through_llm_instance: Optional[Any] = None
        
        # Metadata
        self._version: str = DEFAULT_EDGE_VERSION
        self._status: WorkflowStatus = WorkflowStatus.DRAFT
        self._tags: List[str] = []
        
        # Config
        self._priority: int = 0
        self._weight: float = 1.0
        self._timeout_ms: Optional[int] = None
        
        # Data mapping
        self._data_mapping: Dict[str, str] = {}
        
        # Additional properties
        self._properties: Dict[str, Any] = {}

    def with_id(self, edge_id: str) -> EdgeBuilder:
        """Set the edge ID."""
        self._id = edge_id
        return self
    
    def with_name(self, name: str) -> EdgeBuilder:
        """Set the edge name."""
        self._name = name
        return self
    
    def with_description(self, description: str) -> EdgeBuilder:
        """Set the edge description."""
        self._description = description
        return self
    
    # =========================================================================
    # Connection methods
    # =========================================================================
    
    def from_node(self, node_id: str) -> EdgeBuilder:
        """Set the source node ID."""
        self._source_node_id = node_id
        return self
    
    def to_node(self, node_id: str) -> EdgeBuilder:
        """Set the target node ID."""
        self._target_node_id = node_id
        return self
    
    # =========================================================================
    # Type methods
    # =========================================================================
    
    def as_default(self) -> EdgeBuilder:
        """Set as default edge (always traversed)."""
        self._edge_type = EdgeType.DEFAULT
        return self
    
    def as_conditional(self) -> EdgeBuilder:
        """Set as conditional edge."""
        self._edge_type = EdgeType.CONDITIONAL
        return self
    
    def as_error_handler(self) -> EdgeBuilder:
        """Set as error handling edge."""
        self._edge_type = EdgeType.ERROR
        return self
    
    def as_timeout_handler(self) -> EdgeBuilder:
        """Set as timeout handling edge."""
        self._edge_type = EdgeType.TIMEOUT
        return self
    
    def as_fallback(self) -> EdgeBuilder:
        """Set as fallback edge."""
        self._edge_type = EdgeType.FALLBACK
        return self
    
    # =========================================================================
    # Expression Condition methods
    # =========================================================================
    
    def with_condition(
        self,
        field: str,
        operator: ConditionOperator,
        value: Any = None,
        negate: bool = False,
        description: str = ""
    ) -> EdgeBuilder:
        """
        Add an expression-based condition.
        
        Args:
            field: Field path to evaluate (dot notation supported)
            operator: Comparison operator
            value: Value to compare against
            negate: Whether to negate the result
            description: Human-readable description
        """
        self._conditions.append(EdgeCondition(
            condition_type=EdgeConditionType.EXPRESSION,
            field=field,
            operator=operator,
            value=value,
            negate=negate,
            description=description,
        ))
        return self
    
    def with_dynamic_condition(
        self,
        field: str,
        operator: ConditionOperator,
        value: Any = None,
        negate: bool = False,
        description: str = ""
    ) -> EdgeBuilder:
        """
        Add a dynamic variable condition (evaluated at runtime).
        
        Args:
            field: Variable path to evaluate
            operator: Comparison operator
            value: Value to compare against
            negate: Whether to negate the result
            description: Human-readable description
        """
        self._conditions.append(EdgeCondition(
            condition_type=EdgeConditionType.DYNAMIC,
            field=field,
            operator=operator,
            value=value,
            negate=negate,
            description=description,
        ))
        return self
    
    def with_custom_condition(
        self,
        func: Callable[[Any, Dict[str, Any]], bool],
        field: Optional[str] = None,
        description: str = ""
    ) -> EdgeBuilder:
        """
        Add a custom function condition.
        
        Args:
            func: Custom evaluation function (field_value, context) -> bool
            field: Optional field to pass to function
            description: Human-readable description
        """
        self._conditions.append(EdgeCondition(
            condition_type=EdgeConditionType.FUNCTION,
            field=field,
            operator=ConditionOperator.CUSTOM,
            custom_func=func,
            description=description,
        ))
        return self
    
    # =========================================================================
    # LLM Condition methods
    # =========================================================================
    
    def with_llm_condition(
        self,
        condition_prompt: str,
        evaluation_mode: LLMEvaluationMode = LLMEvaluationMode.BINARY,
        llm_ref: Optional[str] = None,
        llm_instance: Optional[Any] = None,
        score_threshold: float = 0.7,
        include_context_keys: Optional[List[str]] = None,
        negate: bool = False,
        description: str = ""
    ) -> EdgeBuilder:
        """
        Add an LLM-based semantic condition.
        
        When the source node is an AGENT, this condition becomes a transfer rule
        in the agent's system prompt. The agent decides when to transfer based
        on the condition.
        
        When the source node is a TOOL, the condition is evaluated by the LLM
        after tool execution.
        
        Args:
            condition_prompt: Natural language description of the condition
                Example: "Check if the user's intent is to book a service"
            evaluation_mode: How to evaluate (BINARY, SCORE, CLASSIFICATION)
            llm_ref: Reference to LLM (required if source is TOOL)
            llm_instance: Direct LLM instance
            score_threshold: Threshold for score-based evaluation
            include_context_keys: Context keys to include in evaluation
            negate: Whether to negate the result
            description: Human-readable description
        """
        llm_config = LLMConditionConfig(
            condition_prompt=condition_prompt,
            evaluation_mode=evaluation_mode,
            llm_ref=llm_ref,
            llm_instance=llm_instance,
            score_threshold=score_threshold,
            include_context_keys=include_context_keys or ["messages", "last_output", "variables"],
        )
        
        self._conditions.append(EdgeCondition(
            condition_type=EdgeConditionType.LLM,
            llm_config=llm_config,
            negate=negate,
            description=description or condition_prompt,
        ))
        return self
    
    def with_classification_condition(
        self,
        condition_prompt: str,
        classification_options: List[str],
        expected_classification: str,
        llm_ref: Optional[str] = None,
        llm_instance: Optional[Any] = None,
        negate: bool = False,
        description: str = ""
    ) -> EdgeBuilder:
        """
        Add an LLM classification-based condition.
        
        The LLM classifies the context into one of the provided options,
        and the condition is met if the classification matches the expected value.
        
        Args:
            condition_prompt: What to classify
            classification_options: List of possible classifications
            expected_classification: The classification that triggers this edge
            llm_ref: Reference to LLM
            llm_instance: Direct LLM instance
            negate: Whether to negate the result
            description: Human-readable description
        """
        llm_config = LLMConditionConfig(
            condition_prompt=condition_prompt,
            evaluation_mode=LLMEvaluationMode.CLASSIFICATION,
            llm_ref=llm_ref,
            llm_instance=llm_instance,
            classification_options=classification_options,
            expected_classification=expected_classification,
        )
        
        self._conditions.append(EdgeCondition(
            condition_type=EdgeConditionType.LLM,
            llm_config=llm_config,
            negate=negate,
            description=description or f"Classify as '{expected_classification}': {condition_prompt}",
        ))
        return self
    
    def join_conditions_with_and(self) -> EdgeBuilder:
        """Join conditions with AND."""
        self._condition_join = ConditionJoinOperator.AND
        return self
    
    def join_conditions_with_or(self) -> EdgeBuilder:
        """Join conditions with OR."""
        self._condition_join = ConditionJoinOperator.OR
        return self
    
    # =========================================================================
    # Pass-through field methods
    # =========================================================================
    
    def with_pass_through_field(
        self,
        name: str,
        description: str = "",
        required: bool = False,
        default_value: Any = None,
        source_path: Optional[str] = None,
        extraction_strategy: PassThroughExtractionStrategy = PassThroughExtractionStrategy.CONTEXT,
        ask_on_missing: bool = True,
        ask_user_prompt: Optional[str] = None,
        validation_regex: Optional[str] = None,
        transform_expr: Optional[str] = None
    ) -> EdgeBuilder:
        """
        Add a pass-through field to extract and pass to the target node.
        
        Pass-through fields are extracted from context when the edge condition
        is met. If the field cannot be found in context, an LLM can extract it
        from the conversation, or the user can be prompted.
        
        Args:
            name: Field name (e.g., "service_name", "booking_date")
            description: What this field represents (used for extraction/prompting)
            required: Whether this field must be present to proceed
            default_value: Default value if extraction fails
            source_path: Dot-notation path to look for value in context
            extraction_strategy: How to extract the value
            ask_on_missing: Whether to ask user if extraction fails
            ask_user_prompt: Custom prompt when asking user
            validation_regex: Regex pattern for validation
            transform_expr: Python expression to transform value
        """
        self._pass_through_fields.append(PassThroughField(
            name=name,
            description=description,
            required=required,
            default_value=default_value,
            source_path=source_path,
            extraction_strategy=extraction_strategy,
            ask_on_missing=ask_on_missing,
            ask_user_prompt=ask_user_prompt,
            validation_regex=validation_regex,
            transform_expr=transform_expr,
        ))
        return self
    
    def with_pass_through_llm(
        self,
        llm_ref: Optional[str] = None,
        llm_instance: Optional[Any] = None
    ) -> EdgeBuilder:
        """
        Set the LLM to use for pass-through field extraction.
        
        Args:
            llm_ref: Reference to LLM
            llm_instance: Direct LLM instance
        """
        self._pass_through_llm_ref = llm_ref
        self._pass_through_llm_instance = llm_instance
        return self
    
    # =========================================================================
    # Metadata methods
    # =========================================================================
    
    def with_version(self, version: str) -> EdgeBuilder:
        """Set the version."""
        self._version = version
        return self
    
    def with_status(self, status: WorkflowStatus) -> EdgeBuilder:
        """Set the status."""
        self._status = status
        return self
    
    def with_tags(self, tags: List[str]) -> EdgeBuilder:
        """Set tags."""
        self._tags = tags
        return self
    
    # =========================================================================
    # Config methods
    # =========================================================================
    
    def with_priority(self, priority: int) -> EdgeBuilder:
        """Set edge priority (lower = higher priority)."""
        self._priority = priority
        return self
    
    def with_weight(self, weight: float) -> EdgeBuilder:
        """Set edge weight for weighted routing."""
        self._weight = weight
        return self
    
    def with_timeout(self, timeout_ms: int) -> EdgeBuilder:
        """Set condition evaluation timeout."""
        self._timeout_ms = timeout_ms
        return self
    
    # =========================================================================
    # Data mapping methods
    # =========================================================================
    
    def map_data(self, target_field: str, source_field: str) -> EdgeBuilder:
        """
        Add a data mapping from source to target.
        
        Args:
            target_field: Field name in target node input
            source_field: Field path in source node output (dot notation)
        """
        self._data_mapping[target_field] = source_field
        return self
    
    # =========================================================================
    # Property methods
    # =========================================================================
    
    def with_property(self, key: str, value: Any) -> EdgeBuilder:
        """Add a custom property."""
        self._properties[key] = value
        return self
    
    # =========================================================================
    # Build method
    # =========================================================================
    
    def build(self) -> EdgeSpec:
        """
        Build the EdgeSpec.
        
        Raises:
            ValueError: If required fields are missing
        """
        if not self._id:
            raise ValueError("Edge ID is required")
        if not self._source_node_id:
            raise ValueError("Source node ID is required")
        if not self._target_node_id:
            raise ValueError("Target node ID is required")
        
        # Build conditions group if we have conditions
        conditions = None
        if self._conditions:
            conditions = EdgeConditionGroup(
                conditions=self._conditions,
                join_operator=self._condition_join,
            )
        
        # Build pass-through config if we have fields
        pass_through = None
        if self._pass_through_fields:
            pass_through = PassThroughConfig(
                fields=self._pass_through_fields,
                llm_ref=self._pass_through_llm_ref,
                llm_instance=self._pass_through_llm_instance,
            )
        
        # Build metadata
        metadata = EdgeMetadata(
            version=self._version,
            status=self._status,
            tags=self._tags,
        )
        
        # Build config
        config = EdgeConfig(
            priority=self._priority,
            weight=self._weight,
            timeout_ms=self._timeout_ms,
        )
        
        return EdgeSpec(
            id=self._id,
            name=self._name,
            description=self._description,
            edge_type=self._edge_type,
            source_node_id=self._source_node_id,
            target_node_id=self._target_node_id,
            conditions=conditions,
            pass_through=pass_through,
            metadata=metadata,
            config=config,
            data_mapping=self._data_mapping,
            properties=self._properties,
        )
