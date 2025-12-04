"""
Agents Subsystem for AI Core.

This module provides a flexible, pluggable, and extensible architecture
for creating intelligent agents with multi-model I/O support.

Architecture:
=============
All agents implement IAgent interface with core methods:
1. run() - Execute agent (non-streaming)
2. stream() - Stream execution
3. get_state() - Get current state

Agent Types:
============
- SimpleAgent: Single-shot Q&A
- ReactAgent: Reason-Act loop (Thought -> Action -> Observation)
- GoalBasedAgent: Goal-driven with checklist tracking
- HierarchicalAgent: Manager delegates to worker agents

Pluggable Components:
=====================
All components are pluggable via interfaces:
- IAgentMemory: Context and history storage
- IAgentScratchpad: Reasoning workspace
- IAgentChecklist: Goal/task tracking
- IAgentPlanner: Planning and task decomposition
- IAgentObserver: Execution observation hooks
- IAgentInputProcessor: Input preprocessing
- IAgentOutputProcessor: Output postprocessing

Builder Pattern:
================
    from core.agents import AgentBuilder, AgentType
    
    agent = (AgentBuilder()
        .with_name("my_agent")
        .with_llm(llm)
        .with_tools([search_tool, calc_tool])
        .with_memory(DictMemory())
        .with_scratchpad(BasicScratchpad())
        .with_max_iterations(10)
        .with_input_types([AgentInputType.TEXT])
        .with_output_types([AgentOutputType.TEXT, AgentOutputType.STRUCTURED])
        .as_type(AgentType.REACT)
        .build())
    
    result = await agent.run("What is 2+2?", ctx)
"""

# Enums
from .enum import (
    AgentType,
    AgentState,
    ChecklistStatus,
    AgentInputType,
    AgentOutputType,
    AgentOutputFormat,
)

# Exceptions
from .exceptions import (
    AgentError,
    AgentBuildError,
    AgentExecutionError,
    MaxIterationsError,
    ToolNotFoundError,
    ToolExecutionError,
    LLMFailoverError,
    InvalidAgentStateError,
    ChecklistItemNotFoundError,
    MemoryError,
    AgentTimeoutError,
)

# Interfaces
from .interfaces import (
    IAgent,
    IAgentMemory,
    IAgentScratchpad,
    IAgentChecklist,
    IAgentPlanner,
    IAgentObserver,
    IAgentInputProcessor,
    IAgentOutputProcessor,
)

# Spec
from .spec import (
    AgentContext,
    AgentResult,
    AgentStreamChunk,
    AgentUsage,
    AgentSpec,
    ChecklistItem,
    Checklist,
    create_context,
    create_result,
    create_chunk,
    create_agent_spec,
)

# Builders
from .builders import (
    AgentBuilder,
    AgentContextBuilder,
)

# Runtimes
from .runtimes import (
    # Memory
    NoOpAgentMemory,
    DictMemory,
    AgentMemoryFactory,
    # Scratchpad
    BasicScratchpad,
    StructuredScratchpad,
    ScratchpadFactory,
    # Checklist
    BasicChecklist,
    ChecklistFactory,
    # Observer
    NoOpObserver,
    LoggingObserver,
    ObserverFactory,
    # Agent Factory
    AgentFactory,
    AgentTypeRegistration,
)

# Implementations
from .implementations import (
    BaseAgent,
    SimpleAgent,
    ReactAgent,
    GoalBasedAgent,
    HierarchicalAgent,
)

__all__ = [
    # Enums
    "AgentType",
    "AgentState",
    "ChecklistStatus",
    "AgentInputType",
    "AgentOutputType",
    "AgentOutputFormat",
    # Exceptions
    "AgentError",
    "AgentBuildError",
    "AgentExecutionError",
    "MaxIterationsError",
    "ToolNotFoundError",
    "ToolExecutionError",
    "LLMFailoverError",
    "InvalidAgentStateError",
    "ChecklistItemNotFoundError",
    "MemoryError",
    "AgentTimeoutError",
    # Interfaces
    "IAgent",
    "IAgentMemory",
    "IAgentScratchpad",
    "IAgentChecklist",
    "IAgentPlanner",
    "IAgentObserver",
    "IAgentInputProcessor",
    "IAgentOutputProcessor",
    # Spec
    "AgentContext",
    "AgentResult",
    "AgentStreamChunk",
    "AgentUsage",
    "AgentSpec",
    "ChecklistItem",
    "Checklist",
    "create_context",
    "create_result",
    "create_chunk",
    "create_agent_spec",
    # Builders
    "AgentBuilder",
    "AgentContextBuilder",
    # Memory
    "NoOpAgentMemory",
    "DictMemory",
    "AgentMemoryFactory",
    # Scratchpad
    "BasicScratchpad",
    "StructuredScratchpad",
    "ScratchpadFactory",
    # Checklist
    "BasicChecklist",
    "ChecklistFactory",
    # Observer
    "NoOpObserver",
    "LoggingObserver",
    "ObserverFactory",
    # Agent Factory
    "AgentFactory",
    "AgentTypeRegistration",
    # Implementations
    "BaseAgent",
    "SimpleAgent",
    "ReactAgent",
    "GoalBasedAgent",
    "HierarchicalAgent",
]

