from enum import Enum

class LogLevel(Enum):
    """Enumeration for log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class LoggingFormat(Enum):
    """Enumeration for supported logging output formats."""
    STANDARD = "standard"
    DETAILED = "detailed"
    JSON = "json"

class Environment(Enum):
    """Enumeration for environment types."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"

class RedactionType(Enum):
    """Enumeration for redaction types."""
    REDACT = "redact"
    REMOVE = "remove"
    REPLACE = "replace"
    HASH = "hash"
    CENSOR = "censor"
    MASK = "mask"
    TRUNCATE = "truncate"

class LogConfig(Enum):
    """Enumeration for log configuration types."""
    REDACTION = "redaction"

class RedactionConfig(Enum):
    """Enumeration for redaction configuration types."""
    ENABLED = "enabled"
    PLACEHOLDER = "placeholder"
    PATTERNS = "patterns"

class RedactionPattern(Enum):
    """Enumeration for redaction pattern types."""
    CREDIT_CARD = "credit_card"