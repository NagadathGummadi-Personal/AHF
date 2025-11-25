"""
Local File Storage for Prompts.

Provides file-system based storage for prompt entries.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..interfaces.prompt_registry_interfaces import IPromptStorage
from ..constants import (
    DEFAULT_STORAGE_PATH,
    JSON_EXTENSION,
    UTF_8,
)


class LocalFileStorage(IPromptStorage):
    """
    Local file-system based prompt storage.
    
    Stores each prompt as a separate JSON file in the storage directory.
    
    Usage:
        storage = LocalFileStorage(storage_path=".prompts")
        
        await storage.save("greeting", {"content": "Hello!"})
        data = await storage.load("greeting")
        await storage.delete("greeting")
    """
    
    def __init__(self, storage_path: str = DEFAULT_STORAGE_PATH):
        """
        Initialize local storage.
        
        Args:
            storage_path: Directory path for storing prompts
        """
        self.storage_path = Path(storage_path)
        self._ensure_directory()
    
    def _ensure_directory(self) -> None:
        """Ensure storage directory exists."""
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    def _get_file_path(self, key: str) -> Path:
        """Get file path for a key."""
        # Sanitize key for filename
        safe_key = key.replace("/", "_").replace("\\", "_")
        return self.storage_path / f"{safe_key}{JSON_EXTENSION}"
    
    async def save(self, key: str, data: Dict[str, Any]) -> None:
        """Save data to storage."""
        file_path = self._get_file_path(key)
        
        with open(file_path, "w", encoding=UTF_8) as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    async def load(self, key: str) -> Optional[Dict[str, Any]]:
        """Load data from storage."""
        file_path = self._get_file_path(key)
        
        if not file_path.exists():
            return None
        
        with open(file_path, "r", encoding=UTF_8) as f:
            return json.load(f)
    
    async def delete(self, key: str) -> None:
        """Delete data from storage."""
        file_path = self._get_file_path(key)
        
        if file_path.exists():
            file_path.unlink()
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in storage."""
        file_path = self._get_file_path(key)
        return file_path.exists()
    
    async def list_keys(self, prefix: Optional[str] = None) -> List[str]:
        """List all keys in storage."""
        keys = []
        
        for file_path in self.storage_path.glob(f"*{JSON_EXTENSION}"):
            key = file_path.stem
            if prefix is None or key.startswith(prefix):
                keys.append(key)
        
        return sorted(keys)

