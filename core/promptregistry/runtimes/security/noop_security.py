"""
NoOp Prompt Security Implementation.

A security implementation that allows all access.
Use for development/testing or when security is handled externally.
"""

from typing import List

from ...interfaces.prompt_registry_interfaces import (
    IPromptSecurity,
    SecurityContext,
    AccessDecision,
)


class NoOpPromptSecurity(IPromptSecurity):
    """
    NoOp (No Operation) Prompt Security.
    
    Allows all access without any checks.
    Use for development, testing, or when security is handled elsewhere.
    
    Usage:
        security = NoOpPromptSecurity()
        
        # Always returns allowed
        decision = security.can_read("any_label", SecurityContext())
        assert decision.allowed
        
        # All labels pass through filter
        labels = security.filter_accessible(["a", "b", "c"], SecurityContext())
        assert labels == ["a", "b", "c"]
    """
    
    def can_read(
        self,
        label: str,
        context: SecurityContext
    ) -> AccessDecision:
        """Always allows read access."""
        return AccessDecision(
            allowed=True,
            reason="NoOp security - all access allowed"
        )
    
    def can_write(
        self,
        label: str,
        context: SecurityContext
    ) -> AccessDecision:
        """Always allows write access."""
        return AccessDecision(
            allowed=True,
            reason="NoOp security - all access allowed"
        )
    
    def can_delete(
        self,
        label: str,
        context: SecurityContext
    ) -> AccessDecision:
        """Always allows delete access."""
        return AccessDecision(
            allowed=True,
            reason="NoOp security - all access allowed"
        )
    
    def can_admin(
        self,
        label: str,
        context: SecurityContext
    ) -> AccessDecision:
        """Always allows admin access."""
        return AccessDecision(
            allowed=True,
            reason="NoOp security - all access allowed"
        )
    
    def filter_accessible(
        self,
        labels: List[str],
        context: SecurityContext,
        operation: str = "read"
    ) -> List[str]:
        """Returns all labels unchanged."""
        return labels
    
    def get_required_permissions(
        self,
        label: str,
        operation: str
    ) -> List[str]:
        """Returns empty list (no permissions required)."""
        return []

