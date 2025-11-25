"""
No-Op Response Parser.

Returns minimal response without parsing (for debugging/testing).
"""

from typing import Any, Dict, Optional
from ...interfaces.llm_interfaces import IResponseParser
from ...spec.llm_result import LLMResponse, LLMStreamChunk
from ...spec.llm_schema import ModelMetadata


class NoOpResponseParser(IResponseParser):
    """
    No-op implementation of IResponseParser.
    
    Returns raw content without parsing. Useful for:
    - Debugging raw API responses
    - Testing
    - Providers with non-standard response formats
    
    Usage:
        parser = NoOpResponseParser()
        response = parser.parse_response(raw_response, start_time, metadata)
    """
    
    def parse_response(
        self,
        response: Dict[str, Any],
        start_time: float,
        metadata: ModelMetadata
    ) -> LLMResponse:
        """Return raw response as content."""
        import json
        return LLMResponse(
            content=json.dumps(response, indent=2),
            role="assistant",
            metadata={"raw": True}
        )
    
    def parse_stream_chunk(
        self,
        chunk_data: Dict[str, Any],
        metadata: ModelMetadata
    ) -> Optional[LLMStreamChunk]:
        """Return raw chunk as content."""
        import json
        return LLMStreamChunk(
            content=json.dumps(chunk_data),
            is_final=False
        )

