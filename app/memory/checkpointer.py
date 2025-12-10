"""
Voice Agent Checkpointer

Custom lazy checkpointer for the voice agent workflow.
Extends BaseCheckpointer from core.memory.

Version: 1.0.0
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.memory import BaseCheckpointer


class VoiceAgentCheckpointer(BaseCheckpointer):
    """
    Voice agent-specific checkpointer.
    
    Extends BaseCheckpointer with:
    - Local file-based persistence
    - JSON-based WAL
    
    In production, override methods for S3/database persistence.
    """
    
    def __init__(
        self,
        storage_path: str = ".checkpoints",
        cache_max_size: int = 1000,
        batch_size: int = 10,
        batch_timeout_ms: int = 100,
        wal_enabled: bool = True,
    ):
        """
        Initialize checkpointer.
        
        Args:
            storage_path: Directory for checkpoint storage
            cache_max_size: Maximum checkpoints in cache
            batch_size: Batch size for writes
            batch_timeout_ms: Max wait before flushing batch
            wal_enabled: Whether to use Write-Ahead Log
        """
        super().__init__(
            cache_max_size=cache_max_size,
            batch_size=batch_size,
            batch_timeout_ms=batch_timeout_ms,
            wal_enabled=wal_enabled,
        )
        
        self._storage_path = Path(storage_path)
        self._storage_path.mkdir(parents=True, exist_ok=True)
        
        self._checkpoints_dir = self._storage_path / "checkpoints"
        self._checkpoints_dir.mkdir(exist_ok=True)
        
        self._wal_file = self._storage_path / "wal.jsonl"
    
    # =========================================================================
    # Override Abstract Methods
    # =========================================================================
    
    async def _persist_checkpoint(
        self,
        checkpoint_id: str,
        data: Dict[str, Any],
    ) -> None:
        """Persist checkpoint to local file."""
        checkpoint_file = self._checkpoints_dir / f"{checkpoint_id}.json"
        try:
            with open(checkpoint_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass  # Log in production
    
    async def _load_checkpoint(
        self,
        checkpoint_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Load checkpoint from local file."""
        checkpoint_file = self._checkpoints_dir / f"{checkpoint_id}.json"
        if checkpoint_file.exists():
            try:
                with open(checkpoint_file, "r") as f:
                    return json.load(f)
            except Exception:
                return None
        return None
    
    async def _delete_persisted_checkpoint(
        self,
        checkpoint_id: str,
    ) -> bool:
        """Delete checkpoint file."""
        checkpoint_file = self._checkpoints_dir / f"{checkpoint_id}.json"
        if checkpoint_file.exists():
            checkpoint_file.unlink()
            return True
        return False
    
    async def _list_persisted_checkpoints(self) -> List[str]:
        """List all persisted checkpoint IDs."""
        checkpoints = []
        for f in sorted(
            self._checkpoints_dir.glob("*.json"),
            key=lambda x: x.stat().st_mtime,
        ):
            checkpoints.append(f.stem)
        return checkpoints
    
    async def _write_wal_entries(
        self,
        entries: List[Dict[str, Any]],
    ) -> None:
        """Write entries to WAL file."""
        try:
            with open(self._wal_file, "a") as f:
                for entry in entries:
                    f.write(json.dumps(entry) + "\n")
                f.flush()
                os.fsync(f.fileno())
        except Exception:
            pass  # Log in production
    
    async def _recover_from_wal(self) -> None:
        """Recover checkpoints from WAL on startup."""
        if not self._wal_file.exists():
            return
        
        try:
            with open(self._wal_file, "r") as f:
                for line in f:
                    if line.strip():
                        entry = json.loads(line)
                        checkpoint_id = entry.pop("checkpoint_id")
                        self._cache[checkpoint_id] = entry
                        
                        if checkpoint_id not in self._checkpoint_order:
                            self._checkpoint_order.append(checkpoint_id)
            
            # Compact WAL after recovery
            await self._compact_wal()
            
        except Exception:
            pass  # Log in production
    
    async def _compact_wal(self) -> None:
        """Compact WAL by persisting all checkpoints and clearing WAL."""
        # Persist all cached checkpoints
        for checkpoint_id, data in self._cache.items():
            await self._persist_checkpoint(checkpoint_id, data)
        
        # Clear WAL
        if self._wal_file.exists():
            self._wal_file.unlink()
