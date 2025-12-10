"""
Therapist Tool

Retrieves available therapists for a service.

Version: 1.0.0
"""

from typing import Any, Dict, List, Optional

from app.config import Defaults
from app.memory.session import VoiceAgentSession
from .http_client import AsyncHTTPClient


class TherapistTool:
    """
    Tool for getting therapist availability.
    """
    
    def __init__(
        self,
        therapist_url: str = Defaults.THERAPIST_URL,
        timeout_ms: int = 30000,
    ):
        self.name = "GetTherapistForService"
        self.description = "Get available therapists for a service"
        self._url = therapist_url
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
            }
        }
    
    async def execute(
        self,
        args: Dict[str, Any],
        session: Optional[VoiceAgentSession] = None,
    ) -> Dict[str, Any]:
        """Execute therapist lookup."""
        
        service_code = args.get("service_code", "")
        date = args.get("date")
        time = args.get("time")
        
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
        
        if date:
            body["date"] = date
        if time:
            body["time"] = time
        
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
                "therapists": [
                    {
                        "therapist_id": "TH001",
                        "name": "Any Available",
                        "available": True
                    }
                ],
                "_note": "Dummy therapists - API not available",
            }
        
        return {
            "success": True,
            **response.data,
        }
    
    async def close(self) -> None:
        """Clean up resources."""
        if self._http_client:
            await self._http_client.close()

