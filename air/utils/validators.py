"""
Validators

Input validation utilities.

Version: 1.0.0
"""

import re
from typing import Optional
import uuid


def validate_phone_number(phone: str) -> bool:
    """
    Validate phone number format.
    
    Accepts:
    - +1XXXXXXXXXX (E.164 format)
    - 1XXXXXXXXXX
    - XXXXXXXXXX (10 digits)
    """
    # Remove common separators
    cleaned = re.sub(r'[\s\-\.\(\)]', '', phone)
    
    # Check patterns
    patterns = [
        r'^\+?1?\d{10}$',  # US format
        r'^\+\d{11,15}$',   # International
    ]
    
    return any(re.match(p, cleaned) for p in patterns)


def validate_uuid(value: str) -> bool:
    """Validate UUID format."""
    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError):
        return False


def sanitize_input(
    text: str,
    max_length: int = 10000,
    strip_html: bool = True,
) -> str:
    """
    Sanitize user input.
    
    Args:
        text: Input text
        max_length: Maximum allowed length
        strip_html: Whether to strip HTML tags
        
    Returns:
        Sanitized text
    """
    if not text:
        return ""
    
    # Limit length
    result = text[:max_length]
    
    # Strip HTML if requested
    if strip_html:
        result = re.sub(r'<[^>]+>', '', result)
    
    # Remove control characters (except newlines and tabs)
    result = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', result)
    
    return result.strip()


def validate_service_code(code: str) -> bool:
    """Validate service code format (ZENIDXXXX)."""
    return bool(re.match(r'^ZENID\d{4,}$', code))


def extract_phone_digits(phone: str) -> str:
    """Extract just digits from phone number."""
    return re.sub(r'\D', '', phone)


def normalize_phone(phone: str, country_code: str = "1") -> str:
    """Normalize phone to E.164 format."""
    digits = extract_phone_digits(phone)
    
    if len(digits) == 10:
        return f"+{country_code}{digits}"
    elif len(digits) == 11 and digits[0] == country_code:
        return f"+{digits}"
    elif digits.startswith("+"):
        return digits
    
    return f"+{digits}"

