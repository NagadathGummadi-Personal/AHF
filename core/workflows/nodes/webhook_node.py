"""
Webhook Node Implementation Module.

This module provides a node that makes HTTP webhook calls.
"""

import logging
from typing import Any, Dict, List, Optional

from ..interfaces import IWorkflowContext
from ..enum import NodeType
from ..spec import NodeSpec
from ..exceptions import NodeExecutionError, WebhookError
from .base_node import BaseNode

logger = logging.getLogger(__name__)


class WebhookNode(BaseNode):
    """
    A node that makes HTTP webhook/API calls.
    
    Configuration:
        url: The URL to call
        method: HTTP method (GET, POST, PUT, DELETE, PATCH) - default: POST
        headers: Dictionary of headers to include
        body_template: Template for request body
        body_key: Key in input to use as body
        timeout: Request timeout in seconds (default: 30)
        retry_on_error: Whether to retry on HTTP errors (default: False)
        expected_status: Expected status codes (default: [200, 201, 202])
        response_type: How to parse response (json, text, binary)
    """
    
    def __init__(self, spec: NodeSpec):
        """
        Initialize the webhook node.
        
        Args:
            spec: Node specification.
        """
        if spec.node_type != NodeType.WEBHOOK:
            spec.node_type = NodeType.WEBHOOK
        
        super().__init__(spec)
        
        self._url = self._config.get("url", "")
        self._method = self._config.get("method", "POST").upper()
        self._headers = self._config.get("headers", {})
        self._timeout = self._config.get("timeout", 30)
        self._expected_status = self._config.get("expected_status", [200, 201, 202])
        self._response_type = self._config.get("response_type", "json")
    
    async def execute(
        self,
        input_data: Any,
        context: IWorkflowContext,
    ) -> Any:
        """
        Make the webhook call.
        
        Args:
            input_data: Input from previous node.
            context: Workflow execution context.
            
        Returns:
            Response from the webhook.
        """
        logger.info(f"Executing webhook node: {self._name}")
        
        # Resolve input
        resolved_input = self._resolve_input(context, input_data)
        
        # Build URL (support template variables)
        url = self._build_url(resolved_input, context)
        
        # Build headers
        headers = self._build_headers(resolved_input, context)
        
        # Build body
        body = self._build_body(resolved_input, context)
        
        try:
            response = await self._make_request(url, headers, body)
            
            logger.debug(f"Webhook node {self._name} completed successfully")
            return response
            
        except WebhookError:
            raise
        except Exception as e:
            logger.error(f"Webhook node {self._name} failed: {e}")
            raise WebhookError(
                f"Webhook call failed: {e}",
                url=url,
                details={"error": str(e)},
            ) from e
    
    def _build_url(self, input_data: Any, context: IWorkflowContext) -> str:
        """Build the URL with template substitution."""
        url = self._url
        
        # Substitute variables from input
        if isinstance(input_data, dict):
            for key, value in input_data.items():
                url = url.replace(f"{{{key}}}", str(value))
        
        # Substitute context variables
        for key, value in context.variables.items():
            url = url.replace(f"{{ctx.{key}}}", str(value))
        
        return url
    
    def _build_headers(
        self,
        input_data: Any,
        context: IWorkflowContext,
    ) -> Dict[str, str]:
        """Build request headers."""
        headers = dict(self._headers)
        
        # Add content-type if not present
        if "Content-Type" not in headers and self._method in ("POST", "PUT", "PATCH"):
            headers["Content-Type"] = "application/json"
        
        # Substitute variables
        for key, value in headers.items():
            if isinstance(value, str) and "{" in value:
                if isinstance(input_data, dict):
                    for ik, iv in input_data.items():
                        value = value.replace(f"{{{ik}}}", str(iv))
                headers[key] = value
        
        return headers
    
    def _build_body(self, input_data: Any, context: IWorkflowContext) -> Any:
        """Build request body."""
        body_template = self._config.get("body_template")
        body_key = self._config.get("body_key")
        
        if body_template:
            # Use template
            import json
            if isinstance(body_template, str):
                body = body_template
                if isinstance(input_data, dict):
                    for key, value in input_data.items():
                        body = body.replace(f"{{{key}}}", json.dumps(value) if isinstance(value, (dict, list)) else str(value))
                return body
            return body_template
        
        if body_key and isinstance(input_data, dict):
            return input_data.get(body_key)
        
        return input_data
    
    async def _make_request(
        self,
        url: str,
        headers: Dict[str, str],
        body: Any,
    ) -> Any:
        """Make the HTTP request."""
        try:
            import aiohttp
        except ImportError:
            # Fallback to httpx if aiohttp not available
            try:
                import httpx
                return await self._make_request_httpx(url, headers, body)
            except ImportError:
                raise WebhookError(
                    "No HTTP client available. Install aiohttp or httpx.",
                    url=url,
                )
        
        import json
        
        async with aiohttp.ClientSession() as session:
            # Prepare body
            if isinstance(body, (dict, list)):
                body_data = json.dumps(body)
            else:
                body_data = body
            
            # Make request based on method
            method = getattr(session, self._method.lower())
            
            async with method(
                url,
                headers=headers,
                data=body_data if self._method in ("POST", "PUT", "PATCH") else None,
                timeout=aiohttp.ClientTimeout(total=self._timeout),
            ) as response:
                
                # Check status
                if response.status not in self._expected_status:
                    error_body = await response.text()
                    raise WebhookError(
                        f"Unexpected status code: {response.status}",
                        url=url,
                        status_code=response.status,
                        details={"response_body": error_body[:500]},
                    )
                
                # Parse response
                return await self._parse_response(response)
    
    async def _make_request_httpx(
        self,
        url: str,
        headers: Dict[str, str],
        body: Any,
    ) -> Any:
        """Make request using httpx."""
        import httpx
        import json
        
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            # Prepare body
            if isinstance(body, (dict, list)):
                json_body = body
                data_body = None
            else:
                json_body = None
                data_body = body
            
            response = await client.request(
                self._method,
                url,
                headers=headers,
                json=json_body,
                content=data_body if json_body is None else None,
            )
            
            # Check status
            if response.status_code not in self._expected_status:
                raise WebhookError(
                    f"Unexpected status code: {response.status_code}",
                    url=url,
                    status_code=response.status_code,
                    details={"response_body": response.text[:500]},
                )
            
            # Parse response
            if self._response_type == "json":
                return response.json()
            elif self._response_type == "binary":
                return response.content
            else:
                return response.text
    
    async def _parse_response(self, response) -> Any:
        """Parse the response based on response_type."""
        if self._response_type == "json":
            return await response.json()
        elif self._response_type == "binary":
            return await response.read()
        else:
            return await response.text()
    
    async def validate(self, context: IWorkflowContext) -> List[str]:
        """Validate webhook node configuration."""
        errors = await super().validate(context)
        
        if not self._url:
            errors.append(
                f"Webhook node {self._name}: url is required"
            )
        
        if self._method not in ("GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"):
            errors.append(
                f"Webhook node {self._name}: Invalid HTTP method: {self._method}"
            )
        
        return errors



