"""
Azure OpenAI Connector Implementation.

This module provides the connector for Azure OpenAI Service with backup/failover support.
"""

import os
import asyncio
from typing import Dict, Any, Optional, List
import aiohttp
from ..base.connector import BaseConnector
from ...exceptions import (
    ConfigurationError,
    AuthenticationError,
    ServiceUnavailableError,
    TimeoutError,
    RateLimitError,
    ProviderError,
)
from ...constants import (
    ENV_AZURE_OPENAI_KEY,
    ENV_AZURE_OPENAI_ENDPOINT,
    ENV_AZURE_OPENAI_DEPLOYMENT,
    ENV_AZURE_OPENAI_API_VERSION,
    PROVIDER_AZURE,
)


class AzureConnector(BaseConnector):
    """
    Connector for Azure OpenAI Service with backup/failover support.
    
    Handles authentication, connection management, and request handling
    for Azure OpenAI API endpoints. Supports multiple backup endpoints
    for automatic failover.
    
    Primary Configuration:
        - api_key: Azure OpenAI API key
        - endpoint: Azure OpenAI endpoint URL
        - deployment_name: Deployment name for the model
        - api_version: API version (default: 2024-02-15-preview)
        - timeout: Request timeout in seconds
        - max_retries: Maximum retry attempts
        
    Backup Configuration (optional):
        - backups: List of backup configurations, each containing:
          * endpoint: Backup endpoint URL (different region)
          * deployment_name: Backup deployment name (optional, defaults to primary)
          * api_key: Backup API key (optional, defaults to primary)
          * api_version: Backup API version (optional, defaults to primary)
        
    Example (single endpoint):
        config = {
            "api_key": "...",
            "endpoint": "https://my-resource.openai.azure.com",
            "deployment_name": "gpt-4",
            "api_version": "2024-02-15-preview",
            "timeout": 30
        }
        connector = AzureConnector(config)
    
    Example (with backups):
        config = {
            "api_key": "primary-key",
            "endpoint": "https://eastus-resource.openai.azure.com",
            "deployment_name": "gpt-4.1-mini",
            "backups": [
                {
                    "endpoint": "https://westus-resource.openai.azure.com",
                    # deployment_name defaults to primary
                    # api_key defaults to primary
                },
                {
                    "endpoint": "https://northeurope-resource.openai.azure.com",
                    "deployment_name": "gpt-41-mini",  # Different deployment name
                    "api_key": "different-key"  # Different API key
                }
            ]
        }
        connector = AzureConnector(config)
    """
    
    DEFAULT_API_VERSION = "2024-02-15-preview"
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Azure connector with optional backup endpoints.
        
        Args:
            config: Connector configuration including optional backups
            
        Raises:
            ConfigurationError: If required config is missing
        """
        super().__init__(config)
        
        # Primary configuration
        self.primary_api_key = self._get_api_key()
        self.primary_endpoint = self._get_endpoint()
        self.primary_deployment_name = self._get_deployment_name()
        self.primary_api_version = self._get_api_version()
        
        # Current active configuration (starts with primary)
        self.api_key = self.primary_api_key
        self.endpoint = self.primary_endpoint
        self.deployment_name = self.primary_deployment_name
        self.api_version = self.primary_api_version
        
        # Parse backup configurations
        self.backup_configs = self._parse_backup_configs()
        self.current_config_index = 0  # 0 = primary, 1+ = backups
        self.failed_endpoints: set = set()  # Track failed endpoints
        
        # Session management
        self._session: Optional[aiohttp.ClientSession] = None
    
    def _validate_config(self) -> None:
        """Validate Azure-specific configuration."""
        # Parent class validation
        super()._validate_config()
        
        # Validate Azure-specific fields
        if not self._get_api_key():
            raise ConfigurationError(
                "Azure OpenAI API key not found. Provide 'api_key' in config or set AZURE_OPENAI_KEY environment variable.",
                provider=PROVIDER_AZURE,
                details={"env_var": ENV_AZURE_OPENAI_KEY}
            )
        
        if not self._get_endpoint():
            raise ConfigurationError(
                "Azure OpenAI endpoint not found. Provide 'endpoint' in config or set AZURE_OPENAI_ENDPOINT environment variable.",
                provider=PROVIDER_AZURE,
                details={"env_var": ENV_AZURE_OPENAI_ENDPOINT}
            )
        
        if not self._get_deployment_name():
            raise ConfigurationError(
                "Azure OpenAI deployment name not found. Provide 'deployment_name' in config or set AZURE_OPENAI_DEPLOYMENT environment variable.",
                provider=PROVIDER_AZURE,
                details={"env_var": ENV_AZURE_OPENAI_DEPLOYMENT}
            )
    
    def _get_api_key(self) -> str:
        """Get API key from config or environment."""
        if "api_key" in self.config:
            return self.config["api_key"]
        return os.environ.get(ENV_AZURE_OPENAI_KEY, "")
    
    def _get_endpoint(self) -> str:
        """Get endpoint from config or environment."""
        if "endpoint" in self.config:
            return self.config["endpoint"].rstrip("/")
        endpoint = os.environ.get(ENV_AZURE_OPENAI_ENDPOINT, "")
        return endpoint.rstrip("/") if endpoint else ""
    
    def _get_deployment_name(self) -> str:
        """Get deployment name from config or environment."""
        if "deployment_name" in self.config:
            return self.config["deployment_name"]
        return os.environ.get(ENV_AZURE_OPENAI_DEPLOYMENT, "")
    
    def _get_api_version(self) -> str:
        """Get API version from config or environment."""
        if "api_version" in self.config:
            return self.config["api_version"]
        return os.environ.get(ENV_AZURE_OPENAI_API_VERSION, self.DEFAULT_API_VERSION)
    
    def _parse_backup_configs(self) -> List[Dict[str, str]]:
        """
        Parse backup configurations from config.
        
        Returns:
            List of backup config dicts with endpoint, deployment_name, api_key, api_version
        """
        backups = self.config.get("backups", [])
        if not backups:
            return []
        
        parsed_backups = []
        for i, backup in enumerate(backups):
            if not isinstance(backup, dict):
                continue
            
            # Endpoint is required for backup
            backup_endpoint = backup.get("endpoint", "").rstrip("/")
            if not backup_endpoint:
                continue
            
            # Deployment name defaults to primary
            backup_deployment = backup.get("deployment_name", self.primary_deployment_name)
            
            # API key defaults to primary
            backup_api_key = backup.get("api_key", self.primary_api_key)
            
            # API version defaults to primary
            backup_api_version = backup.get("api_version", self.primary_api_version)
            
            parsed_backups.append({
                "endpoint": backup_endpoint,
                "deployment_name": backup_deployment,
                "api_key": backup_api_key,
                "api_version": backup_api_version,
                "index": i + 1  # 0 is primary
            })
        
        return parsed_backups
    
    def _get_all_configs(self) -> List[Dict[str, Any]]:
        """
        Get all available configurations (primary + backups).
        
        Returns:
            List of config dicts in priority order
        """
        configs = [
            {
                "endpoint": self.primary_endpoint,
                "deployment_name": self.primary_deployment_name,
                "api_key": self.primary_api_key,
                "api_version": self.primary_api_version,
                "index": 0,
                "type": "primary"
            }
        ]
        
        for backup in self.backup_configs:
            configs.append({**backup, "type": "backup"})
        
        return configs
    
    def _switch_to_next_endpoint(self) -> bool:
        """
        Switch to the next available endpoint.
        
        Returns:
            True if switched successfully, False if no more endpoints available
        """
        all_configs = self._get_all_configs()
        
        # Mark current endpoint as failed
        if self.current_config_index < len(all_configs):
            current_endpoint = all_configs[self.current_config_index]["endpoint"]
            self.failed_endpoints.add(current_endpoint)
        
        # Try to find next working endpoint
        for i in range(self.current_config_index + 1, len(all_configs)):
            config = all_configs[i]
            if config["endpoint"] not in self.failed_endpoints:
                # Switch to this config
                self.endpoint = config["endpoint"]
                self.deployment_name = config["deployment_name"]
                self.api_key = config["api_key"]
                self.api_version = config["api_version"]
                self.current_config_index = i
                
                # Close existing session (will be recreated with new config)
                if self._session and not self._session.closed:
                    asyncio.create_task(self._session.close())
                self._session = None
                
                return True
        
        return False
    
    def get_current_endpoint_info(self) -> Dict[str, Any]:
        """
        Get information about currently active endpoint.
        
        Returns:
            Dict with current endpoint info
        """
        all_configs = self._get_all_configs()
        if self.current_config_index < len(all_configs):
            return all_configs[self.current_config_index]
        return {}
    
    def get_backup_status(self) -> Dict[str, Any]:
        """
        Get status of all endpoints (primary + backups).
        
        Returns:
            Status information including failed endpoints
        """
        all_configs = self._get_all_configs()
        return {
            "total_endpoints": len(all_configs),
            "current_index": self.current_config_index,
            "current_endpoint": self.endpoint,
            "current_type": all_configs[self.current_config_index]["type"] if self.current_config_index < len(all_configs) else "unknown",
            "failed_endpoints": list(self.failed_endpoints),
            "available_backups": len(self.backup_configs),
            "has_backups": len(self.backup_configs) > 0
        }
    
    def _build_url(self, operation: str) -> str:
        """
        Build full URL for Azure OpenAI API.
        
        Args:
            operation: API operation (e.g., "chat/completions")
            
        Returns:
            Full URL with deployment and API version
        """
        return (
            f"{self.endpoint}/openai/deployments/{self.deployment_name}/"
            f"{operation}?api-version={self.api_version}"
        )
    
    def _get_session(self) -> aiohttp.ClientSession:
        """
        Get or create aiohttp session (lazy initialization).
        
        Returns:
            Active aiohttp session
        """
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.get_timeout())
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    "api-key": self.api_key,
                    "Content-Type": "application/json",
                }
            )
        return self._session
    
    async def close(self) -> None:
        """
        Close session and clean up resources (optional cleanup).
        """
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    async def test_connection(self) -> bool:
        """
        Test connection by making a simple API call.
        
        Returns:
            True if connection test succeeds
            
        Raises:
            AuthenticationError: If API key is invalid
            ServiceUnavailableError: If service is down
        """
        try:
            # Try to make a minimal chat completion request
            url = self._build_url("chat/completions")
            test_payload = {
                "messages": [{"role": "user", "content": "test"}],
                "max_tokens": 1
            }
            session = self._get_session()
            
            async with session.post(url, json=test_payload) as response:
                if response.status == 401:
                    raise AuthenticationError(
                        "Invalid Azure OpenAI API key",
                        provider=PROVIDER_AZURE,
                        details={"status_code": 401}
                    )
                
                if response.status == 404:
                    raise ConfigurationError(
                        "Azure OpenAI deployment not found. Check endpoint and deployment_name.",
                        provider=PROVIDER_AZURE,
                        details={
                            "status_code": 404,
                            "endpoint": self.endpoint,
                            "deployment": self.deployment_name
                        }
                    )
                
                if response.status == 503:
                    raise ServiceUnavailableError(
                        "Azure OpenAI service unavailable",
                        provider=PROVIDER_AZURE,
                        details={"status_code": 503}
                    )
                
                # Any 2xx or even 4xx (bad request) means connection works
                # We just want to verify auth and connectivity
                return True
        
        except aiohttp.ClientError as e:
            raise ServiceUnavailableError(
                f"Failed to connect to Azure OpenAI: {str(e)}",
                provider=PROVIDER_AZURE,
                details={"error": str(e)}
            )
    
    async def request(
        self,
        endpoint: str,
        payload: Dict[str, Any],
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Make a request to Azure OpenAI API with automatic failover.
        
        If the primary endpoint fails with a service error (503, timeout, etc.),
        automatically tries backup endpoints if configured.
        
        Args:
            endpoint: API operation (e.g., "chat/completions")
            payload: Request payload
            **kwargs: Additional options (including auto_failover=True)
            
        Returns:
            Response dictionary
            
        Raises:
            TimeoutError: If request times out on all endpoints
            RateLimitError: If rate limited
            AuthenticationError: If authentication fails
            ProviderError: For other API errors
        """
        auto_failover = kwargs.get("auto_failover", True)
        last_error = None
        
        # Try current endpoint, then backups if failover is enabled
        while True:
            url = self._build_url(endpoint)
            timeout = kwargs.get("timeout", self.get_timeout())
            session = self._get_session()
            
            current_info = self.get_current_endpoint_info()
            
            try:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                    # Handle error status codes
                    if response.status == 401:
                        raise AuthenticationError(
                            "Authentication failed",
                            provider=PROVIDER_AZURE,
                            details={"status_code": 401, "endpoint": self.endpoint}
                        )
                    
                    if response.status == 429:
                        retry_after = response.headers.get("Retry-After")
                        raise RateLimitError(
                            "Rate limit exceeded",
                            provider=PROVIDER_AZURE,
                            details={"status_code": 429, "endpoint": self.endpoint},
                            retry_after=int(retry_after) if retry_after else None
                        )
                    
                    if response.status == 503:
                        error = ServiceUnavailableError(
                            f"Service temporarily unavailable at {current_info.get('type', 'unknown')} endpoint",
                            provider=PROVIDER_AZURE,
                            details={"status_code": 503, "endpoint": self.endpoint}
                        )
                        
                        # Try failover for 503 errors
                        if auto_failover and self._switch_to_next_endpoint():
                            last_error = error
                            continue  # Retry with backup
                        else:
                            raise error
                    
                    if response.status >= 400:
                        error_body = await response.text()
                        raise ProviderError(
                            f"Azure OpenAI API error: {response.status}",
                            provider=PROVIDER_AZURE,
                            details={
                                "status_code": response.status,
                                "error_body": error_body,
                                "endpoint": self.endpoint
                            }
                        )
                    
                    # Success! Parse and return response
                    return await response.json()
            
            except asyncio.TimeoutError:
                error = TimeoutError(
                    f"Request timed out after {timeout} seconds at {current_info.get('type', 'unknown')} endpoint",
                    provider=PROVIDER_AZURE,
                    details={"timeout_seconds": timeout, "endpoint": self.endpoint}
                )
                
                # Try failover for timeout errors
                if auto_failover and self._switch_to_next_endpoint():
                    last_error = error
                    continue  # Retry with backup
                else:
                    raise error
            
            except aiohttp.ClientError as e:
                error = ProviderError(
                    f"Request failed: {str(e)}",
                    provider=PROVIDER_AZURE,
                    details={"error": str(e), "endpoint": self.endpoint}
                )
                
                # Try failover for connection errors
                if auto_failover and self._switch_to_next_endpoint():
                    last_error = error
                    continue  # Retry with backup
                else:
                    raise error
        
        # Should not reach here, but if we do, raise last error
        if last_error:
            raise last_error
    
    async def stream_request(
        self,
        endpoint: str,
        payload: Dict[str, Any],
        **kwargs: Any
    ):
        """
        Make a streaming request to Azure OpenAI API with automatic failover.
        
        Note: Failover for streaming is best-effort. If a stream fails mid-way,
        it cannot be resumed from the same point. The backup will restart the stream.
        
        Args:
            endpoint: API operation
            payload: Request payload (should have stream=True)
            **kwargs: Additional options (including auto_failover=True)
            
        Yields:
            Response chunks as they arrive
            
        Raises:
            TimeoutError: If request times out on all endpoints
            ProviderError: For API errors
        """
        auto_failover = kwargs.get("auto_failover", True)
        last_error = None
        
        # Ensure streaming is enabled in payload
        payload["stream"] = True
        
        # Try current endpoint, then backups if failover is enabled
        while True:
            url = self._build_url(endpoint)
            timeout = kwargs.get("timeout", self.get_timeout())
            session = self._get_session()
            
            current_info = self.get_current_endpoint_info()
            
            try:
                async with session.post(
                    url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    # Check for errors
                    if response.status == 503:
                        error = ServiceUnavailableError(
                            f"Service unavailable at {current_info.get('type', 'unknown')} endpoint",
                            provider=PROVIDER_AZURE,
                            details={"status_code": 503, "endpoint": self.endpoint}
                        )
                        
                        if auto_failover and self._switch_to_next_endpoint():
                            last_error = error
                            continue  # Retry with backup
                        else:
                            raise error
                    
                    if response.status >= 400:
                        error_body = await response.text()
                        raise ProviderError(
                            f"Azure OpenAI API error: {response.status}",
                            provider=PROVIDER_AZURE,
                            details={
                                "status_code": response.status,
                                "error_body": error_body,
                                "endpoint": self.endpoint
                            }
                        )
                    
                    # Stream chunks as they arrive
                    async for line in response.content:
                        if line:
                            yield line.decode('utf-8')
                    
                    # Stream completed successfully
                    return
            
            except asyncio.TimeoutError:
                error = TimeoutError(
                    f"Stream request timed out after {timeout} seconds",
                    provider=PROVIDER_AZURE,
                    details={"timeout_seconds": timeout, "endpoint": self.endpoint}
                )
                
                if auto_failover and self._switch_to_next_endpoint():
                    last_error = error
                    continue  # Retry with backup
                else:
                    raise error
            
            except aiohttp.ClientError as e:
                error = ProviderError(
                    f"Stream request failed: {str(e)}",
                    provider=PROVIDER_AZURE,
                    details={"error": str(e), "endpoint": self.endpoint}
                )
                
                if auto_failover and self._switch_to_next_endpoint():
                    last_error = error
                    continue  # Retry with backup
                else:
                    raise error
        
        # Should not reach here
        if last_error:
            raise last_error

