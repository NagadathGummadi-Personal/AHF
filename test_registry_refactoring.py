"""
Test script for the refactored model registry system.

This verifies that:
1. The registry properly initializes with provider-based registration
2. Azure models are registered correctly
3. All registry methods work as expected
"""

from core.llms.runtimes.model_registry import get_model_registry, reset_registry
from core.llms.enum import LLMProvider, ModelFamily


def get_enum_value(enum_or_str):
    """Safely get value from enum or string."""
    return enum_or_str.value if hasattr(enum_or_str, 'value') else str(enum_or_str)


def test_registry_initialization():
    """Test that the registry initializes with Azure models."""
    print("=" * 60)
    print("Testing Registry Initialization")
    print("=" * 60)
    
    # Reset registry to test initialization
    reset_registry()
    registry = get_model_registry()
    
    # Get all models
    all_models = registry.get_all_models()
    print(f"\n[OK] Total registered models: {len(all_models)}")
    
    for model_name, metadata in all_models.items():
        print(f"  - {model_name}: {metadata.display_name} ({get_enum_value(metadata.provider)})")
    
    return len(all_models) > 0


def test_azure_gpt41_mini():
    """Test that Azure GPT-4.1 Mini is registered correctly."""
    print("\n" + "=" * 60)
    print("Testing Azure GPT-4.1 Mini Registration")
    print("=" * 60)
    
    registry = get_model_registry()
    
    # Get the model
    model = registry.get_model("azure-gpt-4.1-mini")
    
    if model:
        print(f"\n[OK] Model found: {model.model_name}")
        print(f"  Display Name: {model.display_name}")
        print(f"  Provider: {get_enum_value(model.provider)}")
        print(f"  Family: {get_enum_value(model.model_family)}")
        print(f"  Max Context: {model.max_context_length:,} tokens")
        print(f"  Max Output: {model.max_output_tokens:,} tokens")
        print(f"  Supports Streaming: {model.supports_streaming}")
        print(f"  Supports Vision: {model.supports_vision}")
        print(f"  Supports Function Calling: {model.supports_function_calling}")
        print(f"  Cost per 1K input tokens: ${model.cost_per_1k_input_tokens}")
        print(f"  Cost per 1K output tokens: ${model.cost_per_1k_output_tokens}")
        return True
    else:
        print("[ERROR] Model not found!")
        return False


def test_provider_filtering():
    """Test filtering models by provider."""
    print("\n" + "=" * 60)
    print("Testing Provider Filtering")
    print("=" * 60)
    
    registry = get_model_registry()
    
    # Get all Azure models
    azure_models = registry.get_provider_models(LLMProvider.AZURE)
    print(f"\n[OK] Azure models found: {len(azure_models)}")
    for model_name in azure_models:
        print(f"  - {model_name}")
    
    return len(azure_models) > 0


def test_family_filtering():
    """Test filtering models by family."""
    print("\n" + "=" * 60)
    print("Testing Family Filtering")
    print("=" * 60)
    
    registry = get_model_registry()
    
    # Get all GPT-4.1 Mini family models
    family_models = registry.get_family_models(ModelFamily.AZURE_GPT_4_1_MINI)
    print(f"\n[OK] GPT-4.1 Mini family models found: {len(family_models)}")
    for model_name in family_models:
        print(f"  - {model_name}")
    
    return len(family_models) > 0


def test_providers_and_families_listing():
    """Test listing all providers and families."""
    print("\n" + "=" * 60)
    print("Testing Provider and Family Listing")
    print("=" * 60)
    
    registry = get_model_registry()
    
    # List all providers
    providers = registry.list_all_providers()
    print(f"\n[OK] Registered providers: {len(providers)}")
    for provider in providers:
        print(f"  - {get_enum_value(provider)}")
    
    # List all families
    families = registry.list_all_families()
    print(f"\n[OK] Registered families: {len(families)}")
    for family in families:
        print(f"  - {get_enum_value(family)}")
    
    return len(providers) > 0 and len(families) > 0


def test_model_not_found():
    """Test that querying non-existent model raises appropriate error."""
    print("\n" + "=" * 60)
    print("Testing Model Not Found Error")
    print("=" * 60)
    
    registry = get_model_registry()
    
    try:
        registry.get_model_or_raise("non-existent-model")
        print("[ERROR] Should have raised ModelNotFoundError!")
        return False
    except Exception as e:
        print(f"\n[OK] Correctly raised error: {e.__class__.__name__}")
        print(f"  Message: {str(e)}")
        return True


def main():
    """Run all tests."""
    print("\n")
    print("=" * 60)
    print(" " * 12 + "MODEL REGISTRY REFACTORING TEST")
    print("=" * 60)
    
    tests = [
        ("Registry Initialization", test_registry_initialization),
        ("Azure GPT-4.1 Mini", test_azure_gpt41_mini),
        ("Provider Filtering", test_provider_filtering),
        ("Family Filtering", test_family_filtering),
        ("Providers/Families Listing", test_providers_and_families_listing),
        ("Model Not Found Error", test_model_not_found),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result, None))
        except Exception as e:
            results.append((test_name, False, e))
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result, _ in results if result)
    total = len(results)
    
    for test_name, result, error in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status}: {test_name}")
        if error:
            print(f"  Error: {error}")
    
    print("\n" + "=" * 60)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 60)
    
    if passed == total:
        print("\nAll tests passed! The registry refactoring is working correctly.")
    else:
        print(f"\n{total - passed} test(s) failed. Please review the output above.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

