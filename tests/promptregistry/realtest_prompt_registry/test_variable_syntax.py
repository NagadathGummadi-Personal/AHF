"""
Real Tests for Variable Syntax {{var|default:value}}.

Tests the new double-brace variable syntax with defaults.
No mocks - uses real prompt registry.
"""

import pytest
from core.promptregistry import (
    LocalPromptRegistry,
    PromptMetadata,
    PromptEnvironment,
    PromptType,
    PromptTemplate,
)


class TestVariableSyntax:
    """Tests for {{var|default:value}} syntax."""
    
    def test_basic_variable_extraction(self):
        """Test extracting basic {{var}} variables."""
        template = PromptTemplate(
            content="Hello {{user_name}}, welcome to {{service_name}}!"
        )
        
        variables = template.get_all_variables()
        
        assert "user_name" in variables
        assert "service_name" in variables
        assert len(variables) == 2
    
    def test_variable_with_default(self):
        """Test extracting {{var|default:value}} with inline defaults."""
        template = PromptTemplate(
            content="Hello {{user_name|default:Guest}}! Your role is {{role|default:user}}."
        )
        
        # All variables should be extracted
        all_vars = template.get_all_variables()
        assert "user_name" in all_vars
        assert "role" in all_vars
        
        # Required variables should exclude those with defaults
        required = template.get_required_variables()
        assert len(required) == 0  # Both have defaults
        
        # Effective defaults should include inline defaults
        defaults = template.get_effective_defaults()
        assert defaults["user_name"] == "Guest"
        assert defaults["role"] == "user"
    
    def test_render_with_defaults(self):
        """Test rendering with inline defaults."""
        template = PromptTemplate(
            content="Hello {{user_name|default:Guest}}!"
        )
        
        # Render without providing value - should use default
        result = template.render()
        assert result == "Hello Guest!"
        
        # Render with value - should override default
        result = template.render({"user_name": "Alice"})
        assert result == "Hello Alice!"
    
    def test_render_mixed_variables(self):
        """Test rendering with mix of required and optional variables."""
        template = PromptTemplate(
            content="{{greeting|default:Hello}} {{user_name}}, you have {{count|default:0}} messages."
        )
        
        # Should require only user_name
        required = template.get_required_variables()
        assert required == {"user_name"}
        
        # Render with required variable
        result = template.render({"user_name": "Bob"})
        assert result == "Hello Bob, you have 0 messages."
        
        # Render with all variables
        result = template.render({
            "user_name": "Bob",
            "greeting": "Hi",
            "count": "5"
        })
        assert result == "Hi Bob, you have 5 messages."
    
    def test_explicit_default_overrides_inline(self):
        """Test that explicit default_values override inline defaults."""
        template = PromptTemplate(
            content="Hello {{user_name|default:Guest}}!",
            default_values={"user_name": "VIP Guest"}
        )
        
        # Explicit default should take precedence
        defaults = template.get_effective_defaults()
        assert defaults["user_name"] == "VIP Guest"
        
        result = template.render()
        assert result == "Hello VIP Guest!"
    
    def test_missing_required_variable_raises(self):
        """Test that missing required variables raise error in strict mode."""
        template = PromptTemplate(
            content="Hello {{user_name}}, your order {{order_id}} is ready."
        )
        
        # Should raise for missing variables
        with pytest.raises(ValueError) as exc:
            template.render({"user_name": "Alice"})
        
        assert "order_id" in str(exc.value)
    
    def test_non_strict_mode_preserves_unresolved(self):
        """Test that non-strict mode preserves unresolved variables."""
        template = PromptTemplate(
            content="Hello {{user_name}}, your order {{order_id}} is ready."
        )
        
        # Non-strict should leave unresolved as-is
        result = template.render({"user_name": "Alice"}, strict=False)
        
        assert "Hello Alice" in result
        assert "{{order_id}}" in result


class TestVariableSyntaxWithRegistry:
    """Tests for variable syntax with actual registry storage."""
    
    @pytest.mark.asyncio
    async def test_save_and_retrieve_with_variables(self, prompt_registry):
        """Test saving and retrieving prompts with new variable syntax."""
        content = "Hello {{user_name|default:Guest}}! Welcome to {{service|default:AHF}}."
        
        # Save prompt
        prompt_id = await prompt_registry.save_prompt(
            label="greeting_with_vars",
            content=content,
            metadata=PromptMetadata(
                model_target="gpt-4",
                environment=PromptEnvironment.PROD,
                prompt_type=PromptType.SYSTEM,
            )
        )
        
        assert prompt_id is not None
        
        # Retrieve without variables (should use defaults)
        result = await prompt_registry.get_prompt_with_fallback(
            "greeting_with_vars"
        )
        
        assert result is not None
        assert "Guest" in result.content
        assert "AHF" in result.content
    
    @pytest.mark.asyncio
    async def test_retrieve_with_variables_override(self, prompt_registry):
        """Test retrieving prompts with variable overrides."""
        content = "Hello {{user_name|default:Guest}}!"
        
        await prompt_registry.save_prompt(
            label="greeting_override",
            content=content,
            metadata=PromptMetadata(
                model_target="gpt-4",
                environment=PromptEnvironment.PROD,
            )
        )
        
        # Retrieve with override
        result = await prompt_registry.get_prompt_with_fallback(
            "greeting_override",
            variables={"user_name": "Alice"}
        )
        
        assert result is not None
        assert "Hello Alice!" in result.content
    
    @pytest.mark.asyncio
    async def test_get_dynamic_variables(self, prompt_registry):
        """Test getting dynamic variables from stored prompt."""
        content = "{{greeting|default:Hello}} {{name}}, your {{item_type|default:order}} is ready."
        
        await prompt_registry.save_prompt(
            label="order_notification",
            content=content,
            metadata=PromptMetadata(
                model_target="gpt-4",
                environment=PromptEnvironment.PROD,
            )
        )
        
        # Get required variables (should only be 'name')
        variables = await prompt_registry.get_dynamic_variables("order_notification")
        
        # This returns all variables - check both required and optional
        assert "name" in variables
        assert "greeting" in variables
        assert "item_type" in variables

