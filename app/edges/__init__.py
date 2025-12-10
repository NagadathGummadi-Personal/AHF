"""
Workflow Edges Module

Edge implementations for workflow routing.
All edges implement IEdge from core.workflows.interfaces.
"""

from .base import BaseEdge, EdgeCondition
from .unconditional import UnconditionalEdge
from .booking_edge import BookingEdge
from .service_confirmed_edge import ServiceConfirmedEdge
from .guidelines_complete_edge import GuidelinesCompleteEdge
from .fallback_edge import FallbackEdge

__all__ = [
    "BaseEdge",
    "EdgeCondition",
    "UnconditionalEdge",
    "BookingEdge",
    "ServiceConfirmedEdge",
    "GuidelinesCompleteEdge",
    "FallbackEdge",
]

