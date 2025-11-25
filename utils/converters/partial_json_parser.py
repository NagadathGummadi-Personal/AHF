"""
Partial JSON Parser for Streaming LLM Outputs.

Handles incomplete/partial JSON during streaming to provide real-time parsing.
Supports all streaming edge cases including incomplete keys, values, and nested structures.

Streaming Cases Handled:
1. {"Nam -> {"Nam": null}
2. {"Name -> {"Name": null}
3. {"Name": -> {"Name": null}
4. {"Name": "R -> {"Name": "R"}
5. {"Name": "Ra -> {"Name": "Ra"}
6. {"Name": "Raj" -> {"Name": "Raj"}
7. { -> {}
8. {"Name": "Raj", -> {"Name": "Raj"}
9. {"Name": "Raj"," -> {"Name": "Raj", "": null}
10. {"Name": "Raj","age -> {"Name": "Raj", "age": null}
11. {"Name": "Raj","age": 18 -> {"Name": "Raj", "age": 18}
"""

import json
import re
from typing import Any, Dict, List, Optional, Tuple


def parse_partial_json(s: str) -> Optional[Any]:
    """
    Parse partial/incomplete JSON that may be in the middle of being generated.
    
    Handles:
    - Incomplete strings (keys and values)
    - Missing closing brackets/braces
    - Truncated values
    - Trailing commas
    - Incomplete key-value pairs
    - Nested structures
    
    Args:
        s: Partial JSON string (may be incomplete)
        
    Returns:
        Parsed object (dict, list, etc.) or None if cannot be parsed
        
    Example:
        parse_partial_json('{"name": "Jo')  # Returns: {"name": "Jo"}
        parse_partial_json('{"items": [1, 2, 3')  # Returns: {"items": [1, 2, 3]}
        parse_partial_json('{"key": ')  # Returns: {"key": null}
        parse_partial_json('{"Nam')  # Returns: {"Nam": null}
    """
    if not s or not s.strip():
        return None
    
    s = s.strip()
    
    # Try parsing as-is first (handles complete JSON)
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass
    
    # Attempt to fix and parse
    fixed = _fix_incomplete_json(s)
    if fixed:
        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            pass
    
    return None


def _fix_incomplete_json(s: str) -> Optional[str]:
    """
    Attempt to fix incomplete JSON by completing open structures.
    
    Handles all streaming edge cases including:
    - Incomplete keys: {"Nam -> {"Nam": null}
    - Incomplete values: {"Name": "R -> {"Name": "R"}
    - Missing values: {"Name": -> {"Name": null}
    - Trailing commas: {"Name": "Raj", -> {"Name": "Raj"}
    - Incomplete key starts: {"Name": "Raj"," -> {"Name": "Raj", "": null}
    
    Args:
        s: Partial JSON string
        
    Returns:
        Fixed JSON string, or None if cannot be fixed
    """
    s = s.strip()
    
    if not s:
        return None
    
    # Parse the string and track state
    result, _ = _complete_json_value(s, 0)
    return result


def _complete_json_value(s: str, pos: int) -> Tuple[Optional[str], int]:
    """
    Complete a JSON value starting at position pos.
    
    Args:
        s: The JSON string
        pos: Starting position
        
    Returns:
        Tuple of (completed string, end position)
    """
    # Skip whitespace
    while pos < len(s) and s[pos] in ' \t\n\r':
        pos += 1
    
    if pos >= len(s):
        return "null", pos
    
    char = s[pos]
    
    if char == '{':
        return _complete_object(s, pos)
    elif char == '[':
        return _complete_array(s, pos)
    elif char == '"':
        return _complete_string(s, pos)
    elif char in '-0123456789':
        return _complete_number(s, pos)
    elif s[pos:pos+4] == 'true':
        return "true", pos + 4
    elif s[pos:pos+5] == 'false':
        return "false", pos + 5
    elif s[pos:pos+4] == 'null':
        return "null", pos + 4
    elif char == 't':  # Incomplete true
        return "true", len(s)
    elif char == 'f':  # Incomplete false
        return "false", len(s)
    elif char == 'n':  # Incomplete null
        return "null", len(s)
    else:
        return None, pos


def _complete_object(s: str, pos: int) -> Tuple[Optional[str], int]:
    """
    Complete a JSON object starting at position pos.
    
    Handles:
    - Empty object: { -> {}
    - Incomplete key: {"Nam -> {"Nam": null}
    - Key without value: {"Name": -> {"Name": null}
    - Trailing comma: {"Name": "val", -> {"Name": "val"}
    - Incomplete next key: {"Name": "val"," -> {"Name": "val", "": null}
    """
    if pos >= len(s) or s[pos] != '{':
        return None, pos
    
    pos += 1  # Skip '{'
    result_parts = ['{']
    first_entry = True
    
    while pos < len(s):
        # Skip whitespace
        while pos < len(s) and s[pos] in ' \t\n\r':
            pos += 1
        
        if pos >= len(s):
            break
        
        # Check for closing brace
        if s[pos] == '}':
            result_parts.append('}')
            return ''.join(result_parts), pos + 1
        
        # Handle comma between entries
        if s[pos] == ',':
            pos += 1
            # Skip whitespace after comma
            while pos < len(s) and s[pos] in ' \t\n\r':
                pos += 1
            continue
        
        # We expect a key (string)
        if s[pos] == '"':
            # Parse the key
            key_str, pos = _complete_string(s, pos)
            if key_str is None:
                break
            
            if not first_entry:
                result_parts.append(', ')
            first_entry = False
            result_parts.append(key_str)
            
            # Skip whitespace
            while pos < len(s) and s[pos] in ' \t\n\r':
                pos += 1
            
            # Check for colon
            if pos >= len(s):
                # Key without colon - add null value
                result_parts.append(': null')
                break
            
            if s[pos] == ':':
                result_parts.append(': ')
                pos += 1
                
                # Skip whitespace after colon
                while pos < len(s) and s[pos] in ' \t\n\r':
                    pos += 1
                
                if pos >= len(s):
                    # Colon without value - add null
                    result_parts.append('null')
                    break
                
                # Parse the value
                value_str, pos = _complete_json_value(s, pos)
                if value_str is None:
                    result_parts.append('null')
                    break
                result_parts.append(value_str)
            else:
                # Key without colon - add null value
                result_parts.append(': null')
        else:
            # Might be an incomplete key (unquoted start)
            # Handle cases like {"Nam (incomplete key without closing quote)
            if s[pos] not in '{}[],:\n\r\t ':
                # Looks like start of unquoted key, skip to end
                key_start = pos
                while pos < len(s) and s[pos] not in '{}[],:\n\r\t "':
                    pos += 1
                incomplete_key = s[key_start:pos]
                if incomplete_key:
                    if not first_entry:
                        result_parts.append(', ')
                    first_entry = False
                    result_parts.append(f'"{incomplete_key}": null')
            break
    
    result_parts.append('}')
    return ''.join(result_parts), pos


def _complete_array(s: str, pos: int) -> Tuple[Optional[str], int]:
    """
    Complete a JSON array starting at position pos.
    
    Handles:
    - Empty array: [ -> []
    - Incomplete elements: [1, 2, -> [1, 2]
    - Trailing comma: [1, 2, 3, -> [1, 2, 3]
    """
    if pos >= len(s) or s[pos] != '[':
        return None, pos
    
    pos += 1  # Skip '['
    result_parts = ['[']
    first_element = True
    
    while pos < len(s):
        # Skip whitespace
        while pos < len(s) and s[pos] in ' \t\n\r':
            pos += 1
        
        if pos >= len(s):
            break
        
        # Check for closing bracket
        if s[pos] == ']':
            result_parts.append(']')
            return ''.join(result_parts), pos + 1
        
        # Handle comma between elements
        if s[pos] == ',':
            pos += 1
            # Skip whitespace after comma
            while pos < len(s) and s[pos] in ' \t\n\r':
                pos += 1
            continue
        
        # Parse array element
        value_str, pos = _complete_json_value(s, pos)
        if value_str is None:
            break
        
        if not first_element:
            result_parts.append(', ')
        first_element = False
        result_parts.append(value_str)
    
    result_parts.append(']')
    return ''.join(result_parts), pos


def _complete_string(s: str, pos: int) -> Tuple[Optional[str], int]:
    """
    Complete a JSON string starting at position pos.
    
    Handles:
    - Complete strings: "hello" -> "hello"
    - Incomplete strings: "hel -> "hel"
    - Escape sequences: "hello\nworld -> "hello\nworld"
    """
    if pos >= len(s) or s[pos] != '"':
        return None, pos
    
    pos += 1  # Skip opening quote
    string_chars = ['"']
    escape_next = False
    
    while pos < len(s):
        char = s[pos]
        
        if escape_next:
            string_chars.append(char)
            escape_next = False
            pos += 1
            continue
        
        if char == '\\':
            string_chars.append(char)
            escape_next = True
            pos += 1
            continue
        
        if char == '"':
            string_chars.append('"')
            return ''.join(string_chars), pos + 1
        
        string_chars.append(char)
        pos += 1
    
    # String wasn't closed - close it
    string_chars.append('"')
    return ''.join(string_chars), pos


def _complete_number(s: str, pos: int) -> Tuple[Optional[str], int]:
    """
    Complete a JSON number starting at position pos.
    
    Handles:
    - Integers: 123 -> 123
    - Decimals: 123.45 -> 123.45
    - Negatives: -123 -> -123
    - Incomplete decimals: 123. -> 123.0
    - Exponents: 1e10 -> 1e10
    """
    start_pos = pos
    
    # Handle negative
    if pos < len(s) and s[pos] == '-':
        pos += 1
    
    # Integer part
    while pos < len(s) and s[pos] in '0123456789':
        pos += 1
    
    # Decimal part
    if pos < len(s) and s[pos] == '.':
        pos += 1
        decimal_start = pos
        while pos < len(s) and s[pos] in '0123456789':
            pos += 1
        # If no digits after decimal, add 0
        if pos == decimal_start:
            number_str = s[start_pos:pos] + '0'
            return number_str, pos
    
    # Exponent part
    if pos < len(s) and s[pos] in 'eE':
        pos += 1
        if pos < len(s) and s[pos] in '+-':
            pos += 1
        exp_start = pos
        while pos < len(s) and s[pos] in '0123456789':
            pos += 1
        # If no digits after exponent, add 0
        if pos == exp_start:
            number_str = s[start_pos:pos] + '0'
            return number_str, pos
    
    number_str = s[start_pos:pos]
    if number_str == '-':
        return '0', pos
    return number_str, pos


def parse_json_markdown(text: str) -> Any:
    """
    Parse JSON from text, handling markdown code blocks.
    
    Args:
        text: Text that may contain JSON in markdown code blocks
        
    Returns:
        Parsed JSON object
        
    Raises:
        json.JSONDecodeError: If JSON cannot be parsed
        
    Example:
        text = '''
        ```json
        {"key": "value"}
        ```
        '''
        obj = parse_json_markdown(text)  # Returns: {"key": "value"}
    """
    # Try direct parse first
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    
    # Try to extract from markdown code block
    patterns = [
        r'```json\s*\n(.*?)\n```',
        r'```\s*\n(.*?)\n```',
        r'```json(.*?)```',
        r'```(.*?)```'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            json_str = match.group(1).strip()
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                continue
    
    # Try to extract raw JSON object
    if '{' in text and '}' in text:
        start = text.find('{')
        end = text.rfind('}') + 1
        json_str = text[start:end]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
    
    # Try to extract raw JSON array
    if '[' in text and ']' in text:
        start = text.find('[')
        end = text.rfind(']') + 1
        json_str = text[start:end]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
    
    raise json.JSONDecodeError(
        "Could not parse JSON from text",
        text,
        0
    )


def is_complete_json(text: str) -> bool:
    """
    Check if the text contains complete, valid JSON.
    
    Args:
        text: Text to check
        
    Returns:
        True if text is complete, valid JSON
    """
    try:
        json.loads(text.strip())
        return True
    except json.JSONDecodeError:
        return False


def get_partial_json_progress(text: str) -> float:
    """
    Estimate how complete the JSON is (0.0 to 1.0).
    
    Uses heuristics like bracket/brace matching to estimate progress.
    
    Args:
        text: Partial JSON text
        
    Returns:
        Progress estimate from 0.0 (just started) to 1.0 (complete)
    """
    if not text or not text.strip():
        return 0.0
    
    if is_complete_json(text):
        return 1.0
    
    # Count open vs closed brackets/braces
    open_braces = text.count('{') - text.count('}')
    open_brackets = text.count('[') - text.count(']')
    
    total_open = open_braces + open_brackets
    total_pairs = text.count('{') + text.count('[')
    
    if total_pairs == 0:
        return 0.1  # Just started
    
    # Estimate: (closed pairs / total pairs)
    closed_pairs = total_pairs - total_open
    if total_pairs > 0:
        progress = closed_pairs / total_pairs
        return max(0.0, min(1.0, progress))
    
    return 0.5


def get_partial_json_fields(text: str) -> List[str]:
    """
    Get the list of fields that have been parsed so far.
    
    Args:
        text: Partial JSON text
        
    Returns:
        List of field names found in the partial JSON
    """
    result = parse_partial_json(text)
    if result and isinstance(result, dict):
        return list(result.keys())
    return []


def get_partial_json_dict(text: str) -> Optional[Dict[str, Any]]:
    """
    Parse partial JSON and return as dict (if possible).
    
    Args:
        text: Partial JSON text
        
    Returns:
        Parsed dict or None if not an object
    """
    result = parse_partial_json(text)
    if isinstance(result, dict):
        return result
    return None
