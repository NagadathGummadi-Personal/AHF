"""
Workflow Nodes Module

Tool nodes and agent nodes for the voice agent workflow.
All nodes implement INode from core.workflows.interfaces.

Standalone Testing:
    Each node supports standalone execution for unit testing:
    
    # Tool node example
    from air.nodes import WorkflowInitNode, MockSession
    
    node = WorkflowInitNode()
    result = await node.run_standalone({
        "caller_id": "+1234567890",
        "center_id": "test-center",
        "org_id": "test-org",
        "agent_id": "test-agent",
    })
    
    # Agent node example  
    from air.nodes import GreetingRoutingAgent, MockSession
    from core.llms import LLMFactory
    
    llm = LLMFactory.create_llm("gpt-4o", connector_config={...})
    agent = GreetingRoutingAgent(llm=llm)
    result = await agent.run_standalone({"user_input": "Hello"})
"""

from .base import (
    BaseToolNode,
    BaseAgentNode,
    NodeConfig,
    NodeContext,
    MockSession,
    MockDynamicVars,
    MockTask,
    MockTaskQueue,
)
from .tool_nodes import (
    WorkflowInitNode,
    FirstMessageNode,
    TransformationNode,
    ServiceInfoNode,
    BookingNode,
)
from .agent_nodes import (
    GreetingRoutingAgent,
    ServiceCheckAgent,
    ServiceGuidelinesAgent,
    FallbackAgent,
)

__all__ = [
    # Base classes
    "BaseToolNode",
    "BaseAgentNode",
    "NodeConfig",
    "NodeContext",
    # Mock classes for testing
    "MockSession",
    "MockDynamicVars",
    "MockTask",
    "MockTaskQueue",
    # Tool nodes
    "WorkflowInitNode",
    "FirstMessageNode",
    "TransformationNode",
    "ServiceInfoNode",
    "BookingNode",
    # Agent nodes
    "GreetingRoutingAgent",
    "ServiceCheckAgent",
    "ServiceGuidelinesAgent",
    "FallbackAgent",
]

