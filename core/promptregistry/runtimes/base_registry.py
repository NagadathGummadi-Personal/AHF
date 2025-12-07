"""
Base Prompt Registry Implementation.

Provides common logic for all prompt registry implementations.
Derived classes only need to implement storage-specific initialization.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Set, Any

from ..interfaces.prompt_registry_interfaces import (
    IPromptRegistry,
    IPromptStorage,
    IPromptValidator,
    IPromptSecurity,
    SecurityContext,
)
from ..spec.prompt_models import (
    PromptMetadata,
    PromptEntry,
    PromptVersion,
    PromptRetrievalResult,
    RuntimeMetrics,
)
from core.llms.spec.llm_result import LLMUsage
from ..enum import PromptEnvironment, PromptType
from ..constants import (
    DEFAULT_VERSION,
    DEFAULT_MODEL,
    ERROR_PROMPT_NOT_FOUND,
    ERROR_IMMUTABLE_PROMPT,
    ERROR_NO_FALLBACK_FOUND,
)


class BasePromptRegistry(IPromptRegistry, ABC):
    """
    Abstract base class for prompt registries.
    
    Provides common implementation for all prompt registry operations.
    Derived classes only need to:
    1. Initialize the storage backend in __init__
    2. Optionally override methods for storage-specific optimizations
    
    Storage Structure (conceptual):
        - Each prompt label maps to a PromptEntry
        - Each PromptEntry contains multiple PromptVersions
        - Versions are immutable once created
    
    Example:
        class S3PromptRegistry(BasePromptRegistry):
            def __init__(self, bucket: str, prefix: str = "prompts/"):
                self.storage = S3PromptStorage(bucket, prefix)
                self.validator = None
                self.security = None
                self._prompt_id_cache = {}
    """
    
    # These must be set by derived classes
    storage: IPromptStorage
    validator: Optional[IPromptValidator]
    security: Optional[IPromptSecurity]
    _prompt_id_cache: Dict[str, str]  # prompt_id -> label mapping
    
    # =========================================================================
    # CORE CRUD OPERATIONS
    # =========================================================================
    
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
            
            # Determine version: if metadata explicitly provides a version, use it;
            # otherwise auto-increment from the latest version
            if metadata is not None:
                # User explicitly provided metadata with a version - use it
                version = metadata.version
            else:
                # No metadata provided - auto-increment
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
        """Get prompt content with optional variable substitution."""
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
        """Get prompt with full fallback logic and metadata."""
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
    
    async def delete_prompt(
        self,
        label: str,
        version: Optional[str] = None,
        security_context: Optional[SecurityContext] = None
    ) -> None:
        """Delete a prompt or specific version."""
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
    
    # =========================================================================
    # LIST AND SEARCH OPERATIONS
    # =========================================================================
    
    async def list_prompts(
        self,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        environment: Optional[PromptEnvironment] = None,
        prompt_type: Optional[PromptType] = None,
        security_context: Optional[SecurityContext] = None
    ) -> List[str]:
        """List all prompt labels with optional filters."""
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
    
    async def search_prompts(
        self,
        query: str,
        category: Optional[str] = None,
        environment: Optional[PromptEnvironment] = None
    ) -> List[PromptEntry]:
        """Search prompts by content or label."""
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
    
    # =========================================================================
    # METRICS OPERATIONS
    # =========================================================================
    
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
    
    async def record_usage_from_llm(
        self,
        prompt_id: str,
        usage: Optional[LLMUsage],
        latency_ms: float,
        success: bool = True
    ) -> None:
        """Convenience method to record usage directly from an LLMUsage object."""
        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0
        cost = usage.cost_usd if usage and usage.cost_usd is not None else 0.0

        await self.record_usage(
            prompt_id=prompt_id,
            latency_ms=latency_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost=cost,
            success=success
        )
    
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
            
            for version in entry.versions:
                if version.metadata and version.metadata.id == prompt_id:
                    version.metadata.performance_metrics.update(metrics)
                    version.metadata.update_timestamp()
                    
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
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
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
