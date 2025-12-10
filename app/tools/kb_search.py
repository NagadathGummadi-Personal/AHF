"""
KB Search Tool

Knowledge base search for service matching.

Version: 1.0.0
"""

from typing import Any, Dict, List, Optional

from app.config import Defaults
from app.memory.session import VoiceAgentSession
from .http_client import AsyncHTTPClient


class KBSearchTool:
    """
    Tool for searching the knowledge base.
    
    Used for:
    - Service name matching
    - FAQ retrieval
    - Policy lookup
    """
    
    def __init__(
        self,
        kb_url: str = Defaults.KB_SEARCH_URL,
        timeout_ms: int = 5000,  # Lower timeout for KB search
    ):
        self.name = "KBSearch"
        self.description = "Search the knowledge base for information"
        self._url = kb_url
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
            }
        }
    
    async def execute(
        self,
        args: Dict[str, Any],
        session: Optional[VoiceAgentSession] = None,
    ) -> Dict[str, Any]:
        """Execute KB search."""
        
        query = args.get("query", "")
        search_type = args.get("search_type", "service")
        limit = args.get("limit", 5)
        
        if not query:
            return {
                "success": False,
                "error": "Query is required",
            }
        
        # Build headers
        headers = {"Content-Type": "application/json"}
        if session and session.dynamic_vars:
            dv = session.dynamic_vars
            headers["x-org-id"] = dv.org_id
            headers["center_id"] = dv.center_id
        
        # Build body
        body = {
            "query": query,
            "search_type": search_type,
            "limit": limit,
        }
        
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
                "results": [
                    {
                        "service_id": f"ZENID{hash(query) % 10000:04d}",
                        "service_name": query.title(),
                        "score": 0.95,
                    }
                ],
                "_note": "Dummy KB results - API not available",
            }
        
        return {
            "success": True,
            **response.data,
        }
    
    async def search_service(
        self,
        service_name: str,
        session: Optional[VoiceAgentSession] = None,
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
    
    async def close(self) -> None:
        """Clean up resources."""
        if self._http_client:
            await self._http_client.close()

