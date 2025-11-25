"""
Tests for Azure OpenAI Backup & Failover functionality.

Demonstrates automatic failover when primary endpoint fails.
"""

import pytest
from typing import Dict, Any

from core.llms.providers.azure.connector import AzureConnector
from core.llms.exceptions import ServiceUnavailableError


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def primary_only_config():
    """Configuration with no backups."""
    return {
        "api_key": "test-key",
        "endpoint": "https://primary.openai.azure.com",
        "deployment_name": "gpt-4.1-mini"
    }


@pytest.fixture
def backup_config():
    """Configuration with backup endpoints."""
    return {
        "api_key": "test-key",
        "endpoint": "https://eastus.openai.azure.com",
        "deployment_name": "gpt-4.1-mini",
        "backups": [
            {
                "endpoint": "https://westus.openai.azure.com"
                # deployment_name and api_key inherit from primary
            },
            {
                "endpoint": "https://northeurope.openai.azure.com"
            }
        ]
    }


@pytest.fixture
def complex_backup_config():
    """Configuration with different deployment names and keys."""
    return {
        "api_key": "primary-key",
        "endpoint": "https://eastus-primary.openai.azure.com",
        "deployment_name": "gpt-4.1-mini",
        "backups": [
            {
                "endpoint": "https://westus-backup.openai.azure.com",
                "deployment_name": "gpt-41-mini"  # Different name
                # api_key inherits
            },
            {
                "endpoint": "https://eu-different-subscription.openai.azure.com",
                "deployment_name": "my-gpt-model",
                "api_key": "different-subscription-key"  # Different key
            }
        ]
    }


# ============================================================================
# Configuration Tests
# ============================================================================

def test_primary_only_configuration(primary_only_config):
    """Test connector with no backup configuration."""
    connector = AzureConnector(primary_only_config)
    
    assert connector.endpoint == "https://primary.openai.azure.com"
    assert connector.deployment_name == "gpt-4.1-mini"
    assert connector.api_key == "test-key"
    assert len(connector.backup_configs) == 0
    assert connector.current_config_index == 0
    
    status = connector.get_backup_status()
    assert status['total_endpoints'] == 1
    assert status['current_type'] == 'primary'
    assert status['has_backups'] is False


def test_backup_configuration_parsing(backup_config):
    """Test parsing of backup configurations."""
    connector = AzureConnector(backup_config)
    
    # Primary should be active initially
    assert connector.endpoint == "https://eastus.openai.azure.com"
    assert connector.deployment_name == "gpt-4.1-mini"
    assert connector.current_config_index == 0
    
    # Should have 2 backups
    assert len(connector.backup_configs) == 2
    
    # Check backup configs
    backup1 = connector.backup_configs[0]
    assert backup1['endpoint'] == "https://westus.openai.azure.com"
    assert backup1['deployment_name'] == "gpt-4.1-mini"  # Inherited
    assert backup1['api_key'] == "test-key"  # Inherited
    
    backup2 = connector.backup_configs[1]
    assert backup2['endpoint'] == "https://northeurope.openai.azure.com"
    
    status = connector.get_backup_status()
    assert status['total_endpoints'] == 3  # Primary + 2 backups
    assert status['available_backups'] == 2
    assert status['has_backups'] is True


def test_complex_backup_configuration(complex_backup_config):
    """Test backup configuration with different deployment names and keys."""
    connector = AzureConnector(complex_backup_config)
    
    # Primary
    assert connector.api_key == "primary-key"
    assert connector.deployment_name == "gpt-4.1-mini"
    
    # Backup 1 - different deployment name, inherited key
    backup1 = connector.backup_configs[0]
    assert backup1['deployment_name'] == "gpt-41-mini"
    assert backup1['api_key'] == "primary-key"  # Inherited
    
    # Backup 2 - different everything
    backup2 = connector.backup_configs[1]
    assert backup2['deployment_name'] == "my-gpt-model"
    assert backup2['api_key'] == "different-subscription-key"


# ============================================================================
# Failover Logic Tests
# ============================================================================

def test_switch_to_next_endpoint(backup_config):
    """Test switching to backup endpoint."""
    connector = AzureConnector(backup_config)
    
    # Initially on primary
    assert connector.current_config_index == 0
    assert connector.endpoint == "https://eastus.openai.azure.com"
    
    # Switch to first backup
    success = connector._switch_to_next_endpoint()
    assert success is True
    assert connector.current_config_index == 1
    assert connector.endpoint == "https://westus.openai.azure.com"
    assert "https://eastus.openai.azure.com" in connector.failed_endpoints
    
    # Switch to second backup
    success = connector._switch_to_next_endpoint()
    assert success is True
    assert connector.current_config_index == 2
    assert connector.endpoint == "https://northeurope.openai.azure.com"
    assert "https://westus.openai.azure.com" in connector.failed_endpoints
    
    # No more backups
    success = connector._switch_to_next_endpoint()
    assert success is False
    assert len(connector.failed_endpoints) == 3


def test_get_all_configs(backup_config):
    """Test getting all configurations."""
    connector = AzureConnector(backup_config)
    
    all_configs = connector._get_all_configs()
    assert len(all_configs) == 3
    
    # Primary
    assert all_configs[0]['type'] == 'primary'
    assert all_configs[0]['index'] == 0
    assert all_configs[0]['endpoint'] == "https://eastus.openai.azure.com"
    
    # Backups
    assert all_configs[1]['type'] == 'backup'
    assert all_configs[1]['index'] == 1
    assert all_configs[2]['type'] == 'backup'
    assert all_configs[2]['index'] == 2


def test_current_endpoint_info(backup_config):
    """Test getting current endpoint information."""
    connector = AzureConnector(backup_config)
    
    # Primary
    info = connector.get_current_endpoint_info()
    assert info['type'] == 'primary'
    assert info['index'] == 0
    assert info['endpoint'] == "https://eastus.openai.azure.com"
    
    # Switch to backup
    connector._switch_to_next_endpoint()
    info = connector.get_current_endpoint_info()
    assert info['type'] == 'backup'
    assert info['index'] == 1
    assert info['endpoint'] == "https://westus.openai.azure.com"


def test_backup_status_tracking(backup_config):
    """Test backup status tracking."""
    connector = AzureConnector(backup_config)
    
    # Initial status
    status = connector.get_backup_status()
    assert status['total_endpoints'] == 3
    assert status['current_index'] == 0
    assert status['current_type'] == 'primary'
    assert status['current_endpoint'] == "https://eastus.openai.azure.com"
    assert len(status['failed_endpoints']) == 0
    assert status['available_backups'] == 2
    assert status['has_backups'] is True
    
    # After failover
    connector._switch_to_next_endpoint()
    status = connector.get_backup_status()
    assert status['current_index'] == 1
    assert status['current_type'] == 'backup'
    assert len(status['failed_endpoints']) == 1
    assert "https://eastus.openai.azure.com" in status['failed_endpoints']


# ============================================================================
# Edge Cases
# ============================================================================

def test_empty_backups_list():
    """Test with empty backups list."""
    config = {
        "api_key": "test-key",
        "endpoint": "https://test.openai.azure.com",
        "deployment_name": "gpt-4",
        "backups": []
    }
    
    connector = AzureConnector(config)
    assert len(connector.backup_configs) == 0
    assert connector.get_backup_status()['has_backups'] is False


def test_invalid_backup_format():
    """Test with invalid backup format (should be skipped)."""
    config = {
        "api_key": "test-key",
        "endpoint": "https://test.openai.azure.com",
        "deployment_name": "gpt-4",
        "backups": [
            "not-a-dict",  # Invalid
            {},  # Missing endpoint
            {"endpoint": "https://valid.openai.azure.com"}  # Valid
        ]
    }
    
    connector = AzureConnector(config)
    # Only the valid backup should be parsed
    assert len(connector.backup_configs) == 1
    assert connector.backup_configs[0]['endpoint'] == "https://valid.openai.azure.com"


def test_url_normalization():
    """Test that endpoint URLs are normalized (trailing slash removed)."""
    config = {
        "api_key": "test-key",
        "endpoint": "https://test.openai.azure.com/",  # Trailing slash
        "deployment_name": "gpt-4",
        "backups": [
            {"endpoint": "https://backup.openai.azure.com/"}  # Trailing slash
        ]
    }
    
    connector = AzureConnector(config)
    assert connector.endpoint == "https://test.openai.azure.com"  # No trailing slash
    assert connector.backup_configs[0]['endpoint'] == "https://backup.openai.azure.com"


# ============================================================================
# Integration Example
# ============================================================================

@pytest.mark.skip(reason="Example only - demonstrates usage pattern")
async def test_usage_example():
    """Example showing how to use backup configuration in practice."""
    from core.llms import LLMFactory
    
    # Configure with backups
    llm = LLMFactory.create_llm(
        "azure-gpt-4.1-mini",
        connector_config={
            "api_key": "your-key",
            "endpoint": "https://eastus.openai.azure.com",
            "deployment_name": "gpt-4.1-mini",
            "backups": [
                {"endpoint": "https://westus.openai.azure.com"},
                {"endpoint": "https://northeurope.openai.azure.com"}
            ]
        }
    )
    
    # Use normally - failover happens automatically
    from core.llms.spec.llm_context import create_context
    
    ctx = create_context(user_id="test", session_id="test")
    messages = [{"role": "user", "content": "Hello"}]
    
    response = await llm.get_answer(messages, ctx)
    # If eastus fails, automatically tries westus, then northeurope
    
    # Check which endpoint was used
    status = llm.connector.get_backup_status()
    print(f"Used endpoint: {status['current_endpoint']} ({status['current_type']})")
    if status['failed_endpoints']:
        print(f"Failed endpoints: {status['failed_endpoints']}")

