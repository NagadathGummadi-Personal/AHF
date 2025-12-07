"""
Local Prompt Registry Implementation.

Provides a file-system based prompt registry with support for:
- Versioning with LLM-specific variants
- Environment-based deployment and fallback
- Immutability enforcement
- Dynamic variable substitution
- Runtime metrics tracking
- Pluggable validation and security
"""

from typing import Dict, List, Optional, Set, Any, TYPE_CHECKING
from datetime import datetime
import re

from ...interfaces.prompt_registry_interfaces import (
    IPromptRegistry,
    IPromptStorage,
    IPromptValidator,
    IPromptSecurity,
    SecurityContext,
    ValidationResult,
)
from ...spec.prompt_models import (
    PromptMetadata,
    PromptEntry,
    PromptVersion,
    PromptRetrievalResult,
    RuntimeMetrics,
)
from ...enum import PromptStatus, PromptEnvironment, PromptType, PromptCategory
from .local_storage import LocalFileStorage
from ...constants import (
    DEFAULT_STORAGE_PATH,
    DEFAULT_VERSION,
    DEFAULT_MODEL,
    DEFAULT_ENVIRONMENT,
    ENV_PRIORITY,
    ERROR_PROMPT_NOT_FOUND,
    ERROR_IMMUTABLE_PROMPT,
    ERROR_NO_FALLBACK_FOUND,
)


class LocalPromptRegistry(IPromptRegistry):
    """
    Local file-system based prompt registry.
    
    Stores prompts as JSON/YAML files with support for:
    - Multiple versions per prompt (immutable once created)
    - Model-specific variations
    - Environment-based deployment with fallback
    - Runtime metrics tracking
    - Dynamic variable substitution
    
    Storage Structure:
        .prompts/
            agent_react_system.json       # React agent system prompt
            agent_goal_based_planning.json
            greeting.json
    
    Immutability:
        Once a version is saved, it cannot be modified. Creating a new
        prompt with the same label auto-increments the version.
    
    Fallback Logic:
        When retrieving prompts, if the requested environment is not found,
        the system falls back: prod -> staging -> dev -> test
    
    Usage:
        registry = LocalPromptRegistry(storage_path=".prompts")
        
        # Save prompt (creates immutable version)
        prompt_id = await registry.save_prompt(
            label="greeting",
            content="Hello, I am {name}!",
            metadata=PromptMetadata(
                model_target="gpt-4",
                environment=PromptEnvironment.PROD,
                prompt_type=PromptType.SYSTEM
            )
        )
        
        # Get prompt with fallback
        result = await registry.get_prompt_with_fallback(
            "greeting",
            model="gpt-4",
            variables={"name": "Assistant"}
        )
        
        # Record usage
        await registry.record_usage(prompt_id, latency_ms=150, prompt_tokens=100)
    """
    
    def __init__(
        self,
        storage_path: str = DEFAULT_STORAGE_PATH,
        format: str = "json",
        storage: Optional[IPromptStorage] = None,
        validator: Optional[IPromptValidator] = None,
        security: Optional[IPromptSecurity] = None,
    ):
        """
        Initialize local registry with pluggable components.
        
        Args:
            storage_path: Directory path for storing prompts (used if storage not provided)
            format: Storage format ("json" or "yaml") (used if storage not provided)
            storage: Custom storage implementation (overrides storage_path/format)
            validator: Validator for content/variable validation
            security: Security implementation for access control
        
        Example:
            # Simple usage with defaults
            registry = LocalPromptRegistry(storage_path=".prompts")
            
            # With custom storage
            registry = LocalPromptRegistry(
                storage=S3PromptStorage(bucket="my-prompts")
            )
            
            # With validation and security
            registry = LocalPromptRegistry(
                storage_path=".prompts",
                validator=BasicPromptValidator(max_content_length=50000),
                security=RoleBasedPromptSecurity(write_roles=["admin"])
            )
        """
        # Use provided storage or create default
        if storage is not None:
            self.storage = storage
        else:
            self.storage = LocalFileStorage(storage_path, format=format)
        
        # Optional validator (NoOp by default - no validation)
        self.validator = validator
        
        # Optional security (NoOp by default - all access allowed)
        self.security = security
        
        self._prompt_id_cache: Dict[str, str] = {}  # prompt_id -> label mapping
    
    async def save_prompt(
        self,
        label: str,
        content: str,
        metadata: Optional[PromptMetadata] = None,
        security_context: Optional[SecurityContext] = None
    ) -> str:
        """
        Save a prompt.
        
        Creates new version if prompt exists, otherwise creates new entry.
        The version is immutable after creation.
        
        Args:
            label: Unique label for the prompt
            content: Prompt content
            metadata: Optional metadata
            security_context: Security context for access control
            
        Returns:
            Prompt ID
            
        Raises:
            PermissionError: If security check fails
            ValueError: If validation fails or immutability violated
        """
        # Security check
        if self.security and security_context:
            decision = self.security.can_write(label, security_context)
            if not decision.allowed:
                raise PermissionError(f"Write access denied: {decision.reason}")
        
        # Validate label
        if self.validator:
            label_result = self.validator.validate_label(label)
            if not label_result.is_valid:
                raise ValueError(f"Invalid label: {', '.join(label_result.errors)}")
        
        # Validate content
        if self.validator:
            content_result = self.validator.validate_content(content)
            if not content_result.is_valid:
                raise ValueError(f"Invalid content: {', '.join(content_result.errors)}")
            content = content_result.sanitized_value or content
        
        # Validate metadata
        if self.validator and metadata:
            metadata_result = self.validator.validate_metadata(metadata)
            if not metadata_result.is_valid:
                raise ValueError(f"Invalid metadata: {', '.join(metadata_result.errors)}")
        
        # Load existing entry or create new
        existing_data = await self.storage.load(label)
        
        if existing_data:
            entry = PromptEntry.from_dict(existing_data)
            
            # Determine version
            if metadata and metadata.version != DEFAULT_VERSION:
                version = metadata.version
            else:
                version = self._increment_version(entry.get_latest_version() or DEFAULT_VERSION)
            
            # Check for immutability violation
            model_target = metadata.model_target if metadata else DEFAULT_MODEL
            environment = metadata.environment if metadata else PromptEnvironment.PROD
            
            if entry.version_exists(version, model_target, environment):
                raise ValueError(
                    ERROR_IMMUTABLE_PROMPT.format(label=label, version=version)
                )
        else:
            entry = PromptEntry(label=label)
            version = metadata.version if metadata else DEFAULT_VERSION
        
        # Create metadata if not provided
        if metadata is None:
            metadata = PromptMetadata(version=version)
        else:
            metadata = metadata.model_copy(update={"version": version})
        
        # Mark as immutable
        metadata.mark_immutable()
        
        # Create version
        prompt_version = PromptVersion(
            version=version,
            content=content,
            model_target=metadata.model_target,
            environment=metadata.environment,
            prompt_type=metadata.prompt_type,
            response_format=metadata.response_format,
            metadata=metadata,
        )
        
        # Add to entry
        entry.add_version(prompt_version)
        
        # Update entry metadata from version metadata
        if metadata.tags:
            entry.tags = list(set(entry.tags + metadata.tags))
        if metadata.category:
            entry.category = metadata.category
        if metadata.description:
            entry.description = metadata.description
        if metadata.prompt_type:
            entry.prompt_type = metadata.prompt_type
        
        # Save
        await self.storage.save(label, entry.model_dump())
        
        # Cache the mapping
        self._prompt_id_cache[metadata.id] = label
        
        return metadata.id
    
    async def get_prompt(
        self,
        label: str,
        version: Optional[str] = None,
        model: Optional[str] = None,
        environment: Optional[PromptEnvironment] = None,
        variables: Optional[Dict[str, Any]] = None,
        security_context: Optional[SecurityContext] = None
    ) -> str:
        """
        Get prompt content with optional variable substitution.
        
        Args:
            label: Prompt label
            version: Optional version
            model: Optional model target
            environment: Optional environment
            variables: Variables for template substitution
            security_context: Security context for access control
            
        Returns:
            Rendered prompt content
            
        Raises:
            PermissionError: If security check fails
            ValueError: If prompt not found or variables invalid
        """
        # Security check
        if self.security and security_context:
            decision = self.security.can_read(label, security_context)
            if not decision.allowed:
                raise PermissionError(f"Read access denied: {decision.reason}")
        
        entry = await self.get_prompt_entry(label, version, model)
        
        prompt_version = entry.get_version(version, model, environment)
        if prompt_version:
            if variables:
                # Validate variables before substitution
                if self.validator:
                    allowed_keys = prompt_version.get_dynamic_variables()
                    var_result = self.validator.validate_variables(variables, allowed_keys)
                    if not var_result.is_valid:
                        raise ValueError(f"Invalid variables: {', '.join(var_result.errors)}")
                    variables = var_result.sanitized_value or variables
                
                return prompt_version.render(variables)
            return prompt_version.content
        
        raise ValueError(ERROR_PROMPT_NOT_FOUND.format(label=label))
    
    async def get_prompt_with_fallback(
        self,
        label: str,
        version: Optional[str] = None,
        model: Optional[str] = None,
        environment: Optional[PromptEnvironment] = None,
        variables: Optional[Dict[str, Any]] = None,
        response_format: Optional[Dict[str, Any]] = None,
        security_context: Optional[SecurityContext] = None
    ) -> PromptRetrievalResult:
        """
        Get prompt with full fallback logic and metadata.
        
        Returns detailed information about which version/environment was used.
        
        Args:
            label: Prompt label
            version: Optional version
            model: Optional model target
            environment: Preferred environment
            variables: Variables for template substitution
            response_format: Override response format
            security_context: Security context for access control
            
        Returns:
            PromptRetrievalResult with content and metadata
            
        Raises:
            PermissionError: If security check fails
        """
        # Security check
        if self.security and security_context:
            decision = self.security.can_read(label, security_context)
            if not decision.allowed:
                raise PermissionError(f"Read access denied: {decision.reason}")
        
        entry = await self.get_prompt_entry(label, version, model)
        
        target_env = environment or PromptEnvironment.PROD
        prompt_version = entry.get_version(version, model, target_env)
        
        if not prompt_version:
            raise ValueError(ERROR_NO_FALLBACK_FOUND.format(label=label))
        
        # Determine if fallback was used
        fallback_used = (
            environment is not None and 
            prompt_version.environment != environment
        )
        
        # Validate and render content
        if variables:
            # Validate variables before substitution
            if self.validator:
                allowed_keys = prompt_version.get_dynamic_variables()
                var_result = self.validator.validate_variables(variables, allowed_keys)
                if not var_result.is_valid:
                    raise ValueError(f"Invalid variables: {', '.join(var_result.errors)}")
                variables = var_result.sanitized_value or variables
            
            content = prompt_version.render(variables)
        else:
            content = prompt_version.content
        
        # Determine response format (user override takes precedence)
        final_response_format = response_format or prompt_version.response_format
        
        return PromptRetrievalResult(
            content=content,
            prompt_id=prompt_version.metadata.id if prompt_version.metadata else "",
            label=label,
            version=prompt_version.version,
            model=prompt_version.model_target,
            environment=prompt_version.environment,
            prompt_type=prompt_version.prompt_type,
            response_format=final_response_format,
            variables_used=variables or {},
            fallback_used=fallback_used,
            original_environment=environment,
        )
    
    async def get_prompt_entry(
        self,
        label: str,
        version: Optional[str] = None,
        model: Optional[str] = None
    ) -> PromptEntry:
        """Get full prompt entry."""
        data = await self.storage.load(label)
        
        if not data:
            raise ValueError(ERROR_PROMPT_NOT_FOUND.format(label=label))
        
        return PromptEntry.from_dict(data)
    
    async def get_dynamic_variables(
        self,
        label: str,
        version: Optional[str] = None,
        model: Optional[str] = None
    ) -> Set[str]:
        """Get the dynamic variables required by a prompt."""
        entry = await self.get_prompt_entry(label, version, model)
        return entry.get_dynamic_variables(version, model)
    
    async def list_prompts(
        self,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        environment: Optional[PromptEnvironment] = None,
        prompt_type: Optional[PromptType] = None,
        security_context: Optional[SecurityContext] = None
    ) -> List[str]:
        """
        List all prompt labels.
        
        Args:
            category: Optional category filter
            tags: Optional tag filter
            environment: Optional environment filter
            prompt_type: Optional prompt type filter
            security_context: Security context for filtering accessible prompts
            
        Returns:
            List of prompt labels
        """
        keys = await self.storage.list_keys()
        
        # Security filter
        if self.security and security_context:
            keys = self.security.filter_accessible(keys, security_context, "read")
        
        if not category and not tags and not environment and not prompt_type:
            return keys
        
        # Filter by criteria
        filtered = []
        for key in keys:
            data = await self.storage.load(key)
            if data:
                entry = PromptEntry.from_dict(data)
                
                # Check category
                if category and entry.category.value != category:
                    continue
                
                # Check tags (must have all)
                if tags and not all(t in entry.tags for t in tags):
                    continue
                
                # Check prompt type
                if prompt_type and entry.prompt_type != prompt_type:
                    continue
                
                # Check environment (at least one version in this env)
                if environment:
                    has_env = any(v.environment == environment for v in entry.versions)
                    if not has_env:
                        continue
                
                filtered.append(key)
        
        return filtered
    
    async def list_versions(
        self,
        label: str,
        model: Optional[str] = None,
        environment: Optional[PromptEnvironment] = None
    ) -> List[PromptVersion]:
        """List all versions of a prompt."""
        entry = await self.get_prompt_entry(label)
        
        versions = entry.versions
        
        # Filter by model if specified
        if model:
            versions = [v for v in versions if v.model_target == model or v.model_target == DEFAULT_MODEL]
        
        # Filter by environment if specified
        if environment:
            versions = [v for v in versions if v.environment == environment]
        
        return versions
    
    async def record_usage(
        self,
        prompt_id: str,
        latency_ms: float = 0.0,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        cost: float = 0.0,
        success: bool = True
    ) -> None:
        """Record runtime usage metrics for a prompt."""
        # Find the prompt by ID
        label = await self._find_label_by_id(prompt_id)
        if not label:
            return  # Silently skip if not found
        
        data = await self.storage.load(label)
        if data:
            entry = PromptEntry.from_dict(data)
            
            # Find version with matching ID
            for version in entry.versions:
                if version.metadata and version.metadata.id == prompt_id:
                    version.metadata.record_usage(
                        latency_ms=latency_ms,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        cost=cost,
                        success=success
                    )
                    
                    # Save updated entry
                    await self.storage.save(label, entry.model_dump())
                    return
    
    async def update_metrics(
        self,
        prompt_id: str,
        metrics: Dict[str, float]
    ) -> None:
        """Update legacy performance metrics for a prompt."""
        label = await self._find_label_by_id(prompt_id)
        if not label:
            raise ValueError(f"Prompt not found with ID: {prompt_id}")
        
        data = await self.storage.load(label)
        if data:
            entry = PromptEntry.from_dict(data)
            
            # Find version with matching ID
            for version in entry.versions:
                if version.metadata and version.metadata.id == prompt_id:
                    version.metadata.performance_metrics.update(metrics)
                    version.metadata.update_timestamp()
                    
                    # Save updated entry
                    await self.storage.save(label, entry.model_dump())
                    return
        
        raise ValueError(f"Prompt not found with ID: {prompt_id}")
    
    async def update_eval_scores(
        self,
        prompt_id: str,
        llm_eval_score: Optional[float] = None,
        human_eval_score: Optional[float] = None
    ) -> None:
        """Update evaluation scores for a prompt."""
        label = await self._find_label_by_id(prompt_id)
        if not label:
            raise ValueError(f"Prompt not found with ID: {prompt_id}")
        
        data = await self.storage.load(label)
        if data:
            entry = PromptEntry.from_dict(data)
            
            for version in entry.versions:
                if version.metadata and version.metadata.id == prompt_id:
                    if llm_eval_score is not None:
                        version.metadata.llm_eval_score = llm_eval_score
                    if human_eval_score is not None:
                        version.metadata.human_eval_score = human_eval_score
                    version.metadata.update_timestamp()
                    
                    await self.storage.save(label, entry.model_dump())
                    return
        
        raise ValueError(f"Prompt not found with ID: {prompt_id}")
    
    async def get_runtime_metrics(
        self,
        prompt_id: str
    ) -> RuntimeMetrics:
        """Get runtime metrics for a prompt."""
        label = await self._find_label_by_id(prompt_id)
        if not label:
            raise ValueError(f"Prompt not found with ID: {prompt_id}")
        
        data = await self.storage.load(label)
        if data:
            entry = PromptEntry.from_dict(data)
            
            for version in entry.versions:
                if version.metadata and version.metadata.id == prompt_id:
                    return version.metadata.runtime_metrics
        
        raise ValueError(f"Prompt not found with ID: {prompt_id}")
    
    async def delete_prompt(
        self,
        label: str,
        version: Optional[str] = None,
        security_context: Optional[SecurityContext] = None
    ) -> None:
        """
        Delete a prompt.
        
        Args:
            label: Prompt label
            version: Optional version (deletes all if not specified)
            security_context: Security context for access control
            
        Raises:
            PermissionError: If security check fails
        """
        # Security check
        if self.security and security_context:
            decision = self.security.can_delete(label, security_context)
            if not decision.allowed:
                raise PermissionError(f"Delete access denied: {decision.reason}")
        
        if version is None:
            # Delete entire prompt
            await self.storage.delete(label)
        else:
            # Delete specific version
            entry = await self.get_prompt_entry(label)
            entry.versions = [v for v in entry.versions if v.version != version]
            
            if not entry.versions:
                # No versions left, delete entire entry
                await self.storage.delete(label)
            else:
                await self.storage.save(label, entry.model_dump())
    
    async def get_fine_tuning_context(
        self,
        label: str,
        min_accuracy: Optional[float] = None,
        min_llm_eval: Optional[float] = None,
        min_human_eval: Optional[float] = None
    ) -> List[PromptVersion]:
        """Get prompt versions with metrics for fine-tuning."""
        entry = await self.get_prompt_entry(label)
        
        versions = []
        for version in entry.versions:
            if not version.metadata:
                continue
            
            # Filter by minimum accuracy
            if min_accuracy is not None:
                accuracy = version.metadata.performance_metrics.get("accuracy", 0)
                if accuracy < min_accuracy:
                    continue
            
            # Filter by LLM eval score
            if min_llm_eval is not None:
                if version.metadata.llm_eval_score is None or \
                   version.metadata.llm_eval_score < min_llm_eval:
                    continue
            
            # Filter by human eval score
            if min_human_eval is not None:
                if version.metadata.human_eval_score is None or \
                   version.metadata.human_eval_score < min_human_eval:
                    continue
            
            versions.append(version)
        
        return versions
    
    async def _find_label_by_id(self, prompt_id: str) -> Optional[str]:
        """Find the label for a prompt ID."""
        # Check cache first
        if prompt_id in self._prompt_id_cache:
            return self._prompt_id_cache[prompt_id]
        
        # Search through all prompts
        keys = await self.storage.list_keys()
        
        for key in keys:
            data = await self.storage.load(key)
            if data:
                entry = PromptEntry.from_dict(data)
                for version in entry.versions:
                    if version.metadata and version.metadata.id == prompt_id:
                        self._prompt_id_cache[prompt_id] = key
                        return key
        
        return None
    
    def _increment_version(self, version: str) -> str:
        """Increment version string (simple patch increment)."""
        parts = version.split(".")
        if len(parts) >= 3:
            try:
                parts[-1] = str(int(parts[-1]) + 1)
                return ".".join(parts)
            except ValueError:
                pass
        
        # Fallback: append .1
        return f"{version}.1"
    
    async def search_prompts(
        self,
        query: str,
        category: Optional[str] = None,
        environment: Optional[PromptEnvironment] = None
    ) -> List[PromptEntry]:
        """
        Search prompts by content or label.
        
        Args:
            query: Search query
            category: Optional category filter
            environment: Optional environment filter
            
        Returns:
            List of matching PromptEntry objects
        """
        results = []
        keys = await self.storage.list_keys()
        query_lower = query.lower()
        
        for key in keys:
            data = await self.storage.load(key)
            if data:
                entry = PromptEntry.from_dict(data)
                
                # Check category
                if category and entry.category.value != category:
                    continue
                
                # Check environment
                if environment:
                    has_env = any(v.environment == environment for v in entry.versions)
                    if not has_env:
                        continue
                
                # Search in label and description
                if query_lower in entry.label.lower() or query_lower in entry.description.lower():
                    results.append(entry)
                    continue
                
                # Search in tags
                if any(query_lower in tag.lower() for tag in entry.tags):
                    results.append(entry)
                    continue
                
                # Search in content
                for version in entry.versions:
                    if query_lower in version.content.lower():
                        results.append(entry)
                        break
        
        return results
