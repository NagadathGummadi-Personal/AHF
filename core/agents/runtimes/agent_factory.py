"""
Agent Factory.

Provides a factory pattern for creating and registering agent types.
Allows custom agent types to be registered without modifying core enums.

Example:
    # Register a custom agent type
    AgentFactory.register(
        type_id="air_agent",
        agent_class=AIRAgent,
        display_name="AIR Agent",
        description="Adaptive Intelligent Reasoning Agent",
        default_config={
            "requires_scratchpad": True,
            "max_iterations": 10
        }
    )
    
    # Create agent using factory
    agent = AgentFactory.create("air_agent", spec=spec, llm=llm)
    
    # Or use with builder
    agent = (AgentBuilder()
        .with_name("my_agent")
        .with_llm(llm)
        .as_custom_type("air_agent")
        .build())
"""

from typing import Any, Callable, Dict, List, Optional, Type, Union, TYPE_CHECKING
from dataclasses import dataclass, field
from datetime import datetime
import logging

from ..enum import AgentType
from ..exceptions import AgentBuildError

if TYPE_CHECKING:
    from ..interfaces import IAgent

logger = logging.getLogger(__name__)


@dataclass
class AgentTypeRegistration:
    """
    Registration information for an agent type.
    
    Attributes:
        type_id: Unique identifier for the agent type (e.g., "air_agent")
        agent_class: The class that implements the agent
        display_name: Human-readable name (e.g., "AIR Agent")
        description: Description of what the agent does
        default_config: Default configuration for this agent type
        required_components: List of required components (e.g., ["scratchpad", "memory"])
        validator: Optional function to validate agent configuration
        created_at: When this type was registered
        metadata: Additional metadata about the agent type
    """
    type_id: str
    agent_class: Type['IAgent']
    display_name: str = ""
    description: str = ""
    default_config: Dict[str, Any] = field(default_factory=dict)
    required_components: List[str] = field(default_factory=list)
    validator: Optional[Callable[[Dict[str, Any]], bool]] = None
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.display_name:
            self.display_name = self.type_id.replace("_", " ").title()


class AgentFactory:
    """
    Factory for creating and managing agent types.
    
    This factory provides:
    - Registration of custom agent types
    - Creation of agent instances
    - Validation of agent configurations
    - Discovery of available agent types
    
    Built-in types (REACT, SIMPLE, GOAL_BASED, HIERARCHICAL) are registered
    automatically when the factory is first used.
    
    Example:
        # Register custom type
        AgentFactory.register(
            type_id="my_custom_agent",
            agent_class=MyCustomAgent,
            display_name="My Custom Agent",
            required_components=["scratchpad"]
        )
        
        # List all available types
        types = AgentFactory.list_types()
        
        # Create agent
        agent = AgentFactory.create("my_custom_agent", spec=spec, llm=llm)
    """
    
    _registry: Dict[str, AgentTypeRegistration] = {}
    _initialized: bool = False
    
    @classmethod
    def _ensure_initialized(cls) -> None:
        """Initialize built-in types if not already done."""
        if cls._initialized:
            return
        
        # Import here to avoid circular imports
        from ..implementations import (
            ReactAgent,
            SimpleAgent,
            GoalBasedAgent,
            HierarchicalAgent,
        )
        
        # Register built-in types
        cls._registry[AgentType.REACT.value] = AgentTypeRegistration(
            type_id=AgentType.REACT.value,
            agent_class=ReactAgent,
            display_name="ReAct Agent",
            description="Reasoning and Acting agent using thought-action-observation loop",
            default_config={"max_iterations": 10},
            required_components=[],
        )
        
        cls._registry[AgentType.SIMPLE.value] = AgentTypeRegistration(
            type_id=AgentType.SIMPLE.value,
            agent_class=SimpleAgent,
            display_name="Simple Agent",
            description="Basic single-turn LLM agent without tools",
            default_config={"max_iterations": 1},
            required_components=[],
        )
        
        cls._registry[AgentType.GOAL_BASED.value] = AgentTypeRegistration(
            type_id=AgentType.GOAL_BASED.value,
            agent_class=GoalBasedAgent,
            display_name="Goal-Based Agent",
            description="Agent that works towards goals with checklist tracking",
            default_config={"max_iterations": 10},
            required_components=["checklist"],
        )
        
        cls._registry[AgentType.HIERARCHICAL.value] = AgentTypeRegistration(
            type_id=AgentType.HIERARCHICAL.value,
            agent_class=HierarchicalAgent,
            display_name="Hierarchical Agent",
            description="Manager agent that coordinates sub-agents",
            default_config={"max_iterations": 15},
            required_components=[],
        )
        
        cls._initialized = True
        logger.debug(f"AgentFactory initialized with {len(cls._registry)} built-in types")
    
    @classmethod
    def register(
        cls,
        type_id: str,
        agent_class: Type['IAgent'],
        display_name: Optional[str] = None,
        description: str = "",
        default_config: Optional[Dict[str, Any]] = None,
        required_components: Optional[List[str]] = None,
        validator: Optional[Callable[[Dict[str, Any]], bool]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        override: bool = False,
    ) -> None:
        """
        Register a custom agent type.
        
        Args:
            type_id: Unique identifier for the agent type
            agent_class: Class implementing IAgent interface
            display_name: Human-readable name
            description: Description of the agent
            default_config: Default configuration values
            required_components: List of required components (e.g., ["scratchpad", "memory"])
            validator: Optional function to validate configuration
            metadata: Additional metadata
            override: If True, allows overriding existing registration
            
        Raises:
            AgentBuildError: If type_id already registered and override=False
        """
        cls._ensure_initialized()
        
        if type_id in cls._registry and not override:
            raise AgentBuildError(
                f"Agent type '{type_id}' is already registered. "
                f"Use override=True to replace it.",
                details={"existing_type": type_id}
            )
        
        registration = AgentTypeRegistration(
            type_id=type_id,
            agent_class=agent_class,
            display_name=display_name or type_id.replace("_", " ").title(),
            description=description,
            default_config=default_config or {},
            required_components=required_components or [],
            validator=validator,
            metadata=metadata or {},
        )
        
        cls._registry[type_id] = registration
        logger.info(f"Registered agent type: {type_id} ({registration.display_name})")
    
    @classmethod
    def unregister(cls, type_id: str) -> bool:
        """
        Unregister an agent type.
        
        Args:
            type_id: The type identifier to unregister
            
        Returns:
            True if the type was unregistered, False if it wasn't registered
        """
        cls._ensure_initialized()
        
        if type_id in cls._registry:
            del cls._registry[type_id]
            logger.info(f"Unregistered agent type: {type_id}")
            return True
        return False
    
    @classmethod
    def get_registration(cls, type_id: Union[str, AgentType]) -> Optional[AgentTypeRegistration]:
        """
        Get the registration for an agent type.
        
        Args:
            type_id: The type identifier (string or AgentType enum)
            
        Returns:
            AgentTypeRegistration or None if not found
        """
        cls._ensure_initialized()
        
        if isinstance(type_id, AgentType):
            type_id = type_id.value
        
        return cls._registry.get(type_id)
    
    @classmethod
    def is_registered(cls, type_id: Union[str, AgentType]) -> bool:
        """Check if an agent type is registered."""
        return cls.get_registration(type_id) is not None
    
    @classmethod
    def create(
        cls,
        type_id: Union[str, AgentType],
        **kwargs
    ) -> 'IAgent':
        """
        Create an agent instance of the specified type.
        
        Args:
            type_id: The agent type identifier
            **kwargs: Arguments to pass to the agent constructor
            
        Returns:
            Agent instance
            
        Raises:
            AgentBuildError: If type is not registered or creation fails
        """
        cls._ensure_initialized()
        
        if isinstance(type_id, AgentType):
            type_id = type_id.value
        
        registration = cls._registry.get(type_id)
        if not registration:
            available = list(cls._registry.keys())
            raise AgentBuildError(
                f"Unknown agent type: '{type_id}'",
                details={"available_types": available}
            )
        
        # Validate required components
        missing = []
        for component in registration.required_components:
            if component not in kwargs or kwargs[component] is None:
                missing.append(component)
        
        if missing:
            raise AgentBuildError(
                f"Agent type '{type_id}' requires components: {missing}",
                details={"required": registration.required_components, "missing": missing}
            )
        
        # Run custom validator if provided
        if registration.validator:
            if not registration.validator(kwargs):
                raise AgentBuildError(
                    f"Configuration validation failed for agent type '{type_id}'"
                )
        
        # Note: default_config is informational/for spec - don't pass to constructor
        # The AgentSpec should contain max_iterations, etc.
        
        try:
            return registration.agent_class(**kwargs)
        except Exception as e:
            raise AgentBuildError(
                f"Failed to create agent of type '{type_id}': {e}",
                details={"type_id": type_id, "error": str(e)}
            ) from e
    
    @classmethod
    def get_agent_class(cls, type_id: Union[str, AgentType]) -> Type['IAgent']:
        """
        Get the agent class for a type without creating an instance.
        
        Args:
            type_id: The agent type identifier
            
        Returns:
            The agent class
            
        Raises:
            AgentBuildError: If type is not registered
        """
        registration = cls.get_registration(type_id)
        if not registration:
            raise AgentBuildError(
                f"Unknown agent type: '{type_id}'",
                details={"available_types": list(cls._registry.keys())}
            )
        return registration.agent_class
    
    @classmethod
    def list_types(cls) -> List[str]:
        """Get list of all registered type identifiers."""
        cls._ensure_initialized()
        return list(cls._registry.keys())
    
    @classmethod
    def list_registrations(cls) -> List[AgentTypeRegistration]:
        """Get list of all registrations."""
        cls._ensure_initialized()
        return list(cls._registry.values())
    
    @classmethod
    def get_type_info(cls, type_id: Union[str, AgentType]) -> Dict[str, Any]:
        """
        Get detailed information about an agent type.
        
        Returns:
            Dictionary with type information
        """
        registration = cls.get_registration(type_id)
        if not registration:
            return {}
        
        return {
            "type_id": registration.type_id,
            "display_name": registration.display_name,
            "description": registration.description,
            "default_config": registration.default_config,
            "required_components": registration.required_components,
            "created_at": registration.created_at.isoformat(),
            "metadata": registration.metadata,
        }
    
    @classmethod
    def clear_custom_types(cls) -> int:
        """
        Remove all custom (non-built-in) types.
        
        Returns:
            Number of types removed
        """
        cls._ensure_initialized()
        
        builtin_types = {t.value for t in AgentType}
        custom_types = [t for t in cls._registry.keys() if t not in builtin_types]
        
        for type_id in custom_types:
            del cls._registry[type_id]
        
        logger.info(f"Cleared {len(custom_types)} custom agent types")
        return len(custom_types)
    
    @classmethod
    def reset(cls) -> None:
        """Reset factory to initial state (removes all types including built-ins)."""
        cls._registry.clear()
        cls._initialized = False
        logger.info("AgentFactory reset")

