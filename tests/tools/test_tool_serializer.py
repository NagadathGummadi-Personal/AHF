"""
Test suite for Tool Serialization functionality.

This module tests JSON ↔ Tool object conversion for all tool types,
ensuring proper serialization, deserialization, and error handling.

Test Structure:
===============
1. TestToolToJson - Serialization to JSON strings
2. TestToolToDict - Serialization to dictionaries
3. TestToolFromJson - Deserialization from JSON strings
4. TestToolFromDict - Deserialization from dictionaries
5. TestAllToolTypes - Comprehensive tests for all tool types
6. TestErrorHandling - Error cases and validation
7. TestRoundTrip - Round-trip conversion tests

Pytest Markers:
===============
- unit: Individual serializer tests
- serializer: Serializer-specific tests
- integration: End-to-end serialization tests

Usage:
    pytest tests/tools/test_tool_serializer.py -v
"""

import json
import pytest
from typing import Dict, Any

from core.tools.serializers import (
    tool_to_json,
    tool_to_dict,
    tool_from_json,
    tool_from_dict,
    ToolSerializationError,
)
from core.tools.spec.tool_types import (
    FunctionToolSpec,
    HttpToolSpec,
    DynamoDbToolSpec,
    PostgreSqlToolSpec,
    MySqlToolSpec,
    SqliteToolSpec,
)
from core.tools.spec.tool_parameters import StringParameter, NumericParameter
from core.tools.enum import ToolType, ToolReturnType, ToolReturnTarget


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def function_tool_spec():
    """Create a sample function tool spec"""
    return FunctionToolSpec(
        id="func-tool-001",
        tool_name="calculate",
        description="Calculate something",
        tool_type=ToolType.FUNCTION,
        parameters=[
            NumericParameter(name="x", description="First number", required=True),
            NumericParameter(name="y", description="Second number", required=True),
        ],
        return_type=ToolReturnType.JSON,
        return_target=ToolReturnTarget.STEP,
    )


@pytest.fixture
def http_tool_spec():
    """Create a sample HTTP tool spec"""
    return HttpToolSpec(
        id="http-tool-001",
        tool_name="fetch_data",
        description="Fetch data from API",
        tool_type=ToolType.HTTP,
        url="https://api.example.com/data",
        method="GET",
        headers={"Authorization": "Bearer token123"},
        parameters=[
            StringParameter(name="user_id", description="User ID", required=True),
        ],
    )


@pytest.fixture
def dynamodb_tool_spec():
    """Create a sample DynamoDB tool spec"""
    return DynamoDbToolSpec(
        id="dynamo-tool-001",
        tool_name="get_user",
        description="Get user from DynamoDB",
        tool_type=ToolType.DB,
        driver="dynamodb",
        region="us-west-2",
        table_name="users",
        parameters=[
            StringParameter(name="user_id", description="User ID", required=True),
        ],
    )


@pytest.fixture
def postgresql_tool_spec():
    """Create a sample PostgreSQL tool spec"""
    return PostgreSqlToolSpec(
        id="postgres-tool-001",
        tool_name="query_orders",
        description="Query orders from PostgreSQL",
        tool_type=ToolType.DB,
        driver="postgresql",
        host="localhost",
        port=5432,
        database="mydb",
        username="testuser",
        password="testpass",
        parameters=[
            StringParameter(name="customer_id", description="Customer ID", required=True),
        ],
    )


# ============================================================================
# SERIALIZATION TO JSON TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.serializer
class TestToolToJson:
    """Test suite for tool_to_json function"""
    
    def test_function_tool_to_json(self, function_tool_spec):
        """Test serializing function tool to JSON"""
        json_str = tool_to_json(function_tool_spec)
        
        # Should be valid JSON
        parsed = json.loads(json_str)
        assert parsed["id"] == "func-tool-001"
        assert parsed["tool_name"] == "calculate"
        assert parsed["tool_type"] == "function"
        assert len(parsed["parameters"]) == 2
    
    def test_http_tool_to_json(self, http_tool_spec):
        """Test serializing HTTP tool to JSON"""
        json_str = tool_to_json(http_tool_spec)
        
        parsed = json.loads(json_str)
        assert parsed["tool_type"] == "http"
        assert parsed["url"] == "https://api.example.com/data"
        assert parsed["method"] == "GET"
        assert "Authorization" in parsed["headers"]
    
    def test_dynamodb_tool_to_json(self, dynamodb_tool_spec):
        """Test serializing DynamoDB tool to JSON"""
        json_str = tool_to_json(dynamodb_tool_spec)
        
        parsed = json.loads(json_str)
        assert parsed["tool_type"] == "db"
        assert parsed["driver"] == "dynamodb"
        assert parsed["region"] == "us-west-2"
        assert parsed["table_name"] == "users"
    
    def test_json_formatting(self, function_tool_spec):
        """Test JSON formatting options"""
        # With indentation
        json_indented = tool_to_json(function_tool_spec, indent=4)
        assert "\n" in json_indented
        assert "    " in json_indented
        
        # Without indentation (compact)
        json_compact = tool_to_json(function_tool_spec, indent=None)
        assert json_compact.count("\n") < json_indented.count("\n")
    
    def test_exclude_none_option(self):
        """Test exclude_none parameter"""
        spec = FunctionToolSpec(
            id="test",
            tool_name="test",
            description="Test",
            parameters=[],
            owner=None,  # Explicitly None
        )
        
        # With exclude_none=True (default)
        json_excluded = tool_to_json(spec, exclude_none=True)
        parsed_excluded = json.loads(json_excluded)
        assert "owner" not in parsed_excluded
        
        # With exclude_none=False
        json_included = tool_to_json(spec, exclude_none=False)
        parsed_included = json.loads(json_included)
        assert "owner" in parsed_included
        assert parsed_included["owner"] is None


# ============================================================================
# SERIALIZATION TO DICT TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.serializer
class TestToolToDict:
    """Test suite for tool_to_dict function"""
    
    def test_function_tool_to_dict(self, function_tool_spec):
        """Test serializing function tool to dictionary"""
        tool_dict = tool_to_dict(function_tool_spec)
        
        assert isinstance(tool_dict, dict)
        assert tool_dict["id"] == "func-tool-001"
        assert tool_dict["tool_name"] == "calculate"
        assert tool_dict["tool_type"] == "function"
    
    def test_dict_contains_all_fields(self, http_tool_spec):
        """Test that dictionary contains all expected fields"""
        tool_dict = tool_to_dict(http_tool_spec)
        
        # Check required fields
        assert "id" in tool_dict
        assert "tool_name" in tool_dict
        assert "description" in tool_dict
        assert "tool_type" in tool_dict
        assert "parameters" in tool_dict
        
        # Check HTTP-specific fields
        assert "url" in tool_dict
        assert "method" in tool_dict
        assert "headers" in tool_dict
    
    def test_nested_objects_serialized(self, function_tool_spec):
        """Test that nested objects (parameters) are properly serialized"""
        tool_dict = tool_to_dict(function_tool_spec)
        
        assert isinstance(tool_dict["parameters"], list)
        assert len(tool_dict["parameters"]) == 2
        
        param = tool_dict["parameters"][0]
        assert isinstance(param, dict)
        assert "name" in param
        assert "description" in param


# ============================================================================
# DESERIALIZATION FROM JSON TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.serializer
class TestToolFromJson:
    """Test suite for tool_from_json function"""
    
    def test_deserialize_function_tool(self):
        """Test deserializing function tool from JSON"""
        json_str = """
        {
            "id": "test-func",
            "tool_name": "test_function",
            "description": "Test function",
            "tool_type": "function",
            "parameters": []
        }
        """
        
        tool = tool_from_json(json_str)
        
        assert isinstance(tool, FunctionToolSpec)
        assert tool.id == "test-func"
        assert tool.tool_name == "test_function"
        assert tool.tool_type == ToolType.FUNCTION
    
    def test_deserialize_http_tool(self):
        """Test deserializing HTTP tool from JSON"""
        json_str = """
        {
            "id": "test-http",
            "tool_name": "test_http",
            "description": "Test HTTP",
            "tool_type": "http",
            "url": "https://example.com",
            "method": "POST",
            "parameters": []
        }
        """
        
        tool = tool_from_json(json_str)
        
        assert isinstance(tool, HttpToolSpec)
        assert tool.url == "https://example.com"
        assert tool.method == "POST"
    
    def test_deserialize_dynamodb_tool(self):
        """Test deserializing DynamoDB tool from JSON"""
        json_str = """
        {
            "id": "test-dynamo",
            "tool_name": "test_dynamo",
            "description": "Test DynamoDB",
            "tool_type": "db",
            "driver": "dynamodb",
            "region": "us-east-1",
            "table_name": "test_table",
            "parameters": []
        }
        """
        
        tool = tool_from_json(json_str)
        
        assert isinstance(tool, DynamoDbToolSpec)
        assert tool.driver == "dynamodb"
        assert tool.region == "us-east-1"
        assert tool.table_name == "test_table"
    
    def test_deserialize_postgresql_tool(self):
        """Test deserializing PostgreSQL tool from JSON"""
        json_str = """
        {
            "id": "test-postgres",
            "tool_name": "test_postgres",
            "description": "Test PostgreSQL",
            "tool_type": "db",
            "driver": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database": "testdb",
            "username": "testuser",
            "password": "testpass",
            "parameters": []
        }
        """
        
        tool = tool_from_json(json_str)
        
        assert isinstance(tool, PostgreSqlToolSpec)
        assert tool.driver == "postgresql"
        assert tool.host == "localhost"
        assert tool.port == 5432
    
    def test_deserialize_with_parameters(self):
        """Test deserializing tool with complex parameters"""
        json_str = """
        {
            "id": "test",
            "tool_name": "test",
            "description": "Test",
            "tool_type": "function",
            "parameters": [
                {
                    "name": "param1",
                    "type": "string",
                    "description": "First parameter",
                    "required": true
                },
                {
                    "name": "param2",
                    "type": "number",
                    "description": "Second parameter",
                    "required": false
                }
            ]
        }
        """
        
        tool = tool_from_json(json_str)
        
        assert len(tool.parameters) == 2
        assert tool.parameters[0].name == "param1"
        assert tool.parameters[0].required == True
        assert tool.parameters[1].name == "param2"
        assert tool.parameters[1].required == False


# ============================================================================
# DESERIALIZATION FROM DICT TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.serializer
class TestToolFromDict:
    """Test suite for tool_from_dict function"""
    
    def test_deserialize_from_dict(self):
        """Test deserializing tool from dictionary"""
        data = {
            "id": "test",
            "tool_name": "test",
            "description": "Test",
            "tool_type": "function",
            "parameters": []
        }
        
        tool = tool_from_dict(data)
        
        assert isinstance(tool, FunctionToolSpec)
        assert tool.id == "test"
    
    def test_auto_detect_tool_type(self):
        """Test automatic tool type detection"""
        # Function tool
        func_data = {"id": "1", "tool_name": "f", "description": "F", "tool_type": "function", "parameters": []}
        func_tool = tool_from_dict(func_data)
        assert isinstance(func_tool, FunctionToolSpec)
        
        # HTTP tool
        http_data = {"id": "2", "tool_name": "h", "description": "H", "tool_type": "http", "url": "http://test", "parameters": []}
        http_tool = tool_from_dict(http_data)
        assert isinstance(http_tool, HttpToolSpec)
    
    def test_auto_detect_db_driver(self):
        """Test automatic DB driver detection"""
        # DynamoDB
        dynamo_data = {
            "id": "1", "tool_name": "d", "description": "D",
            "tool_type": "db", "driver": "dynamodb",
            "region": "us-west-2", "table_name": "test",
            "parameters": []
        }
        dynamo_tool = tool_from_dict(dynamo_data)
        assert isinstance(dynamo_tool, DynamoDbToolSpec)
        
        # PostgreSQL
        pg_data = {
            "id": "2", "tool_name": "p", "description": "P",
            "tool_type": "db", "driver": "postgresql",
            "host": "localhost", "port": 5432, "database": "test",
            "username": "testuser", "password": "testpass",
            "parameters": []
        }
        pg_tool = tool_from_dict(pg_data)
        assert isinstance(pg_tool, PostgreSqlToolSpec)


# ============================================================================
# COMPREHENSIVE TOOL TYPES TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.serializer
class TestAllToolTypes:
    """Comprehensive tests for all tool types"""
    
    def test_all_db_tools(self):
        """Test all database tool types"""
        db_tools = [
            (DynamoDbToolSpec, "dynamodb", {"region": "us-west-2", "table_name": "test"}),
            (PostgreSqlToolSpec, "postgresql", {"host": "localhost", "port": 5432, "database": "test", "username": "testuser", "password": "testpass"}),
            (MySqlToolSpec, "mysql", {"host": "localhost", "port": 3306, "database": "test", "username": "testuser", "password": "testpass"}),
            (SqliteToolSpec, "sqlite", {"database_path": "/path/to/db.sqlite"}),
        ]
        
        for spec_class, driver, extra_fields in db_tools:
            data = {
                "id": f"test-{driver}",
                "tool_name": f"test_{driver}",
                "description": f"Test {driver}",
                "tool_type": "db",
                "driver": driver,
                "parameters": [],
                **extra_fields
            }
            
            tool = tool_from_dict(data)
            assert isinstance(tool, spec_class)
            assert tool.driver == driver


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.serializer
class TestErrorHandling:
    """Test error cases and validation"""
    
    def test_invalid_json(self):
        """Test that invalid JSON raises error"""
        with pytest.raises(ToolSerializationError, match="Invalid JSON"):
            tool_from_json("{invalid json}")
    
    def test_missing_tool_type(self):
        """Test that missing tool_type raises error"""
        data = {
            "id": "test",
            "tool_name": "test",
            "description": "Test",
            # Missing tool_type
        }
        
        with pytest.raises(ToolSerializationError, match="tool_type"):
            tool_from_dict(data)
    
    def test_unknown_tool_type(self):
        """Test that unknown tool_type raises error"""
        data = {
            "id": "test",
            "tool_name": "test",
            "description": "Test",
            "tool_type": "unknown_type",
            "parameters": []
        }
        
        with pytest.raises(ToolSerializationError, match="Unknown tool_type"):
            tool_from_dict(data)
    
    def test_missing_required_fields(self):
        """Test that missing required fields raises validation error"""
        # Missing 'url' for HTTP tool
        data = {
            "id": "test",
            "tool_name": "test",
            "description": "Test",
            "tool_type": "http",
            # Missing url
            "parameters": []
        }
        
        with pytest.raises(ToolSerializationError):
            tool_from_dict(data)


# ============================================================================
# ROUND-TRIP CONVERSION TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.serializer
class TestRoundTripConversion:
    """Test that tools can be serialized and deserialized without data loss"""
    
    def test_function_tool_round_trip(self, function_tool_spec):
        """Test function tool round-trip conversion"""
        # Tool -> JSON -> Tool
        json_str = tool_to_json(function_tool_spec)
        restored_tool = tool_from_json(json_str)
        
        assert restored_tool.id == function_tool_spec.id
        assert restored_tool.tool_name == function_tool_spec.tool_name
        assert restored_tool.description == function_tool_spec.description
        assert restored_tool.tool_type == function_tool_spec.tool_type
        assert len(restored_tool.parameters) == len(function_tool_spec.parameters)
    
    def test_http_tool_round_trip(self, http_tool_spec):
        """Test HTTP tool round-trip conversion"""
        json_str = tool_to_json(http_tool_spec)
        restored_tool = tool_from_json(json_str)
        
        assert restored_tool.url == http_tool_spec.url
        assert restored_tool.method == http_tool_spec.method
        assert restored_tool.headers == http_tool_spec.headers
    
    def test_dynamodb_tool_round_trip(self, dynamodb_tool_spec):
        """Test DynamoDB tool round-trip conversion"""
        json_str = tool_to_json(dynamodb_tool_spec)
        restored_tool = tool_from_json(json_str)
        
        assert isinstance(restored_tool, DynamoDbToolSpec)
        assert restored_tool.driver == dynamodb_tool_spec.driver
        assert restored_tool.region == dynamodb_tool_spec.region
        assert restored_tool.table_name == dynamodb_tool_spec.table_name
    
    def test_dict_round_trip(self, postgresql_tool_spec):
        """Test round-trip using dictionary"""
        # Tool -> Dict -> Tool
        tool_dict = tool_to_dict(postgresql_tool_spec)
        restored_tool = tool_from_dict(tool_dict)
        
        assert isinstance(restored_tool, PostgreSqlToolSpec)
        assert restored_tool.host == postgresql_tool_spec.host
        assert restored_tool.port == postgresql_tool_spec.port
        assert restored_tool.database == postgresql_tool_spec.database
    
    def test_multiple_round_trips(self, function_tool_spec):
        """Test multiple round-trip conversions"""
        tool = function_tool_spec
        
        for _ in range(3):
            json_str = tool_to_json(tool)
            tool = tool_from_json(json_str)
        
        # Should still be valid after multiple conversions
        assert tool.id == function_tool_spec.id
        assert tool.tool_name == function_tool_spec.tool_name


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

