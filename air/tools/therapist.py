"""
Therapist Tool

Retrieves available therapists for a service.
Uses core.tools.AioHttpExecutor for HTTP operations.

Version: 1.1.0
"""

from typing import Any, Dict, Optional, TYPE_CHECKING

from air.config import Defaults
from .base import BaseHttpTool

if TYPE_CHECKING:
    from air.memory.session import VoiceAgentSession


class TherapistTool(BaseHttpTool):
    """
    Tool for getting therapist availability.
    
    Uses AioHttpExecutor from core.tools for high-performance
    async HTTP with connection pooling.
    """
    
    def __init__(
        self,
        therapist_url: Optional[str] = None,
        timeout_ms: int = 30000,
    ):
        super().__init__(
            name="GetTherapistForService",
            description="Get available therapists for a service",
            url=therapist_url or Defaults.THERAPIST_URL,
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
                    "description": "Service code to get therapists for"
                },
                "date": {
                    "type": "string",
                    "description": "Date for availability (YYYY-MM-DD)"
                },
                "time": {
                    "type": "string",
                    "description": "Preferred time (HH:MM)"
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
        
        if params.get("date"):
            body["date"] = params["date"]
        if params.get("time"):
            body["time"] = params["time"]
        
        return body
    
    def _get_fallback_response(
        self,
        params: Dict[str, Any],
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Fallback mock therapists for development."""
        return {
            "success": True,
            "therapists": [
                {
                    "therapist_id": "TH001",
                    "name": "Any Available",
                    "available": True
                }
            ],
            "_note": "Dummy therapists - API not available",
        }
    
    async def execute(
        self,
        params: Dict[str, Any],
        session: Optional["VoiceAgentSession"] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Execute therapist lookup with validation."""
        service_code = params.get("service_code", "")
        
        if not service_code:
            return {
                "success": False,
                "error": "Service code is required",
            }
        
        return await super().execute(params, session, **kwargs)
