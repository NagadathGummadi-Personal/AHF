"""
Prompt Models.

This module defines the data models for prompt entries and metadata.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

from ..enum import PromptStatus, PromptCategory
from ..constants import (
    DEFAULT_VERSION,
    DEFAULT_MODEL,
)


class PromptMetadata(BaseModel):
    """
    Metadata for a prompt.
    
    Contains information about the prompt's target model, tags,
    and performance metrics.
    
    Attributes:
        id: Unique prompt ID
        version: Version string (semver-style)
        model_target: Target model (e.g., "gpt-4", "claude-3")
        tags: List of tags for categorization
        category: Prompt category (system, user, template, etc.)
        status: Prompt status (draft, active, deprecated, archived)
        performance_metrics: Performance metrics (accuracy, latency, etc.)
        description: Human-readable description
        author: Author of the prompt
        created_at: Creation timestamp
        updated_at: Last update timestamp
    
    Example:
        metadata = PromptMetadata(
            version="1.0.0",
            model_target="gpt-4",
            tags=["code", "review"],
            performance_metrics={"accuracy": 0.95}
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
        description="Target model"
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
    performance_metrics: Dict[str, float] = Field(
        default_factory=dict,
        description="Performance metrics"
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
    extras: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    
    def update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow().isoformat()
    
    def add_metric(self, name: str, value: float) -> None:
        """Add or update a metric."""
        self.performance_metrics[name] = value
        self.update_timestamp()
    
    def get_metric(self, name: str, default: float = 0.0) -> float:
        """Get a metric value."""
        return self.performance_metrics.get(name, default)


class PromptVersion(BaseModel):
    """
    A specific version of a prompt.
    
    Represents a single version of a prompt with its content and metadata.
    
    Attributes:
        version: Version string
        content: Prompt content
        model_target: Target model for this version
        metadata: Full metadata
        created_at: Creation timestamp
    """
    
    version: str = Field(description="Version string")
    content: str = Field(description="Prompt content")
    model_target: str = Field(
        default=DEFAULT_MODEL,
        description="Target model"
    )
    metadata: Optional[PromptMetadata] = Field(
        default=None,
        description="Full metadata"
    )
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Creation timestamp"
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self.model_dump()


class PromptEntry(BaseModel):
    """
    A complete prompt entry with all versions.
    
    Represents a prompt with all its versions and metadata.
    Used for storage and retrieval.
    
    Attributes:
        label: Unique label for the prompt
        description: Description of the prompt
        category: Prompt category
        tags: Tags for categorization
        versions: List of all versions
        default_version: Default version to use
        default_model: Default model target
        created_at: Creation timestamp
        updated_at: Last update timestamp
    
    Example:
        entry = PromptEntry(
            label="code_review",
            description="Prompt for code review",
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
        model: Optional[str] = None
    ) -> Optional[PromptVersion]:
        """
        Get a specific version.
        
        Args:
            version: Version string (None = latest)
            model: Model target (None = default)
            
        Returns:
            PromptVersion or None
        """
        if not self.versions:
            return None
        
        # Filter by model if specified
        candidates = self.versions
        if model:
            model_candidates = [v for v in candidates if v.model_target == model]
            if model_candidates:
                candidates = model_candidates
        
        # Filter by version if specified
        if version:
            for v in candidates:
                if v.version == version:
                    return v
            return None
        
        # Return latest (last in list)
        return candidates[-1] if candidates else None
    
    def get_content(
        self,
        version: Optional[str] = None,
        model: Optional[str] = None
    ) -> Optional[str]:
        """Get prompt content for a specific version/model."""
        v = self.get_version(version, model)
        return v.content if v else None
    
    def add_version(self, version: PromptVersion) -> None:
        """Add a new version."""
        self.versions.append(version)
        self.updated_at = datetime.utcnow().isoformat()
    
    def get_latest_version(self) -> Optional[str]:
        """Get the latest version string."""
        if self.versions:
            return self.versions[-1].version
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PromptEntry':
        """Create from dictionary."""
        return cls(**data)

