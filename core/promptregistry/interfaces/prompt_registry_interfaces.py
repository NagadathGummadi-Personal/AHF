"""
Interfaces for Prompt Registry.

This module defines the core protocols (interfaces) for prompt management,
including storage, validation, and security interfaces.

All components are designed to be pluggable - you can swap implementations
by implementing the corresponding interface.
"""

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable, Set, TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from ..spec.prompt_models import (
        PromptMetadata, 
        PromptEntry, 
        PromptVersion,
        PromptRetrievalResult,
        RuntimeMetrics,
    )
    from ..enum import PromptEnvironment, PromptType


# ============================================================================
# VALIDATION RESULT
# ============================================================================

@dataclass
class ValidationResult:
    """
    Result of a validation operation.
    
    Attributes:
        is_valid: Whether the validation passed
        errors: List of validation error messages
        sanitized_value: The sanitized/cleaned value (if applicable)
        warnings: Non-fatal warning messages
    """
    is_valid: bool
    errors: List[str]
    sanitized_value: Optional[Any] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


@dataclass
class SecurityContext:
    """
    Security context for access control.
    
    Attributes:
        user_id: User identifier
        tenant_id: Tenant/organization identifier
        roles: List of user roles
        permissions: List of explicit permissions
        metadata: Additional security metadata
    """
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    roles: List[str] = None
    permissions: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.roles is None:
            self.roles = []
        if self.permissions is None:
            self.permissions = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class AccessDecision:
    """
    Result of an access control decision.
    
    Attributes:
        allowed: Whether access is allowed
        reason: Reason for the decision
        required_permissions: Permissions that would grant access
    """
    allowed: bool
    reason: str = ""
    required_permissions: List[str] = None
    
    def __post_init__(self):
        if self.required_permissions is None:
            self.required_permissions = []


# ============================================================================
# VALIDATOR INTERFACE
# ============================================================================

@runtime_checkable
class IPromptValidator(Protocol):
    """
    Interface for Prompt Validation.
    
    Validates prompt content and variables to prevent prompt injection
    and ensure data integrity.
    
    Built-in implementations:
    - NoOpPromptValidator: Passes all validation (development/testing)
    - BasicPromptValidator: Basic validation rules
    
    Future implementations:
    - StrictPromptValidator: Strict security validation
    - MLPromptValidator: ML-based injection detection
    
    Example:
        validator = BasicPromptValidator(
            max_length=10000,
            blocked_patterns=[r'ignore.*instructions', r'system:']
        )
        
        result = validator.validate_content("Review this code...")
        if not result.is_valid:
            raise ValidationError(result.errors)
        
        # Validate variables before substitution
        var_result = validator.validate_variables({"name": user_input})
        if var_result.is_valid:
            prompt = template.render(var_result.sanitized_value)
    """
    
    def validate_content(self, content: str) -> ValidationResult:
        """
        Validate prompt content.
        
        Checks for:
        - Content length limits
        - Blocked patterns (injection attempts)
        - Required structure elements
        - Encoding issues
        
        Args:
            content: The prompt content to validate
            
        Returns:
            ValidationResult with is_valid and any errors
        """
        ...
    
    def validate_variables(
        self,
        variables: Dict[str, Any],
        allowed_keys: Optional[Set[str]] = None
    ) -> ValidationResult:
        """
        Validate variables before template substitution.
        
        Checks for:
        - Injection attempts in variable values
        - Variable value length limits
        - Type validation
        - Sanitization of special characters
        
        Args:
            variables: Dictionary of variable values
            allowed_keys: Optional set of allowed variable names
            
        Returns:
            ValidationResult with sanitized_value containing cleaned variables
        """
        ...
    
    def validate_label(self, label: str) -> ValidationResult:
        """
        Validate a prompt label.
        
        Args:
            label: The prompt label to validate
            
        Returns:
            ValidationResult
        """
        ...
    
    def validate_metadata(self, metadata: 'PromptMetadata') -> ValidationResult:
        """
        Validate prompt metadata.
        
        Args:
            metadata: The metadata to validate
            
        Returns:
            ValidationResult
        """
        ...
    
    def sanitize_content(self, content: str) -> str:
        """
        Sanitize prompt content (remove/escape dangerous patterns).
        
        Args:
            content: Content to sanitize
            
        Returns:
            Sanitized content string
        """
        ...
    
    def sanitize_variable_value(self, value: Any) -> Any:
        """
        Sanitize a single variable value.
        
        Args:
            value: The value to sanitize
            
        Returns:
            Sanitized value
        """
        ...


# ============================================================================
# SECURITY INTERFACE
# ============================================================================

@runtime_checkable
class IPromptSecurity(Protocol):
    """
    Interface for Prompt Security/Access Control.
    
    Controls who can read, write, and manage prompts.
    
    Built-in implementations:
    - NoOpPromptSecurity: Allows all access (development/testing)
    - RoleBasedPromptSecurity: Role-based access control
    
    Future implementations:
    - TenantPromptSecurity: Multi-tenant isolation
    - AttributeBasedPromptSecurity: ABAC implementation
    
    Example:
        security = RoleBasedPromptSecurity(
            admin_roles=["admin", "prompt_admin"],
            write_roles=["developer", "content_manager"],
            read_roles=["*"]  # Everyone can read
        )
        
        ctx = SecurityContext(user_id="user123", roles=["developer"])
        
        decision = security.can_write("code_review", ctx)
        if not decision.allowed:
            raise PermissionDenied(decision.reason)
    """
    
    def can_read(
        self,
        label: str,
        context: SecurityContext
    ) -> AccessDecision:
        """
        Check if the user can read a prompt.
        
        Args:
            label: Prompt label
            context: Security context with user info
            
        Returns:
            AccessDecision
        """
        ...
    
    def can_write(
        self,
        label: str,
        context: SecurityContext
    ) -> AccessDecision:
        """
        Check if the user can write/update a prompt.
        
        Args:
            label: Prompt label
            context: Security context with user info
            
        Returns:
            AccessDecision
        """
        ...
    
    def can_delete(
        self,
        label: str,
        context: SecurityContext
    ) -> AccessDecision:
        """
        Check if the user can delete a prompt.
        
        Args:
            label: Prompt label
            context: Security context with user info
            
        Returns:
            AccessDecision
        """
        ...
    
    def can_admin(
        self,
        label: str,
        context: SecurityContext
    ) -> AccessDecision:
        """
        Check if the user has admin access to a prompt.
        
        Admin access includes: update metrics, change status, etc.
        
        Args:
            label: Prompt label
            context: Security context with user info
            
        Returns:
            AccessDecision
        """
        ...
    
    def filter_accessible(
        self,
        labels: List[str],
        context: SecurityContext,
        operation: str = "read"
    ) -> List[str]:
        """
        Filter a list of labels to only those the user can access.
        
        Args:
            labels: List of prompt labels
            context: Security context
            operation: Type of operation ("read", "write", "delete", "admin")
            
        Returns:
            Filtered list of accessible labels
        """
        ...
    
    def get_required_permissions(
        self,
        label: str,
        operation: str
    ) -> List[str]:
        """
        Get the permissions required for an operation.
        
        Args:
            label: Prompt label
            operation: Operation type
            
        Returns:
            List of required permission strings
        """
        ...


@runtime_checkable
class IPromptRegistry(Protocol):
    """
    Interface for Prompt Registry.
    
    Centralized store for managing prompts with support for:
    - Versioning with LLM-specific variants
    - Environment-based deployment (prod, staging, dev, test)
    - Immutability enforcement (versions cannot be modified after creation)
    - Dynamic variable substitution
    - LLM and human evaluation scores
    - Runtime metrics tracking (latency, tokens, cost)
    - Fallback logic for retrieval
    
    Built-in implementations:
    - LocalPromptRegistry: File-system based storage (JSON/YAML)
    
    Future implementations:
    - S3PromptRegistry: S3/cloud storage
    - DatabasePromptRegistry: SQL database storage
    
    Example:
        registry = LocalPromptRegistry(storage_path=".prompts")
        
        # Save prompt (creates new version - immutable after save)
        prompt_id = await registry.save_prompt(
            label="greeting",
            content="Hello, I am {name}. How can I help with {task}?",
            metadata=PromptMetadata(
                model_target="gpt-4",
                environment=PromptEnvironment.PROD,
                prompt_type=PromptType.SYSTEM,
                tags=["greeting"],
                llm_eval_score=0.95,
                human_eval_score=0.92
            )
        )
        
        # Get prompt with fallback (prod -> staging -> dev -> test)
        result = await registry.get_prompt_with_fallback(
            "greeting",
            model="gpt-4",
            environment=PromptEnvironment.PROD,
            variables={"name": "Assistant", "task": "coding"}
        )
        
        # Record runtime usage
        await registry.record_usage(
            prompt_id,
            latency_ms=150,
            prompt_tokens=100,
            completion_tokens=50,
            cost=0.001
        )
        
        # Get required variables for a prompt
        variables = await registry.get_dynamic_variables("greeting")
    """
    
    async def save_prompt(
        self,
        label: str,
        content: str,
        metadata: Optional['PromptMetadata'] = None
    ) -> str:
        """
        Save a prompt.
        
        Creates a new version. If a prompt with the same label exists,
        increments the version. Once saved, the version is immutable
        and cannot be modified.
        
        Args:
            label: Unique label for the prompt
            content: Prompt content (can include {template} variables)
            metadata: Optional metadata (version, model, environment, tags, etc.)
            
        Returns:
            Unique prompt ID
            
        Raises:
            StorageError: If save fails
            ImmutableError: If trying to overwrite existing version
        """
        ...
    
    async def get_prompt(
        self,
        label: str,
        version: Optional[str] = None,
        model: Optional[str] = None,
        environment: Optional['PromptEnvironment'] = None,
        variables: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Retrieve a prompt.
        
        Resolution logic:
        1. If model is specified, look for model-specific prompt
        2. If version is specified, look for that version
        3. If environment specified, look for that environment first
        4. Default to latest version with prod environment
        
        Args:
            label: Prompt label
            version: Optional specific version
            model: Optional model target
            environment: Optional environment (defaults to prod)
            variables: Optional variables for template substitution
            
        Returns:
            Prompt content string (with variables substituted if provided)
            
        Raises:
            PromptNotFoundError: If prompt not found
            MissingVariablesError: If required variables not provided
        """
        ...
    
    async def get_prompt_with_fallback(
        self,
        label: str,
        version: Optional[str] = None,
        model: Optional[str] = None,
        environment: Optional['PromptEnvironment'] = None,
        variables: Optional[Dict[str, Any]] = None,
        response_format: Optional[Dict[str, Any]] = None
    ) -> 'PromptRetrievalResult':
        """
        Retrieve a prompt with full fallback logic and metadata.
        
        Fallback order for environment: prod -> staging -> dev -> test
        
        If response_format is provided, it overrides the prompt's defined format.
        Otherwise, uses the format defined in the prompt.
        
        Args:
            label: Prompt label
            version: Optional specific version (None = latest)
            model: Optional model target
            environment: Preferred environment (defaults to prod)
            variables: Variables for template substitution
            response_format: Override response format (optional)
            
        Returns:
            PromptRetrievalResult with content and metadata about what was used
            
        Raises:
            PromptNotFoundError: If prompt not found in any environment
        """
        ...
    
    async def get_prompt_entry(
        self,
        label: str,
        version: Optional[str] = None,
        model: Optional[str] = None
    ) -> 'PromptEntry':
        """
        Get full prompt entry with all versions and metadata.
        
        Args:
            label: Prompt label
            version: Optional version filter
            model: Optional model target filter
            
        Returns:
            PromptEntry with all versions and metadata
        """
        ...
    
    async def get_dynamic_variables(
        self,
        label: str,
        version: Optional[str] = None,
        model: Optional[str] = None
    ) -> Set[str]:
        """
        Get the dynamic variables required by a prompt.
        
        Args:
            label: Prompt label
            version: Optional version
            model: Optional model target
            
        Returns:
            Set of variable names that need to be provided
        """
        ...
    
    async def list_prompts(
        self,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        environment: Optional['PromptEnvironment'] = None,
        prompt_type: Optional['PromptType'] = None
    ) -> List[str]:
        """
        List all prompt labels.
        
        Args:
            category: Optional category filter
            tags: Optional tag filter (prompts must have all tags)
            environment: Optional environment filter
            prompt_type: Optional prompt type filter (system/user)
            
        Returns:
            List of prompt labels
        """
        ...
    
    async def list_versions(
        self,
        label: str,
        model: Optional[str] = None,
        environment: Optional['PromptEnvironment'] = None
    ) -> List['PromptVersion']:
        """
        List all versions of a prompt.
        
        Args:
            label: Prompt label
            model: Optional model filter
            environment: Optional environment filter
            
        Returns:
            List of PromptVersion objects
        """
        ...
    
    async def record_usage(
        self,
        prompt_id: str,
        latency_ms: float = 0.0,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        cost: float = 0.0,
        success: bool = True
    ) -> None:
        """
        Record runtime usage metrics for a prompt.
        
        Called after each prompt usage to track performance metrics
        like latency, token counts, and cost. These are aggregated
        to compute averages.
        
        Args:
            prompt_id: Prompt ID (returned from save_prompt or in metadata)
            latency_ms: Response latency in milliseconds
            prompt_tokens: Number of prompt tokens used
            completion_tokens: Number of completion tokens generated
            cost: Cost of the API call
            success: Whether the call was successful
        """
        ...
    
    async def update_metrics(
        self,
        prompt_id: str,
        metrics: Dict[str, float]
    ) -> None:
        """
        Update legacy performance metrics for a prompt.
        
        Args:
            prompt_id: Prompt ID (returned from save_prompt)
            metrics: Metric name-value pairs (e.g., {"accuracy": 0.95})
        """
        ...
    
    async def update_eval_scores(
        self,
        prompt_id: str,
        llm_eval_score: Optional[float] = None,
        human_eval_score: Optional[float] = None
    ) -> None:
        """
        Update evaluation scores for a prompt.
        
        Args:
            prompt_id: Prompt ID
            llm_eval_score: LLM evaluation score (0.0 to 1.0)
            human_eval_score: Human evaluation score (0.0 to 1.0)
        """
        ...
    
    async def get_runtime_metrics(
        self,
        prompt_id: str
    ) -> 'RuntimeMetrics':
        """
        Get runtime metrics for a prompt.
        
        Args:
            prompt_id: Prompt ID
            
        Returns:
            RuntimeMetrics object with usage statistics
        """
        ...
    
    async def delete_prompt(
        self,
        label: str,
        version: Optional[str] = None
    ) -> None:
        """
        Delete a prompt.
        
        Note: Deletion should be used sparingly. Consider deprecating instead.
        
        Args:
            label: Prompt label
            version: Optional version (deletes all if not specified)
        """
        ...
    
    async def get_fine_tuning_context(
        self,
        label: str,
        min_accuracy: Optional[float] = None,
        min_llm_eval: Optional[float] = None,
        min_human_eval: Optional[float] = None
    ) -> List['PromptVersion']:
        """
        Get prompt versions with metrics for fine-tuning.
        
        Returns versions that can be used to evaluate and improve prompts.
        
        Args:
            label: Prompt label
            min_accuracy: Optional minimum accuracy filter
            min_llm_eval: Optional minimum LLM eval score
            min_human_eval: Optional minimum human eval score
            
        Returns:
            List of PromptVersion objects with metrics
        """
        ...


@runtime_checkable
class IPromptStorage(Protocol):
    """
    Interface for Prompt Storage Backend.
    
    Low-level storage operations for prompts.
    Implementations handle actual persistence.
    
    Example:
        class S3PromptStorage(IPromptStorage):
            async def save(self, key, data):
                await self.s3.put_object(Bucket=self.bucket, Key=key, Body=data)
    """
    
    async def save(self, key: str, data: Dict[str, Any]) -> None:
        """
        Save data to storage.
        
        Args:
            key: Storage key
            data: Data to save
        """
        ...
    
    async def load(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Load data from storage.
        
        Args:
            key: Storage key
            
        Returns:
            Data dict or None if not found
        """
        ...
    
    async def delete(self, key: str) -> None:
        """
        Delete data from storage.
        
        Args:
            key: Storage key
        """
        ...
    
    async def exists(self, key: str) -> bool:
        """
        Check if key exists in storage.
        
        Args:
            key: Storage key
            
        Returns:
            True if exists
        """
        ...
    
    async def list_keys(self, prefix: Optional[str] = None) -> List[str]:
        """
        List all keys in storage.
        
        Args:
            prefix: Optional prefix filter
            
        Returns:
            List of keys
        """
        ...
