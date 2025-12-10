"""
Base Checkpointer Implementation.

Abstract base class for lazy checkpointing with WAL support.

Version: 1.0.0
"""

from abc import ABC, abstractmethod
import asyncio
from collections import OrderedDict
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..interfaces import ICheckpointer


class BaseCheckpointer(ABC):
    """
    Abstract base class for checkpointers.
    
    Provides lazy checkpointing with Write-Ahead Log (WAL)
    for minimal latency impact.
    
    Design:
    - save_checkpoint() returns immediately (O(1))
    - Data is cached in memory
    - Background task persists to WAL
    - Batched writes for efficiency
    
    Extend this class to create custom checkpointer implementations
    (e.g., S3-backed, database-backed).
    
    Example:
        class S3Checkpointer(BaseCheckpointer):
            def __init__(self, bucket):
                super().__init__()
                self.bucket = bucket
            
            async def _persist_checkpoint(self, checkpoint_id, data):
                await self.s3.put_object(
                    Bucket=self.bucket,
                    Key=f"checkpoints/{checkpoint_id}.json",
                    Body=json.dumps(data)
                )
    """
    
    def __init__(
        self,
        cache_max_size: int = 1000,
        batch_size: int = 10,
        batch_timeout_ms: int = 100,
        wal_enabled: bool = True,
    ):
        """
        Initialize checkpointer.
        
        Args:
            cache_max_size: Maximum checkpoints in cache
            batch_size: Batch size for writes
            batch_timeout_ms: Max wait before flushing batch
            wal_enabled: Whether to use Write-Ahead Log
        """
        self._cache_max_size = cache_max_size
        self._batch_size = batch_size
        self._batch_timeout_ms = batch_timeout_ms
        self._wal_enabled = wal_enabled
        
        # In-memory cache (LRU-style with OrderedDict)
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        
        # Checkpoint order tracking
        self._checkpoint_order: List[str] = []
        
        # WAL buffer
        self._wal_buffer: List[Dict[str, Any]] = []
        self._wal_lock = asyncio.Lock()
        
        # Background task
        self._flush_task: Optional[asyncio.Task] = None
        self._running = False
    
    # =========================================================================
    # Abstract Methods - Must be implemented by subclasses
    # =========================================================================
    
    @abstractmethod
    async def _persist_checkpoint(
        self,
        checkpoint_id: str,
        data: Dict[str, Any],
    ) -> None:
        """Persist a checkpoint to storage."""
        ...
    
    @abstractmethod
    async def _load_checkpoint(
        self,
        checkpoint_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Load a checkpoint from storage."""
        ...
    
    @abstractmethod
    async def _delete_persisted_checkpoint(
        self,
        checkpoint_id: str,
    ) -> bool:
        """Delete a checkpoint from storage."""
        ...
    
    @abstractmethod
    async def _list_persisted_checkpoints(self) -> List[str]:
        """List all persisted checkpoint IDs."""
        ...
    
    @abstractmethod
    async def _write_wal_entries(
        self,
        entries: List[Dict[str, Any]],
    ) -> None:
        """Write entries to WAL."""
        ...
    
    @abstractmethod
    async def _recover_from_wal(self) -> None:
        """Recover checkpoints from WAL on startup."""
        ...
    
    # =========================================================================
    # ICheckpointer Implementation
    # =========================================================================
    
    async def save_checkpoint(
        self,
        checkpoint_id: str,
        state: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Save a checkpoint. Returns immediately."""
        # Add to cache immediately (O(1))
        checkpoint_data = {
            "state": state,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        # Move to end for LRU behavior
        if checkpoint_id in self._cache:
            self._cache.move_to_end(checkpoint_id)
        
        self._cache[checkpoint_id] = checkpoint_data
        
        # Track order
        if checkpoint_id not in self._checkpoint_order:
            self._checkpoint_order.append(checkpoint_id)
        
        # Trim cache if needed
        while len(self._cache) > self._cache_max_size:
            oldest_id = next(iter(self._cache))
            del self._cache[oldest_id]
            if oldest_id in self._checkpoint_order:
                self._checkpoint_order.remove(oldest_id)
        
        # Add to WAL buffer (non-blocking)
        if self._wal_enabled:
            async with self._wal_lock:
                self._wal_buffer.append({
                    "checkpoint_id": checkpoint_id,
                    **checkpoint_data,
                })
        
        return checkpoint_id
    
    async def get_checkpoint(
        self,
        checkpoint_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get a checkpoint by ID."""
        # Check cache first
        if checkpoint_id in self._cache:
            return self._cache[checkpoint_id]
        
        # Try to load from storage
        data = await self._load_checkpoint(checkpoint_id)
        if data:
            # Add to cache
            self._cache[checkpoint_id] = data
            return data
        
        return None
    
    async def get_latest_checkpoint(self) -> Optional[Dict[str, Any]]:
        """Get the most recent checkpoint."""
        if self._checkpoint_order:
            latest_id = self._checkpoint_order[-1]
            return await self.get_checkpoint(latest_id)
        
        # Fall back to storage
        persisted = await self._list_persisted_checkpoints()
        if persisted:
            return await self.get_checkpoint(persisted[-1])
        
        return None
    
    async def list_checkpoints(
        self,
        limit: Optional[int] = None,
    ) -> List[str]:
        """List checkpoint IDs (newest first)."""
        ids = list(reversed(self._checkpoint_order))
        if limit:
            ids = ids[:limit]
        return ids
    
    async def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """Delete a checkpoint."""
        deleted = False
        
        # Remove from cache
        if checkpoint_id in self._cache:
            del self._cache[checkpoint_id]
            deleted = True
        
        # Remove from order
        if checkpoint_id in self._checkpoint_order:
            self._checkpoint_order.remove(checkpoint_id)
        
        # Remove from storage
        if await self._delete_persisted_checkpoint(checkpoint_id):
            deleted = True
        
        return deleted
    
    async def flush(self) -> None:
        """Force flush pending writes to storage."""
        async with self._wal_lock:
            if self._wal_buffer:
                await self._write_wal_entries(self._wal_buffer)
                self._wal_buffer.clear()
            
            # Persist all cached checkpoints
            for checkpoint_id, data in self._cache.items():
                await self._persist_checkpoint(checkpoint_id, data)
    
    async def close(self) -> None:
        """Close the checkpointer."""
        self._running = False
        
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        
        # Final flush
        await self.flush()
    
    # =========================================================================
    # Lifecycle Methods
    # =========================================================================
    
    async def start(self) -> None:
        """Start the checkpointer (background tasks)."""
        if self._running:
            return
        
        self._running = True
        
        # Recover from WAL
        await self._recover_from_wal()
        
        # Start background flusher
        if self._wal_enabled:
            self._flush_task = asyncio.create_task(self._background_flush())
    
    async def _background_flush(self) -> None:
        """Background task that flushes WAL buffer periodically."""
        while self._running:
            try:
                await asyncio.sleep(self._batch_timeout_ms / 1000)
                
                async with self._wal_lock:
                    if self._wal_buffer and len(self._wal_buffer) >= self._batch_size:
                        await self._write_wal_entries(self._wal_buffer)
                        self._wal_buffer.clear()
                
            except asyncio.CancelledError:
                break
            except Exception:
                pass  # Log error in production

