"""
KB Search Tool

Knowledge base search for service matching.
Uses core.tools.AioHttpExecutor for HTTP operations.

Version: 1.1.0
"""

from typing import Any, Dict, Optional, TYPE_CHECKING

from air.config import Defaults
from .base import BaseHttpTool

if TYPE_CHECKING:
    from air.memory.session import VoiceAgentSession


class KBSearchTool(BaseHttpTool):
    """
    Tool for searching the knowledge base.
    
    Uses AioHttpExecutor from core.tools for high-performance
    async HTTP with connection pooling.
    
    Used for:
    - Service name matching
    - FAQ retrieval
    - Policy lookup
    """
    
    def __init__(
        self,
        kb_url: Optional[str] = None,
        timeout_ms: int = 5000,  # Lower timeout for KB search
    ):
        super().__init__(
            name="KBSearch",
            description="Search the knowledge base for information",
            url=kb_url or Defaults.KB_SEARCH_URL,
            method="POST",
            timeout_ms=timeout_ms,
        )
    
    def get_parameters_schema(self) -> Dict[str, Any]:
        """Get JSON Schema for tool parameters."""
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query"
                },
                "search_type": {
                    "type": "string",
                    "enum": ["service", "faq", "policy"],
                    "description": "Type of search",
                    "default": "service"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum results to return",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    
    def _build_request_body(
        self,
        params: Dict[str, Any],
        session: Optional["VoiceAgentSession"] = None,
    ) -> Dict[str, Any]:
        """Build request body from params."""
        return {
            "query": params.get("query", ""),
            "search_type": params.get("search_type", "service"),
            "limit": params.get("limit", 5),
        }
    
    def _get_fallback_response(
        self,
        params: Dict[str, Any],
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Fallback mock KB results for development."""
        query = params.get("query", "")
        return {
            "success": True,
            "results": [
                {
                    "service_id": f"ZENID{hash(query) % 10000:04d}",
                    "service_name": query.title(),
                    "score": 0.95,
                }
            ],
            "_note": "Dummy KB results - API not available",
        }
    
    async def execute(
        self,
        params: Dict[str, Any],
        session: Optional["VoiceAgentSession"] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Execute KB search with validation."""
        query = params.get("query", "")
        
        if not query:
            return {
                "success": False,
                "error": "Query is required",
            }
        
        return await super().execute(params, session, **kwargs)
    
    async def search_service(
        self,
        service_name: str,
        session: Optional["VoiceAgentSession"] = None,
    ) -> Dict[str, str]:
        """
        Search for service codes by name.
        
        Convenience method for service matching.
        
        Returns:
            Mapping of service_name -> service_code
        """
        result = await self.execute(
            {"query": service_name, "search_type": "service"},
            session=session,
        )
        
        if not result.get("success"):
            return {}
        
        mapping = {}
        for item in result.get("results", []):
            mapping[item.get("service_name", "")] = item.get("service_id", "")
        
        return mapping
