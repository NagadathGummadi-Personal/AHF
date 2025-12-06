"""
Workflow Tools Module.

This module provides tools for workflow-agent interoperability,
allowing workflows to be used as tools by agents.
"""

from .workflow_tool import (
    WorkflowTool,
    WorkflowToolSpec,
    create_workflow_tool,
)

__all__ = [
    "WorkflowTool",
    "WorkflowToolSpec",
    "create_workflow_tool",
]

