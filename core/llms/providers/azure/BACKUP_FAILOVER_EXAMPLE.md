# Azure OpenAI Backup & Failover Configuration

The Azure connector now supports automatic failover to backup endpoints when the primary endpoint fails.

## Quick Start

### Single Endpoint (No Backup)
```python
config = {
    "api_key": "your-api-key",
    "endpoint": "https://eastus-resource.openai.azure.com",
    "deployment_name": "gpt-4.1-mini"
}
connector = AzureConnector(config)
```

### With Backup Endpoints (Same Region, Different Resource)
```python
config = {
    "api_key": "your-api-key",
    "endpoint": "https://eastus-primary.openai.azure.com",
    "deployment_name": "gpt-4.1-mini",
    "backups": [
        {
            "endpoint": "https://eastus-backup.openai.azure.com"
            # deployment_name and api_key inherit from primary
        }
    ]
}
connector = AzureConnector(config)
```

### With Backup Endpoints (Different Regions)
```python
config = {
    "api_key": "shared-key",  # Can use same key if same subscription
    "endpoint": "https://eastus-resource.openai.azure.com",
    "deployment_name": "gpt-4.1-mini",
    "backups": [
        {
            "endpoint": "https://westus-resource.openai.azure.com",
            # Same deployment name, same key
        },
        {
            "endpoint": "https://northeurope-resource.openai.azure.com",
            # Same deployment name, same key
        }
    ]
}
connector = AzureConnector(config)
```

### With Different Deployment Names/Keys
```python
config = {
    "api_key": "primary-key",
    "endpoint": "https://eastus-resource.openai.azure.com",
    "deployment_name": "gpt-4.1-mini",
    "backups": [
        {
            "endpoint": "https://westus-resource.openai.azure.com",
            "deployment_name": "gpt-41-mini",  # Different deployment name
            # api_key inherits from primary
        },
        {
            "endpoint": "https://different-subscription.openai.azure.com",
            "deployment_name": "my-gpt-model",
            "api_key": "different-subscription-key"  # Different API key
        }
    ]
}
connector = AzureConnector(config)
```

## How Failover Works

### Automatic Failover Triggers
Failover automatically happens when:
1. **Service Unavailable (503)** - Region/service is down
2. **Timeout** - Request takes too long
3. **Connection Error** - Network/connectivity issues

### Failover Does NOT Happen For
- **Authentication errors (401)** - Invalid credentials
- **Rate limits (429)** - Quota exceeded
- **Bad requests (400)** - Invalid input
- **Other 4xx errors** - Client-side errors

### Failover Sequence
1. Request fails on primary endpoint
2. Primary endpoint marked as failed
3. Switch to first backup endpoint
4. Retry request automatically
5. If backup fails, try next backup
6. Continue until success or all endpoints exhausted

## Using the Connector

### Normal Usage (Automatic Failover)
```python
from core.llms.providers.azure.connector import AzureConnector

# Configure with backups
config = {
    "api_key": "your-key",
    "endpoint": "https://eastus.openai.azure.com",
    "deployment_name": "gpt-4.1-mini",
    "backups": [
        {"endpoint": "https://westus.openai.azure.com"},
        {"endpoint": "https://northeurope.openai.azure.com"}
    ]
}

connector = AzureConnector(config)

# Make request - failover happens automatically
try:
    response = await connector.request(
        "chat/completions",
        {
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 50
        }
    )
    # Will try eastus, then westus, then northeurope if needed
except Exception as e:
    print(f"All endpoints failed: {e}")
```

### Disable Automatic Failover
```python
# Disable auto-failover for specific request
response = await connector.request(
    "chat/completions",
    payload,
    auto_failover=False  # Only try current endpoint
)
```

### Check Current Endpoint Status
```python
# Get currently active endpoint
info = connector.get_current_endpoint_info()
print(f"Using: {info['type']} endpoint at {info['endpoint']}")

# Get full backup status
status = connector.get_backup_status()
print(f"Total endpoints: {status['total_endpoints']}")
print(f"Current index: {status['current_index']}")
print(f"Failed endpoints: {status['failed_endpoints']}")
print(f"Has backups: {status['has_backups']}")
```

## Real-World Scenarios

### Scenario 1: Regional Disaster Recovery
```python
# Primary in East US, backup in different geography
config = {
    "api_key": "your-key",
    "endpoint": "https://eastus-prod.openai.azure.com",
    "deployment_name": "production-gpt-4",
    "backups": [
        {
            "endpoint": "https://westeurope-dr.openai.azure.com",
            "deployment_name": "production-gpt-4"
        }
    ]
}
```

### Scenario 2: Multi-Region Load Distribution
```python
# Rotate between regions for load distribution
config = {
    "api_key": "shared-key",
    "endpoint": "https://eastus.openai.azure.com",
    "deployment_name": "gpt-4.1-mini",
    "backups": [
        {"endpoint": "https://westus.openai.azure.com"},
        {"endpoint": "https://centralus.openai.azure.com"},
        {"endpoint": "https://northeurope.openai.azure.com"}
    ]
}
```

### Scenario 3: Different Subscriptions
```python
# Failover to different Azure subscription
config = {
    "api_key": "subscription-1-key",
    "endpoint": "https://subscription1.openai.azure.com",
    "deployment_name": "gpt-4.1-mini",
    "backups": [
        {
            "endpoint": "https://subscription2.openai.azure.com",
            "api_key": "subscription-2-key",
            "deployment_name": "gpt-4-mini"  # Might have different name
        }
    ]
}
```

## Integration with LLM Factory

```python
from core.llms import LLMFactory

# The backup config works seamlessly with LLMFactory
llm = LLMFactory.create_llm(
    "azure-gpt-4.1-mini",
    connector_config={
        "api_key": "primary-key",
        "endpoint": "https://eastus.openai.azure.com",
        "deployment_name": "gpt-4.1-mini",
        "backups": [
            {"endpoint": "https://westus.openai.azure.com"},
        ]
    }
)

# Use normally - failover happens transparently
response = await llm.get_answer(messages, ctx)
```

## Best Practices

### 1. Use Different Regions
```python
# ✅ Good - Geographic redundancy
backups = [
    {"endpoint": "https://eastus.openai.azure.com"},
    {"endpoint": "https://westeurope.openai.azure.com"},
    {"endpoint": "https://australiaeast.openai.azure.com"}
]

# ❌ Bad - Same region, same datacenter
backups = [
    {"endpoint": "https://eastus-1.openai.azure.com"},
    {"endpoint": "https://eastus-2.openai.azure.com"}
]
```

### 2. Minimize Configuration Differences
```python
# ✅ Good - Same deployment name and key
config = {
    "api_key": "shared-key",
    "endpoint": "https://eastus.openai.azure.com",
    "deployment_name": "gpt-4.1-mini",
    "backups": [
        {"endpoint": "https://westus.openai.azure.com"}  # Inherits everything
    ]
}

# ⚠️  Acceptable but more complex - Different deployment names
config = {
    "api_key": "key",
    "endpoint": "https://eastus.openai.azure.com",
    "deployment_name": "gpt-4.1-mini",
    "backups": [
        {
            "endpoint": "https://westus.openai.azure.com",
            "deployment_name": "gpt-4-mini-west"  # Have to manage different names
        }
    ]
}
```

### 3. Monitor Failover Events
```python
import logging

# Log failover events
status = connector.get_backup_status()
if status['current_index'] > 0:
    logging.warning(
        f"Using backup endpoint (index {status['current_index']}). "
        f"Failed endpoints: {status['failed_endpoints']}"
    )
```

### 4. Test Your Backup Configuration
```python
# Verify all endpoints are configured correctly
async def test_all_endpoints(connector):
    all_configs = connector._get_all_configs()
    
    for config in all_configs:
        print(f"Testing {config['type']} endpoint: {config['endpoint']}")
        # Force switch to this endpoint for testing
        connector.endpoint = config['endpoint']
        connector.deployment_name = config['deployment_name']
        connector.api_key = config['api_key']
        
        try:
            await connector.test_connection()
            print(f"  ✓ Success")
        except Exception as e:
            print(f"  ✗ Failed: {e}")
```

## Limitations

1. **Streaming Failover**: If a stream fails mid-way, the backup starts a new stream from the beginning
2. **No State Sharing**: Each endpoint is independent - no shared state/context
3. **Cost**: Failover means additional API calls when primary fails
4. **Latency**: Failover adds latency (failed request + retry)

## Monitoring & Debugging

```python
# Get detailed status
status = connector.get_backup_status()
print(f"""
Backup Status:
  Total Endpoints: {status['total_endpoints']}
  Current: {status['current_endpoint']} ({status['current_type']})
  Index: {status['current_index']}
  Failed: {', '.join(status['failed_endpoints']) or 'None'}
  Backups Available: {status['available_backups']}
""")

# Current endpoint details
info = connector.get_current_endpoint_info()
print(f"Active Endpoint: {info}")
```

## Environment Variables

You can also use environment variables for backup configuration:

```bash
# Primary
export AZURE_OPENAI_KEY="primary-key"
export AZURE_OPENAI_ENDPOINT="https://eastus.openai.azure.com"
export AZURE_OPENAI_DEPLOYMENT="gpt-4.1-mini"

# Backups (configure in code)
```

Note: Environment variables work for primary only. Backups must be configured in code.

## Summary

- ✅ Automatic failover for service errors, timeouts, and connection issues
- ✅ Supports multiple backup endpoints
- ✅ Minimal configuration changes (just add "backups" list)
- ✅ Works transparently with existing code
- ✅ Can use same or different API keys/deployment names
- ✅ Regional redundancy for disaster recovery
- ✅ Easy to monitor and debug

