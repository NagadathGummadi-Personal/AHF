"""
Conditional Processor for Prompt Templates.

This module provides conditional expression parsing and evaluation for prompts.
Supports:
- {# if condition #}...{# endif #}
- {# if condition #}...{# else #}...{# endif #}
- {# if condition #}...{# elif condition #}...{# else #}...{# endif #}
- Nested conditionals
- Various condition operators (==, !=, >, <, >=, <=, in, not in, and, or, not)

Example:
    processor = ConditionalProcessor()
    
    template = '''
    {# if is_premium #}
    Welcome, premium member!
    {# else #}
    Welcome! Consider upgrading to premium.
    {# endif #}
    '''
    
    result = processor.process(template, {"is_premium": True})
    # Output: "Welcome, premium member!"
"""

import re
import operator
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum


class TokenType(Enum):
    """Types of tokens in conditional expressions."""
    IF = "if"
    ELIF = "elif"
    ELSE = "else"
    ENDIF = "endif"
    TEXT = "text"


@dataclass
class Token:
    """A token in the template."""
    type: TokenType
    content: str
    condition: Optional[str] = None
    line_number: int = 0


@dataclass
class ConditionalBlock:
    """Represents a parsed conditional block."""
    condition: str
    content: str
    elif_blocks: List[Tuple[str, str]]  # List of (condition, content) tuples
    else_content: Optional[str] = None


class ConditionalProcessor:
    """
    Processes conditional expressions in prompt templates.
    
    Supports the following syntax:
    - {# if condition #}...{# endif #}
    - {# if condition #}...{# else #}...{# endif #}
    - {# if condition #}...{# elif condition #}...{# else #}...{# endif #}
    
    Condition Syntax:
    - Boolean variables: {# if is_active #}
    - Negation: {# if not is_active #}
    - Equality: {# if status == 'active' #}
    - Inequality: {# if count != 0 #}
    - Comparison: {# if age >= 18 #}, {# if price < 100 #}
    - Membership: {# if 'admin' in roles #}
    - Logical operators: {# if is_active and is_verified #}
                        {# if is_admin or is_moderator #}
    - Existence check: {# if user_name #} (checks if variable exists and is truthy)
    
    Example:
        processor = ConditionalProcessor()
        
        template = '''
        Hello{# if name #}, {name}{# endif #}!
        {# if is_premium #}
        You have access to all features.
        {# elif is_trial #}
        Your trial expires soon.
        {# else #}
        Upgrade to premium for more features.
        {# endif #}
        '''
        
        result = processor.process(template, {
            "name": "John",
            "is_premium": False,
            "is_trial": True
        })
    """
    
    # Regex patterns for parsing
    # Match {# keyword condition #} where condition cannot contain #}
    CONDITIONAL_PATTERN = re.compile(
        r'\{#\s*(if|elif|else|endif)(?:\s+([^#]*?))?\s*#\}',
        re.DOTALL
    )
    
    # Operators mapping
    OPERATORS = {
        '==': operator.eq,
        '!=': operator.ne,
        '>': operator.gt,
        '<': operator.lt,
        '>=': operator.ge,
        '<=': operator.le,
    }
    
    def __init__(self, strict: bool = False):
        """
        Initialize the processor.
        
        Args:
            strict: If True, raise errors for undefined variables.
                   If False, undefined variables are treated as falsy.
        """
        self.strict = strict
    
    def process(
        self,
        template: str,
        variables: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Process conditional expressions in a template.
        
        Args:
            template: The template string with conditional blocks
            variables: Dictionary of variable values for condition evaluation
            
        Returns:
            Processed template with conditionals resolved
            
        Raises:
            ValueError: If template has mismatched or invalid conditional blocks
        """
        variables = variables or {}
        return self._process_template(template, variables)
    
    def _process_template(
        self,
        template: str,
        variables: Dict[str, Any]
    ) -> str:
        """
        Recursively process conditional blocks in template.
        """
        result = []
        pos = 0
        
        while pos < len(template):
            # Find next conditional block
            match = self.CONDITIONAL_PATTERN.search(template, pos)
            
            if not match:
                # No more conditionals, append rest of template
                result.append(template[pos:])
                break
            
            # Append text before the conditional
            result.append(template[pos:match.start()])
            
            keyword = match.group(1).lower()
            
            if keyword == 'if':
                # Parse the full if block
                block, end_pos = self._parse_if_block(template, match.start())
                evaluated = self._evaluate_block(block, variables)
                result.append(evaluated)
                pos = end_pos
            elif keyword in ('elif', 'else', 'endif'):
                # These should only appear within an if block
                raise ValueError(
                    f"Unexpected '{keyword}' without matching 'if' at position {match.start()}"
                )
            else:
                # Unknown keyword, treat as text
                result.append(match.group(0))
                pos = match.end()
        
        return ''.join(result)
    
    def _parse_if_block(
        self,
        template: str,
        start_pos: int
    ) -> Tuple[ConditionalBlock, int]:
        """
        Parse a complete if/elif/else/endif block.
        
        Args:
            template: The template string
            start_pos: Position of the opening {# if #} tag
            
        Returns:
            Tuple of (ConditionalBlock, end_position)
        """
        # Find the opening if tag
        if_match = self.CONDITIONAL_PATTERN.match(template[start_pos:])
        if not if_match or if_match.group(1).lower() != 'if':
            raise ValueError(f"Expected 'if' at position {start_pos}")
        
        condition = if_match.group(2)
        if not condition or not condition.strip():
            raise ValueError(f"Missing condition in 'if' at position {start_pos}")
        
        pos = start_pos + if_match.end()
        content_start = pos
        depth = 1
        
        if_content = None
        elif_blocks = []
        else_content = None
        current_section = 'if'
        current_condition = condition.strip()
        
        while pos < len(template) and depth > 0:
            match = self.CONDITIONAL_PATTERN.search(template, pos)
            
            if not match:
                raise ValueError(
                    f"Unclosed 'if' block starting at position {start_pos}"
                )
            
            keyword = match.group(1).lower()
            
            if keyword == 'if':
                # Nested if
                depth += 1
                pos = match.end()
            elif keyword == 'endif':
                depth -= 1
                if depth == 0:
                    # End of our block
                    section_content = template[content_start:match.start()]
                    
                    if current_section == 'if':
                        if_content = section_content
                    elif current_section == 'elif':
                        elif_blocks.append((current_condition, section_content))
                    else:  # else
                        else_content = section_content
                    
                    return ConditionalBlock(
                        condition=condition.strip(),
                        content=if_content or '',
                        elif_blocks=elif_blocks,
                        else_content=else_content
                    ), match.end()
                else:
                    pos = match.end()
            elif keyword == 'elif' and depth == 1:
                # Elif at our level
                section_content = template[content_start:match.start()]
                
                if current_section == 'if':
                    if_content = section_content
                elif current_section == 'elif':
                    elif_blocks.append((current_condition, section_content))
                else:
                    raise ValueError(
                        f"'elif' after 'else' at position {match.start()}"
                    )
                
                current_section = 'elif'
                current_condition = match.group(2)
                if not current_condition or not current_condition.strip():
                    raise ValueError(
                        f"Missing condition in 'elif' at position {match.start()}"
                    )
                current_condition = current_condition.strip()
                content_start = match.end()
                pos = match.end()
            elif keyword == 'else' and depth == 1:
                # Else at our level
                section_content = template[content_start:match.start()]
                
                if current_section == 'if':
                    if_content = section_content
                elif current_section == 'elif':
                    elif_blocks.append((current_condition, section_content))
                elif current_section == 'else':
                    raise ValueError(
                        f"Multiple 'else' blocks at position {match.start()}"
                    )
                
                current_section = 'else'
                content_start = match.end()
                pos = match.end()
            else:
                pos = match.end()
        
        raise ValueError(f"Unclosed 'if' block starting at position {start_pos}")
    
    def _evaluate_block(
        self,
        block: ConditionalBlock,
        variables: Dict[str, Any]
    ) -> str:
        """
        Evaluate a conditional block and return the appropriate content.
        """
        # Check if condition
        if self._evaluate_condition(block.condition, variables):
            content = block.content
        else:
            # Check elif conditions
            content = None
            for elif_condition, elif_content in block.elif_blocks:
                if self._evaluate_condition(elif_condition, variables):
                    content = elif_content
                    break
            
            # Use else content if no condition matched
            if content is None:
                content = block.else_content if block.else_content is not None else ''
        
        # Recursively process any nested conditionals
        return self._process_template(content, variables)
    
    def _evaluate_condition(
        self,
        condition: str,
        variables: Dict[str, Any]
    ) -> bool:
        """
        Evaluate a condition expression.
        
        Supports:
        - Simple variable: is_active
        - Negation: not is_active
        - Comparison: age >= 18
        - Equality: status == 'active'
        - Membership: 'admin' in roles
        - Logical: is_active and is_verified
        """
        condition = condition.strip()
        
        if not condition:
            return False
        
        # Handle 'and' operator
        if ' and ' in condition:
            parts = condition.split(' and ', 1)
            return (
                self._evaluate_condition(parts[0], variables) and
                self._evaluate_condition(parts[1], variables)
            )
        
        # Handle 'or' operator
        if ' or ' in condition:
            parts = condition.split(' or ', 1)
            return (
                self._evaluate_condition(parts[0], variables) or
                self._evaluate_condition(parts[1], variables)
            )
        
        # Handle 'not' operator
        if condition.startswith('not '):
            return not self._evaluate_condition(condition[4:], variables)
        
        # Handle 'not in' operator
        if ' not in ' in condition:
            return self._evaluate_membership(condition, variables, negate=True)
        
        # Handle 'in' operator
        if ' in ' in condition:
            return self._evaluate_membership(condition, variables, negate=False)
        
        # Handle comparison operators
        for op_str in ['==', '!=', '>=', '<=', '>', '<']:
            if op_str in condition:
                return self._evaluate_comparison(condition, op_str, variables)
        
        # Try to resolve as a literal or variable and check truthiness
        value = self._resolve_value(condition, variables)
        return bool(value)
    
    def _evaluate_comparison(
        self,
        condition: str,
        op_str: str,
        variables: Dict[str, Any]
    ) -> bool:
        """Evaluate a comparison expression."""
        parts = condition.split(op_str, 1)
        if len(parts) != 2:
            return False
        
        left = self._resolve_value(parts[0].strip(), variables)
        right = self._resolve_value(parts[1].strip(), variables)
        
        op_func = self.OPERATORS.get(op_str)
        if op_func:
            try:
                return op_func(left, right)
            except (TypeError, ValueError):
                return False
        
        return False
    
    def _evaluate_membership(
        self,
        condition: str,
        variables: Dict[str, Any],
        negate: bool = False
    ) -> bool:
        """Evaluate a membership expression (in/not in)."""
        if negate:
            parts = condition.split(' not in ', 1)
        else:
            parts = condition.split(' in ', 1)
        
        if len(parts) != 2:
            return False
        
        item = self._resolve_value(parts[0].strip(), variables)
        container = self._resolve_value(parts[1].strip(), variables)
        
        try:
            result = item in container
            return not result if negate else result
        except (TypeError, ValueError):
            return False if not negate else True
    
    def _resolve_value(
        self,
        expr: str,
        variables: Dict[str, Any]
    ) -> Any:
        """
        Resolve an expression to its value.
        
        Handles:
        - String literals: 'value' or "value"
        - Numeric literals: 123, 12.5
        - Boolean literals: True, False, true, false
        - None/null: None, null
        - Variable references: variable_name
        """
        expr = expr.strip()
        
        # String literal
        if (expr.startswith("'") and expr.endswith("'")) or \
           (expr.startswith('"') and expr.endswith('"')):
            return expr[1:-1]
        
        # Boolean literal
        if expr.lower() == 'true':
            return True
        if expr.lower() == 'false':
            return False
        
        # None literal
        if expr.lower() in ('none', 'null'):
            return None
        
        # Numeric literal
        try:
            if '.' in expr:
                return float(expr)
            return int(expr)
        except ValueError:
            pass
        
        # Variable reference
        return self._get_variable_value(expr, variables)
    
    def _get_variable_value(
        self,
        name: str,
        variables: Dict[str, Any],
        as_bool: bool = False
    ) -> Any:
        """
        Get a variable value from the variables dict.
        
        Supports dotted notation: user.name, order.items.0
        """
        name = name.strip()
        
        # Handle dotted notation
        if '.' in name:
            parts = name.split('.')
            value = variables
            
            for part in parts:
                if isinstance(value, dict):
                    value = value.get(part)
                elif isinstance(value, (list, tuple)):
                    try:
                        value = value[int(part)]
                    except (ValueError, IndexError):
                        value = None
                elif hasattr(value, part):
                    value = getattr(value, part)
                else:
                    value = None
                
                if value is None:
                    break
            
            if as_bool:
                return bool(value)
            return value
        
        # Simple variable
        if name in variables:
            value = variables[name]
            if as_bool:
                return bool(value)
            return value
        
        # Variable not found
        if self.strict:
            raise ValueError(f"Undefined variable: {name}")
        
        return False if as_bool else None
    
    def has_conditionals(self, template: str) -> bool:
        """
        Check if a template contains any conditional blocks.
        
        Args:
            template: The template string to check
            
        Returns:
            True if the template contains conditional blocks
        """
        return bool(self.CONDITIONAL_PATTERN.search(template))
    
    def extract_conditional_variables(self, template: str) -> set:
        """
        Extract all variable names used in conditional expressions.
        
        Args:
            template: The template string
            
        Returns:
            Set of variable names used in conditions
        """
        variables = set()
        
        for match in self.CONDITIONAL_PATTERN.finditer(template):
            condition = match.group(2)
            if condition:
                variables.update(self._extract_variables_from_condition(condition))
        
        return variables
    
    def _extract_variables_from_condition(self, condition: str) -> set:
        """
        Extract variable names from a condition expression.
        """
        variables = set()
        
        # Remove operators and keywords
        condition = condition.replace(' and ', ' ')
        condition = condition.replace(' or ', ' ')
        condition = condition.replace(' not in ', ' ')
        condition = condition.replace(' in ', ' ')
        condition = condition.replace(' not ', ' ')
        
        for op in self.OPERATORS.keys():
            condition = condition.replace(op, ' ')
        
        # Split into tokens
        tokens = condition.split()
        
        for token in tokens:
            token = token.strip()
            
            # Skip string literals
            if (token.startswith("'") and token.endswith("'")) or \
               (token.startswith('"') and token.endswith('"')):
                continue
            
            # Skip boolean/none literals
            if token.lower() in ('true', 'false', 'none', 'null', 'not'):
                continue
            
            # Skip numeric literals
            try:
                float(token)
                continue
            except ValueError:
                pass
            
            # Skip empty tokens
            if not token:
                continue
            
            # This is a variable (possibly with dotted notation)
            # Get the root variable name
            root_var = token.split('.')[0]
            if root_var and root_var[0].isalpha() or root_var[0] == '_':
                variables.add(root_var)
        
        return variables
    
    def validate_template(self, template: str) -> List[str]:
        """
        Validate a template for correct conditional syntax.
        
        Args:
            template: The template string to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        depth = 0
        positions = []
        
        for match in self.CONDITIONAL_PATTERN.finditer(template):
            keyword = match.group(1).lower()
            condition = match.group(2)
            
            if keyword == 'if':
                if not condition or not condition.strip():
                    errors.append(
                        f"Missing condition in 'if' at position {match.start()}"
                    )
                depth += 1
                positions.append(match.start())
            elif keyword == 'elif':
                if depth == 0:
                    errors.append(
                        f"'elif' without matching 'if' at position {match.start()}"
                    )
                if not condition or not condition.strip():
                    errors.append(
                        f"Missing condition in 'elif' at position {match.start()}"
                    )
            elif keyword == 'else':
                if depth == 0:
                    errors.append(
                        f"'else' without matching 'if' at position {match.start()}"
                    )
            elif keyword == 'endif':
                if depth == 0:
                    errors.append(
                        f"'endif' without matching 'if' at position {match.start()}"
                    )
                else:
                    depth -= 1
                    positions.pop()
        
        if depth > 0:
            for pos in positions:
                errors.append(f"Unclosed 'if' block at position {pos}")
        
        return errors


# Convenience function for quick processing
def process_conditionals(
    template: str,
    variables: Optional[Dict[str, Any]] = None,
    strict: bool = False
) -> str:
    """
    Process conditional expressions in a template.
    
    This is a convenience function that creates a ConditionalProcessor
    and processes the template in one call.
    
    Args:
        template: The template string with conditional blocks
        variables: Dictionary of variable values
        strict: If True, raise errors for undefined variables
        
    Returns:
        Processed template with conditionals resolved
        
    Example:
        result = process_conditionals(
            "{# if is_admin #}Admin{# else #}User{# endif #}",
            {"is_admin": True}
        )
        # Returns: "Admin"
    """
    processor = ConditionalProcessor(strict=strict)
    return processor.process(template, variables)
