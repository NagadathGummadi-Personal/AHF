"""
Prompt Models.

This module defines the data models for prompt entries, templates, and metadata.
Supports:
- Versioning with LLM-specific variants
- Environment-based deployment (prod, staging, dev, test)
- Dynamic variable substitution
- LLM and human evaluation scores
- Runtime metrics tracking (latency, tokens, cost)
- Immutability enforcement for stored prompts
"""

from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
import uuid
import re

from ..enum import PromptStatus, PromptCategory, PromptEnvironment, PromptType
from ..constants import (
    DEFAULT_VERSION,
    DEFAULT_MODEL,
    DEFAULT_ENVIRONMENT,
    VARIABLE_PATTERN,
    MIN_EVAL_SCORE,
    MAX_EVAL_SCORE,
    ERROR_MISSING_VARIABLES,
)


class RuntimeMetrics(BaseModel):
    """
    Runtime metrics for prompt usage tracking.
    
    Tracks real-time performance metrics when prompts are used in production.
    These metrics are aggregated over time to help optimize prompt selection.
    
    Attributes:
        usage_count: Total number of times this prompt was used
        total_latency_ms: Cumulative latency in milliseconds
        avg_latency_ms: Average latency per call
        total_prompt_tokens: Total prompt tokens consumed
        total_completion_tokens: Total completion tokens generated
        total_tokens: Total tokens (prompt + completion)
        avg_tokens: Average tokens per call
        total_cost: Total cost incurred (in USD or smallest unit)
        avg_cost: Average cost per call
        last_used_at: Timestamp of last usage
        error_count: Number of errors encountered
        success_rate: Success rate (0.0 to 1.0)
    
    Example:
        metrics = RuntimeMetrics()
        metrics.record_usage(latency_ms=150, prompt_tokens=100, completion_tokens=50, cost=0.001)
    """
    
    usage_count: int = Field(default=0, description="Total usage count")
    total_latency_ms: float = Field(default=0.0, description="Total latency in ms")
    avg_latency_ms: float = Field(default=0.0, description="Average latency in ms")
    total_prompt_tokens: int = Field(default=0, description="Total prompt tokens")
    total_completion_tokens: int = Field(default=0, description="Total completion tokens")
    total_tokens: int = Field(default=0, description="Total tokens")
    avg_tokens: float = Field(default=0.0, description="Average tokens per call")
    total_cost: float = Field(default=0.0, description="Total cost")
    avg_cost: float = Field(default=0.0, description="Average cost per call")
    last_used_at: Optional[str] = Field(default=None, description="Last usage timestamp")
    error_count: int = Field(default=0, description="Error count")
    success_rate: float = Field(default=1.0, description="Success rate (0-1)")
    
    def record_usage(
        self,
        latency_ms: float = 0.0,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        cost: float = 0.0,
        success: bool = True
    ) -> None:
        """
        Record a single usage of the prompt.
        
        Updates all metrics with the new usage data.
        
        Args:
            latency_ms: Latency of this call in milliseconds
            prompt_tokens: Number of prompt tokens used
            completion_tokens: Number of completion tokens generated
            cost: Cost of this call
            success: Whether the call was successful
        """
        self.usage_count += 1
        self.total_latency_ms += latency_ms
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens
        total_call_tokens = prompt_tokens + completion_tokens
        self.total_tokens += total_call_tokens
        self.total_cost += cost
        self.last_used_at = datetime.utcnow().isoformat()
        
        if not success:
            self.error_count += 1
        
        # Update averages
        if self.usage_count > 0:
            self.avg_latency_ms = self.total_latency_ms / self.usage_count
            self.avg_tokens = self.total_tokens / self.usage_count
            self.avg_cost = self.total_cost / self.usage_count
            self.success_rate = (self.usage_count - self.error_count) / self.usage_count


class PromptMetadata(BaseModel):
    """
    Metadata for a prompt.
    
    Contains information about the prompt's target model, environment,
    evaluation scores, and performance metrics.
    
    Attributes:
        id: Unique prompt ID
        version: Version string (semver-style)
        model_target: Target LLM model (e.g., "gpt-4", "claude-3", "default")
        environment: Deployment environment (prod, staging, dev, test)
        prompt_type: Type of prompt (system or user)
        tags: List of tags for categorization
        category: Prompt category (system, user, template, etc.)
        status: Prompt status (draft, active, deprecated, archived)
        llm_eval_score: LLM-based evaluation score (0.0 to 1.0)
        human_eval_score: Human evaluation score (0.0 to 1.0)
        performance_metrics: Legacy performance metrics dict
        runtime_metrics: Runtime usage metrics
        response_format: Expected response format schema
        description: Human-readable description
        author: Author of the prompt
        created_at: Creation timestamp
        updated_at: Last update timestamp
        is_immutable: Whether this version is locked (set on save)
    
    Example:
        metadata = PromptMetadata(
            version="1.0.0",
            model_target="gpt-4",
            environment=PromptEnvironment.PROD,
            prompt_type=PromptType.SYSTEM,
            tags=["code", "review"],
            llm_eval_score=0.92,
            human_eval_score=0.88
        )
    """
    
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique prompt ID"
    )
    version: str = Field(
        default=DEFAULT_VERSION,
        description="Version string"
    )
    model_target: str = Field(
        default=DEFAULT_MODEL,
        description="Target LLM model"
    )
    environment: PromptEnvironment = Field(
        default=PromptEnvironment.PROD,
        description="Deployment environment"
    )
    prompt_type: PromptType = Field(
        default=PromptType.SYSTEM,
        description="Type of prompt (system or user)"
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Tags for categorization"
    )
    category: PromptCategory = Field(
        default=PromptCategory.TEMPLATE,
        description="Prompt category"
    )
    status: PromptStatus = Field(
        default=PromptStatus.ACTIVE,
        description="Prompt status"
    )
    llm_eval_score: Optional[float] = Field(
        default=None,
        ge=MIN_EVAL_SCORE,
        le=MAX_EVAL_SCORE,
        description="LLM evaluation score (0.0-1.0)"
    )
    human_eval_score: Optional[float] = Field(
        default=None,
        ge=MIN_EVAL_SCORE,
        le=MAX_EVAL_SCORE,
        description="Human evaluation score (0.0-1.0)"
    )
    performance_metrics: Dict[str, float] = Field(
        default_factory=dict,
        description="Legacy performance metrics"
    )
    runtime_metrics: RuntimeMetrics = Field(
        default_factory=RuntimeMetrics,
        description="Runtime usage metrics"
    )
    response_format: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Expected response format schema"
    )
    description: str = Field(
        default="",
        description="Human-readable description"
    )
    author: Optional[str] = Field(
        default=None,
        description="Author of the prompt"
    )
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Creation timestamp"
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Last update timestamp"
    )
    is_immutable: bool = Field(
        default=False,
        description="Whether this version is locked"
    )
    extras: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    
    def update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow().isoformat()
    
    def add_metric(self, name: str, value: float) -> None:
        """Add or update a legacy metric."""
        self.performance_metrics[name] = value
        self.update_timestamp()
    
    def get_metric(self, name: str, default: float = 0.0) -> float:
        """Get a legacy metric value."""
        return self.performance_metrics.get(name, default)
    
    def record_usage(
        self,
        latency_ms: float = 0.0,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        cost: float = 0.0,
        success: bool = True
    ) -> None:
        """
        Record runtime usage metrics.
        
        Args:
            latency_ms: Call latency in milliseconds
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            cost: Cost of the call
            success: Whether call succeeded
        """
        self.runtime_metrics.record_usage(
            latency_ms=latency_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost=cost,
            success=success
        )
        self.update_timestamp()
    
    def mark_immutable(self) -> None:
        """Mark this metadata as immutable (cannot be changed)."""
        self.is_immutable = True


class PromptTemplate(BaseModel):
    """
    Template for prompts with dynamic variable support.
    
    Handles extraction and substitution of dynamic variables in prompt templates.
    Variables are specified using {variable_name} syntax.
    
    Attributes:
        content: The raw template content with {variables}
        dynamic_variables: Set of variable names extracted from content
        default_values: Default values for variables
    
    Example:
        template = PromptTemplate(
            content="You are {role}. Help the user with {task}.",
            default_values={"role": "a helpful assistant"}
        )
        
        # Get required variables
        vars = template.get_required_variables()  # {"role", "task"}
        
        # Render with variables
        rendered = template.render({"role": "an expert", "task": "coding"})
    """
    
    content: str = Field(description="Raw template content")
    dynamic_variables: Set[str] = Field(
        default_factory=set,
        description="Extracted variable names"
    )
    default_values: Dict[str, Any] = Field(
        default_factory=dict,
        description="Default values for variables"
    )
    
    def model_post_init(self, __context: Any) -> None:
        """Extract variables after initialization."""
        self._extract_variables()
    
    def _extract_variables(self) -> None:
        """Extract all {variable} patterns from content."""
        matches = re.findall(VARIABLE_PATTERN, self.content)
        self.dynamic_variables = set(matches)
    
    def get_required_variables(self) -> Set[str]:
        """
        Get the set of required variable names.
        
        Returns:
            Set of variable names that must be provided for rendering.
            Variables with default values are not included.
        """
        return self.dynamic_variables - set(self.default_values.keys())
    
    def get_all_variables(self) -> Set[str]:
        """
        Get all variable names in the template.
        
        Returns:
            Set of all variable names (required and optional).
        """
        return self.dynamic_variables.copy()
    
    def validate_variables(self, variables: Dict[str, Any]) -> List[str]:
        """
        Validate that all required variables are provided.
        
        Args:
            variables: Dictionary of variable values
            
        Returns:
            List of missing variable names (empty if all provided)
        """
        required = self.get_required_variables()
        provided = set(variables.keys())
        missing = required - provided
        return list(missing)
    
    def render(
        self,
        variables: Optional[Dict[str, Any]] = None,
        strict: bool = True
    ) -> str:
        """
        Render the template with provided variables.
        
        Args:
            variables: Dictionary of variable values
            strict: If True, raise error for missing required variables
            
        Returns:
            Rendered prompt string
            
        Raises:
            ValueError: If strict=True and required variables are missing
        """
        variables = variables or {}
        
        # Merge with defaults
        merged = {**self.default_values, **variables}
        
        # Validate if strict
        if strict:
            missing = self.validate_variables(merged)
            if missing:
                raise ValueError(ERROR_MISSING_VARIABLES.format(variables=missing))
        
        # Render template
        try:
            return self.content.format(**merged)
        except KeyError as e:
            if strict:
                raise ValueError(f"Missing variable: {e}")
            # Non-strict: leave unresolved variables as-is
            result = self.content
            for key, value in merged.items():
                result = result.replace(f"{{{key}}}", str(value))
            return result


class PromptVersion(BaseModel):
    """
    A specific version of a prompt.
    
    Represents a single immutable version of a prompt with its content and metadata.
    Once stored, the content cannot be modified - only new versions can be created.
    
    Attributes:
        version: Version string
        content: Raw prompt content (may contain {variables})
        template: PromptTemplate for variable handling
        model_target: Target model for this version
        environment: Deployment environment
        prompt_type: System or user prompt
        response_format: Expected response format
        metadata: Full metadata
        created_at: Creation timestamp
    """
    
    version: str = Field(description="Version string")
    content: str = Field(description="Prompt content")
    model_target: str = Field(
        default=DEFAULT_MODEL,
        description="Target model"
    )
    environment: PromptEnvironment = Field(
        default=PromptEnvironment.PROD,
        description="Deployment environment"
    )
    prompt_type: PromptType = Field(
        default=PromptType.SYSTEM,
        description="Prompt type"
    )
    response_format: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Expected response format"
    )
    metadata: Optional[PromptMetadata] = Field(
        default=None,
        description="Full metadata"
    )
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Creation timestamp"
    )
    
    _template: Optional[PromptTemplate] = None
    
    def model_post_init(self, __context: Any) -> None:
        """Create template after initialization."""
        self._template = PromptTemplate(content=self.content)
    
    @property
    def template(self) -> PromptTemplate:
        """Get the prompt template."""
        if self._template is None:
            self._template = PromptTemplate(content=self.content)
        return self._template
    
    def get_dynamic_variables(self) -> Set[str]:
        """Get the set of dynamic variables in this prompt."""
        return self.template.get_all_variables()
    
    def get_required_variables(self) -> Set[str]:
        """Get variables that must be provided for rendering."""
        return self.template.get_required_variables()
    
    def render(
        self,
        variables: Optional[Dict[str, Any]] = None,
        strict: bool = True
    ) -> str:
        """
        Render the prompt with variables.
        
        Args:
            variables: Variable values to substitute
            strict: Raise error if variables missing
            
        Returns:
            Rendered prompt string
        """
        return self.template.render(variables, strict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self.model_dump(exclude={'_template'})


class PromptEntry(BaseModel):
    """
    A complete prompt entry with all versions.
    
    Represents a prompt with all its versions and metadata.
    Used for storage and retrieval.
    
    Supports:
    - Multiple versions
    - Model-specific variations per version
    - Environment-based deployment
    - Fallback logic for retrieval
    
    Attributes:
        label: Unique label for the prompt
        description: Description of the prompt
        category: Prompt category
        prompt_type: System or user prompt
        tags: Tags for categorization
        versions: List of all versions
        default_version: Default version to use
        default_model: Default model target
        default_environment: Default environment
        created_at: Creation timestamp
        updated_at: Last update timestamp
    
    Example:
        entry = PromptEntry(
            label="code_review",
            description="Prompt for code review",
            prompt_type=PromptType.SYSTEM,
            versions=[
                PromptVersion(version="1.0.0", content="..."),
                PromptVersion(version="1.1.0", content="...", model_target="gpt-4"),
            ]
        )
    """
    
    label: str = Field(description="Unique label")
    description: str = Field(
        default="",
        description="Description"
    )
    category: PromptCategory = Field(
        default=PromptCategory.TEMPLATE,
        description="Category"
    )
    prompt_type: PromptType = Field(
        default=PromptType.SYSTEM,
        description="Prompt type"
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Tags"
    )
    versions: List[PromptVersion] = Field(
        default_factory=list,
        description="All versions"
    )
    default_version: str = Field(
        default=DEFAULT_VERSION,
        description="Default version"
    )
    default_model: str = Field(
        default=DEFAULT_MODEL,
        description="Default model target"
    )
    default_environment: PromptEnvironment = Field(
        default=PromptEnvironment.PROD,
        description="Default environment"
    )
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Creation timestamp"
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Last update timestamp"
    )
    
    def get_version(
        self,
        version: Optional[str] = None,
        model: Optional[str] = None,
        environment: Optional[PromptEnvironment] = None
    ) -> Optional[PromptVersion]:
        """
        Get a specific version with fallback logic.
        
        Resolution order:
        1. Exact match for version + model + environment
        2. Exact version + model, fallback environment
        3. Exact version, any model, fallback environment
        4. Latest version for model + environment
        5. Latest version with fallback
        
        Args:
            version: Version string (None = latest)
            model: Model target (None = default)
            environment: Environment (None = prod, then fallback)
            
        Returns:
            PromptVersion or None
        """
        if not self.versions:
            return None
        
        target_env = environment or PromptEnvironment.PROD
        target_model = model or self.default_model
        
        # Define environment fallback order
        env_order = [PromptEnvironment.PROD, PromptEnvironment.STAGING, 
                     PromptEnvironment.DEV, PromptEnvironment.TEST]
        
        # Start from target environment
        if target_env in env_order:
            idx = env_order.index(target_env)
            env_order = env_order[idx:] + env_order[:idx]
        
        def find_version(
            candidates: List[PromptVersion],
            ver: Optional[str],
            mod: Optional[str],
            envs: List[PromptEnvironment]
        ) -> Optional[PromptVersion]:
            """Find best matching version."""
            for env in envs:
                for v in reversed(candidates):  # Latest first
                    env_match = v.environment == env
                    ver_match = ver is None or v.version == ver
                    mod_match = mod is None or v.model_target == mod or v.model_target == DEFAULT_MODEL
                    
                    if env_match and ver_match and mod_match:
                        return v
            return None
        
        # Try with model specificity
        result = find_version(self.versions, version, target_model, env_order)
        if result:
            return result
        
        # Try without model constraint
        result = find_version(self.versions, version, None, env_order)
        if result:
            return result
        
        # Ultimate fallback: latest version
        return self.versions[-1] if self.versions else None
    
    def get_content(
        self,
        version: Optional[str] = None,
        model: Optional[str] = None,
        environment: Optional[PromptEnvironment] = None,
        variables: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Get prompt content for a specific version/model/environment.
        
        Args:
            version: Version to retrieve
            model: Model target
            environment: Environment
            variables: Variables to substitute in template
            
        Returns:
            Rendered prompt content or None
        """
        v = self.get_version(version, model, environment)
        if v:
            if variables:
                return v.render(variables)
            return v.content
        return None
    
    def add_version(self, version: PromptVersion) -> None:
        """
        Add a new version.
        
        The version is marked as immutable upon addition.
        """
        # Mark as immutable
        if version.metadata:
            version.metadata.mark_immutable()
        
        self.versions.append(version)
        self.updated_at = datetime.utcnow().isoformat()
    
    def version_exists(self, version: str, model: str = DEFAULT_MODEL, 
                       environment: PromptEnvironment = PromptEnvironment.PROD) -> bool:
        """Check if a specific version already exists."""
        for v in self.versions:
            if (v.version == version and 
                v.model_target == model and 
                v.environment == environment):
                return True
        return False
    
    def get_latest_version(self) -> Optional[str]:
        """Get the latest version string."""
        if self.versions:
            return self.versions[-1].version
        return None
    
    def get_dynamic_variables(
        self,
        version: Optional[str] = None,
        model: Optional[str] = None
    ) -> Set[str]:
        """
        Get dynamic variables for a specific version.
        
        Args:
            version: Version to check
            model: Model target
            
        Returns:
            Set of variable names
        """
        v = self.get_version(version, model)
        if v:
            return v.get_dynamic_variables()
        return set()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PromptEntry':
        """Create from dictionary."""
        return cls(**data)


class PromptRetrievalResult(BaseModel):
    """
    Result of a prompt retrieval operation.
    
    Contains the prompt content along with metadata about
    which version, environment, and model was actually used.
    Useful for logging and debugging fallback behavior.
    
    Attributes:
        content: The rendered prompt content
        prompt_id: ID of the prompt metadata
        label: Prompt label
        version: Version that was used
        model: Model target that was matched
        environment: Environment that was matched
        prompt_type: Type of prompt
        response_format: Response format if defined
        variables_used: Variables that were substituted
        fallback_used: Whether fallback was used
        original_environment: Originally requested environment
    """
    
    content: str = Field(description="Rendered prompt content")
    prompt_id: str = Field(description="Prompt metadata ID")
    label: str = Field(description="Prompt label")
    version: str = Field(description="Version used")
    model: str = Field(description="Model target used")
    environment: PromptEnvironment = Field(description="Environment used")
    prompt_type: PromptType = Field(description="Prompt type")
    response_format: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Response format if defined"
    )
    variables_used: Dict[str, Any] = Field(
        default_factory=dict,
        description="Variables that were substituted"
    )
    fallback_used: bool = Field(
        default=False,
        description="Whether fallback was used"
    )
    original_environment: Optional[PromptEnvironment] = Field(
        default=None,
        description="Originally requested environment"
    )
