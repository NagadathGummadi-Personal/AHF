"""
Base Agent Implementation.

Provides an abstract base class for all agent implementations.
"""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional, TYPE_CHECKING
import time

from ..interfaces.agent_interfaces import IAgent
from ..spec.agent_spec import AgentSpec
from ..spec.agent_context import AgentContext
from ..spec.agent_result import AgentResult, AgentStreamChunk, AgentUsage
from ..enum import AgentState, AgentOutputType
from ..exceptions import (
    MaxIterationsError,
    LLMFailoverError,
    ToolExecutionError,
    ToolNotFoundError,
)

if TYPE_CHECKING:
    from ...llms.interfaces.llm_interfaces import ILLM
    from ..interfaces.agent_interfaces import (
        IAgentMemory,
        IAgentScratchpad,
        IAgentChecklist,
        IAgentPlanner,
        IAgentObserver,
        IAgentInputProcessor,
        IAgentOutputProcessor,
    )


class BaseAgent(IAgent, ABC):
    """
    Abstract base class for all agent implementations.
    
    Provides common functionality for:
    - LLM management (primary and backup)
    - Tool execution
    - Memory and scratchpad management
    - Observer notifications
    - Error handling and failover
    - Iteration management
    
    Subclasses must implement:
    - _execute_iteration(): Core iteration logic
    - _should_stop(): Stopping condition
    
    Usage:
        class MyAgent(BaseAgent):
            async def _execute_iteration(self, input_data, ctx, iteration):
                # Implement iteration logic
                return result, should_continue
            
            def _should_stop(self, result, iteration):
                return iteration >= self.spec.max_iterations
    """
    
    def __init__(
        self,
        spec: AgentSpec,
        llm: 'ILLM',
        backup_llm: Optional['ILLM'] = None,
        tools: Optional[List[Any]] = None,
        memory: Optional['IAgentMemory'] = None,
        scratchpad: Optional['IAgentScratchpad'] = None,
        checklist: Optional['IAgentChecklist'] = None,
        planner: Optional['IAgentPlanner'] = None,
        observers: Optional[List['IAgentObserver']] = None,
        input_processor: Optional['IAgentInputProcessor'] = None,
        output_processor: Optional['IAgentOutputProcessor'] = None,
        prompt_registry: Optional[Any] = None,
    ):
        """
        Initialize base agent.
        
        Args:
            spec: Agent specification
            llm: Primary LLM
            backup_llm: Backup LLM for failover
            tools: List of tools available to the agent
            memory: Memory implementation
            scratchpad: Scratchpad implementation
            checklist: Checklist implementation
            planner: Planner implementation
            observers: List of observers
            input_processor: Input processor
            output_processor: Output processor
            prompt_registry: Prompt registry for fetching prompts
        """
        self.spec = spec
        self.llm = llm
        self.backup_llm = backup_llm
        self.tools = tools or []
        self.memory = memory
        self.scratchpad = scratchpad
        self.checklist = checklist
        self.planner = planner
        self.observers = observers or []
        self.input_processor = input_processor
        self.output_processor = output_processor
        self.prompt_registry = prompt_registry
        
        # State
        self._state = AgentState.IDLE
        self._current_iteration = 0
        self._last_action: Optional[str] = None
        self._usage = AgentUsage()
        
        # Build tool map for quick lookup
        self._tool_map = self._build_tool_map()
    
    def _build_tool_map(self) -> Dict[str, Any]:
        """Build a map of tool names to tool objects."""
        tool_map = {}
        for tool in self.tools:
            if hasattr(tool, 'spec') and hasattr(tool.spec, 'tool_name'):
                tool_map[tool.spec.tool_name] = tool
            elif hasattr(tool, 'tool_name'):
                tool_map[tool.tool_name] = tool
            elif hasattr(tool, 'name'):
                tool_map[tool.name] = tool
            elif callable(tool) and hasattr(tool, '__name__'):
                tool_map[tool.__name__] = tool
        return tool_map
    
    def get_state(self) -> Dict[str, Any]:
        """Get the current internal state of the agent."""
        return {
            "status": self._state.value,
            "iteration": self._current_iteration,
            "last_action": self._last_action,
            "usage": self._usage.model_dump() if self._usage else None,
            "agent_type": self.spec.agent_type.value,
            "max_iterations": self.spec.max_iterations,
        }
    
    async def run(
        self,
        input_data: Any,
        ctx: AgentContext,
        **kwargs: Any
    ) -> AgentResult:
        """
        Execute the agent's main loop.
        
        Args:
            input_data: Input to process
            ctx: Agent execution context
            **kwargs: Additional parameters
            
        Returns:
            AgentResult with the final output
        """
        start_time = time.time()
        self._state = AgentState.RUNNING
        self._current_iteration = 0
        self._usage = AgentUsage()
        
        try:
            # Notify observers
            await self._notify_agent_start(input_data, ctx)
            
            # Process input
            processed_input = await self._process_input(input_data, ctx)
            
            # Get system prompt
            system_prompt = await self._get_system_prompt()
            
            # Main execution loop
            result = None
            while self._current_iteration < self.spec.max_iterations:
                self._current_iteration += 1
                
                await self._notify_iteration_start(self._current_iteration, ctx)
                
                # Execute iteration
                iteration_result, should_continue = await self._execute_iteration(
                    processed_input, ctx, self._current_iteration, system_prompt
                )
                
                await self._notify_iteration_end(self._current_iteration, ctx)
                
                if not should_continue:
                    result = iteration_result
                    break
            
            # Check if we exceeded max iterations
            if result is None:
                raise MaxIterationsError(
                    self._current_iteration,
                    self.spec.max_iterations
                )
            
            # Process output
            processed_output = await self._process_output(result, ctx)
            
            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)
            self._usage.duration_ms = duration_ms
            self._usage.iterations = self._current_iteration
            
            # Build final result
            final_result = AgentResult(
                content=processed_output,
                output_type=self.spec.supported_output_types[0] if self.spec.supported_output_types else AgentOutputType.TEXT,
                output_format=self.spec.default_output_format,
                state=AgentState.COMPLETED,
                usage=self._usage,
                reasoning_trace=self._get_reasoning_trace(),
                checklist_state=self._get_checklist_state(),
            )
            
            self._state = AgentState.COMPLETED
            await self._notify_agent_end(final_result, ctx)
            
            return final_result
            
        except Exception as e:
            self._state = AgentState.FAILED
            await self._notify_error(e, ctx)
            
            duration_ms = int((time.time() - start_time) * 1000)
            self._usage.duration_ms = duration_ms
            
            return AgentResult(
                content=None,
                state=AgentState.FAILED,
                usage=self._usage,
                errors=[str(e)],
            )
    
    async def stream(
        self,
        input_data: Any,
        ctx: AgentContext,
        **kwargs: Any
    ) -> AsyncIterator[AgentStreamChunk]:
        """
        Stream the agent's execution steps.
        
        Args:
            input_data: Input to process
            ctx: Agent execution context
            **kwargs: Additional parameters
            
        Yields:
            AgentStreamChunk objects with execution progress
        """
        self._state = AgentState.RUNNING
        self._current_iteration = 0
        
        try:
            await self._notify_agent_start(input_data, ctx)
            
            processed_input = await self._process_input(input_data, ctx)
            system_prompt = await self._get_system_prompt()
            
            while self._current_iteration < self.spec.max_iterations:
                self._current_iteration += 1
                
                await self._notify_iteration_start(self._current_iteration, ctx)
                
                # Stream iteration
                async for chunk in self._stream_iteration(
                    processed_input, ctx, self._current_iteration, system_prompt
                ):
                    yield chunk
                    if chunk.is_final:
                        self._state = AgentState.COMPLETED
                        return
                
                await self._notify_iteration_end(self._current_iteration, ctx)
            
            # Max iterations reached
            yield AgentStreamChunk(
                content="Max iterations reached",
                chunk_type="error",
                iteration=self._current_iteration,
                is_final=True,
                state=AgentState.FAILED,
            )
            
        except Exception as e:
            self._state = AgentState.FAILED
            await self._notify_error(e, ctx)
            yield AgentStreamChunk(
                content=str(e),
                chunk_type="error",
                iteration=self._current_iteration,
                is_final=True,
                state=AgentState.FAILED,
            )
    
    # ==================== Abstract Methods ====================
    
    @abstractmethod
    async def _execute_iteration(
        self,
        input_data: Any,
        ctx: AgentContext,
        iteration: int,
        system_prompt: Optional[str]
    ) -> tuple[Any, bool]:
        """
        Execute a single iteration.
        
        Args:
            input_data: Processed input
            ctx: Agent context
            iteration: Current iteration number
            system_prompt: System prompt
            
        Returns:
            Tuple of (result, should_continue)
        """
        ...
    
    async def _stream_iteration(
        self,
        input_data: Any,
        ctx: AgentContext,
        iteration: int,
        system_prompt: Optional[str]
    ) -> AsyncIterator[AgentStreamChunk]:
        """
        Stream a single iteration (default implementation calls _execute_iteration).
        
        Override for custom streaming behavior.
        """
        result, should_continue = await self._execute_iteration(
            input_data, ctx, iteration, system_prompt
        )
        
        yield AgentStreamChunk(
            content=str(result) if result else "",
            chunk_type="output",
            iteration=iteration,
            is_final=not should_continue,
            state=AgentState.RUNNING if should_continue else AgentState.COMPLETED,
        )
    
    # ==================== LLM Methods ====================
    
    async def _call_llm(
        self,
        messages: List[Dict[str, Any]],
        ctx: AgentContext,
        prompt_id: Optional[str] = None,
        **kwargs
    ) -> Any:
        """
        Call the LLM with failover support and metrics tracking.
        
        Args:
            messages: Messages to send
            ctx: Agent context
            prompt_id: Optional prompt ID for metrics tracking
            **kwargs: Additional LLM parameters
            
        Returns:
            LLM response
        """
        import time
        
        await self._notify_llm_call(messages, ctx)
        self._usage.llm_calls += 1
        
        # Create LLM context with prompt_id for automatic metrics recording
        from ...llms.spec.llm_context import LLMContext
        llm_ctx = LLMContext(
            request_id=ctx.request_id,
            user_id=ctx.user_id,
            session_id=ctx.session_id,
            tenant_id=ctx.tenant_id,
            trace_id=ctx.trace_id,
            prompt_id=prompt_id,
        )
        
        start_time = time.time()
        success = True
        response = None
        
        try:
            response = await self.llm.get_answer(messages, llm_ctx, **kwargs)
            await self._notify_llm_response(response, ctx)
            
            # Update token usage
            if response.usage:
                self._usage.prompt_tokens += response.usage.prompt_tokens
                self._usage.completion_tokens += response.usage.completion_tokens
                self._usage.total_tokens += response.usage.total_tokens
            
            return response
            
        except Exception as primary_error:
            success = False
            if self.backup_llm:
                try:
                    response = await self.backup_llm.get_answer(messages, llm_ctx, **kwargs)
                    await self._notify_llm_response(response, ctx)
                    success = True
                    
                    if response.usage:
                        self._usage.prompt_tokens += response.usage.prompt_tokens
                        self._usage.completion_tokens += response.usage.completion_tokens
                        self._usage.total_tokens += response.usage.total_tokens
                    
                    return response
                    
                except Exception as backup_error:
                    raise LLMFailoverError(primary_error, backup_error)
            raise
        
        finally:
            # Record prompt usage metrics if prompt registry is available
            latency_ms = (time.time() - start_time) * 1000
            await self._record_prompt_metrics(
                prompt_id=prompt_id,
                latency_ms=latency_ms,
                response=response,
                success=success
            )
    
    async def _record_prompt_metrics(
        self,
        prompt_id: Optional[str],
        latency_ms: float,
        response: Any,
        success: bool
    ) -> None:
        """
        Record metrics for prompt usage.
        
        Args:
            prompt_id: Prompt ID to record metrics for
            latency_ms: Call latency in milliseconds
            response: LLM response (may be None on failure)
            success: Whether the call succeeded
        """
        if not self.prompt_registry or not prompt_id:
            return
        
        try:
            prompt_tokens = 0
            completion_tokens = 0
            cost = 0.0
            
            if response and hasattr(response, 'usage') and response.usage:
                prompt_tokens = response.usage.prompt_tokens or 0
                completion_tokens = response.usage.completion_tokens or 0
                # Cost calculation can be added based on model pricing
            
            await self.prompt_registry.record_usage(
                prompt_id,
                latency_ms=latency_ms,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cost=cost,
                success=success
            )
        except Exception:
            pass  # Don't fail execution if metrics recording fails
    
    # ==================== Tool Methods ====================
    
    def _get_tool(self, tool_name: str) -> Any:
        """Get a tool by name."""
        tool = self._tool_map.get(tool_name)
        if not tool:
            raise ToolNotFoundError(tool_name, list(self._tool_map.keys()))
        return tool
    
    async def _execute_tool(
        self,
        tool_name: str,
        args: Dict[str, Any],
        ctx: AgentContext
    ) -> Any:
        """
        Execute a tool.
        
        Args:
            tool_name: Name of the tool
            args: Tool arguments
            ctx: Agent context
            
        Returns:
            Tool result
        """
        await self._notify_tool_call(tool_name, args, ctx)
        self._usage.tool_calls += 1
        self._last_action = tool_name
        
        try:
            tool = self._get_tool(tool_name)
            
            # Create tool context
            from ...tools.spec.tool_context import ToolContext
            tool_ctx = ToolContext(
                user_id=ctx.user_id,
                session_id=ctx.session_id,
                tenant_id=ctx.tenant_id,
                trace_id=ctx.trace_id,
            )
            
            # Execute tool
            if hasattr(tool, 'execute'):
                result = await tool.execute(args, tool_ctx)
            elif callable(tool):
                result = await tool(args)
            else:
                raise ToolExecutionError(tool_name, details={"error": "Tool not executable"})
            
            await self._notify_tool_result(tool_name, result, ctx)
            return result
            
        except Exception as e:
            raise ToolExecutionError(tool_name, e)
    
    def _get_tool_descriptions(self) -> str:
        """Get formatted tool descriptions for prompts."""
        descriptions = []
        for name, tool in self._tool_map.items():
            if hasattr(tool, 'spec') and hasattr(tool.spec, 'description'):
                descriptions.append(f"- {name}: {tool.spec.description}")
            elif hasattr(tool, 'description'):
                descriptions.append(f"- {name}: {tool.description}")
            else:
                descriptions.append(f"- {name}")
        return "\n".join(descriptions)
    
    # ==================== Input/Output Processing ====================
    
    async def _process_input(self, input_data: Any, ctx: AgentContext) -> Any:
        """Process input data."""
        if self.input_processor:
            input_type = self.spec.supported_input_types[0] if self.spec.supported_input_types else None
            if input_type:
                return await self.input_processor.process(input_data, input_type, ctx)
        return input_data
    
    async def _process_output(self, output_data: Any, ctx: AgentContext) -> Any:
        """Process output data."""
        if self.output_processor:
            output_type = self.spec.supported_output_types[0] if self.spec.supported_output_types else None
            if output_type:
                return await self.output_processor.process(
                    output_data, output_type, self.spec.default_output_format.value, ctx
                )
        return output_data
    
    async def _get_system_prompt(self) -> Optional[str]:
        """Get the system prompt."""
        if self.spec.system_prompt:
            return self.spec.system_prompt
        
        if self.spec.system_prompt_label and self.prompt_registry:
            return await self.prompt_registry.get_prompt(self.spec.system_prompt_label)
        
        return None
    
    def _get_reasoning_trace(self) -> Optional[List[str]]:
        """Get the reasoning trace from scratchpad."""
        if self.scratchpad:
            if hasattr(self.scratchpad, 'get_entries'):
                entries = self.scratchpad.get_entries()
                if isinstance(entries, list):
                    return [str(e) for e in entries]
            return [self.scratchpad.read()]
        return None
    
    def _get_checklist_state(self) -> Optional[Dict[str, Any]]:
        """Get the current checklist state."""
        if self.checklist:
            return self.checklist.to_dict()
        return None
    
    # ==================== Observer Notifications ====================
    
    async def _notify_agent_start(self, input_data: Any, ctx: AgentContext) -> None:
        """Notify observers of agent start."""
        for observer in self.observers:
            await observer.on_agent_start(input_data, ctx)
    
    async def _notify_agent_end(self, result: AgentResult, ctx: AgentContext) -> None:
        """Notify observers of agent end."""
        for observer in self.observers:
            await observer.on_agent_end(result, ctx)
    
    async def _notify_iteration_start(self, iteration: int, ctx: AgentContext) -> None:
        """Notify observers of iteration start."""
        for observer in self.observers:
            await observer.on_iteration_start(iteration, ctx)
    
    async def _notify_iteration_end(self, iteration: int, ctx: AgentContext) -> None:
        """Notify observers of iteration end."""
        for observer in self.observers:
            await observer.on_iteration_end(iteration, ctx)
    
    async def _notify_tool_call(
        self,
        tool_name: str,
        args: Dict[str, Any],
        ctx: AgentContext
    ) -> None:
        """Notify observers of tool call."""
        for observer in self.observers:
            await observer.on_tool_call(tool_name, args, ctx)
    
    async def _notify_tool_result(
        self,
        tool_name: str,
        result: Any,
        ctx: AgentContext
    ) -> None:
        """Notify observers of tool result."""
        for observer in self.observers:
            await observer.on_tool_result(tool_name, result, ctx)
    
    async def _notify_llm_call(
        self,
        messages: List[Dict[str, Any]],
        ctx: AgentContext
    ) -> None:
        """Notify observers of LLM call."""
        for observer in self.observers:
            await observer.on_llm_call(messages, ctx)
    
    async def _notify_llm_response(self, response: Any, ctx: AgentContext) -> None:
        """Notify observers of LLM response."""
        for observer in self.observers:
            await observer.on_llm_response(response, ctx)
    
    async def _notify_error(self, error: Exception, ctx: AgentContext) -> None:
        """Notify observers of error."""
        for observer in self.observers:
            await observer.on_error(error, ctx)

