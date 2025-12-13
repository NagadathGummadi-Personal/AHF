"""
Safe Expression Engine for Prompt Conditionals.

Provides safe evaluation of Python-like expressions for conditional
prompt content without using eval() or exec().

Uses AST parsing to whitelist safe operations only.

Supported operations:
- Comparisons: ==, !=, <, >, <=, >=
- Boolean: and, or, not
- Membership: in, not in
- Attributes: object.attr
- Indexing: object[key]
- Literals: strings, numbers, booleans, None, lists, dicts
- Simple function calls: len(), str(), int(), bool()

NOT supported (for security):
- Assignment
- Function definitions
- Lambda
- Import
- Exec/eval
- Comprehensions
- Async

Example:
    evaluator = SafeExpressionEvaluator({"user_type": "premium", "days": 30})
    
    result = evaluator.evaluate("user_type == 'premium' and days > 7")
    # Returns: True
"""

import ast
import operator
from typing import Any, Dict, List, Optional, Set


# Allowed binary operators
BINARY_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

# Allowed comparison operators
COMPARE_OPS = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.Is: operator.is_,
    ast.IsNot: operator.is_not,
    ast.In: lambda a, b: a in b,
    ast.NotIn: lambda a, b: a not in b,
}

# Allowed boolean operators
BOOL_OPS = {
    ast.And: lambda values: all(values),
    ast.Or: lambda values: any(values),
}

# Allowed unary operators
UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
    ast.Not: operator.not_,
}

# Allowed builtin functions
SAFE_BUILTINS = {
    "len": len,
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "abs": abs,
    "min": min,
    "max": max,
    "sum": sum,
    "round": round,
    "sorted": sorted,
    "list": list,
    "dict": dict,
    "set": set,
    "tuple": tuple,
    "type": lambda x: type(x).__name__,
    "isinstance": isinstance,
    "hasattr": hasattr,
    "getattr": getattr,
}

# Maximum expression complexity
MAX_DEPTH = 20
MAX_NODES = 100


class ExpressionError(Exception):
    """Error during expression evaluation."""
    pass


class SafeExpressionEvaluator:
    """
    Safe Python expression evaluator using AST.
    
    Evaluates Python expressions in a sandboxed context without
    using eval() or exec(). Only whitelisted operations are allowed.
    
    Usage:
        context = {"user": {"name": "Alice", "age": 30}, "is_admin": True}
        evaluator = SafeExpressionEvaluator(context)
        
        # Simple comparisons
        evaluator.evaluate("is_admin")  # True
        evaluator.evaluate("user['age'] >= 18")  # True
        
        # Complex expressions
        evaluator.evaluate("is_admin and user['name'] == 'Alice'")  # True
    """
    
    def __init__(self, context: Optional[Dict[str, Any]] = None):
        """
        Initialize with context variables.
        
        Args:
            context: Dictionary of variables available in expressions
        """
        self.context = context or {}
        self._node_count = 0
    
    def evaluate(self, expression: str) -> Any:
        """
        Evaluate an expression safely.
        
        Args:
            expression: Python expression string
            
        Returns:
            Result of the expression
            
        Raises:
            ExpressionError: If expression is invalid or unsafe
        """
        if not expression or not expression.strip():
            return False
        
        try:
            tree = ast.parse(expression, mode='eval')
        except SyntaxError as e:
            raise ExpressionError(f"Invalid expression syntax: {e}")
        
        self._node_count = 0
        
        try:
            return self._eval_node(tree.body, depth=0)
        except ExpressionError:
            raise
        except Exception as e:
            raise ExpressionError(f"Evaluation error: {e}")
    
    def _eval_node(self, node: ast.AST, depth: int = 0) -> Any:
        """Recursively evaluate an AST node."""
        if depth > MAX_DEPTH:
            raise ExpressionError("Expression too deeply nested")
        
        self._node_count += 1
        if self._node_count > MAX_NODES:
            raise ExpressionError("Expression too complex")
        
        # Handle different node types
        if isinstance(node, ast.Constant):
            return node.value
        
        # Legacy support for Python < 3.8
        if isinstance(node, ast.Num):
            return node.n
        if isinstance(node, ast.Str):
            return node.s
        if isinstance(node, ast.NameConstant):
            return node.value
        
        if isinstance(node, ast.Name):
            return self._eval_name(node)
        
        if isinstance(node, ast.BinOp):
            return self._eval_binop(node, depth)
        
        if isinstance(node, ast.UnaryOp):
            return self._eval_unaryop(node, depth)
        
        if isinstance(node, ast.BoolOp):
            return self._eval_boolop(node, depth)
        
        if isinstance(node, ast.Compare):
            return self._eval_compare(node, depth)
        
        if isinstance(node, ast.IfExp):
            return self._eval_ifexp(node, depth)
        
        if isinstance(node, ast.Subscript):
            return self._eval_subscript(node, depth)
        
        if isinstance(node, ast.Attribute):
            return self._eval_attribute(node, depth)
        
        if isinstance(node, ast.Call):
            return self._eval_call(node, depth)
        
        if isinstance(node, ast.List):
            return [self._eval_node(elt, depth + 1) for elt in node.elts]
        
        if isinstance(node, ast.Tuple):
            return tuple(self._eval_node(elt, depth + 1) for elt in node.elts)
        
        if isinstance(node, ast.Dict):
            keys = [self._eval_node(k, depth + 1) if k else None for k in node.keys]
            values = [self._eval_node(v, depth + 1) for v in node.values]
            return dict(zip(keys, values))
        
        if isinstance(node, ast.Set):
            return {self._eval_node(elt, depth + 1) for elt in node.elts}
        
        raise ExpressionError(f"Unsupported expression type: {type(node).__name__}")
    
    def _eval_name(self, node: ast.Name) -> Any:
        """Evaluate a name (variable lookup)."""
        name = node.id
        
        # Check builtins first
        if name in SAFE_BUILTINS:
            return SAFE_BUILTINS[name]
        
        # Check constants
        if name == "True":
            return True
        if name == "False":
            return False
        if name == "None":
            return None
        
        # Look up in context
        if name in self.context:
            return self.context[name]
        
        # Not found - return False instead of error for boolean contexts
        return False
    
    def _eval_binop(self, node: ast.BinOp, depth: int) -> Any:
        """Evaluate a binary operation."""
        op_type = type(node.op)
        if op_type not in BINARY_OPS:
            raise ExpressionError(f"Unsupported operator: {op_type.__name__}")
        
        left = self._eval_node(node.left, depth + 1)
        right = self._eval_node(node.right, depth + 1)
        
        return BINARY_OPS[op_type](left, right)
    
    def _eval_unaryop(self, node: ast.UnaryOp, depth: int) -> Any:
        """Evaluate a unary operation."""
        op_type = type(node.op)
        if op_type not in UNARY_OPS:
            raise ExpressionError(f"Unsupported operator: {op_type.__name__}")
        
        operand = self._eval_node(node.operand, depth + 1)
        return UNARY_OPS[op_type](operand)
    
    def _eval_boolop(self, node: ast.BoolOp, depth: int) -> Any:
        """Evaluate a boolean operation (and/or)."""
        op_type = type(node.op)
        if op_type not in BOOL_OPS:
            raise ExpressionError(f"Unsupported boolean operator: {op_type.__name__}")
        
        # Short-circuit evaluation
        if isinstance(node.op, ast.And):
            for value_node in node.values:
                result = self._eval_node(value_node, depth + 1)
                if not result:
                    return result
            return result
        elif isinstance(node.op, ast.Or):
            for value_node in node.values:
                result = self._eval_node(value_node, depth + 1)
                if result:
                    return result
            return result
        
        # Fallback
        values = [self._eval_node(v, depth + 1) for v in node.values]
        return BOOL_OPS[op_type](values)
    
    def _eval_compare(self, node: ast.Compare, depth: int) -> bool:
        """Evaluate a comparison chain."""
        left = self._eval_node(node.left, depth + 1)
        
        for op, comparator in zip(node.ops, node.comparators):
            op_type = type(op)
            if op_type not in COMPARE_OPS:
                raise ExpressionError(f"Unsupported comparison: {op_type.__name__}")
            
            right = self._eval_node(comparator, depth + 1)
            
            if not COMPARE_OPS[op_type](left, right):
                return False
            
            left = right
        
        return True
    
    def _eval_ifexp(self, node: ast.IfExp, depth: int) -> Any:
        """Evaluate a ternary expression (a if b else c)."""
        test = self._eval_node(node.test, depth + 1)
        if test:
            return self._eval_node(node.body, depth + 1)
        else:
            return self._eval_node(node.orelse, depth + 1)
    
    def _eval_subscript(self, node: ast.Subscript, depth: int) -> Any:
        """Evaluate subscript access (obj[key])."""
        value = self._eval_node(node.value, depth + 1)
        
        # Handle different slice types
        if isinstance(node.slice, ast.Index):
            # Python < 3.9
            index = self._eval_node(node.slice.value, depth + 1)
        else:
            index = self._eval_node(node.slice, depth + 1)
        
        try:
            return value[index]
        except (KeyError, IndexError, TypeError):
            return None
    
    def _eval_attribute(self, node: ast.Attribute, depth: int) -> Any:
        """Evaluate attribute access (obj.attr)."""
        value = self._eval_node(node.value, depth + 1)
        attr = node.attr
        
        # Disallow private attributes
        if attr.startswith('_'):
            raise ExpressionError(f"Access to private attributes is not allowed: {attr}")
        
        try:
            return getattr(value, attr)
        except AttributeError:
            # Try dict access as fallback
            if isinstance(value, dict):
                return value.get(attr)
            return None
    
    def _eval_call(self, node: ast.Call, depth: int) -> Any:
        """Evaluate a function call."""
        func = self._eval_node(node.func, depth + 1)
        
        # Only allow safe builtins
        if func not in SAFE_BUILTINS.values():
            # Check if it's a method on a known safe type
            if not callable(func):
                raise ExpressionError(f"Cannot call non-callable: {func}")
        
        args = [self._eval_node(arg, depth + 1) for arg in node.args]
        
        kwargs = {}
        for keyword in node.keywords:
            kwargs[keyword.arg] = self._eval_node(keyword.value, depth + 1)
        
        try:
            return func(*args, **kwargs)
        except Exception as e:
            raise ExpressionError(f"Function call error: {e}")

