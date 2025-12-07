"""
Workflow Interfaces

This module defines all interfaces for the workflow system.
"""

from .workflow_interfaces import (
    # Core interfaces
    INode,
    IEdge,
    IWorkflow,
    # Registry interfaces
    IWorkflowStorage,
    IWorkflowRegistry,
    # Execution interfaces
    IWorkflowExecutor,
    INodeExecutor,
    # Formatter interface
    IIOFormatter,
)

__all__ = [
    # Core interfaces
    "INode",
    "IEdge",
    "IWorkflow",
    # Registry interfaces
    "IWorkflowStorage",
    "IWorkflowRegistry",
    # Execution interfaces
    "IWorkflowExecutor",
    "INodeExecutor",
    # Formatter interface
    "IIOFormatter",
]
