"""
DynamoDB Metrics Store.

Production-grade metrics storage using DynamoDB with:
- Built-in TTL for automatic expiration
- Local file fallback for development
- In-memory caching for fast reads

Version: 1.0.0
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base_metrics_store import BaseMetricsStore


# Default TTL settings
DEFAULT_TTL_DAYS = 30
MAX_TTL_DAYS = 365


class DynamoDBMetricsStore(BaseMetricsStore):
    """
    DynamoDB-based metrics store for production use.
    
    Features:
    - Automatic TTL-based expiration (1-365 days)
    - In-memory cache for fast reads
    - Local file fallback for development
    
    DynamoDB Table Schema:
    - Partition Key: entity_id (String)
    - Sort Key: entry_id (String)
    - Attributes: entity_type, metric_type, scores, metadata, timestamp, ttl
    
    Usage:
        # Production with DynamoDB
        store = DynamoDBMetricsStore(
            table_name="ahf_metrics",
            ttl_days=30,
        )
        
        # Development with local fallback
        store = DynamoDBMetricsStore(
            use_local_fallback=True,
            local_path=".metrics",
        )
    """
    
    def __init__(
        self,
        table_name: str = "ahf_metrics",
        ttl_days: int = DEFAULT_TTL_DAYS,
        region_name: str = "us-east-1",
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        use_local_fallback: bool = True,
        local_path: str = ".metrics",
        cache_max_entries: int = 10000,
        max_samples_per_entity: int = 1000,
    ):
        """
        Initialize DynamoDB metrics store.
        
        Args:
            table_name: DynamoDB table name
            ttl_days: Days before entries expire (1-365)
            region_name: AWS region
            aws_access_key_id: Optional AWS key
            aws_secret_access_key: Optional AWS secret
            endpoint_url: Optional endpoint for local DynamoDB
            use_local_fallback: Use local file storage if DynamoDB unavailable
            local_path: Path for local fallback storage
            cache_max_entries: Max entries in memory cache
            max_samples_per_entity: Max samples per entity
        """
        super().__init__(
            cache_max_entries=cache_max_entries,
            max_samples_per_entity=max_samples_per_entity,
        )
        
        self._table_name = table_name
        self._ttl_days = min(max(ttl_days, 1), MAX_TTL_DAYS)
        self._region_name = region_name
        self._endpoint_url = endpoint_url
        self._use_local_fallback = use_local_fallback
        self._local_path = Path(local_path)
        
        # AWS credentials
        self._aws_access_key_id = aws_access_key_id
        self._aws_secret_access_key = aws_secret_access_key
        
        # DynamoDB client (lazy init)
        self._dynamodb = None
        self._table = None
        self._client_initialized = False
        self._using_local = False
    
    async def _ensure_client(self) -> bool:
        """Ensure DynamoDB client is initialized."""
        if self._client_initialized:
            return not self._using_local
        
        try:
            import boto3
            from botocore.config import Config
            
            config = Config(
                retries={'max_attempts': 3, 'mode': 'adaptive'},
                connect_timeout=5,
                read_timeout=10,
            )
            
            session_kwargs = {}
            if self._aws_access_key_id and self._aws_secret_access_key:
                session_kwargs['aws_access_key_id'] = self._aws_access_key_id
                session_kwargs['aws_secret_access_key'] = self._aws_secret_access_key
            
            session = boto3.Session(**session_kwargs)
            
            dynamodb_kwargs = {
                'region_name': self._region_name,
                'config': config,
            }
            if self._endpoint_url:
                dynamodb_kwargs['endpoint_url'] = self._endpoint_url
            
            self._dynamodb = session.resource('dynamodb', **dynamodb_kwargs)
            self._table = self._dynamodb.Table(self._table_name)
            
            # Test connection
            self._table.table_status
            
            self._client_initialized = True
            self._using_local = False
            return True
            
        except Exception:
            if self._use_local_fallback:
                self._using_local = True
                self._client_initialized = True
                self._local_path.mkdir(parents=True, exist_ok=True)
                return False
            else:
                raise
    
    def _get_ttl_timestamp(self) -> int:
        """Get TTL timestamp (Unix epoch) for expiration."""
        expire_at = datetime.utcnow() + timedelta(days=self._ttl_days)
        return int(expire_at.timestamp())
    
    def _get_local_path(self, entity_id: str) -> Path:
        """Get local file path for entity metrics."""
        safe_id = entity_id.replace("/", "_").replace("\\", "_").replace(":", "_")
        return self._local_path / f"{safe_id}.json"
    
    async def _persist_entry(self, entry: Dict[str, Any]) -> None:
        """Persist a single entry."""
        await self._ensure_client()
        
        if self._using_local:
            await self._persist_local(entry)
        else:
            await self._persist_dynamodb(entry)
    
    async def _persist_dynamodb(self, entry: Dict[str, Any]) -> None:
        """Persist to DynamoDB."""
        try:
            item = {
                'entity_id': entry['entity_id'],
                'entry_id': entry['id'],
                'entity_type': entry['entity_type'],
                'metric_type': entry['metric_type'],
                'scores': entry['scores'],
                'metadata': entry.get('metadata', {}),
                'timestamp': entry['timestamp'],
                'ttl': self._get_ttl_timestamp(),
            }
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: self._table.put_item(Item=item))
            
        except Exception:
            if self._use_local_fallback:
                await self._persist_local(entry)
    
    async def _persist_local(self, entry: Dict[str, Any]) -> None:
        """Persist to local file."""
        try:
            entity_id = entry['entity_id']
            file_path = self._get_local_path(entity_id)
            
            # Load existing entries
            entries = []
            if file_path.exists():
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    entries = data.get('entries', [])
            
            # Add new entry
            entry_with_ttl = {
                **entry,
                '_ttl': self._get_ttl_timestamp(),
            }
            entries.append(entry_with_ttl)
            
            # Save
            with open(file_path, 'w') as f:
                json.dump({'entries': entries}, f, indent=2, default=str)
                
        except Exception:
            pass  # Log in production
    
    async def _load_entries(self, entity_id: str) -> List[Dict[str, Any]]:
        """Load entries from persistence."""
        await self._ensure_client()
        
        if self._using_local:
            return await self._load_local(entity_id)
        else:
            return await self._load_dynamodb(entity_id)
    
    async def _load_dynamodb(self, entity_id: str) -> List[Dict[str, Any]]:
        """Load from DynamoDB."""
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._table.query(
                    KeyConditionExpression='entity_id = :eid',
                    ExpressionAttributeValues={':eid': entity_id},
                    ScanIndexForward=False,  # Newest first
                )
            )
            
            items = response.get('Items', [])
            
            return [
                {
                    'id': item.get('entry_id'),
                    'entity_id': item.get('entity_id'),
                    'entity_type': item.get('entity_type'),
                    'metric_type': item.get('metric_type'),
                    'scores': item.get('scores', {}),
                    'metadata': item.get('metadata', {}),
                    'timestamp': item.get('timestamp'),
                }
                for item in items
            ]
            
        except Exception:
            if self._use_local_fallback:
                return await self._load_local(entity_id)
            return []
    
    async def _load_local(self, entity_id: str) -> List[Dict[str, Any]]:
        """Load from local file."""
        try:
            file_path = self._get_local_path(entity_id)
            
            if not file_path.exists():
                return []
            
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            entries = data.get('entries', [])
            current_time = time.time()
            
            # Filter out expired entries
            valid_entries = []
            for entry in entries:
                ttl = entry.get('_ttl', 0)
                if not ttl or ttl >= current_time:
                    # Remove internal fields
                    entry_copy = {k: v for k, v in entry.items() if not k.startswith('_')}
                    valid_entries.append(entry_copy)
            
            return valid_entries
            
        except Exception:
            return []
    
    async def _delete_persisted(
        self,
        entity_id: str,
        older_than_days: Optional[int] = None,
    ) -> None:
        """Delete from persistence."""
        await self._ensure_client()
        
        if self._using_local:
            await self._delete_local(entity_id, older_than_days)
        else:
            await self._delete_dynamodb(entity_id, older_than_days)
    
    async def _delete_dynamodb(
        self,
        entity_id: str,
        older_than_days: Optional[int] = None,
    ) -> None:
        """Delete from DynamoDB."""
        try:
            # Load all entries first
            entries = await self._load_dynamodb(entity_id)
            
            if older_than_days is not None:
                cutoff = (datetime.utcnow() - timedelta(days=older_than_days)).isoformat()
                entries = [e for e in entries if e.get('timestamp', '') < cutoff]
            
            # Delete matching entries
            loop = asyncio.get_event_loop()
            for entry in entries:
                await loop.run_in_executor(
                    None,
                    lambda eid=entry['id']: self._table.delete_item(
                        Key={'entity_id': entity_id, 'entry_id': eid}
                    )
                )
                
        except Exception:
            pass
    
    async def _delete_local(
        self,
        entity_id: str,
        older_than_days: Optional[int] = None,
    ) -> None:
        """Delete from local file."""
        try:
            file_path = self._get_local_path(entity_id)
            
            if not file_path.exists():
                return
            
            if older_than_days is None:
                # Delete entire file
                file_path.unlink()
            else:
                # Filter entries
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                cutoff = (datetime.utcnow() - timedelta(days=older_than_days)).isoformat()
                entries = [
                    e for e in data.get('entries', [])
                    if e.get('timestamp', '') >= cutoff
                ]
                
                if entries:
                    with open(file_path, 'w') as f:
                        json.dump({'entries': entries}, f, indent=2, default=str)
                else:
                    file_path.unlink()
                    
        except Exception:
            pass
    
    async def _clear_persisted(self) -> None:
        """Clear all persisted data."""
        if self._using_local:
            try:
                for f in self._local_path.glob("*.json"):
                    f.unlink()
            except Exception:
                pass
    
    @property
    def is_using_local(self) -> bool:
        """Check if using local fallback."""
        return self._using_local


# =============================================================================
# Factory Function
# =============================================================================

def create_metrics_store(
    store_type: str = "memory",
    **kwargs,
) -> BaseMetricsStore:
    """
    Create a metrics store instance.
    
    Args:
        store_type: "memory" or "dynamodb"
        **kwargs: Store-specific arguments
        
    Returns:
        Configured metrics store
    """
    if store_type == "dynamodb":
        return DynamoDBMetricsStore(**kwargs)
    else:
        from .memory_store import InMemoryMetricsStore
        return InMemoryMetricsStore(**kwargs)

