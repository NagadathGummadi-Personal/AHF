"""
Agent Builder.

Provides a fluent interface for building agent instances with all dependencies.
"""

from typing import Any, Dict, List, Optional, Type, Callable, TYPE_CHECKING

from ..enum import AgentType, AgentInputType, AgentOutputType, AgentOutputFormat
from ..spec.agent_spec import AgentSpec
from ..constants import DEFAULT_MAX_ITERATIONS, DEFAULT_TIMEOUT_SECONDS
from ..exceptions import AgentBuildError

if TYPE_CHECKING:
    from ...llms.interfaces.llm_interfaces import ILLM
    from ...tools.spec.tool_types import ToolSpec
    from ..interfaces.agent_interfaces import (
        IAgent,
        IAgentMemory,
        IAgentScratchpad,
        IAgentChecklist,
        IAgentPlanner,
        IAgentObserver,
        IAgentInputProcessor,
        IAgentOutputProcessor,
    )


class AgentBuilder:
    """
    Fluent builder for creating agent instances.
    
    Provides a convenient way to construct agents with all dependencies
    using method chaining.
    
    Usage:
        # Simple agent
        agent = (AgentBuilder()
            .with_name("research_agent")
            .with_llm(llm)
            .with_tools([search_tool, write_tool])
            .build())
        
        # Full agent with all components
        agent = (AgentBuilder()
            .with_name("advanced_agent")
            .with_description("An advanced research agent")
            .with_llm(primary_llm)
            .with_backup_llm(backup_llm)
            .with_tools([search_tool, write_tool])
            .with_memory(VectorMemory())
            .with_scratchpad(BasicScratchpad())
            .with_checklist(Checklist())
            .with_prompt_registry(LocalPromptRegistry())
            .with_system_prompt("You are a helpful assistant...")
            .with_max_iterations(20)
            .with_timeout(300)
            .with_input_types([AgentInputType.TEXT, AgentInputType.IMAGE])
            .with_output_types([AgentOutputType.TEXT, AgentOutputType.STRUCTURED])
            .as_type(AgentType.REACT)
            .build())
        
        # Using observer
        agent = (AgentBuilder()
            .with_name("monitored_agent")
            .with_llm(llm)
            .with_observer(LoggingObserver())
            .build())
    """
    
    def __init__(self):
        """Initialize builder with default values."""
        # Identity
        self._name: Optional[str] = None
        self._description: str = ""
        self._agent_type: AgentType = AgentType.REACT
        
        # LLMs
        self._llm: Optional['ILLM'] = None
        self._backup_llm: Optional['ILLM'] = None
        
        # Tools
        self._tools: List[Any] = []  # Can be tool specs or executors
        self._tool_specs: List['ToolSpec'] = []
        
        # Components
        self._memory: Optional['IAgentMemory'] = None
        self._scratchpad: Optional['IAgentScratchpad'] = None
        self._checklist: Optional['IAgentChecklist'] = None
        self._planner: Optional['IAgentPlanner'] = None
        self._observers: List['IAgentObserver'] = []
        self._input_processor: Optional['IAgentInputProcessor'] = None
        self._output_processor: Optional['IAgentOutputProcessor'] = None
        
        # Prompt
        self._prompt_registry: Optional[Any] = None  # IPromptRegistry
        self._system_prompt: Optional[str] = None
        self._system_prompt_label: Optional[str] = None
        
        # Constraints
        self._max_iterations: int = DEFAULT_MAX_ITERATIONS
        self._timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
        
        # Input/Output types
        self._supported_input_types: List[AgentInputType] = [AgentInputType.TEXT]
        self._supported_output_types: List[AgentOutputType] = [AgentOutputType.TEXT]
        self._default_output_format: AgentOutputFormat = AgentOutputFormat.TEXT
        self._output_schema: Optional[Dict[str, Any]] = None
        
        # Metadata
        self._version: str = "1.0.0"
        self._tags: List[str] = []
        self._metadata: Dict[str, Any] = {}
        
        # Custom agent class
        self._agent_class: Optional[Type['IAgent']] = None
    
    # ==================== Identity ====================
    
    def with_name(self, name: str) -> 'AgentBuilder':
        """Set agent name."""
        self._name = name
        return self
    
    def with_description(self, description: str) -> 'AgentBuilder':
        """Set agent description."""
        self._description = description
        return self
    
    def as_type(self, agent_type: AgentType) -> 'AgentBuilder':
        """
        Specify the type of agent to build.
        
        Args:
            agent_type: Type of agent (react, goal_based, hierarchical, simple)
        """
        self._agent_type = agent_type
        return self
    
    # ==================== LLMs ====================
    
    def with_llm(self, llm: 'ILLM') -> 'AgentBuilder':
        """Set the primary LLM."""
        self._llm = llm
        return self
    
    def with_backup_llm(self, llm: 'ILLM') -> 'AgentBuilder':
        """Set the backup LLM for failover."""
        self._backup_llm = llm
        return self
    
    # ==================== Tools ====================
    
    def with_tools(self, tools: List[Any]) -> 'AgentBuilder':
        """
        Add tools to the agent.
        
        Args:
            tools: List of tool specs, executors, or callables
        """
        self._tools.extend(tools)
        return self
    
    def with_tool(self, tool: Any) -> 'AgentBuilder':
        """Add a single tool."""
        self._tools.append(tool)
        return self
    
    def with_tool_specs(self, specs: List['ToolSpec']) -> 'AgentBuilder':
        """Add tool specifications."""
        self._tool_specs.extend(specs)
        return self
    
    # ==================== Components ====================
    
    def with_memory(self, memory: 'IAgentMemory') -> 'AgentBuilder':
        """Set memory implementation."""
        self._memory = memory
        return self
    
    def with_scratchpad(self, scratchpad: 'IAgentScratchpad') -> 'AgentBuilder':
        """Set scratchpad implementation."""
        self._scratchpad = scratchpad
        return self
    
    def with_checklist(self, checklist: 'IAgentChecklist') -> 'AgentBuilder':
        """Set checklist implementation."""
        self._checklist = checklist
        return self
    
    def with_planner(self, planner: 'IAgentPlanner') -> 'AgentBuilder':
        """Set planner implementation."""
        self._planner = planner
        return self
    
    def with_observer(self, observer: 'IAgentObserver') -> 'AgentBuilder':
        """Add an observer."""
        self._observers.append(observer)
        return self
    
    def with_observers(self, observers: List['IAgentObserver']) -> 'AgentBuilder':
        """Add multiple observers."""
        self._observers.extend(observers)
        return self
    
    def with_input_processor(self, processor: 'IAgentInputProcessor') -> 'AgentBuilder':
        """Set input processor."""
        self._input_processor = processor
        return self
    
    def with_output_processor(self, processor: 'IAgentOutputProcessor') -> 'AgentBuilder':
        """Set output processor."""
        self._output_processor = processor
        return self
    
    # ==================== Prompts ====================
    
    def with_prompt_registry(self, registry: Any) -> 'AgentBuilder':
        """Set prompt registry."""
        self._prompt_registry = registry
        return self
    
    def with_system_prompt(self, prompt: str) -> 'AgentBuilder':
        """Set system prompt directly."""
        self._system_prompt = prompt
        return self
    
    def with_system_prompt_label(self, label: str) -> 'AgentBuilder':
        """Set system prompt label (to fetch from registry)."""
        self._system_prompt_label = label
        return self
    
    # ==================== Constraints ====================
    
    def with_max_iterations(self, iterations: int) -> 'AgentBuilder':
        """Set maximum iterations."""
        self._max_iterations = iterations
        return self
    
    def with_timeout(self, timeout_seconds: float) -> 'AgentBuilder':
        """Set execution timeout in seconds."""
        self._timeout_seconds = timeout_seconds
        return self
    
    # ==================== Input/Output ====================
    
    def with_input_types(self, types: List[AgentInputType]) -> 'AgentBuilder':
        """Set supported input types."""
        self._supported_input_types = types
        return self
    
    def with_output_types(self, types: List[AgentOutputType]) -> 'AgentBuilder':
        """Set supported output types."""
        self._supported_output_types = types
        return self
    
    def with_output_format(self, format: AgentOutputFormat) -> 'AgentBuilder':
        """Set default output format."""
        self._default_output_format = format
        return self
    
    def with_output_schema(self, schema: Dict[str, Any]) -> 'AgentBuilder':
        """Set output JSON schema for structured output."""
        self._output_schema = schema
        return self
    
    # ==================== Metadata ====================
    
    def with_version(self, version: str) -> 'AgentBuilder':
        """Set agent version."""
        self._version = version
        return self
    
    def with_tags(self, tags: List[str]) -> 'AgentBuilder':
        """Set tags."""
        self._tags = tags
        return self
    
    def with_metadata(self, **kwargs) -> 'AgentBuilder':
        """Add metadata."""
        self._metadata.update(kwargs)
        return self
    
    # ==================== Custom Class ====================
    
    def with_agent_class(self, agent_class: Type['IAgent']) -> 'AgentBuilder':
        """
        Use a custom agent class.
        
        Args:
            agent_class: Custom class implementing IAgent
        """
        self._agent_class = agent_class
        return self
    
    # ==================== Factory Methods ====================
    
    def with_memory_by_name(self, name: str) -> 'AgentBuilder':
        """
        Set memory implementation by factory name.
        
        Args:
            name: Memory implementation name (e.g., 'noop', 'dict')
        """
        from ..runtimes.memory.memory_factory import AgentMemoryFactory
        self._memory = AgentMemoryFactory.get_memory(name)
        return self
    
    def with_scratchpad_by_name(self, name: str) -> 'AgentBuilder':
        """
        Set scratchpad implementation by factory name.
        
        Args:
            name: Scratchpad implementation name (e.g., 'basic')
        """
        from ..runtimes.scratchpad.scratchpad_factory import ScratchpadFactory
        self._scratchpad = ScratchpadFactory.get_scratchpad(name)
        return self
    
    def with_defaults(self, profile: str = 'noop') -> 'AgentBuilder':
        """
        Set all components to default implementations.
        
        Args:
            profile: Profile name ('noop', 'basic')
        """
        if profile == 'noop':
            self.with_memory_by_name('noop')
            self.with_scratchpad_by_name('basic')
        elif profile == 'basic':
            self.with_memory_by_name('dict')
            self.with_scratchpad_by_name('basic')
        return self
    
    # ==================== Build ====================
    
    def _validate(self) -> None:
        """Validate builder configuration."""
        if not self._name:
            raise AgentBuildError("Agent name is required")
        
        if not self._llm:
            raise AgentBuildError("LLM is required")
    
    def _create_spec(self) -> AgentSpec:
        """Create agent specification from builder config."""
        return AgentSpec(
            name=self._name,
            description=self._description,
            agent_type=self._agent_type,
            supported_input_types=self._supported_input_types,
            supported_output_types=self._supported_output_types,
            default_output_format=self._default_output_format,
            output_schema=self._output_schema,
            max_iterations=self._max_iterations,
            timeout_seconds=self._timeout_seconds,
            system_prompt=self._system_prompt,
            system_prompt_label=self._system_prompt_label,
            version=self._version,
            tags=self._tags,
            metadata=self._metadata,
        )
    
    def _get_agent_class(self) -> Type['IAgent']:
        """Get the appropriate agent class based on type."""
        if self._agent_class:
            return self._agent_class
        
        # Import agent implementations
        from ..implementations import (
            ReactAgent,
            GoalBasedAgent,
            HierarchicalAgent,
            SimpleAgent,
        )
        
        type_map = {
            AgentType.REACT: ReactAgent,
            AgentType.GOAL_BASED: GoalBasedAgent,
            AgentType.HIERARCHICAL: HierarchicalAgent,
            AgentType.SIMPLE: SimpleAgent,
        }
        
        agent_class = type_map.get(self._agent_type)
        if not agent_class:
            raise AgentBuildError(
                f"Unknown agent type: {self._agent_type}",
                details={"available_types": list(type_map.keys())}
            )
        
        return agent_class
    
    def build(self) -> 'IAgent':
        """
        Constructs the agent based on the configuration.
        
        Returns:
            Configured agent instance implementing IAgent
            
        Raises:
            AgentBuildError: If configuration is invalid
        """
        self._validate()
        
        spec = self._create_spec()
        agent_class = self._get_agent_class()
        
        # Construct agent with all dependencies
        agent = agent_class(
            spec=spec,
            llm=self._llm,
            backup_llm=self._backup_llm,
            tools=self._tools,
            memory=self._memory,
            scratchpad=self._scratchpad,
            checklist=self._checklist,
            planner=self._planner,
            observers=self._observers,
            input_processor=self._input_processor,
            output_processor=self._output_processor,
            prompt_registry=self._prompt_registry,
        )
        
        return agent
    
    def build_spec(self) -> AgentSpec:
        """
        Build only the agent spec without creating the agent.
        
        Useful for serialization or validation.
        
        Returns:
            AgentSpec instance
        """
        if not self._name:
            raise AgentBuildError("Agent name is required")
        return self._create_spec()

