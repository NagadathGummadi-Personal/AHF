"""
Fallback Edge

Edge for routing to fallback agent on errors or deviations.

Version: 1.0.0
"""

from typing import Any, Dict

from .base import BaseEdge, EdgeCondition


class FallbackEdge(BaseEdge):
    """
    Edge for fallback/error routing.
    
    Triggers when:
    - Node execution fails
    - User deviates from current flow
    - Unknown intent detected
    """
    
    def __init__(
        self,
        edge_id: str = "fallback_edge",
        source_node: str = "any",  # Can be from any node
        target_node: str = "fallback_agent",
        **kwargs,
    ):
        super().__init__(
            edge_id=edge_id,
            source_node=source_node,
            target_node=target_node,
            name="Fallback Edge",
            description="Route to fallback agent on errors or deviations",
            **kwargs,
        )
    
    def should_traverse(self, context: Dict[str, Any]) -> bool:
        """
        Check if fallback is needed.
        
        Conditions:
        - Node result has error
        - User deviated from flow
        - Unknown intent
        """
        node_output = context.get("node_output", {})
        
        # Check for error
        if context.get("error"):
            return True
        
        if node_output.get("error"):
            return True
        
        # Check for deviation signal
        if context.get("deviation_detected"):
            return True
        
        # Check for unknown intent that needs handling
        intent = node_output.get("detected_intent", "")
        if intent == "UNKNOWN" and context.get("requires_fallback"):
            return True
        
        return False


class ErrorFallbackEdge(BaseEdge):
    """
    Edge specifically for error handling.
    
    Routes to fallback with error context.
    """
    
    def __init__(
        self,
        edge_id: str = "error_fallback_edge",
        source_node: str = "any",
        target_node: str = "fallback_agent",
        **kwargs,
    ):
        super().__init__(
            edge_id=edge_id,
            source_node=source_node,
            target_node=target_node,
            name="Error Fallback Edge",
            description="Route to fallback on node errors",
            **kwargs,
        )
    
    def should_traverse(self, context: Dict[str, Any]) -> bool:
        """Check if there's an error to handle."""
        return bool(context.get("error")) or bool(context.get("node_output", {}).get("error"))
    
    def transform_data(self, source_output: Any) -> Dict[str, Any]:
        """Add error context to output."""
        result = super().transform_data(source_output)
        
        if isinstance(result, dict) and isinstance(source_output, dict):
            result["error_context"] = {
                "error": source_output.get("error"),
                "source_node": self._source_node,
            }
        
        return result

