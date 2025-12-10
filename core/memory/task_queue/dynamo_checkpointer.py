"""
DynamoDB Checkpointer Implementation.

Production-grade checkpointer using DynamoDB with:
- Built-in TTL for automatic expiration
- No WAL needed (DynamoDB is durable)
- Local fallback for development

Version: 1.0.0
"""

import asyncio
import json
import time
from collections import OrderedDict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base_checkpointer import BaseCheckpointer


# Default TTL settings
DEFAULT_TTL_DAYS = 1
MAX_TTL_DAYS = 10


class DynamoDBCheckpointer(BaseCheckpointer):
    """
    DynamoDB-based checkpointer for production use.
    
    Features:
    - Automatic TTL-based expiration (1-10 days)
    - No WAL needed (DynamoDB provides durability)
    - In-memory cache for fast reads
    - Local file fallback for development (when DynamoDB unavailable)
    
    DynamoDB Table Schema:
    - Partition Key: session_id (String)
    - Sort Key: checkpoint_id (String)
    - Attributes: state (Map), metadata (Map), timestamp (String), ttl (Number)
    
    Usage:
        # Production with DynamoDB
        checkpointer = DynamoDBCheckpointer(
            table_name="workflow_checkpoints",
            session_id="session-123",
            ttl_days=1,
        )
        
        # Development with local fallback
        checkpointer = DynamoDBCheckpointer(
            session_id="session-123",
            use_local_fallback=True,
            local_path=".checkpoints",
        )
    """
    
    def __init__(
        self,
        session_id: str,
        table_name: str = "ahf_workflow_checkpoints",
        ttl_days: int = DEFAULT_TTL_DAYS,
        region_name: str = "us-east-1",
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        endpoint_url: Optional[str] = None,  # For local DynamoDB
        use_local_fallback: bool = False,
        local_path: str = ".checkpoints",
        cache_max_size: int = 100,
    ):
        """
        Initialize DynamoDB checkpointer.
        
        Args:
            session_id: Session identifier (partition key)
            table_name: DynamoDB table name
            ttl_days: Days before checkpoint expires (1-10)
            region_name: AWS region
            aws_access_key_id: Optional AWS key (uses env/role if not provided)
            aws_secret_access_key: Optional AWS secret
            endpoint_url: Optional endpoint for local DynamoDB
            use_local_fallback: Use local file storage if DynamoDB unavailable
            local_path: Path for local fallback storage
            cache_max_size: Max checkpoints in memory cache
        """
        # DynamoDB doesn't need WAL - it's already durable
        super().__init__(
            cache_max_size=cache_max_size,
            batch_size=1,  # Immediate writes for DynamoDB
            batch_timeout_ms=0,
            wal_enabled=False,  # No WAL needed
        )
        
        self._session_id = session_id
        self._table_name = table_name
        self._ttl_days = min(max(ttl_days, 1), MAX_TTL_DAYS)  # Clamp to 1-10
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
        """
        Ensure DynamoDB client is initialized.
        
        Returns:
            True if DynamoDB is available, False if using local fallback
        """
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
            
        except Exception as e:
            if self._use_local_fallback:
                self._using_local = True
                self._client_initialized = True
                self._local_path.mkdir(parents=True, exist_ok=True)
                return False
            else:
                raise RuntimeError(f"Failed to connect to DynamoDB: {e}")
    
    def _get_ttl_timestamp(self) -> int:
        """Get TTL timestamp (Unix epoch) for expiration."""
        expire_at = datetime.utcnow() + timedelta(days=self._ttl_days)
        return int(expire_at.timestamp())
    
    def _get_local_path(self, checkpoint_id: str) -> Path:
        """Get local file path for checkpoint."""
        session_dir = self._local_path / self._session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir / f"{checkpoint_id}.json"
    
    # =========================================================================
    # Override Abstract Methods
    # =========================================================================
    
    async def _persist_checkpoint(
        self,
        checkpoint_id: str,
        data: Dict[str, Any],
    ) -> None:
        """Persist checkpoint to DynamoDB or local storage."""
        await self._ensure_client()
        
        if self._using_local:
            await self._persist_local(checkpoint_id, data)
        else:
            await self._persist_dynamodb(checkpoint_id, data)
    
    async def _persist_dynamodb(
        self,
        checkpoint_id: str,
        data: Dict[str, Any],
    ) -> None:
        """Persist to DynamoDB."""
        try:
            item = {
                'session_id': self._session_id,
                'checkpoint_id': checkpoint_id,
                'state': data.get('state', {}),
                'metadata': data.get('metadata', {}),
                'timestamp': data.get('timestamp', datetime.utcnow().isoformat()),
                'ttl': self._get_ttl_timestamp(),
            }
            
            # Run in executor to not block
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: self._table.put_item(Item=item))
            
        except Exception as e:
            # Log error in production
            if self._use_local_fallback:
                await self._persist_local(checkpoint_id, data)
    
    async def _persist_local(
        self,
        checkpoint_id: str,
        data: Dict[str, Any],
    ) -> None:
        """Persist to local file (fallback)."""
        try:
            file_path = self._get_local_path(checkpoint_id)
            
            # Add TTL for local cleanup
            data_with_ttl = {
                **data,
                '_ttl': self._get_ttl_timestamp(),
                '_created': datetime.utcnow().isoformat(),
            }
            
            with open(file_path, 'w') as f:
                json.dump(data_with_ttl, f, indent=2, default=str)
                
        except Exception:
            pass  # Log in production
    
    async def _load_checkpoint(
        self,
        checkpoint_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Load checkpoint from DynamoDB or local storage."""
        await self._ensure_client()
        
        if self._using_local:
            return await self._load_local(checkpoint_id)
        else:
            return await self._load_dynamodb(checkpoint_id)
    
    async def _load_dynamodb(
        self,
        checkpoint_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Load from DynamoDB."""
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._table.get_item(
                    Key={
                        'session_id': self._session_id,
                        'checkpoint_id': checkpoint_id,
                    }
                )
            )
            
            item = response.get('Item')
            if not item:
                return None
            
            return {
                'state': item.get('state', {}),
                'metadata': item.get('metadata', {}),
                'timestamp': item.get('timestamp'),
            }
            
        except Exception:
            if self._use_local_fallback:
                return await self._load_local(checkpoint_id)
            return None
    
    async def _load_local(
        self,
        checkpoint_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Load from local file."""
        try:
            file_path = self._get_local_path(checkpoint_id)
            
            if not file_path.exists():
                return None
            
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Check TTL
            ttl = data.get('_ttl', 0)
            if ttl and ttl < time.time():
                # Expired - delete and return None
                file_path.unlink()
                return None
            
            # Remove internal fields
            data.pop('_ttl', None)
            data.pop('_created', None)
            
            return data
            
        except Exception:
            return None
    
    async def _delete_persisted_checkpoint(
        self,
        checkpoint_id: str,
    ) -> bool:
        """Delete checkpoint from storage."""
        await self._ensure_client()
        
        if self._using_local:
            return await self._delete_local(checkpoint_id)
        else:
            return await self._delete_dynamodb(checkpoint_id)
    
    async def _delete_dynamodb(
        self,
        checkpoint_id: str,
    ) -> bool:
        """Delete from DynamoDB."""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._table.delete_item(
                    Key={
                        'session_id': self._session_id,
                        'checkpoint_id': checkpoint_id,
                    }
                )
            )
            return True
        except Exception:
            return False
    
    async def _delete_local(
        self,
        checkpoint_id: str,
    ) -> bool:
        """Delete from local file."""
        try:
            file_path = self._get_local_path(checkpoint_id)
            if file_path.exists():
                file_path.unlink()
                return True
            return False
        except Exception:
            return False
    
    async def _list_persisted_checkpoints(self) -> List[str]:
        """List all checkpoint IDs for this session."""
        await self._ensure_client()
        
        if self._using_local:
            return await self._list_local()
        else:
            return await self._list_dynamodb()
    
    async def _list_dynamodb(self) -> List[str]:
        """List from DynamoDB."""
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._table.query(
                    KeyConditionExpression='session_id = :sid',
                    ExpressionAttributeValues={':sid': self._session_id},
                    ProjectionExpression='checkpoint_id,#ts',
                    ExpressionAttributeNames={'#ts': 'timestamp'},
                    ScanIndexForward=False,  # Newest first
                )
            )
            
            items = response.get('Items', [])
            return [item['checkpoint_id'] for item in items]
            
        except Exception:
            if self._use_local_fallback:
                return await self._list_local()
            return []
    
    async def _list_local(self) -> List[str]:
        """List from local files."""
        try:
            session_dir = self._local_path / self._session_id
            if not session_dir.exists():
                return []
            
            checkpoints = []
            for f in sorted(session_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
                checkpoints.append(f.stem)
            
            return checkpoints
            
        except Exception:
            return []
    
    async def _write_wal_entries(
        self,
        entries: List[Dict[str, Any]],
    ) -> None:
        """WAL not used for DynamoDB - writes are durable."""
        # DynamoDB is already durable, no WAL needed
        pass
    
    async def _recover_from_wal(self) -> None:
        """WAL not used for DynamoDB."""
        # No WAL to recover from
        # Just load existing checkpoints into cache
        checkpoint_ids = await self._list_persisted_checkpoints()
        for cp_id in checkpoint_ids[:self._cache_max_size]:
            if cp_id not in self._checkpoint_order:
                self._checkpoint_order.append(cp_id)
    
    # =========================================================================
    # Additional Methods
    # =========================================================================
    
    async def cleanup_expired_local(self) -> int:
        """
        Clean up expired local checkpoints.
        
        Call periodically if using local fallback.
        
        Returns:
            Number of deleted checkpoints
        """
        if not self._using_local:
            return 0
        
        deleted = 0
        try:
            session_dir = self._local_path / self._session_id
            if not session_dir.exists():
                return 0
            
            current_time = time.time()
            
            for f in session_dir.glob("*.json"):
                try:
                    with open(f, 'r') as fp:
                        data = json.load(fp)
                    
                    ttl = data.get('_ttl', 0)
                    if ttl and ttl < current_time:
                        f.unlink()
                        deleted += 1
                        
                except Exception:
                    pass
                    
        except Exception:
            pass
        
        return deleted
    
    async def delete_session_checkpoints(self) -> int:
        """
        Delete all checkpoints for this session.
        
        Returns:
            Number of deleted checkpoints
        """
        await self._ensure_client()
        
        checkpoint_ids = await self._list_persisted_checkpoints()
        deleted = 0
        
        for cp_id in checkpoint_ids:
            if await self._delete_persisted_checkpoint(cp_id):
                deleted += 1
            
            # Remove from cache
            if cp_id in self._cache:
                del self._cache[cp_id]
            if cp_id in self._checkpoint_order:
                self._checkpoint_order.remove(cp_id)
        
        return deleted
    
    @property
    def ttl_days(self) -> int:
        """Get current TTL setting."""
        return self._ttl_days
    
    @property
    def is_using_local(self) -> bool:
        """Check if using local fallback."""
        return self._using_local


# =============================================================================
# Factory Function
# =============================================================================

def create_dynamodb_checkpointer(
    session_id: str,
    table_name: str = "ahf_workflow_checkpoints",
    ttl_days: int = DEFAULT_TTL_DAYS,
    use_local_fallback: bool = True,
    **kwargs,
) -> DynamoDBCheckpointer:
    """
    Create a DynamoDB checkpointer with sensible defaults.
    
    Args:
        session_id: Session identifier
        table_name: DynamoDB table name
        ttl_days: Checkpoint TTL (1-10 days, default 1)
        use_local_fallback: Fall back to local storage if DynamoDB unavailable
        **kwargs: Additional DynamoDBCheckpointer arguments
        
    Returns:
        Configured DynamoDBCheckpointer
    """
    return DynamoDBCheckpointer(
        session_id=session_id,
        table_name=table_name,
        ttl_days=ttl_days,
        use_local_fallback=use_local_fallback,
        **kwargs,
    )


# =============================================================================
# DynamoDB Table Creation Helper
# =============================================================================

DYNAMODB_TABLE_SCHEMA = {
    "TableName": "ahf_workflow_checkpoints",
    "KeySchema": [
        {"AttributeName": "session_id", "KeyType": "HASH"},
        {"AttributeName": "checkpoint_id", "KeyType": "RANGE"},
    ],
    "AttributeDefinitions": [
        {"AttributeName": "session_id", "AttributeType": "S"},
        {"AttributeName": "checkpoint_id", "AttributeType": "S"},
    ],
    "BillingMode": "PAY_PER_REQUEST",
    "TimeToLiveSpecification": {
        "Enabled": True,
        "AttributeName": "ttl",
    },
}


async def create_table_if_not_exists(
    table_name: str = "ahf_workflow_checkpoints",
    region_name: str = "us-east-1",
    **boto_kwargs,
) -> bool:
    """
    Create DynamoDB table if it doesn't exist.
    
    Run this during deployment or first-time setup.
    
    Args:
        table_name: Table name
        region_name: AWS region
        **boto_kwargs: Additional boto3 arguments
        
    Returns:
        True if table was created or exists
    """
    try:
        import boto3
        
        dynamodb = boto3.resource('dynamodb', region_name=region_name, **boto_kwargs)
        
        # Check if table exists
        existing_tables = [t.name for t in dynamodb.tables.all()]
        if table_name in existing_tables:
            return True
        
        # Create table
        schema = DYNAMODB_TABLE_SCHEMA.copy()
        schema["TableName"] = table_name
        
        table = dynamodb.create_table(**schema)
        table.wait_until_exists()
        
        return True
        
    except Exception as e:
        print(f"Failed to create table: {e}")
        return False

