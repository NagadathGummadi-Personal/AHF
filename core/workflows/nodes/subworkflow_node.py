"""
Subworkflow Node Implementation Module.

This module provides a node that executes another workflow as a subworkflow.
"""

import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from ..interfaces import IWorkflowContext, IWorkflow, IWorkflowExecutor
from ..enum import NodeType
from ..spec import NodeSpec, WorkflowContext
from ..exceptions import NodeExecutionError, SubworkflowError
from .base_node import BaseNode

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class SubworkflowNode(BaseNode):
    """
    A node that executes another workflow as a subworkflow.
    
    Configuration:
        workflow_id: ID of workflow to execute
        workflow: Direct workflow instance
        input_mapping: Map current context to subworkflow input
        output_mapping: Map subworkflow output to current context
        inherit_context: Whether to pass current context variables (default: True)
    """
    
    def __init__(
        self,
        spec: NodeSpec,
        workflow: Optional[IWorkflow] = None,
        workflow_executor: Optional[IWorkflowExecutor] = None,
        workflow_registry: Optional[Dict[str, IWorkflow]] = None,
    ):
        """
        Initialize the subworkflow node.
        
        Args:
            spec: Node specification.
            workflow: Optional direct workflow instance.
            workflow_executor: Executor for running the subworkflow.
            workflow_registry: Registry for looking up workflows by ID.
        """
        if spec.node_type != NodeType.SUBWORKFLOW:
            spec.node_type = NodeType.SUBWORKFLOW
        
        super().__init__(spec)
        
        self._workflow = workflow
        self._workflow_executor = workflow_executor
        self._workflow_registry = workflow_registry or {}
        self._inherit_context = self._config.get("inherit_context", True)
    
    async def execute(
        self,
        input_data: Any,
        context: IWorkflowContext,
    ) -> Any:
        """
        Execute the subworkflow.
        
        Args:
            input_data: Input from previous node.
            context: Workflow execution context.
            
        Returns:
            Subworkflow output.
        """
        logger.info(f"Executing subworkflow node: {self._name}")
        
        # Get the workflow to execute
        workflow = self._get_workflow()
        
        if not workflow:
            raise NodeExecutionError(
                f"No workflow available for subworkflow node {self._name}",
                node_id=self._id,
                node_type=self._node_type.value,
            )
        
        # Resolve input
        resolved_input = self._resolve_input(context, input_data)
        
        # Create subworkflow context
        sub_context = self._create_subworkflow_context(context, resolved_input)
        
        try:
            if self._workflow_executor:
                # Use provided executor
                output, final_context = await self._workflow_executor.execute(
                    workflow,
                    resolved_input,
                    sub_context,
                )
            else:
                # Execute workflow directly if it has a run method
                if hasattr(workflow, 'execute'):
                    output, final_context = await workflow.execute(
                        resolved_input,
                        sub_context,
                    )
                else:
                    raise NodeExecutionError(
                        f"No executor available for subworkflow {workflow.id}",
                        node_id=self._id,
                        node_type=self._node_type.value,
                    )
            
            # Apply output mapping
            result = self._map_output(output, final_context, context)
            
            logger.debug(f"Subworkflow node {self._name} completed successfully")
            return result
            
        except NodeExecutionError:
            raise
        except Exception as e:
            logger.error(f"Subworkflow node {self._name} failed: {e}")
            raise SubworkflowError(
                f"Subworkflow execution failed: {e}",
                subworkflow_id=workflow.id if workflow else "unknown",
                details={"error": str(e)},
            ) from e
    
    def _get_workflow(self) -> Optional[IWorkflow]:
        """Get the workflow to execute."""
        if self._workflow:
            return self._workflow
        
        workflow_id = self._config.get("workflow_id")
        if workflow_id and workflow_id in self._workflow_registry:
            return self._workflow_registry[workflow_id]
        
        return None
    
    def _create_subworkflow_context(
        self,
        parent_context: IWorkflowContext,
        input_data: Any,
    ) -> WorkflowContext:
        """Create context for the subworkflow."""
        workflow = self._get_workflow()
        workflow_id = workflow.id if workflow else "subworkflow"
        
        sub_context = WorkflowContext(
            workflow_id=workflow_id,
        )
        
        # Inherit parent context variables if configured
        if self._inherit_context:
            for key, value in parent_context.variables.items():
                if not key.startswith("__"):  # Skip internal variables
                    sub_context.set(key, value)
        
        # Store input
        sub_context.input_data = input_data
        
        # Add reference to parent
        sub_context.metadata["parent_workflow_id"] = parent_context.workflow_id
        sub_context.metadata["parent_execution_id"] = parent_context.execution_id
        sub_context.metadata["parent_node_id"] = self._id
        
        return sub_context
    
    def _map_output(
        self,
        output: Any,
        sub_context: IWorkflowContext,
        parent_context: IWorkflowContext,
    ) -> Any:
        """Map subworkflow output to parent context."""
        output_mappings = self._config.get("output_mapping", {})
        
        if output_mappings:
            for parent_key, sub_key in output_mappings.items():
                if sub_key.startswith("$output"):
                    # Extract from output
                    value = output
                    path_parts = sub_key.split(".")[1:]
                    for part in path_parts:
                        if isinstance(value, dict):
                            value = value.get(part)
                        elif hasattr(value, part):
                            value = getattr(value, part)
                        else:
                            value = None
                            break
                elif sub_key.startswith("$ctx"):
                    # Extract from subworkflow context
                    var_name = sub_key.split(".")[1] if "." in sub_key else None
                    value = sub_context.get(var_name) if var_name else sub_context.variables
                else:
                    value = sub_key
                
                parent_context.set(parent_key, value)
        
        return output
    
    async def validate(self, context: IWorkflowContext) -> List[str]:
        """Validate subworkflow node configuration."""
        errors = await super().validate(context)
        
        if not self._workflow and not self._config.get("workflow_id"):
            errors.append(
                f"Subworkflow node {self._name}: Must specify workflow or workflow_id"
            )
        
        return errors
    
    def set_workflow(self, workflow: IWorkflow) -> None:
        """Set the workflow instance directly."""
        self._workflow = workflow
    
    def set_workflow_executor(self, executor: IWorkflowExecutor) -> None:
        """Set the workflow executor."""
        self._workflow_executor = executor
    
    def register_workflow(self, workflow_id: str, workflow: IWorkflow) -> None:
        """Register a workflow in the local registry."""
        self._workflow_registry[workflow_id] = workflow



