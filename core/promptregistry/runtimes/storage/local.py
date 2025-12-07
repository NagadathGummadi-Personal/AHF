"""
Local Prompt Registry and Storage Implementation.

Provides file-system based prompt storage and registry.
Supports both JSON and YAML formats.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Literal

from ..base_registry import BasePromptRegistry
from ...interfaces.prompt_registry_interfaces import (
    IPromptStorage,
    IPromptValidator,
    IPromptSecurity,
)
from ...constants import (
    DEFAULT_STORAGE_PATH,
    JSON_EXTENSION,
    YAML_EXTENSION,
    YML_EXTENSION,
    STORAGE_FORMAT_JSON,
    STORAGE_FORMAT_YAML,
    DEFAULT_STORAGE_FORMAT,
    UTF_8,
)

# Optional YAML support
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


# =============================================================================
# STORAGE IMPLEMENTATION
# =============================================================================

class LocalFileStorage(IPromptStorage):
    """
    Local file-system based prompt storage.
    
    Stores each prompt as a separate JSON or YAML file in the storage directory.
    Supports both formats and can read either format regardless of default.
    
    Usage:
        storage = LocalFileStorage(storage_path=".prompts")
        await storage.save("greeting", {"content": "Hello!"})
        data = await storage.load("greeting")
    """
    
    def __init__(
        self,
        storage_path: str = DEFAULT_STORAGE_PATH,
        format: Literal["json", "yaml"] = DEFAULT_STORAGE_FORMAT
    ):
        """
        Initialize local storage.
        
        Args:
            storage_path: Directory path for storing prompts
            format: Storage format ("json" or "yaml")
        """
        self.storage_path = Path(storage_path)
        self.format = format
        
        if format == STORAGE_FORMAT_YAML and not YAML_AVAILABLE:
            raise ImportError(
                "YAML support requires PyYAML. Install with: pip install pyyaml"
            )
        
        self._ensure_directory()
    
    def _ensure_directory(self) -> None:
        """Ensure storage directory exists."""
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    def _get_extension(self) -> str:
        """Get file extension for current format."""
        return YAML_EXTENSION if self.format == STORAGE_FORMAT_YAML else JSON_EXTENSION
    
    def _get_file_path(self, key: str) -> Path:
        """Get file path for a key."""
        safe_key = key.replace("/", "_").replace("\\", "_").replace(".", "_")
        return self.storage_path / f"{safe_key}{self._get_extension()}"
    
    def _find_existing_file(self, key: str) -> Optional[Path]:
        """Find existing file for key (checks both JSON and YAML)."""
        safe_key = key.replace("/", "_").replace("\\", "_").replace(".", "_")
        
        extensions = [self._get_extension()]
        for ext in [JSON_EXTENSION, YAML_EXTENSION, YML_EXTENSION]:
            if ext not in extensions:
                extensions.append(ext)
        
        for ext in extensions:
            path = self.storage_path / f"{safe_key}{ext}"
            if path.exists():
                return path
        
        return None
    
    async def save(self, key: str, data: Dict[str, Any]) -> None:
        """Save data to storage."""
        file_path = self._get_file_path(key)
        
        with open(file_path, "w", encoding=UTF_8) as f:
            if self.format == STORAGE_FORMAT_YAML:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            else:
                json.dump(data, f, indent=2, ensure_ascii=False)
    
    async def load(self, key: str) -> Optional[Dict[str, Any]]:
        """Load data from storage (supports both JSON and YAML)."""
        file_path = self._find_existing_file(key)
        
        if file_path is None:
            return None
        
        with open(file_path, "r", encoding=UTF_8) as f:
            if file_path.suffix in [YAML_EXTENSION, YML_EXTENSION]:
                if not YAML_AVAILABLE:
                    raise ImportError("YAML support requires PyYAML")
                return yaml.safe_load(f)
            else:
                return json.load(f)
    
    async def delete(self, key: str) -> None:
        """Delete data from storage."""
        file_path = self._find_existing_file(key)
        
        if file_path and file_path.exists():
            file_path.unlink()
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in storage."""
        return self._find_existing_file(key) is not None
    
    async def list_keys(self, prefix: Optional[str] = None) -> List[str]:
        """List all keys in storage."""
        keys = set()
        
        for pattern in [f"*{JSON_EXTENSION}", f"*{YAML_EXTENSION}", f"*{YML_EXTENSION}"]:
            for file_path in self.storage_path.glob(pattern):
                key = file_path.stem
                if prefix is None or key.startswith(prefix):
                    keys.add(key)
        
        return sorted(keys)


# =============================================================================
# REGISTRY IMPLEMENTATION
# =============================================================================

class LocalPromptRegistry(BasePromptRegistry):
    """
    Local file-system based prompt registry.
    
    Stores prompts as JSON/YAML files with support for:
    - Multiple versions per prompt (immutable once created)
    - Model-specific variations
    - Environment-based deployment with fallback
    - Runtime metrics tracking
    - Dynamic variable substitution
    
    Storage Structure:
        .prompts/
            greeting.json
            code_review.json
    
    Usage:
        registry = LocalPromptRegistry(storage_path=".prompts")
        
        # Save prompt
        prompt_id = await registry.save_prompt(
            label="greeting",
            content="Hello, I am {name}!",
            metadata=PromptMetadata(model_target="gpt-4")
        )
        
        # Get prompt
        result = await registry.get_prompt_with_fallback(
            "greeting",
            variables={"name": "Assistant"}
        )
        
        # Record usage
        await registry.record_usage(prompt_id, latency_ms=150)
    """
    
    def __init__(
        self,
        storage_path: str = DEFAULT_STORAGE_PATH,
        format: str = "json",
        storage: Optional[IPromptStorage] = None,
        validator: Optional[IPromptValidator] = None,
        security: Optional[IPromptSecurity] = None,
    ):
        """
        Initialize local registry.
        
        Args:
            storage_path: Directory path for storing prompts
            format: Storage format ("json" or "yaml")
            storage: Custom storage implementation (overrides storage_path/format)
            validator: Validator for content/variable validation
            security: Security implementation for access control
        """
        # Use provided storage or create default local file storage
        if storage is not None:
            self.storage = storage
        else:
            self.storage = LocalFileStorage(storage_path, format=format)
        
        self.validator = validator
        self.security = security
        self._prompt_id_cache: Dict[str, str] = {}
