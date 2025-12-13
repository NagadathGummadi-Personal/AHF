"""
Pricing Info Tool

Retrieves pricing for services and add-ons.
Uses core.tools.AioHttpExecutor for HTTP operations.

Version: 1.1.0
"""

from typing import Any, Dict, Optional, TYPE_CHECKING

from air.config import Defaults
from .base import BaseHttpTool

if TYPE_CHECKING:
    from air.memory.session import VoiceAgentSession


class PricingInfoTool(BaseHttpTool):
    """
    Tool for getting service pricing information.
    
    Uses AioHttpExecutor from core.tools for high-performance
    async HTTP with connection pooling.
    """
    
    def __init__(
        self,
        pricing_url: Optional[str] = None,
        timeout_ms: int = 30000,
    ):
        super().__init__(
            name="GetPricingInfo",
            description="Get pricing information for a service",
            url=pricing_url or Defaults.PRICING_INFO_URL,
            method="POST",
            timeout_ms=timeout_ms,
        )
    
    def get_parameters_schema(self) -> Dict[str, Any]:
        """Get JSON Schema for tool parameters."""
        return {
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
    
    def _build_request_body(
        self,
        params: Dict[str, Any],
        session: Optional["VoiceAgentSession"] = None,
    ) -> Dict[str, Any]:
        """Build request body from params."""
        body = {
            "service_code": params.get("service_code", ""),
        }
        
        if params.get("addon_codes"):
            body["addon_codes"] = params["addon_codes"]
        
        if params.get("therapist_code"):
            body["therapist_code"] = params["therapist_code"]
        
        return body
    
    def _get_fallback_response(
        self,
        params: Dict[str, Any],
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Fallback mock pricing for development."""
        return {
            "success": True,
            "service_code": params.get("service_code", ""),
            "service_price": "$50.00",
            "addon_prices": [],
            "total": "$50.00",
            "_note": "Dummy pricing - API not available",
        }
    
    async def execute(
        self,
        params: Dict[str, Any],
        session: Optional["VoiceAgentSession"] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Execute pricing lookup with validation."""
        service_code = params.get("service_code", "")
        
        if not service_code:
            return {
                "success": False,
                "error": "Service code is required",
            }
        
        return await super().execute(params, session, **kwargs)
