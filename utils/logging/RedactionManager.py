
"""Data redaction manager for logging sensitive information."""

import re
from typing import Any


class RedactionManager:
    """Manages data redaction based on regex patterns and special tags."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.redaction_placeholder = config.get("placeholder", "[REDACTED]")
        self.redaction_patterns = self._compile_patterns()

    def _compile_patterns(self) -> list[tuple[re.Pattern, str]]:
        """Compile redaction patterns from configuration."""
        patterns = []

        # Add default [Redact]...[/Redact] pattern
        redact_tag_pattern = re.compile(
            r"\[Redact\](.*?)\[/Redact\]", re.IGNORECASE | re.DOTALL
        )
        patterns.append((redact_tag_pattern, self.redaction_placeholder))

        # Add custom patterns from config
        custom_patterns = self.config.get("patterns", [])
        for pattern_config in custom_patterns:
            if isinstance(pattern_config, dict):
                pattern_str = pattern_config.get("pattern")
                placeholder = pattern_config.get(
                    "placeholder", self.redaction_placeholder
                )
                flags = self._get_regex_flags(pattern_config.get("flags", []))

                if pattern_str:
                    try:
                        compiled_pattern = re.compile(pattern_str, flags)
                        patterns.append((compiled_pattern, placeholder))
                    except re.error as e:
                        # Log pattern compilation error but continue
                        # Use logging instead of print in production
                        msg = f"Warning: Invalid regex pattern '{pattern_str}': {e}"
                        print(msg)
            elif isinstance(pattern_config, str):
                # Simple string pattern
                try:
                    compiled_pattern = re.compile(pattern_config)
                    patterns.append(
                        (compiled_pattern, self.redaction_placeholder))
                except re.error as e:
                    # Use logging instead of print in production
                    msg = f"Warning: Invalid regex pattern '{pattern_config}': {e}"
                    print(msg)

        return patterns

    def _get_regex_flags(self, flag_names: list[str]) -> int:
        """Convert flag names to regex flags."""
        flags = 0
        flag_map = {
            "ignorecase": re.IGNORECASE,
            "multiline": re.MULTILINE,
            "dotall": re.DOTALL,
            "verbose": re.VERBOSE,
            "ascii": re.ASCII,
        }

        for flag_name in flag_names:
            if flag_name.lower() in flag_map:
                flags |= flag_map[flag_name.lower()]

        return flags

    def redact_message(self, message: str) -> str:
        """Apply redaction patterns to a message."""
        if not isinstance(message, str):
            return str(message)

        redacted_message = message

        # Apply patterns in reverse order so custom patterns override defaults
        for pattern, placeholder in reversed(self.redaction_patterns):
            redacted_message = pattern.sub(placeholder, redacted_message)

        return redacted_message

    def redact_data(self, data: Any) -> Any:
        """Recursively redact data in various formats."""
        if isinstance(data, str):
            return self.redact_message(data)
        if isinstance(data, dict):
            return {key: self.redact_data(value)
                    for key, value in data.items()}
        if isinstance(data, list):
            return [self.redact_data(item) for item in data]
        if isinstance(data, tuple):
            return tuple(self.redact_data(item) for item in data)
        # Convert to string and redact for other types
        return self.redact_message(str(data))
