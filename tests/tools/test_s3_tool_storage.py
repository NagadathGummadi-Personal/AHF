"""
Tests for S3 Tool Storage

Tests the S3-based storage implementation for tool specifications.

To run these tests:
    - Ensure AWS credentials are configured
    - Set environment variable TEST_S3_BUCKET to your test bucket name
    - Or use LocalStack for local testing

Usage:
    # Run all S3 storage tests
    uv run pytest tests/tools/test_s3_tool_storage.py -v
    
    # Run with real S3 (requires AWS creds and TEST_S3_BUCKET env var)
    TEST_S3_BUCKET=my-test-bucket uv run pytest tests/tools/test_s3_tool_storage.py -v
    
    # Skip if no S3 available
    uv run pytest tests/tools/test_s3_tool_storage.py -v -m "not requires_s3"
"""

import os
import json
import pytest
from datetime import datetime
from typing import Dict, Any

from core.tools.runtimes.storage import S3ToolStorage, IToolStorage
from core.tools.runtimes.storage.storage_interface import ToolStorageResult, ToolVersionInfo
from core.tools.spec.tool_types import FunctionToolSpec, HttpToolSpec
from core.tools.spec.tool_parameters import StringParameter
from core.tools.serializers.tool_serializer import tool_to_dict, tool_from_dict


# Test configuration
TEST_BUCKET = os.environ.get("TEST_S3_BUCKET", "ahf-test-tools")
TEST_REGION = os.environ.get("AWS_DEFAULT_REGION", "us-west-2")
LOCALSTACK_ENDPOINT = os.environ.get("LOCALSTACK_ENDPOINT", None)  # e.g., "http://localhost:4566"


def get_test_storage() -> S3ToolStorage:
    """Create a test storage instance."""
    return S3ToolStorage(
        bucket_name=TEST_BUCKET,
        region=TEST_REGION,
        endpoint_url=LOCALSTACK_ENDPOINT,
        prefix="test-tools",
    )


def create_sample_function_tool() -> Dict[str, Any]:
    """Create a sample function tool spec for testing."""
    spec = FunctionToolSpec(
        id="test-calculator-v1",
        tool_name="calculator",
        description="A simple calculator tool for testing",
        parameters=[
            StringParameter(
                name="operation",
                description="Math operation: add, subtract, multiply, divide",
                required=True,
            ),
            StringParameter(
                name="a",
                description="First number",
                required=True,
            ),
            StringParameter(
                name="b", 
                description="Second number",
                required=True,
            ),
        ],
    )
    return tool_to_dict(spec)


def create_sample_http_tool() -> Dict[str, Any]:
    """Create a sample HTTP tool spec for testing."""
    spec = HttpToolSpec(
        id="test-weather-api-v1",
        tool_name="get_weather",
        description="Get weather information from API",
        url="https://api.weather.com/v1/current",
        method="GET",
        parameters=[
            StringParameter(
                name="city",
                description="City name",
                required=True,
            ),
        ],
        headers={"X-API-Key": "${API_KEY}"},
    )
    return tool_to_dict(spec)


# =============================================================================
# Unit Tests (No S3 Required)
# =============================================================================

class TestToolStorageInterface:
    """Test the storage interface and result classes."""
    
    def test_tool_storage_result_creation(self):
        """Test ToolStorageResult dataclass."""
        result = ToolStorageResult(
            success=True,
            tool_id="my-tool",
            version_id="v123",
            version="1.0.0",
            message="Success",
            data={"key": "value"},
        )
        
        assert result.success is True
        assert result.tool_id == "my-tool"
        assert result.version_id == "v123"
        assert result.version == "1.0.0"
        assert result.data == {"key": "value"}
    
    def test_tool_version_info_creation(self):
        """Test ToolVersionInfo dataclass."""
        info = ToolVersionInfo(
            version_id="v123",
            version="1.0.0",
            created_at="2024-01-01T00:00:00",
            is_latest=True,
            size_bytes=1024,
        )
        
        assert info.version_id == "v123"
        assert info.version == "1.0.0"
        assert info.is_latest is True
        assert info.size_bytes == 1024


class TestS3StorageConfiguration:
    """Test S3 storage configuration."""
    
    def test_storage_initialization(self):
        """Test storage can be initialized with parameters."""
        storage = S3ToolStorage(
            bucket_name="test-bucket",
            region="us-east-1",
            prefix="my-tools",
        )
        
        assert storage._bucket_name == "test-bucket"
        assert storage._region == "us-east-1"
        assert storage._prefix == "my-tools"
    
    def test_storage_with_custom_endpoint(self):
        """Test storage with LocalStack endpoint."""
        storage = S3ToolStorage(
            bucket_name="test-bucket",
            region="us-west-2",
            endpoint_url="http://localhost:4566",
        )
        
        assert storage._endpoint_url == "http://localhost:4566"
    
    def test_key_generation(self):
        """Test S3 key generation."""
        storage = S3ToolStorage(
            bucket_name="test-bucket",
            region="us-west-2",
            prefix="tools",
        )
        
        # Latest key
        key = storage._get_tool_key("my-tool")
        assert key == "tools/my-tool/spec.json"
        
        # Versioned key (semantic versioning mode)
        key = storage._get_tool_key("my-tool", "1.0.0")
        assert key == "tools/my-tool/versions/1.0.0/spec.json"
        
        # Metadata key
        key = storage._get_metadata_key("my-tool")
        assert key == "tools/my-tool/metadata.json"


class TestToolSpecSerialization:
    """Test tool spec serialization for storage."""
    
    def test_function_tool_serialization(self):
        """Test FunctionToolSpec can be serialized to dict."""
        spec_dict = create_sample_function_tool()
        
        assert spec_dict["id"] == "test-calculator-v1"
        assert spec_dict["tool_name"] == "calculator"
        assert spec_dict["tool_type"] == "function"
        assert len(spec_dict["parameters"]) == 3
    
    def test_http_tool_serialization(self):
        """Test HttpToolSpec can be serialized to dict."""
        spec_dict = create_sample_http_tool()
        
        assert spec_dict["id"] == "test-weather-api-v1"
        assert spec_dict["tool_name"] == "get_weather"
        assert spec_dict["tool_type"] == "http"
        assert spec_dict["url"] == "https://api.weather.com/v1/current"
    
    def test_roundtrip_serialization(self):
        """Test serialization and deserialization roundtrip."""
        original_spec = create_sample_function_tool()
        
        # Simulate what storage does
        json_str = json.dumps(original_spec, indent=2)
        restored_dict = json.loads(json_str)
        restored_spec = tool_from_dict(restored_dict)
        
        assert restored_spec.id == "test-calculator-v1"
        assert restored_spec.tool_name == "calculator"


# =============================================================================
# Integration Tests (Requires S3/LocalStack)
# =============================================================================

def s3_available() -> bool:
    """Check if S3 is available for testing."""
    try:
        import boto3
        storage = get_test_storage()
        client = storage._get_client()
        # Try to list buckets to verify credentials
        client.list_buckets()
        return True
    except Exception as e:
        print(f"S3 not available: {e}")
        return False


# Skip decorator for tests requiring S3
requires_s3 = pytest.mark.skipif(
    not s3_available(),
    reason="S3 not available (set AWS credentials or use LocalStack)"
)


@requires_s3
class TestS3StorageIntegration:
    """Integration tests for S3 storage (requires S3 or LocalStack)."""
    
    @pytest.fixture
    async def storage(self):
        """Create and setup storage for tests."""
        storage = get_test_storage()
        # Ensure bucket exists before running tests
        bucket_created = await storage.ensure_bucket_exists()
        if not bucket_created:
            pytest.skip("Could not create/access S3 bucket")
        return storage
    
    @pytest.fixture
    def sample_tool(self) -> Dict[str, Any]:
        """Create a sample tool for testing."""
        return create_sample_function_tool()
    
    async def test_save_and_load_tool(self, storage: S3ToolStorage, sample_tool: Dict[str, Any]):
        """Test saving and loading a tool spec."""
        tool_id = f"test-tool-{datetime.now().timestamp()}"
        
        # Save
        result = await storage.save(tool_id, sample_tool, version="1.0.0")
        
        assert result.success is True
        assert result.tool_id == tool_id
        assert result.version == "1.0.0"
        
        # Load
        result = await storage.load(tool_id)
        
        assert result.success is True
        assert result.data is not None
        assert result.data["tool_name"] == "calculator"
        assert result.data["version"] == "1.0.0"
        
        # Cleanup
        await storage.delete(tool_id)
    
    async def test_save_multiple_versions(self, storage: S3ToolStorage, sample_tool: Dict[str, Any]):
        """Test saving multiple versions of a tool."""
        tool_id = f"test-versioned-tool-{datetime.now().timestamp()}"
        
        # Save v1
        result = await storage.save(tool_id, sample_tool, version="1.0.0")
        assert result.success is True
        
        # Save v2 with modified description
        sample_tool["description"] = "Updated calculator v2"
        result = await storage.save(tool_id, sample_tool, version="1.1.0")
        assert result.success is True
        
        # List versions
        versions = await storage.list_versions(tool_id)
        assert len(versions) >= 2
        version_strings = [v.version for v in versions]
        assert "1.0.0" in version_strings
        assert "1.1.0" in version_strings
        
        # Load specific version
        result = await storage.load(tool_id, version="1.0.0")
        assert result.success is True
        assert "Updated" not in result.data["description"]
        
        # Load latest (should be 1.1.0)
        result = await storage.load(tool_id)
        assert result.success is True
        assert result.data["version"] == "1.1.0"
        
        # Cleanup
        await storage.delete(tool_id)
    
    async def test_auto_version_increment(self, storage: S3ToolStorage, sample_tool: Dict[str, Any]):
        """Test automatic version increment."""
        tool_id = f"test-auto-version-{datetime.now().timestamp()}"
        
        # Save without version (should be 1.0.0)
        result = await storage.save(tool_id, sample_tool)
        assert result.success is True
        assert result.version == "1.0.0"
        
        # Save again without version (should increment)
        result = await storage.save(tool_id, sample_tool)
        assert result.success is True
        assert result.version == "1.0.1"
        
        # Cleanup
        await storage.delete(tool_id)
    
    async def test_tool_exists(self, storage: S3ToolStorage, sample_tool: Dict[str, Any]):
        """Test checking if tool exists."""
        tool_id = f"test-exists-{datetime.now().timestamp()}"
        
        # Should not exist
        exists = await storage.exists(tool_id)
        assert exists is False
        
        # Save
        await storage.save(tool_id, sample_tool, version="1.0.0")
        
        # Should exist
        exists = await storage.exists(tool_id)
        assert exists is True
        
        # Cleanup
        await storage.delete(tool_id)
    
    async def test_list_tools(self, storage: S3ToolStorage, sample_tool: Dict[str, Any]):
        """Test listing tools."""
        # Create unique tools
        tool_ids = [f"test-list-{i}-{datetime.now().timestamp()}" for i in range(3)]
        
        for tool_id in tool_ids:
            await storage.save(tool_id, sample_tool, version="1.0.0")
        
        # List
        tools = await storage.list_tools(prefix="test-list")
        
        # Should contain our tools
        for tool_id in tool_ids:
            assert tool_id in tools
        
        # Cleanup
        for tool_id in tool_ids:
            await storage.delete(tool_id)
    
    async def test_delete_tool(self, storage: S3ToolStorage, sample_tool: Dict[str, Any]):
        """Test deleting a tool."""
        tool_id = f"test-delete-{datetime.now().timestamp()}"
        
        # Save
        await storage.save(tool_id, sample_tool, version="1.0.0")
        
        # Delete
        result = await storage.delete(tool_id)
        assert result.success is True
        
        # Should not exist
        exists = await storage.exists(tool_id)
        assert exists is False
    
    async def test_delete_specific_version(self, storage: S3ToolStorage, sample_tool: Dict[str, Any]):
        """Test deleting a specific version."""
        tool_id = f"test-delete-version-{datetime.now().timestamp()}"
        
        # Save two versions
        await storage.save(tool_id, sample_tool, version="1.0.0")
        await storage.save(tool_id, sample_tool, version="1.1.0")
        
        # Delete v1.0.0
        result = await storage.delete(tool_id, version="1.0.0")
        assert result.success is True
        
        # v1.0.0 should not exist
        exists = await storage.exists(tool_id, version="1.0.0")
        assert exists is False
        
        # v1.1.0 should still exist
        exists = await storage.exists(tool_id, version="1.1.0")
        assert exists is True
        
        # Cleanup
        await storage.delete(tool_id)
    
    async def test_load_nonexistent_tool(self, storage: S3ToolStorage):
        """Test loading a tool that doesn't exist."""
        result = await storage.load("nonexistent-tool-xyz")
        
        assert result.success is False
        # Accept both "not found" and bucket-related errors
        error_msg = result.message.lower()
        assert "not found" in error_msg or "nosuchkey" in error_msg or "failed to load" in error_msg
    
    async def test_get_latest_version(self, storage: S3ToolStorage, sample_tool: Dict[str, Any]):
        """Test getting latest version."""
        tool_id = f"test-latest-{datetime.now().timestamp()}"
        
        # Save versions
        await storage.save(tool_id, sample_tool, version="1.0.0")
        await storage.save(tool_id, sample_tool, version="2.0.0")
        await storage.save(tool_id, sample_tool, version="1.5.0")  # Out of order
        
        # Get latest (should be the last saved, which updates metadata)
        latest = await storage.get_latest_version(tool_id)
        assert latest == "1.5.0"
        
        # Cleanup
        await storage.delete(tool_id)


# =============================================================================
# Example/Demo Tests
# =============================================================================

class TestStorageExamples:
    """Example usage patterns for documentation."""
    
    def test_create_function_tool_spec(self):
        """Example: Create a function tool spec."""
        spec = FunctionToolSpec(
            id="my-calculator",
            tool_name="calculator",
            description="Performs basic math operations",
            parameters=[
                StringParameter(
                    name="operation",
                    description="add, subtract, multiply, or divide",
                    required=True,
                ),
                StringParameter(name="a", description="First number", required=True),
                StringParameter(name="b", description="Second number", required=True),
            ],
        )
        
        # Convert to dict for storage
        spec_dict = tool_to_dict(spec)
        
        assert spec_dict["tool_type"] == "function"
        assert len(spec_dict["parameters"]) == 3
    
    def test_create_http_tool_spec(self):
        """Example: Create an HTTP tool spec."""
        spec = HttpToolSpec(
            id="weather-api",
            tool_name="get_weather",
            description="Get current weather",
            url="https://api.weather.com/v1/current",
            method="GET",
            headers={"Authorization": "Bearer ${TOKEN}"},
            parameters=[
                StringParameter(name="city", description="City name", required=True),
            ],
        )
        
        spec_dict = tool_to_dict(spec)
        
        assert spec_dict["tool_type"] == "http"
        assert spec_dict["method"] == "GET"
        assert "Authorization" in spec_dict["headers"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
