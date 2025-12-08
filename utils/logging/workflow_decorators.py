"""
Workflow Logging Decorators.

Provides decorators for collecting metrics during workflow execution
without synchronous logging. Metrics are collected into WorkflowMetrics
and logged asynchronously at the end of execution.

Configuration is loaded from the workflow_logging section of the log config files.

Usage:
    from utils.logging.workflow_decorators import (
        collect_workflow_metrics,
        collect_agent_metrics,
        collect_llm_metrics,
        collect_node_metrics,
        collect_edge_metrics,
        collect_tool_metrics,
    )
    
    @collect_agent_metrics
    async def run(self, message, context):
        return await self._execute(message)
    
    @collect_llm_metrics("gpt-4")
    async def generate(self, messages, **kwargs):
        return await self._call_api(messages)

Version: 1.0.0
"""

import functools
import time
import uuid
import asyncio
from contextlib import contextmanager
from typing import Any, Callable, Optional, TypeVar, Generator

from .LoggerAdaptor import LoggerAdaptor, WorkflowMetrics
from .DelayedLogger import DelayedLogger

F = TypeVar('F', bound=Callable[..., Any])


def _get_logger(name: str = "workflow") -> LoggerAdaptor:
    """Get or create a logger instance."""
    return LoggerAdaptor.get_logger(name)


def _get_workflow_config() -> dict:
    """Get workflow logging config from LoggerAdaptor."""
    config = LoggerAdaptor._config or {}
    return config.get('workflow_logging', {})


def _is_enabled() -> bool:
    """Check if workflow logging is enabled."""
    return _get_workflow_config().get('enabled', True)


def _should_use_async() -> bool:
    """Check if async logging should be used."""
    return _get_workflow_config().get('async_logging', True)


@contextmanager
def metrics_context(
    component_type: str,
    component_id: Optional[str] = None,
    component_name: Optional[str] = None,
    trace_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
    node_id: Optional[str] = None,
    user_message: Optional[str] = None,
    **metadata
) -> Generator[WorkflowMetrics, None, None]:
    """
    Context manager for collecting metrics during execution.
    
    Collects timing, tokens, cost, and other metrics without
    synchronous logging. Logs all metrics at the end.
    
    Args:
        component_type: Type of component ('workflow', 'node', 'edge', 'agent', 'llm', 'tool')
        component_id: Component identifier
        component_name: Human-readable component name
        trace_id: Trace ID for correlation (auto-generated if not provided)
        workflow_id: Parent workflow ID
        node_id: Parent node ID
        user_message: User input message
        **metadata: Additional metadata to include
    
    Yields:
        WorkflowMetrics instance for collecting metrics
    
    Usage:
        with metrics_context('agent', agent_id='greeting') as metrics:
            result = await agent.run(message)
            metrics.update_from_usage(result.usage)
            metrics.response = result.content
    """
    if not _is_enabled():
        # Yield a dummy metrics object that won't be logged
        yield WorkflowMetrics()
        return
    
    # Create metrics object
    metrics = WorkflowMetrics(
        component_type=component_type,
        component_id=component_id,
        component_name=component_name,
        trace_id=trace_id or str(uuid.uuid4())[:8],
        workflow_id=workflow_id,
        node_id=node_id,
        user_message=user_message,
        metadata=metadata,
    )
    
    start_time = time.perf_counter()
    
    try:
        yield metrics
        metrics.success = True
    except Exception as e:
        metrics.success = False
        metrics.error = str(e)
        metrics.error_type = type(e).__name__
        raise
    finally:
        # Record duration
        metrics.duration_ms = (time.perf_counter() - start_time) * 1000
        
        # Log metrics (async or sync based on config)
        logger = _get_logger("workflow")
        
        if _should_use_async():
            # Use delayed logger for async logging
            delayed = DelayedLogger(logger)
            if LoggerAdaptor._config:
                delayed.configure(LoggerAdaptor._config)
            # Queue the metrics for async logging
            _log_metrics_delayed(delayed, metrics)
        else:
            # Log immediately
            logger.log_workflow_metrics(metrics)


def _log_metrics_delayed(delayed_logger: DelayedLogger, metrics: WorkflowMetrics):
    """Log metrics using delayed logger."""
    config = _get_workflow_config()
    log_context = metrics.to_log_dict(config)
    messages = config.get('messages', {})
    
    component_type = metrics.component_type or 'workflow'
    component_name = metrics.component_name or metrics.component_id or 'unknown'
    
    # Token message
    if config.get('log_usage_metrics', True) and metrics.total_tokens:
        token_template = messages.get(
            'tokens',
            "Consumed Input tokens {input_tokens}, Output tokens {output_tokens}, Total {total_tokens}"
        )
        token_msg = token_template.format(
            input_tokens=metrics.input_tokens or 0,
            output_tokens=metrics.output_tokens or 0,
            total_tokens=metrics.total_tokens or 0,
        )
        delayed_logger.info_delayed(token_msg, **log_context)
    
    # Duration message
    if metrics.duration_ms is not None:
        duration_template = messages.get(
            'duration',
            "{component} '{name}' completed in {duration_ms:.2f}ms"
        )
        duration_msg = duration_template.format(
            component=component_type.title(),
            name=component_name,
            duration_ms=metrics.duration_ms,
        )
        delayed_logger.info_delayed(duration_msg, **log_context)
    
    # Error message
    if metrics.error:
        error_template = messages.get(
            'error',
            "{component} '{name}' failed: {error}"
        )
        error_msg = error_template.format(
            component=component_type.title(),
            name=component_name,
            error=metrics.error,
        )
        delayed_logger.error_delayed(error_msg, error_type=metrics.error_type, **log_context)
    
    # Flush if configured
    delayed_logger.flush_on_completion()


# =============================================================================
# DECORATORS
# =============================================================================

def collect_workflow_metrics(
    workflow_id: Optional[str] = None,
    workflow_name: Optional[str] = None,
):
    """
    Decorator for collecting metrics during workflow execution.
    
    Args:
        workflow_id: Workflow identifier (auto-detected if not provided)
        workflow_name: Workflow name
    
    Usage:
        @collect_workflow_metrics("my-workflow")
        async def execute(self, input_data):
            ...
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            if not _is_enabled():
                return await func(*args, **kwargs)
            
            # Extract workflow ID
            _workflow_id = workflow_id
            _workflow_name = workflow_name
            
            if not _workflow_id and len(args) > 0:
                self_obj = args[0]
                if hasattr(self_obj, 'id'):
                    _workflow_id = self_obj.id
                elif hasattr(self_obj, 'spec') and hasattr(self_obj.spec, 'id'):
                    _workflow_id = self_obj.spec.id
                if hasattr(self_obj, 'name'):
                    _workflow_name = _workflow_name or self_obj.name
                elif hasattr(self_obj, 'spec') and hasattr(self_obj.spec, 'name'):
                    _workflow_name = _workflow_name or self_obj.spec.name
            
            _workflow_id = _workflow_id or func.__name__
            
            # Get user message from args
            user_message = args[1] if len(args) > 1 else kwargs.get("input", None)
            
            with metrics_context(
                component_type='workflow',
                component_id=_workflow_id,
                component_name=_workflow_name,
                workflow_id=_workflow_id,
                user_message=str(user_message) if user_message else None,
            ) as metrics:
                result = await func(*args, **kwargs)
                
                # Extract response if available
                if hasattr(result, 'content'):
                    metrics.response = str(result.content)
                elif isinstance(result, str):
                    metrics.response = result
                
                # Extract usage if available
                if hasattr(result, 'usage'):
                    metrics.update_from_usage(result.usage)
                
                return result
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            if not _is_enabled():
                return func(*args, **kwargs)
            
            _workflow_id = workflow_id or func.__name__
            
            with metrics_context(
                component_type='workflow',
                component_id=_workflow_id,
                workflow_id=_workflow_id,
            ):
                result = func(*args, **kwargs)
                return result
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def collect_node_metrics(
    node_id: Optional[str] = None,
    node_name: Optional[str] = None,
):
    """
    Decorator for collecting metrics during node execution.
    
    Args:
        node_id: Node identifier
        node_name: Node name
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            if not _is_enabled():
                return await func(*args, **kwargs)
            
            _node_id = node_id
            _node_name = node_name
            
            if not _node_id and len(args) > 0:
                self_obj = args[0]
                if hasattr(self_obj, 'id'):
                    _node_id = self_obj.id
                elif hasattr(self_obj, 'spec') and hasattr(self_obj.spec, 'id'):
                    _node_id = self_obj.spec.id
                if hasattr(self_obj, 'name'):
                    _node_name = _node_name or self_obj.name
            
            _node_id = _node_id or func.__name__
            user_message = args[1] if len(args) > 1 else kwargs.get("input", None)
            
            with metrics_context(
                component_type='node',
                component_id=_node_id,
                component_name=_node_name,
                node_id=_node_id,
                user_message=str(user_message) if user_message else None,
            ) as metrics:
                result = await func(*args, **kwargs)
                
                if hasattr(result, 'content'):
                    metrics.response = str(result.content)
                if hasattr(result, 'usage'):
                    metrics.update_from_usage(result.usage)
                
                return result
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return func
    
    return decorator


def collect_agent_metrics(
    agent_id: Optional[str] = None,
):
    """
    Decorator for collecting metrics during agent execution.
    
    Args:
        agent_id: Agent identifier
    
    Usage:
        @collect_agent_metrics("greeting-agent")
        async def run(self, message, context):
            return await self._execute(message)
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            if not _is_enabled():
                return await func(*args, **kwargs)
            
            _agent_id = agent_id
            
            if not _agent_id and len(args) > 0:
                self_obj = args[0]
                if hasattr(self_obj, 'spec') and hasattr(self_obj.spec, 'name'):
                    _agent_id = self_obj.spec.name
                elif hasattr(self_obj, 'id'):
                    _agent_id = self_obj.id
            
            _agent_id = _agent_id or func.__name__
            
            # Get user message (usually second arg after self)
            user_message = args[1] if len(args) > 1 else kwargs.get("message", kwargs.get("input", None))
            
            with metrics_context(
                component_type='agent',
                component_id=_agent_id,
                user_message=str(user_message) if user_message else None,
            ) as metrics:
                result = await func(*args, **kwargs)
                
                # Extract response
                if hasattr(result, 'content'):
                    metrics.response = str(result.content)
                
                # Extract usage metrics
                if hasattr(result, 'usage'):
                    metrics.update_from_usage(result.usage)
                
                return result
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            if not _is_enabled():
                return func(*args, **kwargs)
            
            _agent_id = agent_id or func.__name__
            user_message = args[1] if len(args) > 1 else None
            
            with metrics_context(
                component_type='agent',
                component_id=_agent_id,
                user_message=str(user_message) if user_message else None,
            ) as metrics:
                result = func(*args, **kwargs)
                if hasattr(result, 'usage'):
                    metrics.update_from_usage(result.usage)
                return result
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def collect_llm_metrics(
    llm_id: Optional[str] = None,
):
    """
    Decorator for collecting metrics during LLM calls.
    
    Args:
        llm_id: LLM identifier
    
    Usage:
        @collect_llm_metrics("gpt-4")
        async def generate(self, messages, **kwargs):
            return await self._call_api(messages)
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            if not _is_enabled():
                return await func(*args, **kwargs)
            
            _llm_id = llm_id
            
            if not _llm_id and len(args) > 0:
                self_obj = args[0]
                if hasattr(self_obj, 'metadata') and hasattr(self_obj.metadata, 'name'):
                    _llm_id = self_obj.metadata.name
                elif hasattr(self_obj, 'id'):
                    _llm_id = self_obj.id
            
            _llm_id = _llm_id or func.__name__
            
            # Try to extract user message from messages arg
            user_message = None
            messages = kwargs.get('messages', args[1] if len(args) > 1 else None)
            if isinstance(messages, list) and messages:
                last_user = next(
                    (m for m in reversed(messages) if m.get("role") == "user"),
                    None
                )
                if last_user:
                    user_message = last_user.get("content", "")
            
            with metrics_context(
                component_type='llm',
                component_id=_llm_id,
                user_message=user_message,
            ) as metrics:
                result = await func(*args, **kwargs)
                
                # Extract response
                if hasattr(result, 'content'):
                    metrics.response = str(result.content)
                
                # Extract usage metrics
                if hasattr(result, 'usage'):
                    metrics.update_from_usage(result.usage)
                
                return result
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            if not _is_enabled():
                return func(*args, **kwargs)
            
            _llm_id = llm_id or func.__name__
            
            with metrics_context(
                component_type='llm',
                component_id=_llm_id,
            ) as metrics:
                result = func(*args, **kwargs)
                if hasattr(result, 'usage'):
                    metrics.update_from_usage(result.usage)
                return result
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def collect_edge_metrics(
    edge_id: Optional[str] = None,
):
    """
    Decorator for collecting metrics during edge evaluation.
    
    Args:
        edge_id: Edge identifier
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            if not _is_enabled():
                return await func(*args, **kwargs)
            
            _edge_id = edge_id
            source_node = None
            target_node = None
            
            if len(args) > 0:
                self_obj = args[0]
                if hasattr(self_obj, 'id'):
                    _edge_id = _edge_id or self_obj.id
                if hasattr(self_obj, 'source_node_id'):
                    source_node = self_obj.source_node_id
                if hasattr(self_obj, 'target_node_id'):
                    target_node = self_obj.target_node_id
            
            _edge_id = _edge_id or func.__name__
            
            with metrics_context(
                component_type='edge',
                component_id=_edge_id,
                source_node=source_node,
                target_node=target_node,
            ) as metrics:
                result = await func(*args, **kwargs)
                
                if isinstance(result, bool):
                    metrics.condition_result = result
                
                return result
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            if not _is_enabled():
                return func(*args, **kwargs)
            
            _edge_id = edge_id or func.__name__
            
            with metrics_context(
                component_type='edge',
                component_id=_edge_id,
            ) as metrics:
                result = func(*args, **kwargs)
                if isinstance(result, bool):
                    metrics.condition_result = result
                return result
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def collect_tool_metrics(
    tool_id: Optional[str] = None,
    tool_name: Optional[str] = None,
):
    """
    Decorator for collecting metrics during tool execution.
    
    Args:
        tool_id: Tool identifier
        tool_name: Tool name
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            if not _is_enabled():
                return await func(*args, **kwargs)
            
            _tool_id = tool_id
            _tool_name = tool_name
            
            if not _tool_id and len(args) > 0:
                self_obj = args[0]
                if hasattr(self_obj, 'id'):
                    _tool_id = self_obj.id
                if hasattr(self_obj, 'name'):
                    _tool_name = _tool_name or self_obj.name
                elif hasattr(self_obj, 'spec') and hasattr(self_obj.spec, 'name'):
                    _tool_name = _tool_name or self_obj.spec.name
            
            _tool_id = _tool_id or func.__name__
            
            with metrics_context(
                component_type='tool',
                component_id=_tool_id,
                component_name=_tool_name,
            ) as metrics:
                result = await func(*args, **kwargs)
                
                if isinstance(result, str):
                    metrics.response = result
                elif hasattr(result, 'output'):
                    metrics.response = str(result.output)
                
                return result
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            if not _is_enabled():
                return func(*args, **kwargs)
            
            _tool_id = tool_id or func.__name__
            
            with metrics_context(
                component_type='tool',
                component_id=_tool_id,
                component_name=tool_name,
            ) as metrics:
                result = func(*args, **kwargs)
                if isinstance(result, str):
                    metrics.response = result
                return result
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator
