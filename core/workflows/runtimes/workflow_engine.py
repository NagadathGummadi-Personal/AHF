"""
Workflow Engine Implementation Module.

This module provides the main workflow execution engine.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, AsyncIterator, Dict, List, Optional, Set, Tuple

from ..interfaces import (
    IWorkflow,
    IWorkflowExecutor,
    IWorkflowContext,
    IWorkflowObserver,
    INodeObserver,
    INode,
    IEdge,
    IRouter,
)
from ..enum import WorkflowState, NodeState, RoutingStrategy
from ..spec import (
    WorkflowContext,
    WorkflowResult,
    NodeResult,
    NodeExecutionRecord,
)
from ..exceptions import (
    WorkflowExecutionError,
    NodeExecutionError,
    MaxIterationsError,
    WorkflowTimeoutError,
    RoutingError,
)
from ..constants import NODE_ID_START, NODE_ID_END

logger = logging.getLogger(__name__)


class DefaultRouter(IRouter):
    """Default workflow router implementation."""
    
    def __init__(self, strategy: RoutingStrategy = RoutingStrategy.FIRST_MATCH):
        self._strategy = strategy
    
    @property
    def strategy(self) -> RoutingStrategy:
        return self._strategy
    
    async def get_next_nodes(
        self,
        current_node_id: str,
        context: IWorkflowContext,
        edges: List[IEdge],
    ) -> List[Tuple[str, Optional[IEdge]]]:
        """Determine next nodes based on strategy."""
        if not edges:
            return []
        
        # Sort by priority (higher first)
        sorted_edges = sorted(edges, key=lambda e: e.priority, reverse=True)
        
        if self._strategy == RoutingStrategy.FIRST_MATCH:
            for edge in sorted_edges:
                if edge.can_traverse(context):
                    return [(edge.target_id, edge)]
            return []
        
        elif self._strategy == RoutingStrategy.ALL_MATCHES:
            matches = []
            for edge in sorted_edges:
                if edge.can_traverse(context):
                    matches.append((edge.target_id, edge))
            return matches
        
        else:
            # Default to first match
            for edge in sorted_edges:
                if edge.can_traverse(context):
                    return [(edge.target_id, edge)]
            return []
    
    def to_dict(self) -> Dict[str, Any]:
        return {"strategy": self._strategy.value}


class WorkflowEngine(IWorkflowExecutor):
    """
    Main workflow execution engine.
    
    Orchestrates the execution of workflow nodes, handles routing,
    error recovery, and state management.
    """
    
    def __init__(
        self,
        workflow_observers: Optional[List[IWorkflowObserver]] = None,
        node_observers: Optional[List[INodeObserver]] = None,
    ):
        """
        Initialize the workflow engine.
        
        Args:
            workflow_observers: Optional workflow lifecycle observers.
            node_observers: Optional node execution observers.
        """
        self._workflow_observers = workflow_observers or []
        self._node_observers = node_observers or []
        
        # Execution tracking
        self._active_executions: Dict[str, Dict[str, Any]] = {}
    
    async def execute(
        self,
        workflow: IWorkflow,
        input_data: Any,
        context: Optional[IWorkflowContext] = None,
    ) -> Tuple[Any, IWorkflowContext]:
        """
        Execute a workflow to completion.
        
        Args:
            workflow: The workflow to execute.
            input_data: Initial input data.
            context: Optional pre-configured context.
            
        Returns:
            Tuple of (final_output, final_context).
        """
        # Create context if not provided
        if context is None:
            context = WorkflowContext(
                workflow_id=workflow.id,
                input_data=input_data,
            )
        
        execution_id = context.execution_id
        start_time = time.time()
        
        logger.info(
            f"Starting workflow execution: {workflow.name} "
            f"(id={workflow.id}, execution={execution_id})"
        )
        
        # Track execution
        self._active_executions[execution_id] = {
            "workflow_id": workflow.id,
            "state": WorkflowState.RUNNING,
            "started_at": datetime.utcnow(),
            "context": context,
        }
        
        try:
            # Notify observers
            await self._notify_workflow_start(workflow, input_data, context)
            
            # Execute the workflow
            output = await self._execute_workflow(workflow, input_data, context)
            
            # Complete
            duration_ms = (time.time() - start_time) * 1000
            context.output_data = output
            
            # Notify observers
            await self._notify_workflow_complete(workflow, output, context, duration_ms)
            
            logger.info(
                f"Workflow completed: {workflow.name} "
                f"(duration={duration_ms:.2f}ms)"
            )
            
            return output, context
            
        except Exception as e:
            # Notify observers of error
            await self._notify_workflow_error(workflow, e, context)
            
            logger.error(f"Workflow failed: {workflow.name} - {e}")
            raise
            
        finally:
            # Cleanup
            self._active_executions.pop(execution_id, None)
    
    async def _execute_workflow(
        self,
        workflow: IWorkflow,
        input_data: Any,
        context: WorkflowContext,
    ) -> Any:
        """Execute the workflow graph."""
        # Get start node
        start_node_id = workflow.start_node_id
        start_node = workflow.get_node(start_node_id)
        
        if not start_node:
            raise WorkflowExecutionError(
                f"Start node not found: {start_node_id}",
                workflow_id=workflow.id,
            )
        
        # Get router
        router = workflow.router if hasattr(workflow, 'router') else DefaultRouter()
        
        # Track execution
        iteration = 0
        max_iterations = context.metadata.get("max_iterations", 100)
        timeout = context.metadata.get("timeout_seconds", 3600)
        start_time = time.time()
        
        # Initialize with start node
        current_data = input_data
        nodes_to_execute: List[Tuple[str, Any, Optional[IEdge]]] = [
            (start_node_id, input_data, None)
        ]
        
        while nodes_to_execute:
            # Check iteration limit
            iteration += 1
            if iteration > max_iterations:
                raise MaxIterationsError(max_iterations, workflow.id)
            
            # Check timeout
            if time.time() - start_time > timeout:
                raise WorkflowTimeoutError(timeout, workflow.id)
            
            # Get next node to execute
            node_id, node_input, incoming_edge = nodes_to_execute.pop(0)
            
            # Get the node
            node = workflow.get_node(node_id)
            if not node:
                logger.warning(f"Node not found: {node_id}")
                continue
            
            # Check if already completed
            if context.get_node_state(node_id) == NodeState.COMPLETED:
                continue
            
            # Transform data if edge has transformer
            if incoming_edge:
                node_input = await incoming_edge.transform_data(node_input, context)
            
            # Execute node
            try:
                node_output = await self._execute_node(
                    node, node_input, context, iteration
                )
                current_data = node_output
                
            except Exception as e:
                # Check for error edges
                error_edges = [
                    edge for edge in workflow.get_outgoing_edges(node_id)
                    if edge.edge_type.value == "error"
                ]
                
                if error_edges:
                    # Store error in context for error edge evaluation
                    context.set("__current_error__", e)
                    # Route to error handler
                    for edge in error_edges:
                        if edge.can_traverse(context):
                            nodes_to_execute.append((edge.target_id, current_data, edge))
                            break
                    context.set("__current_error__", None)
                    continue
                
                raise
            
            # Check if this is an end node
            if node_id in workflow.end_node_ids:
                logger.debug(f"Reached end node: {node_id}")
                continue
            
            # Get outgoing edges and route
            outgoing_edges = workflow.get_outgoing_edges(node_id)
            next_nodes = await router.get_next_nodes(node_id, context, outgoing_edges)
            
            if not next_nodes and node_id not in workflow.end_node_ids:
                logger.warning(f"No outgoing edges from node {node_id}")
            
            # Add next nodes to queue
            for target_id, edge in next_nodes:
                nodes_to_execute.append((target_id, node_output, edge))
        
        # Return final output
        return current_data
    
    async def _execute_node(
        self,
        node: INode,
        input_data: Any,
        context: WorkflowContext,
        iteration: int,
    ) -> Any:
        """Execute a single node."""
        node_id = node.id
        start_time = time.time()
        
        logger.debug(f"Executing node: {node.name} (iteration={iteration})")
        
        # Update state
        context.set_node_state(node_id, NodeState.RUNNING)
        context.execution_path.append(node_id)
        
        # Notify observers
        await self._notify_node_start(node, input_data, context)
        
        try:
            # Execute the node
            output = await node.execute(input_data, context)
            
            # Update context
            duration_ms = (time.time() - start_time) * 1000
            context.set_node_state(node_id, NodeState.COMPLETED)
            context.set_node_output(node_id, output)
            
            # Notify observers
            await self._notify_node_complete(node, output, context, duration_ms)
            
            logger.debug(
                f"Node completed: {node.name} (duration={duration_ms:.2f}ms)"
            )
            
            return output
            
        except Exception as e:
            # Update state
            context.set_node_state(node_id, NodeState.FAILED)
            
            # Notify observers
            await self._notify_node_error(node, e, context)
            
            logger.error(f"Node failed: {node.name} - {e}")
            raise NodeExecutionError(
                str(e),
                node_id=node_id,
                node_type=node.node_type.value,
            ) from e
    
    async def execute_streaming(
        self,
        workflow: IWorkflow,
        input_data: Any,
        context: Optional[IWorkflowContext] = None,
    ) -> AsyncIterator[Tuple[str, Any, IWorkflowContext]]:
        """
        Execute workflow with streaming output.
        
        Yields after each node execution.
        """
        if context is None:
            context = WorkflowContext(
                workflow_id=workflow.id,
                input_data=input_data,
            )
        
        # Similar to execute but yield after each node
        start_node_id = workflow.start_node_id
        router = workflow.router if hasattr(workflow, 'router') else DefaultRouter()
        
        iteration = 0
        max_iterations = 100
        current_data = input_data
        nodes_to_execute = [(start_node_id, input_data, None)]
        
        while nodes_to_execute:
            iteration += 1
            if iteration > max_iterations:
                break
            
            node_id, node_input, incoming_edge = nodes_to_execute.pop(0)
            node = workflow.get_node(node_id)
            
            if not node or context.get_node_state(node_id) == NodeState.COMPLETED:
                continue
            
            if incoming_edge:
                node_input = await incoming_edge.transform_data(node_input, context)
            
            # Execute and yield
            node_output = await self._execute_node(node, node_input, context, iteration)
            current_data = node_output
            
            yield (node_id, node_output, context)
            
            if node_id in workflow.end_node_ids:
                continue
            
            outgoing_edges = workflow.get_outgoing_edges(node_id)
            next_nodes = await router.get_next_nodes(node_id, context, outgoing_edges)
            
            for target_id, edge in next_nodes:
                nodes_to_execute.append((target_id, node_output, edge))
    
    async def pause(self, execution_id: str) -> bool:
        """Pause a running execution."""
        if execution_id not in self._active_executions:
            return False
        
        self._active_executions[execution_id]["state"] = WorkflowState.PAUSED
        logger.info(f"Paused execution: {execution_id}")
        return True
    
    async def resume(
        self,
        execution_id: str,
        input_data: Optional[Any] = None,
    ) -> Tuple[Any, IWorkflowContext]:
        """Resume a paused execution."""
        if execution_id not in self._active_executions:
            raise WorkflowExecutionError(
                f"Execution not found: {execution_id}"
            )
        
        execution = self._active_executions[execution_id]
        if execution["state"] != WorkflowState.PAUSED:
            raise WorkflowExecutionError(
                f"Execution is not paused: {execution_id}"
            )
        
        execution["state"] = WorkflowState.RUNNING
        context = execution["context"]
        
        logger.info(f"Resumed execution: {execution_id}")
        
        # Continue from where we left off
        # This would require more sophisticated state tracking
        return context.output_data, context
    
    async def cancel(self, execution_id: str) -> bool:
        """Cancel a running execution."""
        if execution_id not in self._active_executions:
            return False
        
        self._active_executions[execution_id]["state"] = WorkflowState.CANCELLED
        logger.info(f"Cancelled execution: {execution_id}")
        return True
    
    async def get_status(self, execution_id: str) -> Optional[WorkflowState]:
        """Get execution status."""
        if execution_id not in self._active_executions:
            return None
        return self._active_executions[execution_id]["state"]
    
    # Observer notification methods
    async def _notify_workflow_start(
        self, workflow: IWorkflow, input_data: Any, context: IWorkflowContext
    ) -> None:
        for observer in self._workflow_observers:
            try:
                await observer.on_workflow_start(workflow, input_data, context)
            except Exception as e:
                logger.warning(f"Workflow observer error: {e}")
    
    async def _notify_workflow_complete(
        self, workflow: IWorkflow, output: Any, context: IWorkflowContext, duration_ms: float
    ) -> None:
        for observer in self._workflow_observers:
            try:
                await observer.on_workflow_complete(workflow, output, context, duration_ms)
            except Exception as e:
                logger.warning(f"Workflow observer error: {e}")
    
    async def _notify_workflow_error(
        self, workflow: IWorkflow, error: Exception, context: IWorkflowContext
    ) -> None:
        for observer in self._workflow_observers:
            try:
                await observer.on_workflow_error(workflow, error, context)
            except Exception as e:
                logger.warning(f"Workflow observer error: {e}")
    
    async def _notify_node_start(
        self, node: INode, input_data: Any, context: IWorkflowContext
    ) -> None:
        for observer in self._node_observers:
            try:
                await observer.on_node_start(node, input_data, context)
            except Exception as e:
                logger.warning(f"Node observer error: {e}")
    
    async def _notify_node_complete(
        self, node: INode, output: Any, context: IWorkflowContext, duration_ms: float
    ) -> None:
        for observer in self._node_observers:
            try:
                await observer.on_node_complete(node, output, context, duration_ms)
            except Exception as e:
                logger.warning(f"Node observer error: {e}")
    
    async def _notify_node_error(
        self, node: INode, error: Exception, context: IWorkflowContext
    ) -> None:
        for observer in self._node_observers:
            try:
                await observer.on_node_error(node, error, context)
            except Exception as e:
                logger.warning(f"Node observer error: {e}")

