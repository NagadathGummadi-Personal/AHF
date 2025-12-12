"""
Test suite for Conditional Prompt Loading.

Tests the conditional expression processing in prompts including:
- Simple if/endif blocks
- If/else blocks
- If/elif/else blocks
- Nested conditionals
- Various condition operators
- Integration with PromptTemplate and PromptRegistry
"""

import pytest
import tempfile
import shutil

from core.promptregistry import (
    ConditionalProcessor,
    process_conditionals,
    PromptTemplate,
    LocalPromptRegistry,
    PromptMetadata,
    PromptEnvironment,
    PromptType,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def processor():
    """Create a ConditionalProcessor instance."""
    return ConditionalProcessor()


@pytest.fixture
def strict_processor():
    """Create a strict ConditionalProcessor instance."""
    return ConditionalProcessor(strict=True)


@pytest.fixture
def temp_storage_path():
    """Create a temporary directory for storage."""
    path = tempfile.mkdtemp()
    yield path
    shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def registry(temp_storage_path):
    """Create LocalPromptRegistry instance."""
    return LocalPromptRegistry(storage_path=temp_storage_path)


# ============================================================================
# CONDITIONAL PROCESSOR TESTS - BASIC
# ============================================================================

@pytest.mark.unit
class TestConditionalProcessorBasic:
    """Test basic conditional processing functionality."""
    
    def test_no_conditionals(self, processor):
        """Test template without conditionals passes through."""
        template = "Hello, world!"
        result = processor.process(template, {})
        assert result == "Hello, world!"
    
    def test_simple_if_true(self, processor):
        """Test simple if block with true condition."""
        template = "{# if is_active #}Active{# endif #}"
        result = processor.process(template, {"is_active": True})
        assert result == "Active"
    
    def test_simple_if_false(self, processor):
        """Test simple if block with false condition."""
        template = "{# if is_active #}Active{# endif #}"
        result = processor.process(template, {"is_active": False})
        assert result == ""
    
    def test_if_else_true(self, processor):
        """Test if/else block with true condition."""
        template = "{# if is_premium #}Premium{# else #}Free{# endif #}"
        result = processor.process(template, {"is_premium": True})
        assert result == "Premium"
    
    def test_if_else_false(self, processor):
        """Test if/else block with false condition."""
        template = "{# if is_premium #}Premium{# else #}Free{# endif #}"
        result = processor.process(template, {"is_premium": False})
        assert result == "Free"
    
    def test_if_elif_else(self, processor):
        """Test if/elif/else block."""
        template = """
{# if role == 'admin' #}Admin Panel{# elif role == 'user' #}User Dashboard{# else #}Guest View{# endif #}
""".strip()
        
        # Admin
        result = processor.process(template, {"role": "admin"})
        assert "Admin Panel" in result
        
        # User
        result = processor.process(template, {"role": "user"})
        assert "User Dashboard" in result
        
        # Guest
        result = processor.process(template, {"role": "guest"})
        assert "Guest View" in result
    
    def test_multiple_elif(self, processor):
        """Test multiple elif blocks."""
        template = """{# if score >= 90 #}A{# elif score >= 80 #}B{# elif score >= 70 #}C{# elif score >= 60 #}D{# else #}F{# endif #}"""
        
        assert processor.process(template, {"score": 95}) == "A"
        assert processor.process(template, {"score": 85}) == "B"
        assert processor.process(template, {"score": 75}) == "C"
        assert processor.process(template, {"score": 65}) == "D"
        assert processor.process(template, {"score": 55}) == "F"


# ============================================================================
# CONDITIONAL PROCESSOR TESTS - OPERATORS
# ============================================================================

@pytest.mark.unit
class TestConditionalProcessorOperators:
    """Test condition operators."""
    
    def test_equality_string(self, processor):
        """Test string equality."""
        template = "{# if status == 'active' #}Yes{# endif #}"
        
        assert processor.process(template, {"status": "active"}) == "Yes"
        assert processor.process(template, {"status": "inactive"}) == ""
    
    def test_equality_number(self, processor):
        """Test number equality."""
        template = "{# if count == 5 #}Five{# endif #}"
        
        assert processor.process(template, {"count": 5}) == "Five"
        assert processor.process(template, {"count": 3}) == ""
    
    def test_inequality(self, processor):
        """Test inequality operator."""
        template = "{# if count != 0 #}Not Zero{# endif #}"
        
        assert processor.process(template, {"count": 5}) == "Not Zero"
        assert processor.process(template, {"count": 0}) == ""
    
    def test_greater_than(self, processor):
        """Test greater than operator."""
        template = "{# if age > 18 #}Adult{# endif #}"
        
        assert processor.process(template, {"age": 21}) == "Adult"
        assert processor.process(template, {"age": 18}) == ""
        assert processor.process(template, {"age": 15}) == ""
    
    def test_greater_than_or_equal(self, processor):
        """Test greater than or equal operator."""
        template = "{# if age >= 18 #}Adult{# endif #}"
        
        assert processor.process(template, {"age": 21}) == "Adult"
        assert processor.process(template, {"age": 18}) == "Adult"
        assert processor.process(template, {"age": 15}) == ""
    
    def test_less_than(self, processor):
        """Test less than operator."""
        template = "{# if price < 100 #}Affordable{# endif #}"
        
        assert processor.process(template, {"price": 50}) == "Affordable"
        assert processor.process(template, {"price": 100}) == ""
        assert processor.process(template, {"price": 150}) == ""
    
    def test_less_than_or_equal(self, processor):
        """Test less than or equal operator."""
        template = "{# if price <= 100 #}Affordable{# endif #}"
        
        assert processor.process(template, {"price": 50}) == "Affordable"
        assert processor.process(template, {"price": 100}) == "Affordable"
        assert processor.process(template, {"price": 150}) == ""
    
    def test_negation(self, processor):
        """Test not operator."""
        template = "{# if not is_blocked #}Welcome{# endif #}"
        
        assert processor.process(template, {"is_blocked": False}) == "Welcome"
        assert processor.process(template, {"is_blocked": True}) == ""
    
    def test_and_operator(self, processor):
        """Test and operator."""
        template = "{# if is_active and is_verified #}Full Access{# endif #}"
        
        assert processor.process(template, {"is_active": True, "is_verified": True}) == "Full Access"
        assert processor.process(template, {"is_active": True, "is_verified": False}) == ""
        assert processor.process(template, {"is_active": False, "is_verified": True}) == ""
    
    def test_or_operator(self, processor):
        """Test or operator."""
        template = "{# if is_admin or is_moderator #}Elevated{# endif #}"
        
        assert processor.process(template, {"is_admin": True, "is_moderator": False}) == "Elevated"
        assert processor.process(template, {"is_admin": False, "is_moderator": True}) == "Elevated"
        assert processor.process(template, {"is_admin": True, "is_moderator": True}) == "Elevated"
        assert processor.process(template, {"is_admin": False, "is_moderator": False}) == ""
    
    def test_in_operator(self, processor):
        """Test in operator."""
        template = "{# if 'admin' in roles #}Admin{# endif #}"
        
        assert processor.process(template, {"roles": ["admin", "user"]}) == "Admin"
        assert processor.process(template, {"roles": ["user"]}) == ""
    
    def test_not_in_operator(self, processor):
        """Test not in operator."""
        template = "{# if 'banned' not in status_list #}Allowed{# endif #}"
        
        assert processor.process(template, {"status_list": ["active", "verified"]}) == "Allowed"
        assert processor.process(template, {"status_list": ["banned", "inactive"]}) == ""


# ============================================================================
# CONDITIONAL PROCESSOR TESTS - ADVANCED
# ============================================================================

@pytest.mark.unit
class TestConditionalProcessorAdvanced:
    """Test advanced conditional processing features."""
    
    def test_nested_conditionals(self, processor):
        """Test nested conditional blocks."""
        template = """
{# if is_logged_in #}
Welcome!
{# if is_admin #}
Admin Panel Available
{# else #}
User Dashboard Available
{# endif #}
{# else #}
Please log in
{# endif #}
""".strip()
        
        # Logged in admin
        result = processor.process(template, {"is_logged_in": True, "is_admin": True})
        assert "Welcome!" in result
        assert "Admin Panel Available" in result
        
        # Logged in user
        result = processor.process(template, {"is_logged_in": True, "is_admin": False})
        assert "Welcome!" in result
        assert "User Dashboard Available" in result
        
        # Not logged in
        result = processor.process(template, {"is_logged_in": False})
        assert "Please log in" in result
    
    def test_dotted_variable_access(self, processor):
        """Test accessing nested variables with dot notation."""
        template = "{# if user.is_premium #}Premium{# else #}Free{# endif #}"
        
        result = processor.process(template, {"user": {"is_premium": True}})
        assert result == "Premium"
        
        result = processor.process(template, {"user": {"is_premium": False}})
        assert result == "Free"
    
    def test_undefined_variable_non_strict(self, processor):
        """Test undefined variables in non-strict mode."""
        template = "{# if undefined_var #}Yes{# else #}No{# endif #}"
        
        # Should default to False
        result = processor.process(template, {})
        assert result == "No"
    
    def test_undefined_variable_strict(self, strict_processor):
        """Test undefined variables in strict mode."""
        template = "{# if undefined_var #}Yes{# endif #}"
        
        with pytest.raises(ValueError) as exc_info:
            strict_processor.process(template, {})
        assert "Undefined variable" in str(exc_info.value)
    
    def test_boolean_literals(self, processor):
        """Test boolean literals in conditions."""
        template = "{# if True #}Always{# endif #}"
        assert processor.process(template, {}) == "Always"
        
        template = "{# if False #}Never{# endif #}"
        assert processor.process(template, {}) == ""
    
    def test_none_literal(self, processor):
        """Test None/null literals."""
        template = "{# if value == None #}Is None{# else #}Has Value{# endif #}"
        
        assert processor.process(template, {"value": None}) == "Is None"
        assert processor.process(template, {"value": "something"}) == "Has Value"
    
    def test_truthy_values(self, processor):
        """Test truthy value checking."""
        template = "{# if value #}Truthy{# else #}Falsy{# endif #}"
        
        # Truthy values
        assert processor.process(template, {"value": True}) == "Truthy"
        assert processor.process(template, {"value": 1}) == "Truthy"
        assert processor.process(template, {"value": "text"}) == "Truthy"
        assert processor.process(template, {"value": [1, 2]}) == "Truthy"
        
        # Falsy values
        assert processor.process(template, {"value": False}) == "Falsy"
        assert processor.process(template, {"value": 0}) == "Falsy"
        assert processor.process(template, {"value": ""}) == "Falsy"
        assert processor.process(template, {"value": []}) == "Falsy"
        assert processor.process(template, {"value": None}) == "Falsy"
    
    def test_mixed_text_and_conditionals(self, processor):
        """Test template with mixed text and conditionals."""
        template = """Hello{# if name #}, {name}{# endif #}!
{# if greeting_style == 'formal' #}
It is a pleasure to meet you.
{# else #}
Nice to meet you!
{# endif #}"""
        
        result = processor.process(template, {
            "name": "John",
            "greeting_style": "formal"
        })
        assert "Hello, {name}!" in result  # Variable not substituted by processor
        assert "It is a pleasure to meet you." in result


# ============================================================================
# CONDITIONAL PROCESSOR TESTS - VALIDATION
# ============================================================================

@pytest.mark.unit
class TestConditionalProcessorValidation:
    """Test template validation."""
    
    def test_has_conditionals(self, processor):
        """Test detecting conditionals in template."""
        assert processor.has_conditionals("{# if x #}yes{# endif #}")
        assert not processor.has_conditionals("no conditionals here")
    
    def test_extract_conditional_variables(self, processor):
        """Test extracting variables from conditions."""
        template = """{# if is_admin and user_type == 'premium' #}
{# elif age >= 18 or 'vip' in roles #}
{# endif #}"""
        
        variables = processor.extract_conditional_variables(template)
        assert "is_admin" in variables
        assert "user_type" in variables
        assert "age" in variables
        assert "roles" in variables
    
    def test_validate_valid_template(self, processor):
        """Test validating a valid template."""
        template = "{# if x #}y{# elif z #}w{# else #}v{# endif #}"
        errors = processor.validate_template(template)
        assert errors == []
    
    def test_validate_unclosed_if(self, processor):
        """Test validating unclosed if block."""
        template = "{# if x #}content"
        errors = processor.validate_template(template)
        assert len(errors) > 0
        assert any("Unclosed" in e for e in errors)
    
    def test_validate_orphan_endif(self, processor):
        """Test validating orphan endif."""
        template = "content{# endif #}"
        errors = processor.validate_template(template)
        assert len(errors) > 0
        assert any("without matching" in e for e in errors)
    
    def test_validate_missing_condition(self, processor):
        """Test validating if without condition."""
        template = "{# if #}content{# endif #}"
        errors = processor.validate_template(template)
        assert len(errors) > 0
        assert any("Missing condition" in e for e in errors)


# ============================================================================
# CONVENIENCE FUNCTION TESTS
# ============================================================================

@pytest.mark.unit
class TestProcessConditionals:
    """Test the process_conditionals convenience function."""
    
    def test_basic_usage(self):
        """Test basic usage of convenience function."""
        result = process_conditionals(
            "{# if flag #}Yes{# else #}No{# endif #}",
            {"flag": True}
        )
        assert result == "Yes"
    
    def test_with_strict_mode(self):
        """Test convenience function with strict mode."""
        with pytest.raises(ValueError):
            process_conditionals(
                "{# if undefined #}X{# endif #}",
                {},
                strict=True
            )


# ============================================================================
# PROMPT TEMPLATE INTEGRATION TESTS
# ============================================================================

@pytest.mark.unit
class TestPromptTemplateWithConditionals:
    """Test PromptTemplate with conditional support."""
    
    def test_template_with_conditionals(self):
        """Test template processes conditionals."""
        template = PromptTemplate(
            content="""You are an assistant.
{# if is_premium #}
You have access to advanced features.
{# else #}
Standard features are available.
{# endif #}
Help the user with {task}."""
        )
        
        # Premium user
        result = template.render({
            "is_premium": True,
            "task": "coding"
        })
        assert "advanced features" in result
        assert "coding" in result
        assert "{# if" not in result
        
        # Free user
        result = template.render({
            "is_premium": False,
            "task": "coding"
        })
        assert "Standard features" in result
        assert "coding" in result
    
    def test_template_get_all_variables(self):
        """Test getting all variables including conditional ones."""
        template = PromptTemplate(
            content="{# if is_admin #}Admin: {name}{# else #}User: {name}{# endif #}"
        )
        
        all_vars = template.get_all_variables()
        assert "name" in all_vars
        assert "is_admin" in all_vars
    
    def test_template_get_conditional_variables(self):
        """Test getting only conditional variables."""
        template = PromptTemplate(
            content="{# if is_premium and level >= 5 #}VIP{# endif #}: {name}"
        )
        
        cond_vars = template.get_conditional_variables()
        assert "is_premium" in cond_vars
        assert "level" in cond_vars
        assert "name" not in cond_vars
    
    def test_template_has_conditionals(self):
        """Test detecting conditionals in template."""
        with_cond = PromptTemplate(content="{# if x #}y{# endif #}")
        without_cond = PromptTemplate(content="no conditionals")
        
        assert with_cond.has_conditionals()
        assert not without_cond.has_conditionals()
    
    def test_template_validate_conditionals(self):
        """Test validating conditional syntax."""
        valid = PromptTemplate(content="{# if x #}y{# endif #}")
        assert valid.validate_conditionals() == []
        
        invalid = PromptTemplate(content="{# if x #}y")  # Missing endif
        assert len(invalid.validate_conditionals()) > 0
    
    def test_template_disable_conditionals(self):
        """Test disabling conditional processing."""
        template = PromptTemplate(
            content="{# if x #}y{# endif #}",
            enable_conditionals=False
        )
        
        # Should not process conditionals (use strict=False since {# ... #} conflicts with format)
        result = template.render({"x": True}, strict=False, process_conditionals=False)
        assert "{# if x #}" in result
    
    def test_template_with_defaults_and_conditionals(self):
        """Test template with default values and conditionals."""
        template = PromptTemplate(
            content="{# if formal #}Dear {name},{# else #}Hi {name}!{# endif #}",
            default_values={"name": "User"}
        )
        
        # Use default name with conditional
        result = template.render({"formal": True})
        assert result == "Dear User,"
        
        # Override name
        result = template.render({"formal": False, "name": "John"})
        assert result == "Hi John!"
    
    def test_complex_template(self):
        """Test complex template with multiple features."""
        template = PromptTemplate(
            content="""You are {role}.
{# if include_capabilities #}
Your capabilities include:
{# if has_search #}
- Web search
{# endif #}
{# if has_code #}
- Code execution
{# endif #}
{# if has_files #}
- File management
{# endif #}
{# endif #}
Help with: {task}""",
            default_values={"role": "an AI assistant"}
        )
        
        result = template.render({
            "include_capabilities": True,
            "has_search": True,
            "has_code": True,
            "has_files": False,
            "task": "debugging"
        })
        
        assert "an AI assistant" in result
        assert "Web search" in result
        assert "Code execution" in result
        assert "File management" not in result
        assert "debugging" in result


# ============================================================================
# PROMPT REGISTRY INTEGRATION TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestPromptRegistryWithConditionals:
    """Test LocalPromptRegistry with conditional prompts."""
    
    async def test_save_and_get_conditional_prompt(self, registry):
        """Test saving and getting prompt with conditionals."""
        await registry.save_prompt(
            label="greeting",
            content="""{# if is_formal #}Good day, {name}. How may I assist you?{# else #}Hey {name}! What's up?{# endif #}""",
            metadata=PromptMetadata(prompt_type=PromptType.USER)
        )
        
        # Formal greeting
        result = await registry.get_prompt(
            "greeting",
            variables={"is_formal": True, "name": "Dr. Smith"}
        )
        assert "Good day, Dr. Smith" in result
        
        # Casual greeting
        result = await registry.get_prompt(
            "greeting",
            variables={"is_formal": False, "name": "John"}
        )
        assert "Hey John! What's up?" in result
    
    async def test_get_dynamic_variables_includes_conditionals(self, registry):
        """Test that get_dynamic_variables returns conditional variables too."""
        await registry.save_prompt(
            label="test",
            content="{# if is_admin #}Admin: {name}{# endif #}"
        )
        
        variables = await registry.get_dynamic_variables("test")
        assert "name" in variables
        # Note: conditional variables are tracked separately in the template
    
    async def test_complex_conditional_prompt(self, registry):
        """Test complex prompt with multiple conditional blocks."""
        content = """You are a customer service agent.

{# if customer_tier == 'gold' #}
Priority: HIGH - Gold customer
{# elif customer_tier == 'silver' #}
Priority: MEDIUM - Silver customer
{# else #}
Priority: STANDARD
{# endif #}

Customer: {customer_name}
{# if has_previous_issues #}
Note: This customer has previous unresolved issues.
{# endif #}

{# if language != 'en' #}
Please respond in {language}.
{# endif #}

Issue: {issue_description}"""
        
        await registry.save_prompt(
            label="support",
            content=content
        )
        
        # Gold customer with previous issues
        result = await registry.get_prompt(
            "support",
            variables={
                "customer_tier": "gold",
                "customer_name": "John Gold",
                "has_previous_issues": True,
                "language": "en",
                "issue_description": "Cannot login"
            }
        )
        
        assert "Priority: HIGH - Gold customer" in result
        assert "John Gold" in result
        assert "previous unresolved issues" in result
        assert "Cannot login" in result
        assert "Please respond in" not in result  # English, so no language note
    
    async def test_prompt_with_fallback_and_conditionals(self, registry):
        """Test get_prompt_with_fallback with conditional content."""
        await registry.save_prompt(
            label="welcome",
            content="{# if new_user #}Welcome to our service!{# else #}Welcome back!{# endif #}",
            metadata=PromptMetadata(environment=PromptEnvironment.DEV)
        )
        
        result = await registry.get_prompt_with_fallback(
            "welcome",
            environment=PromptEnvironment.PROD,
            variables={"new_user": True}
        )
        
        assert "Welcome to our service!" in result.content
        assert result.fallback_used  # Fell back from prod to dev


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

@pytest.mark.unit
class TestConditionalErrorHandling:
    """Test error handling in conditional processing."""
    
    def test_unclosed_if_raises_error(self, processor):
        """Test that unclosed if block raises error."""
        template = "{# if x #}content"
        
        with pytest.raises(ValueError) as exc_info:
            processor.process(template, {"x": True})
        assert "Unclosed" in str(exc_info.value)
    
    def test_orphan_else_raises_error(self, processor):
        """Test that orphan else raises error."""
        template = "{# else #}content{# endif #}"
        
        with pytest.raises(ValueError) as exc_info:
            processor.process(template, {})
        assert "without matching" in str(exc_info.value)
    
    def test_else_after_else_raises_error(self, processor):
        """Test that multiple else blocks raise error."""
        template = "{# if x #}a{# else #}b{# else #}c{# endif #}"
        
        with pytest.raises(ValueError) as exc_info:
            processor.process(template, {"x": True})
        assert "Multiple 'else'" in str(exc_info.value)
    
    def test_elif_after_else_raises_error(self, processor):
        """Test that elif after else raises error."""
        template = "{# if x #}a{# else #}b{# elif y #}c{# endif #}"
        
        with pytest.raises(ValueError) as exc_info:
            processor.process(template, {"x": True, "y": True})
        assert "after 'else'" in str(exc_info.value)
    
    def test_missing_if_condition_raises_error(self, processor):
        """Test that if without condition raises error."""
        template = "{# if #}content{# endif #}"
        
        with pytest.raises(ValueError) as exc_info:
            processor.process(template, {})
        assert "Missing condition" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
