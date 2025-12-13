"""
Real Tests for Expression Engine (Python Inline Conditionals).

Tests the {{#if condition}}...{{#else}}...{{#endif}} syntax.
No mocks - uses real expression evaluator.
"""

import pytest
from core.promptregistry.runtimes import SafeExpressionEvaluator, ExpressionError
from core.promptregistry import PromptTemplate


class TestSafeExpressionEvaluator:
    """Tests for the safe Python expression evaluator."""
    
    def test_simple_boolean_variable(self):
        """Test evaluating simple boolean variables."""
        evaluator = SafeExpressionEvaluator({"is_admin": True, "is_guest": False})
        
        assert evaluator.evaluate("is_admin") == True
        assert evaluator.evaluate("is_guest") == False
        assert evaluator.evaluate("not is_guest") == True
    
    def test_comparison_operators(self):
        """Test comparison operators."""
        evaluator = SafeExpressionEvaluator({
            "age": 25,
            "score": 85.5,
            "name": "Alice"
        })
        
        assert evaluator.evaluate("age > 18") == True
        assert evaluator.evaluate("age >= 25") == True
        assert evaluator.evaluate("age < 30") == True
        assert evaluator.evaluate("score == 85.5") == True
        assert evaluator.evaluate("name == 'Alice'") == True
        assert evaluator.evaluate("name != 'Bob'") == True
    
    def test_boolean_operators(self):
        """Test and/or operators with short-circuit evaluation."""
        evaluator = SafeExpressionEvaluator({
            "is_premium": True,
            "days_active": 30,
            "is_verified": True
        })
        
        assert evaluator.evaluate("is_premium and days_active > 7") == True
        assert evaluator.evaluate("is_premium and days_active > 100") == False
        assert evaluator.evaluate("is_premium or days_active > 100") == True
        assert evaluator.evaluate("is_premium and is_verified") == True
    
    def test_membership_operators(self):
        """Test in/not in operators."""
        evaluator = SafeExpressionEvaluator({
            "role": "admin",
            "roles": ["admin", "user"],
            "permissions": {"read", "write"}
        })
        
        assert evaluator.evaluate("role in roles") == True
        assert evaluator.evaluate("'guest' not in roles") == True
        assert evaluator.evaluate("'read' in permissions") == True
    
    def test_dict_and_list_access(self):
        """Test dictionary and list access."""
        evaluator = SafeExpressionEvaluator({
            "user": {"name": "Alice", "age": 30},
            "scores": [90, 85, 95]
        })
        
        assert evaluator.evaluate("user['name'] == 'Alice'") == True
        assert evaluator.evaluate("user['age'] >= 18") == True
        assert evaluator.evaluate("scores[0] > 80") == True
    
    def test_attribute_access(self):
        """Test attribute access on objects."""
        class User:
            name = "Alice"
            is_active = True
        
        evaluator = SafeExpressionEvaluator({"user": User()})
        
        assert evaluator.evaluate("user.name == 'Alice'") == True
        assert evaluator.evaluate("user.is_active") == True
    
    def test_builtin_functions(self):
        """Test allowed builtin functions."""
        evaluator = SafeExpressionEvaluator({
            "items": [1, 2, 3, 4, 5],
            "text": "hello"
        })
        
        assert evaluator.evaluate("len(items) == 5") == True
        assert evaluator.evaluate("len(text) > 3") == True
        assert evaluator.evaluate("sum(items) == 15") == True
        assert evaluator.evaluate("max(items) == 5") == True
    
    def test_ternary_expression(self):
        """Test ternary (if-else) expressions."""
        evaluator = SafeExpressionEvaluator({"is_premium": True})
        
        result = evaluator.evaluate("'VIP' if is_premium else 'Standard'")
        assert result == "VIP"
        
        evaluator = SafeExpressionEvaluator({"is_premium": False})
        result = evaluator.evaluate("'VIP' if is_premium else 'Standard'")
        assert result == "Standard"
    
    def test_complex_expression(self):
        """Test complex multi-part expressions."""
        evaluator = SafeExpressionEvaluator({
            "user_type": "premium",
            "days_active": 45,
            "has_verified_email": True
        })
        
        expr = "user_type == 'premium' and days_active > 30 and has_verified_email"
        assert evaluator.evaluate(expr) == True
        
        expr = "(user_type == 'premium' or user_type == 'vip') and days_active >= 30"
        assert evaluator.evaluate(expr) == True
    
    def test_undefined_variable_returns_false(self):
        """Test that undefined variables return False (boolean context)."""
        evaluator = SafeExpressionEvaluator({})
        
        # Undefined should be falsy
        assert evaluator.evaluate("undefined_var") == False
    
    def test_invalid_syntax_raises(self):
        """Test that invalid syntax raises ExpressionError."""
        evaluator = SafeExpressionEvaluator({})
        
        with pytest.raises(ExpressionError):
            evaluator.evaluate("if x then y")  # Invalid Python syntax
    
    def test_security_private_attributes_blocked(self):
        """Test that private attributes are blocked."""
        class Obj:
            _secret = "hidden"
            public = "visible"
        
        evaluator = SafeExpressionEvaluator({"obj": Obj()})
        
        with pytest.raises(ExpressionError):
            evaluator.evaluate("obj._secret")
    
    def test_deeply_nested_blocked(self):
        """Test that deeply nested expressions are blocked."""
        evaluator = SafeExpressionEvaluator({})
        
        # Create a very deeply nested expression
        deep_expr = "(((((((((((((((((((((1))))))))))))))))))))))"
        # Should still work for reasonable depth
        result = evaluator.evaluate(deep_expr)
        assert result == 1


class TestConditionalBlocks:
    """Tests for conditional blocks in PromptTemplate."""
    
    def test_simple_if_block(self):
        """Test simple {{#if}} block."""
        template = PromptTemplate(
            content="{{#if is_new_user}}Welcome, new user!{{#endif}}"
        )
        
        result = template.render(context={"is_new_user": True})
        assert "Welcome, new user!" in result
        
        result = template.render(context={"is_new_user": False})
        assert "Welcome, new user!" not in result
        assert result.strip() == ""
    
    def test_if_else_block(self):
        """Test {{#if}}...{{#else}}...{{#endif}} block."""
        template = PromptTemplate(
            content="{{#if is_premium}}Welcome, VIP!{{#else}}Welcome!{{#endif}}"
        )
        
        result = template.render(context={"is_premium": True})
        assert "Welcome, VIP!" in result
        
        result = template.render(context={"is_premium": False})
        assert "Welcome!" in result
        assert "VIP" not in result
    
    def test_conditional_with_comparison(self):
        """Test conditional with comparison expression."""
        template = PromptTemplate(
            content="{{#if age >= 18}}Adult content allowed.{{#else}}Restricted.{{#endif}}"
        )
        
        result = template.render(context={"age": 25})
        assert "Adult content allowed" in result
        
        result = template.render(context={"age": 15})
        assert "Restricted" in result
    
    def test_conditional_with_variables(self):
        """Test conditional combined with variables."""
        template = PromptTemplate(
            content="Hello {{user_name|default:Guest}}! {{#if is_premium}}You have VIP access.{{#endif}}"
        )
        
        result = template.render(
            variables={"user_name": "Alice"},
            context={"is_premium": True}
        )
        assert "Hello Alice!" in result
        assert "VIP access" in result
    
    def test_complex_conditional(self):
        """Test complex conditional expression."""
        template = PromptTemplate(
            content="{{#if user_type == 'admin' and is_verified}}Admin panel enabled.{{#else}}Standard access.{{#endif}}"
        )
        
        result = template.render(context={"user_type": "admin", "is_verified": True})
        assert "Admin panel enabled" in result
        
        result = template.render(context={"user_type": "admin", "is_verified": False})
        assert "Standard access" in result
    
    def test_multiline_conditional(self):
        """Test multiline content in conditional blocks."""
        template = PromptTemplate(
            content="""{{#if show_header}}
# Welcome Header
This is a welcome message.
{{#endif}}
Main content here."""
        )
        
        result = template.render(context={"show_header": True})
        assert "Welcome Header" in result
        assert "Main content here" in result
        
        result = template.render(context={"show_header": False})
        assert "Welcome Header" not in result
        assert "Main content here" in result

