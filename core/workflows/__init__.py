"""
Workflows Module

A comprehensive workflow system for orchestrating AI agents, tools, and prompts.

Version: 1.0.0

Components:
- Node: Fundamental building block containing agents, tools, or prompts
- Edge: Connections between nodes with conditional routing
- Workflow: Container for nodes and edges forming a directed graph

Features:
- Pluggable design for future components
- Input/Output type specifications with formatter support
- Background agents for monitoring
- User-provided additional prompts
- Dynamic variable assignments
- Local file-based storage (JSON/YAML)
- Version management with immutability

Usage:
    from core.workflows import (
        NodeBuilder, EdgeBuilder, WorkflowBuilder,
        LocalWorkflowRegistry,
        NodeSpec, EdgeSpec, WorkflowSpec,
        IOType, NodeType, EdgeType,
    )
    
    # Build an agent node
    greeting_node = (NodeBuilder()
        .with_id("greeting")
        .with_name("Greeting Node")
        .with_agent(greeting_agent)
        .with_input_type(IOType.TEXT)
        .with_output_type(IOType.TEXT)
        .build())
    
    # Build a tool node
    lookup_node = (NodeBuilder()
        .with_id("lookup")
        .with_name("Database Lookup")
        .with_tool(db_tool)
        .build())
    
    # Build workflow
    workflow = (WorkflowBuilder()
        .with_id("chat-flow")
        .with_name("Chat Flow")
        .add_node(greeting_node)
        .add_node(lookup_node)
        .connect("greeting", "lookup")
        .set_start_node("greeting")
        .build())
    
    # Save to registry
    registry = LocalWorkflowRegistry(storage_path=".workflows")
    await registry.save_workflow("chat-flow", workflow)
"""

# =============================================================================
# ENUMS
# =============================================================================

from .enum import (
    # Status
    WorkflowStatus,
    ExecutionState,
    # Node types
    NodeType,
    # Edge types
    EdgeType,
    # IO types
    IOType,
    IOFormat,
    # Prompt configuration
    PromptPrecedence,
    PromptMergeStrategy,
    # Background agents
    BackgroundAgentMode,
    # Conditions
    ConditionOperator,
    ConditionJoinOperator,
)

# =============================================================================
# SPEC MODELS
# =============================================================================

from .spec import (
    # IO Types
    IOTypeSpec,
    InputSpec,
    OutputSpec,
    # Node models
    NodeMetadata,
    NodeConfig,
    BackgroundAgentConfig,
    UserPromptConfig,
    NodeSpec,
    NodeResult,
    NodeVersion,
    NodeEntry,
    # Edge models
    EdgeCondition,
    EdgeMetadata,
    EdgeConfig,
    EdgeSpec,
    EdgeVersion,
    EdgeEntry,
    # Workflow models
    WorkflowMetadata,
    WorkflowConfig,
    WorkflowSpec,
    WorkflowVersion,
    WorkflowEntry,
    WorkflowExecutionContext,
    WorkflowResult,
    # Variable assignment
    NodeVariableAssignment,
    NodeDynamicVariableConfig,
)

# =============================================================================
# INTERFACES
# =============================================================================

from .interfaces import (
    INode,
    IEdge,
    IWorkflow,
    IWorkflowStorage,
    IWorkflowRegistry,
    IWorkflowExecutor,
    INodeExecutor,
    IIOFormatter,
)

# =============================================================================
# RUNTIMES
# =============================================================================

from .runtimes import (
    BaseWorkflowRegistry,
    LocalWorkflowRegistry,
    LocalWorkflowStorage,
)

# =============================================================================
# BUILDERS
# =============================================================================

from .builders import (
    NodeBuilder,
    EdgeBuilder,
    WorkflowBuilder,
)

# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Enums
    "WorkflowStatus",
    "ExecutionState",
    "NodeType",
    "EdgeType",
    "IOType",
    "IOFormat",
    "PromptPrecedence",
    "PromptMergeStrategy",
    "BackgroundAgentMode",
    "ConditionOperator",
    "ConditionJoinOperator",
    # IO Types
    "IOTypeSpec",
    "InputSpec",
    "OutputSpec",
    # Node models
    "NodeMetadata",
    "NodeConfig",
    "BackgroundAgentConfig",
    "UserPromptConfig",
    "NodeSpec",
    "NodeResult",
    "NodeVersion",
    "NodeEntry",
    # Edge models
    "EdgeCondition",
    "EdgeMetadata",
    "EdgeConfig",
    "EdgeSpec",
    "EdgeVersion",
    "EdgeEntry",
    # Workflow models
    "WorkflowMetadata",
    "WorkflowConfig",
    "WorkflowSpec",
    "WorkflowVersion",
    "WorkflowEntry",
    "WorkflowExecutionContext",
    "WorkflowResult",
    # Variable assignment
    "NodeVariableAssignment",
    "NodeDynamicVariableConfig",
    # Interfaces
    "INode",
    "IEdge",
    "IWorkflow",
    "IWorkflowStorage",
    "IWorkflowRegistry",
    "IWorkflowExecutor",
    "INodeExecutor",
    "IIOFormatter",
    # Runtimes
    "BaseWorkflowRegistry",
    "LocalWorkflowRegistry",
    "LocalWorkflowStorage",
    # Builders
    "NodeBuilder",
    "EdgeBuilder",
    "WorkflowBuilder",
]
