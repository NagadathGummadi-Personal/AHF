"""
Handover Tool

Transfers call to human agent.

Version: 1.0.0
"""

from typing import Any, Dict, Optional

from core.tools.interfaces import IToolExecutor
from core.tools.spec import ToolResult, ToolContext

from app.config import Defaults
from app.memory.session import VoiceAgentSession
from .http_client import AsyncHTTPClient


class HandoverTool:
    """
    Tool for transferring calls to human agents.
    
    Implements IToolExecutor from core.tools.
    """
    
    def __init__(
        self,
        handover_url: str = Defaults.HANDOVER_URL,
        timeout_ms: int = 30000,
    ):
        self.name = "HandoverCallToHuman"
        self.description = "Transfer the call to a human agent"
        self._url = handover_url
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
                        "reason": {
                            "type": "string",
                            "description": "Reason for handover"
                        },
                        "call_summary": {
                            "type": "string",
                            "description": "Summary of the call"
                        },
                        "is_direct_handover": {
                            "type": "boolean",
                            "description": "Whether to do direct handover",
                            "default": False
                        },
                        "intent_fulfilled": {
                            "type": "boolean",
                            "description": "Whether the intent was fulfilled",
                            "default": False
                        }
                    },
                    "required": ["reason"]
                }
            }
        }
    
    async def execute(
        self,
        args: Dict[str, Any],
        ctx: Optional[ToolContext] = None,
        session: Optional[VoiceAgentSession] = None,
    ) -> Dict[str, Any]:
        """Execute handover."""
        
        reason = args.get("reason", "User requested handover")
        call_summary = args.get("call_summary", "")
        is_direct = args.get("is_direct_handover", False)
        intent_fulfilled = args.get("intent_fulfilled", False)
        
        # Get dynamic variables for headers
        headers = {}
        if session and session.dynamic_vars:
            dv = session.dynamic_vars
            headers = {
                "guest_number": dv.caller_id,
                "agent_id": dv.agent_id,
                "transfer_to_number": dv.hand_over_number,
                "guest_name": dv.get_guest_display_name(),
                "guest_id": dv.guest_id,
                "x-org-id": dv.org_id,
                "center_id": dv.center_id,
                "caller_id": dv.caller_id,
                "phone_code": dv.phone_code,
            }
        
        body = {
            "is_direct_handover": is_direct,
            "intent_fulfilled": intent_fulfilled,
            "call_summary": call_summary,
            "handover_reason": reason,
        }
        
        # Make API call
        client = await self._get_client()
        response = await client.post(
            self._url,
            headers=headers,
            json_data=body,
        )
        
        if not response.is_success:
            return {
                "success": False,
                "error": response.error or f"Handover failed: {response.status_code}",
            }
        
        return {
            "success": True,
            "message": "Call is being transferred to a human agent.",
            "response": response.data,
        }
    
    async def close(self) -> None:
        """Clean up resources."""
        if self._http_client:
            await self._http_client.close()

