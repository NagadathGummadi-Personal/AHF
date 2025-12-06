"""
Workflow Tool Module.

This module provides a wrapper that exposes a workflow as a tool
that can be used by agents.
"""

import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from pydantic import BaseModel, Field

from core.tools.spec.tool_types import FunctionToolSpec
from core.tools.spec.tool_parameters import ToolParameter, StringParameter, ObjectParameter
from core.tools.enum import ToolType, ToolReturnType, ToolReturnTarget

if TYPE_CHECKING:
    from ..interfaces import IWorkflow, IWorkflowContext
    from ..runtimes.workflow_engine import WorkflowEngine

logger = logging.getLogger(__name__)


class WorkflowToolSpec(FunctionToolSpec):
    """
    Tool specification for workflow-based tools.
    
    Wraps a workflow as a tool that can be called by agents.
    
    Attributes:
        workflow_id: ID of the workflow to execute
        workflow: Direct workflow instance (alternative to workflow_id)
        input_mapping: Map tool parameters to workflow input
        output_mapping: Map workflow output to tool result
        async_execution: If True, return immediately with execution ID
    """
    
    tool_type: ToolType = Field(default=ToolType.FUNCTION)
    
    # Workflow reference
    workflow_id: Optional[str] = None
    workflow: Optional[Any] = None  # IWorkflow instance
    
    # Mappings
    input_mapping: Dict[str, str] = Field(
        default_factory=dict,
        description="Map tool parameters to workflow input fields"
    )
    output_mapping: Dict[str, str] = Field(
        default_factory=dict,
        description="Map workflow output fields to tool result"
    )
    
    # Execution options
    async_execution: bool = Field(
        default=False,
        description="If True, execute async and return execution ID"
    )
    timeout_s: int = Field(
        default=300,
        description="Workflow execution timeout in seconds"
    )


class WorkflowTool:
    """
    Wrapper that makes a workflow usable as an agent tool.
    
    This allows agents to invoke complex workflows as simple tool calls,
    enabling hierarchical and compositional agent architectures.
    
    Example:
        # Create a booking workflow
        booking_workflow = WorkflowBuilder()...build()
        
        # Wrap it as a tool
        booking_tool = WorkflowTool(
            workflow=booking_workflow,
            tool_name="book_service",
            description="Book a service for a customer",
            parameters=[
                StringParameter(name="service_name", required=True),
                StringParameter(name="guest_name", required=True),
            ]
        )
        
        # Use in an agent
        agent = AgentBuilder()
            .add_tool(booking_tool)
            .build()
    """
    
    def __init__(
        self,
        workflow: Optional["IWorkflow"] = None,
        workflow_id: Optional[str] = None,
        workflow_registry: Optional[Any] = None,
        workflow_engine: Optional["WorkflowEngine"] = None,
        tool_name: Optional[str] = None,
        description: Optional[str] = None,
        parameters: Optional[List[ToolParameter]] = None,
        input_mapping: Optional[Dict[str, str]] = None,
        output_mapping: Optional[Dict[str, str]] = None,
        async_execution: bool = False,
        timeout_s: int = 300,
    ):
        """
        Initialize the workflow tool.
        
        Args:
            workflow: Direct workflow instance.
            workflow_id: ID of workflow to load from registry.
            workflow_registry: Registry to load workflow from.
            workflow_engine: Engine to execute workflow.
            tool_name: Name for the tool.
            description: Tool description.
            parameters: Tool parameters (inferred from workflow if not provided).
            input_mapping: Map parameter names to workflow input.
            output_mapping: Map workflow output to result.
            async_execution: Whether to execute asynchronously.
            timeout_s: Execution timeout.
        """
        self._workflow = workflow
        self._workflow_id = workflow_id
        self._workflow_registry = workflow_registry
        self._workflow_engine = workflow_engine
        self._input_mapping = input_mapping or {}
        self._output_mapping = output_mapping or {}
        self._async_execution = async_execution
        self._timeout_s = timeout_s
        
        # Build tool spec
        self._spec = self._build_spec(
            tool_name=tool_name,
            description=description,
            parameters=parameters,
        )
    
    def _build_spec(
        self,
        tool_name: Optional[str],
        description: Optional[str],
        parameters: Optional[List[ToolParameter]],
    ) -> WorkflowToolSpec:
        """Build the tool specification."""
        workflow = self._get_workflow()
        
        # Infer from workflow if not provided
        if not tool_name and workflow:
            tool_name = f"workflow_{workflow.name}".replace(" ", "_").lower()
        tool_name = tool_name or "workflow_tool"
        
        if not description and workflow:
            description = workflow.description or f"Execute workflow: {workflow.name}"
        description = description or "Execute a workflow"
        
        # Build parameters from workflow input spec if not provided
        if not parameters and workflow:
            parameters = self._infer_parameters(workflow)
        parameters = parameters or []
        
        return WorkflowToolSpec(
            id=f"workflow-tool-{self._workflow_id or 'inline'}",
            tool_name=tool_name,
            description=description,
            parameters=parameters,
            workflow_id=self._workflow_id,
            workflow=self._workflow,
            input_mapping=self._input_mapping,
            output_mapping=self._output_mapping,
            async_execution=self._async_execution,
            timeout_s=self._timeout_s,
            return_type=ToolReturnType.JSON,
            return_target=ToolReturnTarget.AGENT,
        )
    
    def _infer_parameters(self, workflow: "IWorkflow") -> List[ToolParameter]:
        """Infer tool parameters from workflow input spec."""
        parameters = []
        
        # Get from workflow spec if available
        if hasattr(workflow, 'spec') and workflow.spec:
            spec = workflow.spec
            
            # Try input_spec first
            if hasattr(spec, 'input_spec') and spec.input_spec:
                for field in spec.input_spec.fields:
                    param = StringParameter(
                        name=field.name,
                        description=field.description or f"Input: {field.name}",
                        required=field.required,
                    )
                    parameters.append(param)
            
            # Fall back to input_variables
            elif hasattr(spec, 'input_variables'):
                for var in spec.input_variables:
                    param = StringParameter(
                        name=var.name,
                        description=var.description or f"Input: {var.name}",
                        required=var.required,
                    )
                    parameters.append(param)
        
        return parameters
    
    def _get_workflow(self) -> Optional["IWorkflow"]:
        """Get the workflow instance."""
        if self._workflow:
            return self._workflow
        
        if self._workflow_id and self._workflow_registry:
            try:
                return self._workflow_registry.get(self._workflow_id)
            except Exception as e:
                logger.warning(f"Failed to get workflow {self._workflow_id}: {e}")
        
        return None
    
    @property
    def spec(self) -> WorkflowToolSpec:
        """Get the tool specification."""
        return self._spec
    
    @property
    def name(self) -> str:
        """Get the tool name."""
        return self._spec.tool_name
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the workflow with the given parameters.
        
        Args:
            **kwargs: Tool parameters mapped to workflow input.
            
        Returns:
            Workflow output mapped through output_mapping.
        """
        logger.info(f"Executing workflow tool: {self.name}")
        
        # Get workflow
        workflow = self._get_workflow()
        if not workflow:
            return {
                "success": False,
                "error": f"Workflow not found: {self._workflow_id}",
            }
        
        # Get or create engine
        engine = self._workflow_engine
        if not engine:
            from ..runtimes.workflow_engine import WorkflowEngine
            engine = WorkflowEngine()
        
        # Map input
        workflow_input = self._map_input(kwargs)
        
        try:
            # Execute workflow
            output, context = await engine.execute(
                workflow,
                workflow_input,
                timeout_seconds=self._timeout_s,
            )
            
            # Map output
            result = self._map_output(output, context)
            result["success"] = True
            
            logger.info(f"Workflow tool {self.name} completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Workflow tool {self.name} failed: {e}")
            return {
                "success": False,
                "error": str(e),
            }
    
    def _map_input(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Map tool parameters to workflow input."""
        if not self._input_mapping:
            return params
        
        mapped = {}
        for param_name, value in params.items():
            target = self._input_mapping.get(param_name, param_name)
            mapped[target] = value
        
        return mapped
    
    def _map_output(
        self,
        output: Any,
        context: "IWorkflowContext",
    ) -> Dict[str, Any]:
        """Map workflow output to tool result."""
        if not self._output_mapping:
            if isinstance(output, dict):
                return output
            return {"result": output}
        
        result = {}
        for source, target in self._output_mapping.items():
            if source.startswith("$ctx."):
                value = context.get(source[5:])
            elif source.startswith("$output."):
                if isinstance(output, dict):
                    value = output.get(source[8:])
                else:
                    value = output
            else:
                if isinstance(output, dict):
                    value = output.get(source)
                else:
                    value = output
            
            result[target] = value
        
        return result
    
    def __call__(self, **kwargs) -> Any:
        """
        Make the tool callable.
        
        Synchronous wrapper for async execute.
        """
        import asyncio
        return asyncio.get_event_loop().run_until_complete(self.execute(**kwargs))
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "tool_name": self._spec.tool_name,
            "description": self._spec.description,
            "parameters": [p.model_dump() for p in self._spec.parameters],
            "workflow_id": self._workflow_id,
            "input_mapping": self._input_mapping,
            "output_mapping": self._output_mapping,
            "async_execution": self._async_execution,
            "timeout_s": self._timeout_s,
        }


def create_workflow_tool(
    workflow: "IWorkflow",
    tool_name: Optional[str] = None,
    description: Optional[str] = None,
    parameters: Optional[List[ToolParameter]] = None,
    **kwargs
) -> WorkflowTool:
    """
    Convenience function to create a workflow tool.
    
    Args:
        workflow: The workflow to wrap.
        tool_name: Optional tool name.
        description: Optional description.
        parameters: Optional parameter list.
        **kwargs: Additional WorkflowTool options.
        
    Returns:
        Configured WorkflowTool instance.
    """
    return WorkflowTool(
        workflow=workflow,
        tool_name=tool_name,
        description=description,
        parameters=parameters,
        **kwargs
    )


