"""
Interfaces for Prompt Registry.

This module defines the core protocols (interfaces) for prompt management.
"""

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:
    from ..spec.prompt_models import PromptMetadata, PromptEntry, PromptVersion


@runtime_checkable
class IPromptRegistry(Protocol):
    """
    Interface for Prompt Registry.
    
    Centralized store for managing prompts with support for:
    - Versioning
    - Model-specific variations
    - Performance metrics tracking
    - Fine-tuning context
    
    Built-in implementations:
    - LocalPromptRegistry: File-system based storage
    
    Future implementations:
    - DatabasePromptRegistry: SQL database storage
    - RedisPromptRegistry: Redis-based storage
    - S3PromptRegistry: S3/cloud storage
    
    Example:
        registry = LocalPromptRegistry(storage_path=".prompts")
        
        # Save prompt
        prompt_id = await registry.save_prompt(
            label="greeting",
            content="Hello, I am {name}. How can I help?",
            metadata=PromptMetadata(tags=["greeting"])
        )
        
        # Get prompt (with model preference)
        prompt = await registry.get_prompt("greeting", model="gpt-4")
        
        # Update metrics
        await registry.update_metrics(prompt_id, {"accuracy": 0.95})
    """
    
    async def save_prompt(
        self,
        label: str,
        content: str,
        metadata: Optional['PromptMetadata'] = None
    ) -> str:
        """
        Save a prompt.
        
        If a prompt with the same label exists, creates a new version.
        
        Args:
            label: Unique label for the prompt
            content: Prompt content (can include template variables)
            metadata: Optional metadata (version, model, tags, etc.)
            
        Returns:
            Unique prompt ID
            
        Raises:
            StorageError: If save fails
        """
        ...
    
    async def get_prompt(
        self,
        label: str,
        version: Optional[str] = None,
        model: Optional[str] = None
    ) -> str:
        """
        Retrieve a prompt.
        
        Resolution logic:
        1. If model is specified, look for model-specific prompt
        2. If version is specified, look for that version
        3. Default to latest version with default model
        
        Args:
            label: Prompt label
            version: Optional specific version
            model: Optional model target
            
        Returns:
            Prompt content string
            
        Raises:
            PromptNotFoundError: If prompt not found
        """
        ...
    
    async def get_prompt_entry(
        self,
        label: str,
        version: Optional[str] = None,
        model: Optional[str] = None
    ) -> 'PromptEntry':
        """
        Get full prompt entry with metadata.
        
        Args:
            label: Prompt label
            version: Optional version
            model: Optional model target
            
        Returns:
            PromptEntry with content and metadata
        """
        ...
    
    async def list_prompts(
        self,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[str]:
        """
        List all prompt labels.
        
        Args:
            category: Optional category filter
            tags: Optional tag filter (prompts must have all tags)
            
        Returns:
            List of prompt labels
        """
        ...
    
    async def list_versions(self, label: str) -> List['PromptVersion']:
        """
        List all versions of a prompt.
        
        Args:
            label: Prompt label
            
        Returns:
            List of PromptVersion objects
        """
        ...
    
    async def update_metrics(
        self,
        prompt_id: str,
        metrics: Dict[str, float]
    ) -> None:
        """
        Update performance metrics for a prompt.
        
        Metrics are used for fine-tuning context - tracking which
        prompts perform better helps with prompt optimization.
        
        Args:
            prompt_id: Prompt ID (returned from save_prompt)
            metrics: Metric name-value pairs (e.g., {"accuracy": 0.95})
        """
        ...
    
    async def delete_prompt(
        self,
        label: str,
        version: Optional[str] = None
    ) -> None:
        """
        Delete a prompt.
        
        Args:
            label: Prompt label
            version: Optional version (deletes all if not specified)
        """
        ...
    
    async def get_fine_tuning_context(
        self,
        label: str,
        min_accuracy: Optional[float] = None
    ) -> List['PromptVersion']:
        """
        Get prompt versions with metrics for fine-tuning.
        
        Returns versions that can be used to evaluate and improve prompts.
        
        Args:
            label: Prompt label
            min_accuracy: Optional minimum accuracy filter
            
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

