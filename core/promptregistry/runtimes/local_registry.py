"""
Local Prompt Registry Implementation.

Provides a file-system based prompt registry.
"""

from typing import Dict, List, Optional
from datetime import datetime
import re

from ..interfaces.prompt_registry_interfaces import IPromptRegistry
from ..spec.prompt_models import PromptMetadata, PromptEntry, PromptVersion
from ..enum import PromptStatus
from .local_storage import LocalFileStorage
from ..constants import (
    DEFAULT_STORAGE_PATH,
    DEFAULT_VERSION,
    DEFAULT_MODEL,
    LATEST_VERSION,
    ERROR_PROMPT_NOT_FOUND,
)


class LocalPromptRegistry(IPromptRegistry):
    """
    Local file-system based prompt registry.
    
    Stores prompts as JSON files with support for:
    - Multiple versions per prompt
    - Model-specific variations
    - Performance metrics tracking
    
    Storage Structure:
        .prompts/
            greeting.json       # Contains all versions of "greeting" prompt
            code_review.json    # Contains all versions of "code_review" prompt
    
    Usage:
        registry = LocalPromptRegistry(storage_path=".prompts")
        
        # Save prompt
        prompt_id = await registry.save_prompt(
            label="greeting",
            content="Hello, I am {name}!",
            metadata=PromptMetadata(model_target="gpt-4")
        )
        
        # Get prompt
        content = await registry.get_prompt("greeting", model="gpt-4")
        
        # Get with full metadata
        entry = await registry.get_prompt_entry("greeting")
    """
    
    def __init__(self, storage_path: str = DEFAULT_STORAGE_PATH):
        """
        Initialize local registry.
        
        Args:
            storage_path: Directory path for storing prompts
        """
        self.storage = LocalFileStorage(storage_path)
    
    async def save_prompt(
        self,
        label: str,
        content: str,
        metadata: Optional[PromptMetadata] = None
    ) -> str:
        """
        Save a prompt.
        
        Creates new version if prompt exists, otherwise creates new entry.
        """
        # Load existing entry or create new
        existing_data = await self.storage.load(label)
        
        if existing_data:
            entry = PromptEntry.from_dict(existing_data)
            # Increment version
            version = self._increment_version(entry.get_latest_version() or DEFAULT_VERSION)
        else:
            entry = PromptEntry(label=label)
            version = DEFAULT_VERSION
        
        # Create metadata if not provided
        if metadata is None:
            metadata = PromptMetadata(version=version)
        else:
            metadata = metadata.model_copy(update={"version": version})
        
        # Create version
        prompt_version = PromptVersion(
            version=version,
            content=content,
            model_target=metadata.model_target,
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
        
        # Save
        await self.storage.save(label, entry.model_dump())
        
        return metadata.id
    
    async def get_prompt(
        self,
        label: str,
        version: Optional[str] = None,
        model: Optional[str] = None
    ) -> str:
        """Get prompt content."""
        entry = await self.get_prompt_entry(label, version, model)
        
        prompt_version = entry.get_version(version, model)
        if prompt_version:
            return prompt_version.content
        
        raise ValueError(ERROR_PROMPT_NOT_FOUND.format(label=label))
    
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
    
    async def list_prompts(
        self,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[str]:
        """List all prompt labels."""
        keys = await self.storage.list_keys()
        
        if not category and not tags:
            return keys
        
        # Filter by category and tags
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
                
                filtered.append(key)
        
        return filtered
    
    async def list_versions(self, label: str) -> List[PromptVersion]:
        """List all versions of a prompt."""
        entry = await self.get_prompt_entry(label)
        return entry.versions
    
    async def update_metrics(
        self,
        prompt_id: str,
        metrics: Dict[str, float]
    ) -> None:
        """Update performance metrics for a prompt."""
        # Find the prompt by ID
        keys = await self.storage.list_keys()
        
        for key in keys:
            data = await self.storage.load(key)
            if data:
                entry = PromptEntry.from_dict(data)
                
                # Find version with matching ID
                for version in entry.versions:
                    if version.metadata and version.metadata.id == prompt_id:
                        version.metadata.performance_metrics.update(metrics)
                        version.metadata.update_timestamp()
                        
                        # Save updated entry
                        await self.storage.save(key, entry.model_dump())
                        return
        
        raise ValueError(f"Prompt not found with ID: {prompt_id}")
    
    async def delete_prompt(
        self,
        label: str,
        version: Optional[str] = None
    ) -> None:
        """Delete a prompt."""
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
        min_accuracy: Optional[float] = None
    ) -> List[PromptVersion]:
        """Get prompt versions with metrics for fine-tuning."""
        entry = await self.get_prompt_entry(label)
        
        versions = []
        for version in entry.versions:
            # Include versions with metrics
            if version.metadata and version.metadata.performance_metrics:
                # Filter by minimum accuracy if specified
                if min_accuracy is not None:
                    accuracy = version.metadata.performance_metrics.get("accuracy", 0)
                    if accuracy < min_accuracy:
                        continue
                
                versions.append(version)
        
        return versions
    
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
        category: Optional[str] = None
    ) -> List[PromptEntry]:
        """
        Search prompts by content or label.
        
        Args:
            query: Search query
            category: Optional category filter
            
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

