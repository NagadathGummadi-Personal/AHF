"""
Handover Tool

Transfers call to human agent.
Uses core.tools.AioHttpExecutor for HTTP operations.

Version: 1.1.0
"""

from typing import Any, Dict, Optional, TYPE_CHECKING

from air.config import Defaults
from .base import BaseHttpTool

if TYPE_CHECKING:
    from air.memory.session import VoiceAgentSession


class HandoverTool(BaseHttpTool):
    """
    Tool for transferring calls to human agents.
    
    Uses AioHttpExecutor from core.tools for high-performance
    async HTTP with connection pooling.
    """
    
    def __init__(
        self,
        handover_url: Optional[str] = None,
        timeout_ms: int = 30000,
    ):
        super().__init__(
            name="HandoverCallToHuman",
            description="Transfer the call to a human agent",
            url=handover_url or Defaults.HANDOVER_URL,
            method="POST",
            timeout_ms=timeout_ms,
        )
    
    def get_parameters_schema(self) -> Dict[str, Any]:
        """Get JSON Schema for tool parameters."""
        return {
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
    
    def _build_headers(
        self,
        session: Optional["VoiceAgentSession"] = None,
    ) -> Dict[str, str]:
        """Build headers with session-specific values."""
        headers = {"Content-Type": "application/json"}
        
        if session and session.dynamic_vars:
            dv = session.dynamic_vars
            headers.update({
                "guest_number": str(getattr(dv, 'caller_id', '')),
                "agent_id": str(getattr(dv, 'agent_id', '')),
                "transfer_to_number": str(getattr(dv, 'hand_over_number', '')),
                "guest_name": dv.get_guest_display_name() if hasattr(dv, 'get_guest_display_name') else '',
                "guest_id": str(getattr(dv, 'guest_id', '')),
                "x-org-id": str(getattr(dv, 'org_id', '')),
                "center_id": str(getattr(dv, 'center_id', '')),
                "caller_id": str(getattr(dv, 'caller_id', '')),
                "phone_code": str(getattr(dv, 'phone_code', '')),
            })
        
        return headers
    
    def _build_request_body(
        self,
        params: Dict[str, Any],
        session: Optional["VoiceAgentSession"] = None,
    ) -> Dict[str, Any]:
        """Build request body from params."""
        return {
            "is_direct_handover": params.get("is_direct_handover", False),
            "intent_fulfilled": params.get("intent_fulfilled", False),
            "call_summary": params.get("call_summary", ""),
            "handover_reason": params.get("reason", "User requested handover"),
        }
    
    def _process_response(
        self,
        response: Dict[str, Any],
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Process handover response."""
        status_code = response.get("status_code", 0)
        data = response.get("response", {})
        
        if 200 <= status_code < 300:
            return {
                "success": True,
                "message": "Call is being transferred to a human agent.",
                "response": data,
            }
        else:
            return {
                "success": False,
                "error": f"Handover failed: HTTP {status_code}",
            }
    
    def _get_fallback_response(
        self,
        params: Dict[str, Any],
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Fallback when handover API fails."""
        return {
            "success": False,
            "error": error or "Handover API unavailable",
        }
