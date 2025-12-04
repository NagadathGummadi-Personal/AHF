"""
Parallel Node Implementation Module.

This module provides a node that executes multiple child nodes in parallel.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from ..interfaces import IWorkflowContext, INode
from ..enum import NodeType, NodeState
from ..spec import NodeSpec
from ..exceptions import NodeExecutionError, ParallelExecutionError
from ..constants import DEFAULT_PARALLEL_MAX_CONCURRENCY
from .base_node import BaseNode

logger = logging.getLogger(__name__)


class ParallelNode(BaseNode):
    """
    A node that executes multiple operations in parallel.
    
    Configuration:
        max_concurrency: Maximum parallel executions (default: 10)
        fail_fast: Stop all on first failure (default: True)
        collect_results: How to collect results ("dict", "list", "merge")
        branches: List of branch configurations
            - name: Branch identifier
            - node_id: ID of node to execute
            - input: Optional input override
    """
    
    def __init__(
        self,
        spec: NodeSpec,
        child_nodes: Optional[Dict[str, INode]] = None,
    ):
        """
        Initialize the parallel node.
        
        Args:
            spec: Node specification.
            child_nodes: Dictionary of child nodes by ID.
        """
        if spec.node_type != NodeType.PARALLEL:
            spec.node_type = NodeType.PARALLEL
        
        super().__init__(spec)
        
        self._child_nodes = child_nodes or {}
        self._max_concurrency = self._config.get(
            "max_concurrency",
            DEFAULT_PARALLEL_MAX_CONCURRENCY
        )
        self._fail_fast = self._config.get("fail_fast", True)
        self._collect_mode = self._config.get("collect_results", "dict")
    
    async def execute(
        self,
        input_data: Any,
        context: IWorkflowContext,
    ) -> Any:
        """
        Execute branches in parallel.
        
        Args:
            input_data: Input from previous node.
            context: Workflow execution context.
            
        Returns:
            Collected results from all branches.
        """
        logger.info(f"Executing parallel node: {self._name}")
        
        # Resolve input
        resolved_input = self._resolve_input(context, input_data)
        
        # Get branches to execute
        branches = self._config.get("branches", [])
        
        if not branches:
            logger.warning(f"Parallel node {self._name} has no branches")
            return {}
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(self._max_concurrency)
        
        # Execute branches
        tasks = []
        for branch in branches:
            branch_name = branch.get("name", branch.get("node_id", "unknown"))
            branch_input = branch.get("input", resolved_input)
            
            task = self._execute_branch(
                branch_name,
                branch,
                branch_input,
                context.clone(),  # Clone context for each branch
                semaphore,
            )
            tasks.append((branch_name, task))
        
        # Wait for all tasks
        results = {}
        errors = []
        
        if self._fail_fast:
            # Use gather with return_exceptions=False to fail fast
            try:
                task_results = await asyncio.gather(
                    *[t[1] for t in tasks],
                    return_exceptions=False,
                )
                for i, (name, _) in enumerate(tasks):
                    results[name] = task_results[i]
            except Exception as e:
                errors.append(str(e))
        else:
            # Execute all and collect errors
            task_results = await asyncio.gather(
                *[t[1] for t in tasks],
                return_exceptions=True,
            )
            for i, (name, _) in enumerate(tasks):
                if isinstance(task_results[i], Exception):
                    errors.append(f"{name}: {task_results[i]}")
                else:
                    results[name] = task_results[i]
        
        if errors and self._fail_fast:
            raise ParallelExecutionError(
                f"Parallel execution failed: {'; '.join(errors)}",
                failed_nodes=[e.split(":")[0] for e in errors],
            )
        
        # Collect and format results
        output = self._collect_results(results, errors)
        
        logger.debug(
            f"Parallel node {self._name} completed: "
            f"{len(results)} succeeded, {len(errors)} failed"
        )
        
        return output
    
    async def _execute_branch(
        self,
        branch_name: str,
        branch_config: Dict[str, Any],
        input_data: Any,
        context: IWorkflowContext,
        semaphore: asyncio.Semaphore,
    ) -> Any:
        """Execute a single branch."""
        async with semaphore:
            node_id = branch_config.get("node_id")
            
            if node_id and node_id in self._child_nodes:
                node = self._child_nodes[node_id]
                return await node.execute(input_data, context)
            
            # Check for inline callable
            func = branch_config.get("function")
            if func and callable(func):
                if asyncio.iscoroutinefunction(func):
                    return await func(input_data, context)
                else:
                    return func(input_data, context)
            
            # No execution - just pass through
            return input_data
    
    def _collect_results(
        self,
        results: Dict[str, Any],
        errors: List[str],
    ) -> Any:
        """Collect and format results based on mode."""
        if self._collect_mode == "list":
            return list(results.values())
        
        elif self._collect_mode == "merge":
            merged = {}
            for result in results.values():
                if isinstance(result, dict):
                    merged.update(result)
            return merged
        
        else:  # dict (default)
            return {
                "results": results,
                "errors": errors,
                "success_count": len(results),
                "error_count": len(errors),
            }
    
    def add_child_node(self, node_id: str, node: INode) -> None:
        """Add a child node."""
        self._child_nodes[node_id] = node
    
    def remove_child_node(self, node_id: str) -> None:
        """Remove a child node."""
        self._child_nodes.pop(node_id, None)
    
    async def validate(self, context: IWorkflowContext) -> List[str]:
        """Validate parallel node configuration."""
        errors = await super().validate(context)
        
        branches = self._config.get("branches", [])
        if not branches:
            errors.append(
                f"Parallel node {self._name}: Must have at least one branch"
            )
        
        # Validate branch configurations
        for i, branch in enumerate(branches):
            if "node_id" not in branch and "function" not in branch:
                errors.append(
                    f"Parallel node {self._name}: Branch {i} must have node_id or function"
                )
        
        return errors

