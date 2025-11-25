"""
Base Connector for LLM Providers.

This module provides the abstract base class for all LLM provider connectors.
Connectors handle low-level communication with provider APIs.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import asyncio
from ...exceptions import (
    ServiceUnavailableError,
    TimeoutError,
    RateLimitError,
)
from ...constants import (
    DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_MAX_RETRIES,
    DEFAULT_RETRY_DELAY_SECONDS,
    DEFAULT_BACKOFF_FACTOR,
    CONFIG_TIMEOUT,
    CONFIG_MAX_RETRIES,
    CONFIG_RETRY_DELAY,
    ERROR_MSG_REQUEST_FAILED_ALL_RETRIES,
)


class BaseConnector(ABC):
    """
    Abstract base class for LLM provider connectors.
    
    Connectors handle authentication, request handling, and provider-specific
    protocol details. No explicit connection lifecycle needed for HTTP APIs.
    
    Attributes:
        config: Connector configuration
        
    Subclasses must implement:
        - request() - make API requests
        - Optional: test_connection() - verify credentials/connectivity
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the base connector.
        
        Args:
            config: Connector configuration including:
                - timeout: Request timeout in seconds
                - max_retries: Maximum retry attempts
                - retry_delay: Delay between retries
                
        Raises:
            ConfigurationError: If required config is missing
        """
        self.config = config
        self._validate_config()
    
    def _validate_config(self) -> None:
        """
        Validate connector configuration.
        
        Subclasses can override to add provider-specific validation.
        
        Raises:
            ConfigurationError: If configuration is invalid
        """
        # Base validation - subclasses add more
        pass
    
    async def test_connection(self) -> bool:
        """
        Test connectivity and authentication (optional).
        
        Default implementation makes a test request.
        Subclasses can override for provider-specific health checks.
        
        Returns:
            True if connection test succeeds
            
        Raises:
            AuthenticationError: If credentials are invalid
            ServiceUnavailableError: If service is down
            
        Example:
            if await connector.test_connection():
                print("Connector ready")
        """
        # Default: assume ready if config is valid
        return True
    
    @abstractmethod
    async def request(
        self,
        endpoint: str,
        payload: Dict[str, Any],
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Make a request to the provider API.
        
        This is the core method that sends requests to the provider.
        Subclasses implement provider-specific request logic.
        
        Args:
            endpoint: API endpoint or operation
            payload: Request payload
            **kwargs: Additional request options
            
        Returns:
            Response dictionary from provider
            
        Raises:
            TimeoutError: If request times out
            RateLimitError: If rate limited
            ServiceUnavailableError: If service unavailable
            
        Example:
            response = await connector.request(
                "chat/completions",
                {"model": "gpt-4", "messages": [...]},
                timeout=30
            )
        """
        pass
    
    async def request_with_retry(
        self,
        endpoint: str,
        payload: Dict[str, Any],
        max_retries: Optional[int] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Make a request with automatic retry logic.
        
        Implements exponential backoff for transient failures.
        
        Args:
            endpoint: API endpoint
            payload: Request payload
            max_retries: Maximum retry attempts (uses config default if None)
            **kwargs: Additional request options
            
        Returns:
            Response dictionary
            
        Raises:
            TimeoutError: If all retries fail
            RateLimitError: If rate limited
        """
        if max_retries is None:
            max_retries = self.config.get(CONFIG_MAX_RETRIES, DEFAULT_MAX_RETRIES)
        
        retry_delay = self.config.get(CONFIG_RETRY_DELAY, DEFAULT_RETRY_DELAY_SECONDS)
        backoff_factor = DEFAULT_BACKOFF_FACTOR
        
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                return await self.request(endpoint, payload, **kwargs)
            
            except (ServiceUnavailableError, TimeoutError) as e:
                last_exception = e
                
                if attempt < max_retries:
                    # Exponential backoff
                    delay = retry_delay * (backoff_factor ** attempt)
                    await asyncio.sleep(delay)
                    continue
                
                # Last attempt failed
                raise
            
            except RateLimitError as e:
                # For rate limits, respect retry_after if provided
                if hasattr(e, 'retry_after') and e.retry_after:
                    await asyncio.sleep(e.retry_after)
                else:
                    delay = retry_delay * (backoff_factor ** attempt)
                    await asyncio.sleep(delay)
                
                if attempt >= max_retries:
                    raise
                continue
        
        # Should not reach here, but just in case
        if last_exception:
            raise last_exception
        
        raise Exception(ERROR_MSG_REQUEST_FAILED_ALL_RETRIES)
    
    def get_timeout(self) -> int:
        """
        Get the configured timeout.
        
        Returns:
            Timeout in seconds
        """
        return self.config.get(CONFIG_TIMEOUT, DEFAULT_TIMEOUT_SECONDS)
    
    def get_max_retries(self) -> int:
        """
        Get the configured maximum retries.
        
        Returns:
            Maximum retry attempts
        """
        return self.config.get(CONFIG_MAX_RETRIES, DEFAULT_MAX_RETRIES)

