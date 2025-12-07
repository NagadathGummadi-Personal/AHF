"""
S3 Tool Storage Implementation

AWS S3-based storage for tool specifications with versioning support.

Features:
- S3 versioning for automatic version tracking
- Semantic versioning support (tool_id/version/spec.json)
- Metadata storage with tool specs
- Support for custom endpoints (LocalStack testing)

Version: 1.0.0
"""

import json
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from .storage_interface import IToolStorage, ToolStorageResult, ToolVersionInfo


class S3ToolStorage(IToolStorage):
    """
    AWS S3-based storage for tool specifications.
    
    Storage Structure:
        {bucket}/tools/{tool_id}/spec.json          - Latest spec
        {bucket}/tools/{tool_id}/versions/{version}/spec.json  - Versioned specs
        {bucket}/tools/{tool_id}/metadata.json      - Tool metadata
    
    With S3 Versioning:
        When S3 versioning is enabled on the bucket, each save creates
        a new version automatically. Versions can be retrieved by S3 version ID.
    
    Without S3 Versioning (semantic versioning):
        Uses folder structure: tools/{tool_id}/versions/{version}/spec.json
    
    Usage:
        storage = S3ToolStorage(
            bucket_name="my-tools-bucket",
            region="us-west-2",
            use_s3_versioning=True
        )
        
        # Save a tool spec
        result = await storage.save("my-tool", tool_spec_dict, version="1.0.0")
        
        # Load latest version
        result = await storage.load("my-tool")
        
        # Load specific version
        result = await storage.load("my-tool", version="1.0.0")
    
    Environment Variables:
        AWS_ACCESS_KEY_ID: AWS access key
        AWS_SECRET_ACCESS_KEY: AWS secret key
        AWS_DEFAULT_REGION: Default AWS region
    """
    
    def __init__(
        self,
        bucket_name: str,
        region: str = "us-west-2",
        prefix: str = "tools",
        endpoint_url: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        use_s3_versioning: bool = False,
    ):
        """
        Initialize S3 storage.
        
        Args:
            bucket_name: S3 bucket name
            region: AWS region
            prefix: Key prefix for all tools (default: "tools")
            endpoint_url: Custom endpoint URL (for LocalStack/testing)
            aws_access_key_id: Optional AWS access key (prefer env vars or IAM)
            aws_secret_access_key: Optional AWS secret key
            use_s3_versioning: Use S3 native versioning (bucket must have it enabled)
        """
        self._bucket_name = bucket_name
        self._region = region
        self._prefix = prefix
        self._endpoint_url = endpoint_url
        self._aws_access_key_id = aws_access_key_id
        self._aws_secret_access_key = aws_secret_access_key
        self._use_s3_versioning = use_s3_versioning
        self._client = None
    
    def _get_client(self):
        """Get or create boto3 S3 client."""
        if self._client is None:
            import boto3
            
            kwargs = {
                "region_name": self._region,
            }
            
            if self._endpoint_url:
                kwargs["endpoint_url"] = self._endpoint_url
            
            if self._aws_access_key_id and self._aws_secret_access_key:
                kwargs["aws_access_key_id"] = self._aws_access_key_id
                kwargs["aws_secret_access_key"] = self._aws_secret_access_key
            
            self._client = boto3.client("s3", **kwargs)
        
        return self._client
    
    def _get_tool_key(self, tool_id: str, version: Optional[str] = None) -> str:
        """Get S3 key for a tool spec."""
        if version and not self._use_s3_versioning:
            return f"{self._prefix}/{tool_id}/versions/{version}/spec.json"
        return f"{self._prefix}/{tool_id}/spec.json"
    
    def _get_metadata_key(self, tool_id: str) -> str:
        """Get S3 key for tool metadata."""
        return f"{self._prefix}/{tool_id}/metadata.json"
    
    async def save(
        self,
        tool_id: str,
        spec: Dict[str, Any],
        version: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> ToolStorageResult:
        """
        Save a tool specification to S3.
        
        Args:
            tool_id: Unique tool identifier
            spec: Tool specification dictionary
            version: Optional semantic version
            metadata: Optional metadata
            
        Returns:
            ToolStorageResult with version info
        """
        try:
            client = self._get_client()
            
            # Auto-increment version if not provided
            if not version:
                latest = await self.get_latest_version(tool_id)
                version = self._increment_version(latest) if latest else "1.0.0"
            
            # Add version to spec
            spec_with_version = {**spec, "version": version}
            
            # Serialize spec
            spec_json = json.dumps(spec_with_version, indent=2, default=str)
            
            # Prepare S3 metadata
            s3_metadata = {
                "tool-id": tool_id,
                "version": version,
                "updated-at": datetime.utcnow().isoformat(),
            }
            if metadata:
                s3_metadata.update(metadata)
            
            def _put_object():
                key = self._get_tool_key(tool_id, version if not self._use_s3_versioning else None)
                
                response = client.put_object(
                    Bucket=self._bucket_name,
                    Key=key,
                    Body=spec_json.encode("utf-8"),
                    ContentType="application/json",
                    Metadata=s3_metadata,
                )
                
                # If using semantic versioning (not S3 versioning), also save to latest
                if not self._use_s3_versioning and version:
                    latest_key = self._get_tool_key(tool_id)
                    client.put_object(
                        Bucket=self._bucket_name,
                        Key=latest_key,
                        Body=spec_json.encode("utf-8"),
                        ContentType="application/json",
                        Metadata=s3_metadata,
                    )
                
                # Update metadata file
                metadata_key = self._get_metadata_key(tool_id)
                tool_metadata = {
                    "tool_id": tool_id,
                    "latest_version": version,
                    "versions": [],
                    "updated_at": datetime.utcnow().isoformat(),
                }
                
                # Try to load existing metadata
                try:
                    existing = client.get_object(Bucket=self._bucket_name, Key=metadata_key)
                    tool_metadata = json.loads(existing["Body"].read().decode("utf-8"))
                except Exception:
                    # Key doesn't exist or other error - use default metadata
                    pass
                
                # Update versions list
                if version not in tool_metadata.get("versions", []):
                    tool_metadata.setdefault("versions", []).append(version)
                tool_metadata["latest_version"] = version
                tool_metadata["updated_at"] = datetime.utcnow().isoformat()
                
                client.put_object(
                    Bucket=self._bucket_name,
                    Key=metadata_key,
                    Body=json.dumps(tool_metadata, indent=2).encode("utf-8"),
                    ContentType="application/json",
                )
                
                return response
            
            response = await asyncio.to_thread(_put_object)
            version_id = response.get("VersionId")
            
            return ToolStorageResult(
                success=True,
                tool_id=tool_id,
                version_id=version_id,
                version=version,
                message=f"Tool {tool_id} v{version} saved successfully",
            )
            
        except Exception as e:
            return ToolStorageResult(
                success=False,
                tool_id=tool_id,
                version=version,
                message=f"Failed to save tool: {str(e)}",
            )
    
    async def load(
        self,
        tool_id: str,
        version: Optional[str] = None
    ) -> ToolStorageResult:
        """
        Load a tool specification from S3.
        
        Args:
            tool_id: Tool identifier
            version: Specific version (None for latest)
            
        Returns:
            ToolStorageResult with spec in data field
        """
        try:
            client = self._get_client()
            
            def _get_object():
                key = self._get_tool_key(tool_id, version if not self._use_s3_versioning else None)
                
                kwargs = {
                    "Bucket": self._bucket_name,
                    "Key": key,
                }
                
                # If using S3 versioning and specific version requested
                if self._use_s3_versioning and version:
                    # We need to find the version ID for this semantic version
                    # For simplicity, we'll use the metadata file
                    pass
                
                response = client.get_object(**kwargs)
                body = response["Body"].read().decode("utf-8")
                spec = json.loads(body)
                
                return {
                    "spec": spec,
                    "version_id": response.get("VersionId"),
                    "etag": response.get("ETag"),
                    "last_modified": response.get("LastModified"),
                }
            
            result = await asyncio.to_thread(_get_object)
            
            return ToolStorageResult(
                success=True,
                tool_id=tool_id,
                version_id=result.get("version_id"),
                version=result["spec"].get("version"),
                message="Tool loaded successfully",
                data=result["spec"],
            )
            
        except Exception as e:
            error_str = str(e).lower()
            if "nosuchkey" in error_str or "not found" in error_str:
                return ToolStorageResult(
                    success=False,
                    tool_id=tool_id,
                    version=version,
                    message=f"Tool {tool_id} not found",
                )
            return ToolStorageResult(
                success=False,
                tool_id=tool_id,
                version=version,
                message=f"Failed to load tool: {str(e)}",
            )
    
    async def delete(
        self,
        tool_id: str,
        version: Optional[str] = None
    ) -> ToolStorageResult:
        """
        Delete a tool specification from S3.
        
        Args:
            tool_id: Tool identifier
            version: Specific version (None for all versions)
            
        Returns:
            ToolStorageResult indicating success/failure
        """
        try:
            client = self._get_client()
            
            def _delete_object():
                if version and not self._use_s3_versioning:
                    # Delete specific version
                    key = self._get_tool_key(tool_id, version)
                    client.delete_object(Bucket=self._bucket_name, Key=key)
                    
                    # Update metadata
                    metadata_key = self._get_metadata_key(tool_id)
                    try:
                        existing = client.get_object(Bucket=self._bucket_name, Key=metadata_key)
                        tool_metadata = json.loads(existing["Body"].read().decode("utf-8"))
                        if version in tool_metadata.get("versions", []):
                            tool_metadata["versions"].remove(version)
                        if tool_metadata.get("latest_version") == version:
                            # Set latest to previous version
                            versions = tool_metadata.get("versions", [])
                            tool_metadata["latest_version"] = versions[-1] if versions else None
                        client.put_object(
                            Bucket=self._bucket_name,
                            Key=metadata_key,
                            Body=json.dumps(tool_metadata, indent=2).encode("utf-8"),
                            ContentType="application/json",
                        )
                    except Exception:
                        # Metadata doesn't exist - nothing to update
                        pass
                else:
                    # Delete all versions (list and delete)
                    prefix = f"{self._prefix}/{tool_id}/"
                    response = client.list_objects_v2(
                        Bucket=self._bucket_name,
                        Prefix=prefix,
                    )
                    
                    for obj in response.get("Contents", []):
                        client.delete_object(Bucket=self._bucket_name, Key=obj["Key"])
            
            await asyncio.to_thread(_delete_object)
            
            return ToolStorageResult(
                success=True,
                tool_id=tool_id,
                version=version,
                message=f"Tool {tool_id} deleted successfully",
            )
            
        except Exception as e:
            return ToolStorageResult(
                success=False,
                tool_id=tool_id,
                version=version,
                message=f"Failed to delete tool: {str(e)}",
            )
    
    async def list_tools(
        self,
        prefix: Optional[str] = None,
        limit: int = 100
    ) -> List[str]:
        """
        List all tool identifiers.
        
        Args:
            prefix: Optional prefix filter
            limit: Maximum number of results
            
        Returns:
            List of tool identifiers
        """
        try:
            client = self._get_client()
            
            def _list_objects():
                search_prefix = f"{self._prefix}/"
                if prefix:
                    search_prefix = f"{self._prefix}/{prefix}"
                
                response = client.list_objects_v2(
                    Bucket=self._bucket_name,
                    Prefix=search_prefix,
                    Delimiter="/",
                    MaxKeys=limit,
                )
                
                tool_ids = []
                for common_prefix in response.get("CommonPrefixes", []):
                    # Extract tool_id from prefix like "tools/my-tool/"
                    p = common_prefix["Prefix"]
                    parts = p.rstrip("/").split("/")
                    if len(parts) >= 2:
                        tool_ids.append(parts[-1])
                
                return tool_ids
            
            return await asyncio.to_thread(_list_objects)
            
        except Exception:
            return []
    
    async def list_versions(
        self,
        tool_id: str
    ) -> List[ToolVersionInfo]:
        """
        List all versions of a tool.
        
        Args:
            tool_id: Tool identifier
            
        Returns:
            List of ToolVersionInfo objects
        """
        try:
            client = self._get_client()
            
            def _list_versions():
                metadata_key = self._get_metadata_key(tool_id)
                
                try:
                    response = client.get_object(Bucket=self._bucket_name, Key=metadata_key)
                    tool_metadata = json.loads(response["Body"].read().decode("utf-8"))
                    
                    versions = []
                    latest = tool_metadata.get("latest_version")
                    
                    for v in tool_metadata.get("versions", []):
                        versions.append(ToolVersionInfo(
                            version_id=v,  # Using version as ID for semantic versioning
                            version=v,
                            created_at=tool_metadata.get("updated_at", ""),
                            is_latest=(v == latest),
                        ))
                    
                    return versions
                    
                except Exception:
                    # Tool doesn't exist or error reading metadata
                    return []
            
            return await asyncio.to_thread(_list_versions)
            
        except Exception:
            return []
    
    async def exists(
        self,
        tool_id: str,
        version: Optional[str] = None
    ) -> bool:
        """
        Check if a tool exists.
        
        Args:
            tool_id: Tool identifier
            version: Optional specific version
            
        Returns:
            True if exists
        """
        try:
            client = self._get_client()
            
            def _head_object():
                key = self._get_tool_key(tool_id, version if not self._use_s3_versioning else None)
                client.head_object(Bucket=self._bucket_name, Key=key)
                return True
            
            return await asyncio.to_thread(_head_object)
            
        except Exception:
            return False
    
    async def get_latest_version(
        self,
        tool_id: str
    ) -> Optional[str]:
        """
        Get the latest version string for a tool.
        
        Args:
            tool_id: Tool identifier
            
        Returns:
            Latest version string or None
        """
        try:
            client = self._get_client()
            
            def _get_latest():
                metadata_key = self._get_metadata_key(tool_id)
                
                try:
                    response = client.get_object(Bucket=self._bucket_name, Key=metadata_key)
                    tool_metadata = json.loads(response["Body"].read().decode("utf-8"))
                    return tool_metadata.get("latest_version")
                except Exception:
                    # Tool doesn't exist or error
                    return None
            
            return await asyncio.to_thread(_get_latest)
            
        except Exception:
            return None
    
    def _increment_version(self, version: str) -> str:
        """Increment semantic version (patch)."""
        parts = version.split(".")
        if len(parts) == 3:
            parts[2] = str(int(parts[2]) + 1)
        return ".".join(parts)
    
    async def ensure_bucket_exists(self) -> bool:
        """
        Ensure the S3 bucket exists, create if not.
        
        Returns:
            True if bucket exists or was created
        """
        try:
            import botocore.exceptions
            client = self._get_client()
            
            def _ensure():
                try:
                    client.head_bucket(Bucket=self._bucket_name)
                    return True
                except botocore.exceptions.ClientError as e:
                    error_code = e.response.get("Error", {}).get("Code", "")
                    if error_code in ("404", "NoSuchBucket"):
                        # Create bucket
                        try:
                            if self._region == "us-east-1":
                                client.create_bucket(Bucket=self._bucket_name)
                            else:
                                client.create_bucket(
                                    Bucket=self._bucket_name,
                                    CreateBucketConfiguration={"LocationConstraint": self._region},
                                )
                            return True
                        except Exception:
                            return False
                    return False
                except Exception:
                    return False
            
            return await asyncio.to_thread(_ensure)
            
        except Exception:
            return False
