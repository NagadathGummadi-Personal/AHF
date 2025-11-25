"""
Test suite for LLM Factory.

Tests the unified LLMFactory for creating LLM instances.
"""

import pytest
from core.llms import (
    LLMFactory,
    get_model_registry,
    reset_registry,
    LLMProvider,
    ModelFamily,
    OpenAILLM,
    AzureLLM,
    ModelNotFoundError,
)


# ============================================================================
# REGISTRY TESTS
# ============================================================================

@pytest.mark.unit
class TestModelRegistry:
    """Test model registry functionality."""
    
    def test_registry_initialization(self):
        """Test that registry initializes and loads models"""
        registry = get_model_registry()
        
        # Should have models registered
        all_models = registry.get_all_models()
        assert len(all_models) > 0
        
        # Should have Azure provider (OpenAI not yet migrated)
        providers = registry.list_all_providers()
        assert LLMProvider.AZURE in providers
        # TODO: Add OpenAI when migrated
        # assert LLMProvider.OPENAI in providers
    
    def test_get_model(self):
        """Test getting a model by name"""
        registry = get_model_registry()
        
        # Get Azure GPT-4.1 Mini model
        metadata = registry.get_model("azure-gpt-4.1-mini")
        assert metadata is not None
        assert metadata.model_name == "azure-gpt-4.1-mini"
        assert metadata.provider == LLMProvider.AZURE
        
        # TODO: Test OpenAI models when migrated
        # metadata = registry.get_model("gpt-4o")
        # assert metadata is not None
    
    def test_get_model_not_found(self):
        """Test getting non-existent model returns None"""
        registry = get_model_registry()
        
        metadata = registry.get_model("nonexistent-model")
        assert metadata is None
    
    def test_get_model_or_raise(self):
        """Test get_model_or_raise raises on not found"""
        registry = get_model_registry()
        
        with pytest.raises(ModelNotFoundError):
            registry.get_model_or_raise("nonexistent-model")
    
    def test_get_provider_models(self):
        """Test listing models by provider"""
        registry = get_model_registry()
        
        azure_models = registry.get_provider_models(LLMProvider.AZURE)
        assert len(azure_models) > 0
        assert "azure-gpt-4.1-mini" in azure_models
        
        # TODO: Test OpenAI when migrated
        # openai_models = registry.get_provider_models(LLMProvider.OPENAI)
        # assert len(openai_models) > 0
    
    @pytest.mark.skip(reason="OpenAI models not yet migrated")
    def test_get_family_models(self):
        """Test listing models by family"""
        registry = get_model_registry()
        
        gpt4_models = registry.get_family_models(ModelFamily.GPT_4)
        assert "gpt-4o" in gpt4_models or "gpt-4-turbo" in gpt4_models


# ============================================================================
# FACTORY TESTS
# ============================================================================

@pytest.mark.unit
class TestLLMFactory:
    """Test LLM factory functionality."""
    
    @pytest.mark.skip(reason="OpenAI not yet migrated to providers structure")
    def test_create_openai_llm(self):
        """Test creating OpenAI LLM instance"""
        config = {
            "api_key": "test-key-123",
            "timeout": 30
        }
        
        llm = LLMFactory.create_llm("gpt-4o", connector_config=config)
        
        assert isinstance(llm, OpenAILLM)
        assert llm.metadata.model_name == "gpt-4o"
        assert llm.metadata.provider == LLMProvider.OPENAI
    
    def test_create_azure_llm(self):
        """Test creating Azure LLM instance"""
        config = {
            "api_key": "test-key-456",
            "endpoint": "https://test.openai.azure.com",
            "deployment_name": "gpt-4.1-mini",
            "api_version": "2024-02-15-preview"
        }
        
        llm = LLMFactory.create_llm("azure-gpt-4.1-mini", connector_config=config)
        
        assert isinstance(llm, AzureLLM)
        assert llm.metadata.model_name == "azure-gpt-4.1-mini"
        assert llm.metadata.provider == LLMProvider.AZURE
    
    def test_create_llm_model_not_found(self):
        """Test creating LLM with nonexistent model"""
        with pytest.raises(ModelNotFoundError):
            LLMFactory.create_llm(
                "nonexistent-model",
                connector_config={"api_key": "test"}
            )
    
    def test_list_available_models(self):
        """Test listing all available models"""
        models = LLMFactory.list_available_models()
        
        assert len(models) > 0
        assert "azure-gpt-4.1-mini" in models
        # TODO: Add when OpenAI migrated
        # assert "gpt-4o" in models
    
    def test_list_provider_models(self):
        """Test listing models by provider"""
        azure_models = LLMFactory.list_provider_models(LLMProvider.AZURE)
        
        assert len(azure_models) > 0
        assert "azure-gpt-4.1-mini" in azure_models
        
        # TODO: Test OpenAI when migrated
        # openai_models = LLMFactory.list_provider_models(LLMProvider.OPENAI)
        # assert len(openai_models) > 0
        # assert "gpt-4o" in openai_models
    
    def test_get_model_metadata(self):
        """Test getting model metadata without creating LLM"""
        metadata = LLMFactory.get_model_metadata("azure-gpt-4.1-mini")
        
        assert metadata.model_name == "azure-gpt-4.1-mini"
        assert metadata.provider == LLMProvider.AZURE
        assert metadata.max_output_tokens > 0
        assert metadata.supports_streaming is True


# ============================================================================
# CAPABILITIES TESTS
# ============================================================================

@pytest.mark.unit
class TestLLMCapabilities:
    """Test LLM capability queries."""
    
    @pytest.mark.skip(reason="OpenAI not yet migrated to providers structure")
    def test_openai_capabilities(self):
        """Test OpenAI LLM capabilities"""
        config = {"api_key": "test-key"}
        llm = LLMFactory.create_llm("gpt-4o", connector_config=config)
        
        caps = llm.get_supported_capabilities()
        
        assert caps["provider"] == "openai"
        assert caps["supports_streaming"] is True
        assert caps["supports_function_calling"] is True
        assert caps["supports_vision"] is True
        assert caps["max_context_length"] == 128000
    
    def test_azure_capabilities(self):
        """Test Azure LLM capabilities"""
        config = {
            "api_key": "test-key",
            "endpoint": "https://test.openai.azure.com",
            "deployment_name": "gpt-4.1-mini",
            "api_version": "2024-02-15-preview"
        }
        llm = LLMFactory.create_llm("azure-gpt-4.1-mini", connector_config=config)
        
        caps = llm.get_supported_capabilities()
        
        assert caps["provider"] == "azure"
        assert caps["supports_streaming"] is True
        assert caps["supports_function_calling"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

