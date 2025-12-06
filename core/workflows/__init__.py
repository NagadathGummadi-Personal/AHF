"""
Workflows Module.

This module provides a comprehensive workflow system for orchestrating
agents, tools, and other components in complex multi-step processes.

Key Components:
- Workflow: Main workflow class
- WorkflowBuilder: Fluent API for building workflows
- WorkflowEngine: Execution engine for running workflows
- Nodes: Various node types (LLM, Agent, Tool, Decision, Switch, Loop, etc.)
- Edges: Edge types with conditions, transitions, and transformations
- Factories: Node and Edge factories for extensibility
- WorkflowTool: Wrapper to use workflows as agent tools

Node Categories:
- Execution Nodes: LLM, Agent, Tool, Subworkflow
- Control-Flow Nodes: Decision, Switch, Parallel, Loop
- Data & Integration Nodes: Transform, Webhook (HTTP/DB via tools)
- Human Interaction Nodes: HumanInput (HITL)
- Utility Nodes: Delay, Start, End

Example:
    from core.workflows import (
        WorkflowBuilder,
        WorkflowEngine,
        NodeType,
        EdgeType,
    )
    
    # Build a simple workflow
    workflow = (
        WorkflowBuilder()
        .with_name("My Pipeline")
        .add_node("start", NodeType.START)
        .add_agent_node("process", agent_id="my_agent")
        .add_node("end", NodeType.END)
        .add_edge("start", "process")
        .add_edge("process", "end")
        .build()
    )
    
    # Execute
    engine = WorkflowEngine()
    result, context = await engine.execute(workflow, {"query": "Hello"})
    
    # Use workflow as a tool in an agent
    from core.workflows.tools import WorkflowTool
    tool = WorkflowTool(workflow=workflow, tool_name="my_workflow")
"""

# Enums
from .enum import (
    NodeType,
    NodeState,
    EdgeType,
    WorkflowState,
    ConditionOperator,
    RoutingStrategy,
    ExecutionMode,
    DataTransformType,
    DataType,
    DataFormat,
    TriggerType,
    RetryStrategy,
    ConditionSourceType,
    VariableRequirement,
    IntentType,
)

# Interfaces
from .interfaces import (
    # Node Interfaces
    INode,
    INodeExecutor,
    INodeValidator,
    # Edge Interfaces
    IEdge,
    ICondition,
    IConditionEvaluator,
    IDataTransformer,
    # Workflow Interfaces
    IWorkflow,
    IWorkflowExecutor,
    IWorkflowValidator,
    # Router Interface
    IRouter,
    # Context and State
    IWorkflowContext,
    IWorkflowStateManager,
    # Observers
    IWorkflowObserver,
    INodeObserver,
    # Triggers
    ITrigger,
    ITriggerHandler,
    # Serialization
    IWorkflowSerializer,
    INodeSerializer,
)

# Spec Models
from .spec import (
    # Condition Models
    ConditionSpec,
    ConditionGroup,
    # I/O Specification Models (new)
    IOFieldSpec,
    IOSpec,
    # Transition Models (new)
    TransitionVariable,
    TransitionCondition,
    TransitionSpec,
    # Transform Models
    TransformSpec,
    # Node Models
    NodeSpec,
    NodeInputMapping,
    NodeOutputMapping,
    RetryConfig,
    # Edge Models
    EdgeSpec,
    # Workflow Models
    WorkflowSpec,
    WorkflowMetadata,
    WorkflowVariable,
    # Context Models
    WorkflowContext,
    NodeExecutionRecord,
    WorkflowExecutionRecord,
    # Result Models
    NodeResult,
    WorkflowResult,
    # Trigger Models
    TriggerSpec,
    ScheduleConfig,
    WebhookConfig,
)

# Node Implementations
from .nodes import (
    BaseNode,
    NodeFactory,
    # Execution Nodes
    LLMNode,
    AgentNode,
    ToolNode,
    SubworkflowNode,
    # Control-Flow Nodes
    DecisionNode,
    SwitchNode,
    ParallelNode,
    LoopNode,
    # Data & Integration Nodes
    TransformNode,
    WebhookNode,
    # Human Interaction Nodes
    HumanInputNode,
    # Utility Nodes
    DelayNode,
    StartNode,
    EndNode,
)

# Tools (Workflow-Agent Interoperability)
from .tools import (
    WorkflowTool,
    WorkflowToolSpec,
    create_workflow_tool,
)

# Edge Implementations
from .edges import (
    BaseEdge,
    BaseCondition,
    ConditionalEdge,
    FallbackEdge,
    ErrorEdge,
    DataTransformer,
    EdgeFactory,
)

# Workflow Implementation
from .implementations import Workflow

# Builders
from .builders import WorkflowBuilder

# Runtime
from .runtimes import WorkflowEngine, DefaultRouter

# Exceptions
from .exceptions import (
    WorkflowError,
    WorkflowNotFoundError,
    WorkflowBuildError,
    WorkflowValidationError,
    WorkflowExecutionError,
    NodeNotFoundError,
    NodeExecutionError,
    NodeValidationError,
    EdgeNotFoundError,
    EdgeValidationError,
    RoutingError,
    ConditionEvaluationError,
    TransformError,
    WorkflowTimeoutError,
    MaxIterationsError,
    CycleDetectedError,
    ParallelExecutionError,
    WebhookError,
    SubworkflowError,
    WorkflowStateError,
)

__all__ = [
    # Enums
    "NodeType",
    "NodeState",
    "EdgeType",
    "WorkflowState",
    "ConditionOperator",
    "RoutingStrategy",
    "ExecutionMode",
    "DataTransformType",
    "DataType",
    "DataFormat",
    "TriggerType",
    "RetryStrategy",
    "ConditionSourceType",
    "VariableRequirement",
    "IntentType",
    # Interfaces
    "INode",
    "INodeExecutor",
    "INodeValidator",
    "IEdge",
    "ICondition",
    "IConditionEvaluator",
    "IDataTransformer",
    "IWorkflow",
    "IWorkflowExecutor",
    "IWorkflowValidator",
    "IRouter",
    "IWorkflowContext",
    "IWorkflowStateManager",
    "IWorkflowObserver",
    "INodeObserver",
    "ITrigger",
    "ITriggerHandler",
    "IWorkflowSerializer",
    "INodeSerializer",
    # Spec Models
    "ConditionSpec",
    "ConditionGroup",
    "IOFieldSpec",
    "IOSpec",
    "TransitionVariable",
    "TransitionCondition",
    "TransitionSpec",
    "TransformSpec",
    "NodeSpec",
    "NodeInputMapping",
    "NodeOutputMapping",
    "RetryConfig",
    "EdgeSpec",
    "WorkflowSpec",
    "WorkflowMetadata",
    "WorkflowVariable",
    "WorkflowContext",
    "NodeExecutionRecord",
    "WorkflowExecutionRecord",
    "NodeResult",
    "WorkflowResult",
    "TriggerSpec",
    "ScheduleConfig",
    "WebhookConfig",
    # Node Implementations
    "BaseNode",
    "NodeFactory",
    "LLMNode",
    "AgentNode",
    "ToolNode",
    "SubworkflowNode",
    "DecisionNode",
    "SwitchNode",
    "ParallelNode",
    "LoopNode",
    "TransformNode",
    "WebhookNode",
    "HumanInputNode",
    "DelayNode",
    "StartNode",
    "EndNode",
    # Edge Implementations
    "BaseEdge",
    "BaseCondition",
    "ConditionalEdge",
    "FallbackEdge",
    "ErrorEdge",
    "DataTransformer",
    "EdgeFactory",
    # Workflow
    "Workflow",
    # Builders
    "WorkflowBuilder",
    # Runtime
    "WorkflowEngine",
    "DefaultRouter",
    # Tools (Agent-Workflow Interoperability)
    "WorkflowTool",
    "WorkflowToolSpec",
    "create_workflow_tool",
    # Exceptions
    "WorkflowError",
    "WorkflowNotFoundError",
    "WorkflowBuildError",
    "WorkflowValidationError",
    "WorkflowExecutionError",
    "NodeNotFoundError",
    "NodeExecutionError",
    "NodeValidationError",
    "EdgeNotFoundError",
    "EdgeValidationError",
    "RoutingError",
    "ConditionEvaluationError",
    "TransformError",
    "WorkflowTimeoutError",
    "MaxIterationsError",
    "CycleDetectedError",
    "ParallelExecutionError",
    "WebhookError",
    "SubworkflowError",
    "WorkflowStateError",
]
