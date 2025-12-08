"""
Memory Factory.

Creates memory instances based on configuration with registration support.
Allows custom implementations to be registered and instantiated via the factory.

Version: 2.0.0
"""

from typing import Any, Dict, Optional, Type
from enum import Enum

from .conversation_history import (
    BaseConversationHistory,
    DefaultConversationHistory,
)
from .state_tracker import (
    BaseStateTracker,
    DefaultStateTracker,
)
from .working_memory import (
    BaseWorkingMemory,
    DefaultWorkingMemory,
)


class MemoryType(str, Enum):
    """Types of memory."""
    WORKING = "working"
    CONVERSATION = "conversation"
    STATE_TRACKER = "state_tracker"


class MemoryFactory:
    """
    Factory for creating memory instances with registration support.
    
    Features:
    - Create default memory implementations
    - Register custom implementations
    - Create from configuration
    - Type-safe creation methods
    
    Usage:
        # Create default working memory
        memory = MemoryFactory.create_working_memory(
            session_id="session-123",
            max_messages=100,
        )
        
        # Register custom implementation
        MemoryFactory.register_working_memory("agent", AgentWorkingMemory)
        
        # Create custom implementation
        memory = MemoryFactory.create_working_memory(
            session_id="session-123",
            implementation="agent",
        )
        
        # Create from config
        memory = MemoryFactory.create_from_config({
            "type": "working",
            "implementation": "agent",
            "session_id": "session-123",
        })
    """
    
    # Registered implementations
    _working_memory_registry: Dict[str, Type[BaseWorkingMemory]] = {
        "default": DefaultWorkingMemory,
    }
    _conversation_registry: Dict[str, Type[BaseConversationHistory]] = {
        "default": DefaultConversationHistory,
    }
    _state_tracker_registry: Dict[str, Type[BaseStateTracker]] = {
        "default": DefaultStateTracker,
    }
    
    # =========================================================================
    # Registration Methods
    # =========================================================================
    
    @classmethod
    def register_working_memory(
        cls,
        name: str,
        implementation: Type[BaseWorkingMemory],
    ) -> None:
        """
        Register a working memory implementation.
        
        Args:
            name: Implementation name (e.g., "agent", "workflow")
            implementation: Working memory class (must extend BaseWorkingMemory)
            
        Example:
            class AgentWorkingMemory(BaseWorkingMemory):
                ...
            
            MemoryFactory.register_working_memory("agent", AgentWorkingMemory)
        """
        if not issubclass(implementation, BaseWorkingMemory):
            raise TypeError(
                f"Implementation must be a subclass of BaseWorkingMemory, "
                f"got {implementation.__name__}"
            )
        cls._working_memory_registry[name] = implementation
    
    @classmethod
    def register_conversation_history(
        cls,
        name: str,
        implementation: Type[BaseConversationHistory],
    ) -> None:
        """
        Register a conversation history implementation.
        
        Args:
            name: Implementation name (e.g., "chat", "task")
            implementation: Conversation history class (must extend BaseConversationHistory)
            
        Example:
            class ChatConversationHistory(BaseConversationHistory):
                ...
            
            MemoryFactory.register_conversation_history("chat", ChatConversationHistory)
        """
        if not issubclass(implementation, BaseConversationHistory):
            raise TypeError(
                f"Implementation must be a subclass of BaseConversationHistory, "
                f"got {implementation.__name__}"
            )
        cls._conversation_registry[name] = implementation
    
    @classmethod
    def register_state_tracker(
        cls,
        name: str,
        implementation: Type[BaseStateTracker],
    ) -> None:
        """
        Register a state tracker implementation.
        
        Args:
            name: Implementation name (e.g., "persistent", "distributed")
            implementation: State tracker class (must extend BaseStateTracker)
            
        Example:
            class PersistentStateTracker(BaseStateTracker):
                ...
            
            MemoryFactory.register_state_tracker("persistent", PersistentStateTracker)
        """
        if not issubclass(implementation, BaseStateTracker):
            raise TypeError(
                f"Implementation must be a subclass of BaseStateTracker, "
                f"got {implementation.__name__}"
            )
        cls._state_tracker_registry[name] = implementation
    
    # =========================================================================
    # List Registered Implementations
    # =========================================================================
    
    @classmethod
    def list_working_memory_implementations(cls) -> list[str]:
        """List registered working memory implementations."""
        return list(cls._working_memory_registry.keys())
    
    @classmethod
    def list_conversation_implementations(cls) -> list[str]:
        """List registered conversation history implementations."""
        return list(cls._conversation_registry.keys())
    
    @classmethod
    def list_state_tracker_implementations(cls) -> list[str]:
        """List registered state tracker implementations."""
        return list(cls._state_tracker_registry.keys())
    
    # =========================================================================
    # Creation Methods
    # =========================================================================
    
    @classmethod
    def create_working_memory(
        cls,
        session_id: Optional[str] = None,
        max_messages: Optional[int] = None,
        max_checkpoints: int = 50,
        implementation: str = "default",
        **kwargs,
    ) -> BaseWorkingMemory:
        """
        Create a working memory instance.
        
        Args:
            session_id: Session identifier
            max_messages: Max conversation messages
            max_checkpoints: Max checkpoints to keep
            implementation: Implementation name (default: "default")
            **kwargs: Additional arguments for custom implementations
            
        Returns:
            Working memory instance
            
        Raises:
            ValueError: If implementation is not registered
        """
        impl_class = cls._working_memory_registry.get(implementation)
        if impl_class is None:
            available = cls.list_working_memory_implementations()
            raise ValueError(
                f"Unknown working memory implementation: '{implementation}'. "
                f"Available: {available}"
            )
        
        return impl_class(
            session_id=session_id,
            max_messages=max_messages,
            max_checkpoints=max_checkpoints,
            **kwargs,
        )
    
    @classmethod
    def create_conversation_history(
        cls,
        max_messages: Optional[int] = None,
        implementation: str = "default",
        **kwargs,
    ) -> BaseConversationHistory:
        """
        Create a conversation history instance.
        
        Args:
            max_messages: Max messages to keep
            implementation: Implementation name (default: "default")
            **kwargs: Additional arguments for custom implementations
            
        Returns:
            Conversation history instance
            
        Raises:
            ValueError: If implementation is not registered
        """
        impl_class = cls._conversation_registry.get(implementation)
        if impl_class is None:
            available = cls.list_conversation_implementations()
            raise ValueError(
                f"Unknown conversation history implementation: '{implementation}'. "
                f"Available: {available}"
            )
        
        return impl_class(max_messages=max_messages, **kwargs)
    
    @classmethod
    def create_state_tracker(
        cls,
        session_id: str,
        max_checkpoints: int = 50,
        implementation: str = "default",
        **kwargs,
    ) -> BaseStateTracker:
        """
        Create a state tracker instance.
        
        Args:
            session_id: Session identifier
            max_checkpoints: Max checkpoints to keep
            implementation: Implementation name (default: "default")
            **kwargs: Additional arguments for custom implementations
            
        Returns:
            State tracker instance
            
        Raises:
            ValueError: If implementation is not registered
        """
        impl_class = cls._state_tracker_registry.get(implementation)
        if impl_class is None:
            available = cls.list_state_tracker_implementations()
            raise ValueError(
                f"Unknown state tracker implementation: '{implementation}'. "
                f"Available: {available}"
            )
        
        return impl_class(
            session_id=session_id,
            max_checkpoints=max_checkpoints,
            **kwargs,
        )
    
    @classmethod
    def create_from_config(cls, config: Dict[str, Any]) -> Any:
        """
        Create memory from configuration dictionary.
        
        Args:
            config: Configuration with "type", "implementation" and type-specific params
            
        Returns:
            Memory instance
            
        Example config:
            {
                "type": "working",
                "implementation": "agent",
                "session_id": "session-123",
                "max_messages": 100,
                "max_checkpoints": 50,
            }
        """
        memory_type = config.get("type", MemoryType.WORKING)
        implementation = config.get("implementation", "default")
        
        # Extract common params
        session_id = config.get("session_id")
        max_messages = config.get("max_messages")
        max_checkpoints = config.get("max_checkpoints", 50)
        
        # Extra params for custom implementations
        extra_params = {
            k: v for k, v in config.items() 
            if k not in ["type", "implementation", "session_id", "max_messages", "max_checkpoints"]
        }
        
        if memory_type == MemoryType.WORKING or memory_type == "working":
            return cls.create_working_memory(
                session_id=session_id,
                max_messages=max_messages,
                max_checkpoints=max_checkpoints,
                implementation=implementation,
                **extra_params,
            )
        
        elif memory_type == MemoryType.CONVERSATION or memory_type == "conversation":
            return cls.create_conversation_history(
                max_messages=max_messages,
                implementation=implementation,
                **extra_params,
            )
        
        elif memory_type == MemoryType.STATE_TRACKER or memory_type == "state_tracker":
            if not session_id:
                raise ValueError("session_id is required for state_tracker")
            return cls.create_state_tracker(
                session_id=session_id,
                max_checkpoints=max_checkpoints,
                implementation=implementation,
                **extra_params,
            )
        
        else:
            raise ValueError(f"Unknown memory type: {memory_type}")
    
    # =========================================================================
    # Restoration Methods
    # =========================================================================
    
    @classmethod
    def restore_working_memory(
        cls,
        data: Dict[str, Any],
        implementation: str = "default",
    ) -> BaseWorkingMemory:
        """
        Restore a working memory from serialized data.
        
        Args:
            data: Serialized memory data
            implementation: Implementation name to use for restoration
            
        Returns:
            Restored working memory instance
        """
        impl_class = cls._working_memory_registry.get(implementation)
        if impl_class is None:
            available = cls.list_working_memory_implementations()
            raise ValueError(
                f"Unknown working memory implementation: '{implementation}'. "
                f"Available: {available}"
            )
        
        return impl_class.from_dict(data)
    
    @classmethod
    def restore_conversation_history(
        cls,
        data: Dict[str, Any],
        implementation: str = "default",
    ) -> BaseConversationHistory:
        """
        Restore a conversation history from serialized data.
        
        Args:
            data: Serialized data
            implementation: Implementation name to use for restoration
            
        Returns:
            Restored conversation history instance
        """
        impl_class = cls._conversation_registry.get(implementation)
        if impl_class is None:
            available = cls.list_conversation_implementations()
            raise ValueError(
                f"Unknown conversation history implementation: '{implementation}'. "
                f"Available: {available}"
            )
        
        return impl_class.from_dict(data)
    
    @classmethod
    def restore_state_tracker(
        cls,
        data: Dict[str, Any],
        implementation: str = "default",
    ) -> BaseStateTracker:
        """
        Restore a state tracker from serialized data.
        
        Args:
            data: Serialized data
            implementation: Implementation name to use for restoration
            
        Returns:
            Restored state tracker instance
        """
        impl_class = cls._state_tracker_registry.get(implementation)
        if impl_class is None:
            available = cls.list_state_tracker_implementations()
            raise ValueError(
                f"Unknown state tracker implementation: '{implementation}'. "
                f"Available: {available}"
            )
        
        return impl_class.from_dict(data)


# =========================================================================
# Convenience Functions
# =========================================================================

def create_working_memory(
    session_id: Optional[str] = None,
    max_messages: Optional[int] = None,
    max_checkpoints: int = 50,
    implementation: str = "default",
    **kwargs,
) -> BaseWorkingMemory:
    """Create working memory (convenience function)."""
    return MemoryFactory.create_working_memory(
        session_id=session_id,
        max_messages=max_messages,
        max_checkpoints=max_checkpoints,
        implementation=implementation,
        **kwargs,
    )


def create_conversation_history(
    max_messages: Optional[int] = None,
    implementation: str = "default",
    **kwargs,
) -> BaseConversationHistory:
    """Create conversation history (convenience function)."""
    return MemoryFactory.create_conversation_history(
        max_messages=max_messages,
        implementation=implementation,
        **kwargs,
    )


def create_state_tracker(
    session_id: str,
    max_checkpoints: int = 50,
    implementation: str = "default",
    **kwargs,
) -> BaseStateTracker:
    """Create state tracker (convenience function)."""
    return MemoryFactory.create_state_tracker(
        session_id=session_id,
        max_checkpoints=max_checkpoints,
        implementation=implementation,
        **kwargs,
    )
