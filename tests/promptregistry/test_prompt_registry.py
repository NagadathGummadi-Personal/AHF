"""
Test suite for Prompt Registry.

Tests the prompt registry interfaces, models, and implementations.
"""

import pytest
import tempfile
import os
import shutil

from core.promptregistry import (
    LocalPromptRegistry,
    LocalFileStorage,
    PromptRegistryFactory,
    PromptMetadata,
    PromptEntry,
    PromptVersion,
    IPromptRegistry,
    IPromptStorage,
    PromptStatus,
    PromptCategory,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def temp_storage_path():
    """Create a temporary directory for storage."""
    path = tempfile.mkdtemp()
    yield path
    shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def local_storage(temp_storage_path):
    """Create LocalFileStorage instance."""
    return LocalFileStorage(storage_path=temp_storage_path)


@pytest.fixture
def local_registry(temp_storage_path):
    """Create LocalPromptRegistry instance."""
    return LocalPromptRegistry(storage_path=temp_storage_path)


# ============================================================================
# PROMPT METADATA TESTS
# ============================================================================

@pytest.mark.unit
class TestPromptMetadata:
    """Test PromptMetadata model."""
    
    def test_metadata_creation(self):
        """Test basic metadata creation."""
        metadata = PromptMetadata(
            version="1.0.0",
            model_target="gpt-4",
            tags=["code", "review"]
        )
        
        assert metadata.version == "1.0.0"
        assert metadata.model_target == "gpt-4"
        assert "code" in metadata.tags
    
    def test_metadata_defaults(self):
        """Test metadata defaults."""
        metadata = PromptMetadata()
        
        assert metadata.version == "1.0.0"
        assert metadata.model_target == "default"
        assert metadata.status == PromptStatus.ACTIVE
        assert metadata.category == PromptCategory.TEMPLATE
    
    def test_metadata_add_metric(self):
        """Test adding metrics."""
        metadata = PromptMetadata()
        
        metadata.add_metric("accuracy", 0.95)
        metadata.add_metric("latency_ms", 150.0)
        
        assert metadata.get_metric("accuracy") == 0.95
        assert metadata.get_metric("latency_ms") == 150.0
        assert metadata.get_metric("unknown") == 0.0


# ============================================================================
# PROMPT VERSION TESTS
# ============================================================================

@pytest.mark.unit
class TestPromptVersion:
    """Test PromptVersion model."""
    
    def test_version_creation(self):
        """Test basic version creation."""
        version = PromptVersion(
            version="1.0.0",
            content="You are a helpful assistant.",
            model_target="gpt-4"
        )
        
        assert version.version == "1.0.0"
        assert version.content == "You are a helpful assistant."
        assert version.model_target == "gpt-4"
    
    def test_version_to_dict(self):
        """Test version to_dict."""
        version = PromptVersion(
            version="1.0.0",
            content="Test prompt"
        )
        
        data = version.to_dict()
        assert data["version"] == "1.0.0"
        assert data["content"] == "Test prompt"


# ============================================================================
# PROMPT ENTRY TESTS
# ============================================================================

@pytest.mark.unit
class TestPromptEntry:
    """Test PromptEntry model."""
    
    def test_entry_creation(self):
        """Test basic entry creation."""
        entry = PromptEntry(
            label="greeting",
            description="Greeting prompts"
        )
        
        assert entry.label == "greeting"
        assert entry.description == "Greeting prompts"
        assert entry.versions == []
    
    def test_entry_add_version(self):
        """Test adding versions."""
        entry = PromptEntry(label="test")
        
        version1 = PromptVersion(version="1.0.0", content="Version 1")
        version2 = PromptVersion(version="1.0.1", content="Version 2")
        
        entry.add_version(version1)
        entry.add_version(version2)
        
        assert len(entry.versions) == 2
        assert entry.get_latest_version() == "1.0.1"
    
    def test_entry_get_version(self):
        """Test getting specific version."""
        entry = PromptEntry(label="test")
        entry.add_version(PromptVersion(version="1.0.0", content="V1"))
        entry.add_version(PromptVersion(version="1.0.1", content="V2", model_target="gpt-4"))
        
        # Get by version
        v1 = entry.get_version(version="1.0.0")
        assert v1.content == "V1"
        
        # Get by model
        gpt4 = entry.get_version(model="gpt-4")
        assert gpt4.content == "V2"
        
        # Get latest
        latest = entry.get_version()
        assert latest.version == "1.0.1"
    
    def test_entry_get_content(self):
        """Test getting content."""
        entry = PromptEntry(label="test")
        entry.add_version(PromptVersion(version="1.0.0", content="Test content"))
        
        content = entry.get_content()
        assert content == "Test content"


# ============================================================================
# LOCAL FILE STORAGE TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestLocalFileStorage:
    """Test LocalFileStorage implementation."""
    
    async def test_storage_implements_interface(self, local_storage):
        """Test LocalFileStorage implements IPromptStorage."""
        assert isinstance(local_storage, IPromptStorage)
    
    async def test_storage_save_load(self, local_storage):
        """Test save and load operations."""
        data = {"content": "Test prompt", "version": "1.0.0"}
        
        await local_storage.save("test_prompt", data)
        loaded = await local_storage.load("test_prompt")
        
        assert loaded == data
    
    async def test_storage_exists(self, local_storage):
        """Test exists operation."""
        assert not await local_storage.exists("nonexistent")
        
        await local_storage.save("test", {"data": "value"})
        assert await local_storage.exists("test")
    
    async def test_storage_delete(self, local_storage):
        """Test delete operation."""
        await local_storage.save("test", {"data": "value"})
        assert await local_storage.exists("test")
        
        await local_storage.delete("test")
        assert not await local_storage.exists("test")
    
    async def test_storage_list_keys(self, local_storage):
        """Test list_keys operation."""
        await local_storage.save("prompt1", {})
        await local_storage.save("prompt2", {})
        await local_storage.save("other", {})
        
        all_keys = await local_storage.list_keys()
        assert len(all_keys) == 3
        
        prompt_keys = await local_storage.list_keys(prefix="prompt")
        assert len(prompt_keys) == 2


# ============================================================================
# LOCAL PROMPT REGISTRY TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestLocalPromptRegistry:
    """Test LocalPromptRegistry implementation."""
    
    async def test_registry_implements_interface(self, local_registry):
        """Test LocalPromptRegistry implements IPromptRegistry."""
        assert isinstance(local_registry, IPromptRegistry)
    
    async def test_registry_save_prompt(self, local_registry):
        """Test saving a prompt."""
        prompt_id = await local_registry.save_prompt(
            label="greeting",
            content="Hello, I am {name}!",
            metadata=PromptMetadata(tags=["greeting"])
        )
        
        assert prompt_id is not None
    
    async def test_registry_get_prompt(self, local_registry):
        """Test getting a prompt."""
        await local_registry.save_prompt(
            label="greeting",
            content="Hello, world!"
        )
        
        content = await local_registry.get_prompt("greeting")
        assert content == "Hello, world!"
    
    async def test_registry_get_prompt_not_found(self, local_registry):
        """Test getting nonexistent prompt."""
        with pytest.raises(ValueError):
            await local_registry.get_prompt("nonexistent")
    
    async def test_registry_versioning(self, local_registry):
        """Test prompt versioning."""
        # Save initial version
        await local_registry.save_prompt(
            label="greeting",
            content="Version 1"
        )
        
        # Save new version
        await local_registry.save_prompt(
            label="greeting",
            content="Version 2"
        )
        
        # Get latest (should be version 2)
        content = await local_registry.get_prompt("greeting")
        assert content == "Version 2"
        
        # List versions
        versions = await local_registry.list_versions("greeting")
        assert len(versions) == 2
    
    async def test_registry_model_specific(self, local_registry):
        """Test model-specific prompts."""
        # Default prompt
        await local_registry.save_prompt(
            label="code_review",
            content="Default review prompt"
        )
        
        # GPT-4 specific
        await local_registry.save_prompt(
            label="code_review",
            content="GPT-4 optimized review prompt",
            metadata=PromptMetadata(model_target="gpt-4")
        )
        
        # Get for GPT-4
        gpt4_content = await local_registry.get_prompt("code_review", model="gpt-4")
        assert "GPT-4 optimized" in gpt4_content
    
    async def test_registry_list_prompts(self, local_registry):
        """Test listing prompts."""
        await local_registry.save_prompt(
            label="prompt1",
            content="Content 1",
            metadata=PromptMetadata(tags=["tag1"])
        )
        await local_registry.save_prompt(
            label="prompt2",
            content="Content 2",
            metadata=PromptMetadata(tags=["tag1", "tag2"])
        )
        
        all_prompts = await local_registry.list_prompts()
        assert len(all_prompts) == 2
        
        # Filter by tags
        tagged = await local_registry.list_prompts(tags=["tag1"])
        assert len(tagged) == 2
        
        tagged2 = await local_registry.list_prompts(tags=["tag2"])
        assert len(tagged2) == 1
    
    async def test_registry_update_metrics(self, local_registry):
        """Test updating metrics."""
        prompt_id = await local_registry.save_prompt(
            label="test",
            content="Test content"
        )
        
        await local_registry.update_metrics(prompt_id, {
            "accuracy": 0.95,
            "latency_ms": 150.0
        })
        
        # Get entry and check metrics
        entry = await local_registry.get_prompt_entry("test")
        version = entry.versions[-1]
        assert version.metadata.get_metric("accuracy") == 0.95
    
    async def test_registry_delete_prompt(self, local_registry):
        """Test deleting prompts."""
        await local_registry.save_prompt(
            label="to_delete",
            content="Will be deleted"
        )
        
        # Verify it exists
        content = await local_registry.get_prompt("to_delete")
        assert content == "Will be deleted"
        
        # Delete
        await local_registry.delete_prompt("to_delete")
        
        # Should not exist
        with pytest.raises(ValueError):
            await local_registry.get_prompt("to_delete")
    
    async def test_registry_get_fine_tuning_context(self, local_registry):
        """Test getting fine-tuning context."""
        # Save prompts with metrics
        prompt_id = await local_registry.save_prompt(
            label="test",
            content="Version 1"
        )
        await local_registry.update_metrics(prompt_id, {"accuracy": 0.80})
        
        prompt_id2 = await local_registry.save_prompt(
            label="test",
            content="Version 2"
        )
        await local_registry.update_metrics(prompt_id2, {"accuracy": 0.95})
        
        # Get all with metrics
        all_versions = await local_registry.get_fine_tuning_context("test")
        assert len(all_versions) == 2
        
        # Filter by min accuracy
        high_accuracy = await local_registry.get_fine_tuning_context(
            "test",
            min_accuracy=0.90
        )
        assert len(high_accuracy) == 1


# ============================================================================
# FACTORY TESTS
# ============================================================================

@pytest.mark.unit
class TestPromptRegistryFactory:
    """Test PromptRegistryFactory."""
    
    def test_get_local_registry(self, temp_storage_path):
        """Test getting local registry."""
        registry = PromptRegistryFactory.get_registry(
            'local',
            storage_path=temp_storage_path
        )
        
        assert isinstance(registry, LocalPromptRegistry)
    
    def test_get_default_registry(self, temp_storage_path):
        """Test getting default registry."""
        registry = PromptRegistryFactory.get_registry(
            'default',
            storage_path=temp_storage_path
        )
        
        assert isinstance(registry, IPromptRegistry)
    
    def test_list_available(self):
        """Test listing available registries."""
        available = PromptRegistryFactory.list_available()
        
        assert 'local' in available
        assert 'default' in available
    
    def test_unknown_registry_raises(self):
        """Test unknown registry raises error."""
        with pytest.raises(ValueError):
            PromptRegistryFactory.get_registry('unknown')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

