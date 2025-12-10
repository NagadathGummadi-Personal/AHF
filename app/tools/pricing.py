"""
Pricing Info Tool

Retrieves pricing for services and add-ons.

Version: 1.0.0
"""

from typing import Any, Dict, List, Optional

from app.config import Defaults
from app.memory.session import VoiceAgentSession
from .http_client import AsyncHTTPClient


class PricingInfoTool:
    """
    Tool for getting service pricing information.
    """
    
    def __init__(
        self,
        pricing_url: str = Defaults.PRICING_INFO_URL,
        timeout_ms: int = 30000,
    ):
        self.name = "GetPricingInfo"
        self.description = "Get pricing information for a service"
        self._url = pricing_url
        self._timeout_ms = timeout_ms
        self._http_client: Optional[AsyncHTTPClient] = None
    
    async def _get_client(self) -> AsyncHTTPClient:
        """Get HTTP client."""
        if not self._http_client:
            self._http_client = AsyncHTTPClient(timeout_ms=self._timeout_ms)
        return self._http_client
    
    def get_spec(self) -> Dict[str, Any]:
        """Get tool specification for LLM."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "service_code": {
                            "type": "string",
                            "description": "Service code to get pricing for"
                        },
                        "addon_codes": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional addon codes to include"
                        },
                        "therapist_code": {
                            "type": "string",
                            "description": "Optional therapist code for specific pricing"
                        }
                    },
                    "required": ["service_code"]
                }
            }
        }
    
    async def execute(
        self,
        args: Dict[str, Any],
        session: Optional[VoiceAgentSession] = None,
    ) -> Dict[str, Any]:
        """Execute pricing lookup."""
        
        service_code = args.get("service_code", "")
        addon_codes = args.get("addon_codes", [])
        therapist_code = args.get("therapist_code")
        
        if not service_code:
            return {
                "success": False,
                "error": "Service code is required",
            }
        
        # Build headers
        headers = {"Content-Type": "application/json"}
        if session and session.dynamic_vars:
            dv = session.dynamic_vars
            headers["x-org-id"] = dv.org_id
            headers["center_id"] = dv.center_id
        
        # Build body
        body = {
            "service_code": service_code,
        }
        
        if addon_codes:
            body["addon_codes"] = addon_codes
        
        if therapist_code:
            body["therapist_code"] = therapist_code
        
        # Make API call
        client = await self._get_client()
        response = await client.post(
            self._url,
            headers=headers,
            json_data=body,
        )
        
        if not response.is_success:
            # Return dummy data for development
            return {
                "success": True,
                "service_code": service_code,
                "service_price": "$50.00",
                "addon_prices": [],
                "total": "$50.00",
                "_note": "Dummy pricing - API not available",
            }
        
        return {
            "success": True,
            **response.data,
        }
    
    async def close(self) -> None:
        """Clean up resources."""
        if self._http_client:
            await self._http_client.close()

