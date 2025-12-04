"""
Workflow Exceptions Module.

This module defines all custom exceptions used throughout the workflows subsystem.
"""

from typing import Any, Dict, Optional, List


class WorkflowError(Exception):
    """Base exception for all workflow-related errors."""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
    
    def __str__(self) -> str:
        parts = [self.message]
        if self.error_code:
            parts.insert(0, f"[{self.error_code}]")
        return " ".join(parts)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "details": self.details,
        }


class WorkflowNotFoundError(WorkflowError):
    """Raised when a workflow cannot be found."""
    
    def __init__(self, workflow_id: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            f"Workflow not found: {workflow_id}",
            error_code="WORKFLOW_NOT_FOUND",
            details=details,
        )
        self.workflow_id = workflow_id


class WorkflowBuildError(WorkflowError):
    """Raised when workflow construction fails."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message,
            error_code="WORKFLOW_BUILD_ERROR",
            details=details,
        )


class WorkflowValidationError(WorkflowError):
    """Raised when workflow validation fails."""
    
    def __init__(
        self,
        message: str,
        validation_errors: Optional[List[str]] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        all_details = details or {}
        all_details["validation_errors"] = validation_errors or []
        super().__init__(
            message,
            error_code="WORKFLOW_VALIDATION_ERROR",
            details=all_details,
        )
        self.validation_errors = validation_errors or []


class WorkflowExecutionError(WorkflowError):
    """Raised when workflow execution fails."""
    
    def __init__(
        self,
        message: str,
        workflow_id: Optional[str] = None,
        node_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        all_details = details or {}
        if workflow_id:
            all_details["workflow_id"] = workflow_id
        if node_id:
            all_details["node_id"] = node_id
        super().__init__(
            message,
            error_code="WORKFLOW_EXECUTION_ERROR",
            details=all_details,
        )
        self.workflow_id = workflow_id
        self.node_id = node_id


class NodeNotFoundError(WorkflowError):
    """Raised when a node cannot be found in a workflow."""
    
    def __init__(
        self,
        node_id: str,
        workflow_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            f"Node not found: {node_id}",
            error_code="NODE_NOT_FOUND",
            details=details,
        )
        self.node_id = node_id
        self.workflow_id = workflow_id


class NodeExecutionError(WorkflowError):
    """Raised when a node fails to execute."""
    
    def __init__(
        self,
        message: str,
        node_id: str,
        node_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        all_details = details or {}
        all_details["node_id"] = node_id
        if node_type:
            all_details["node_type"] = node_type
        super().__init__(
            message,
            error_code="NODE_EXECUTION_ERROR",
            details=all_details,
        )
        self.node_id = node_id
        self.node_type = node_type


class NodeValidationError(WorkflowError):
    """Raised when node validation fails."""
    
    def __init__(
        self,
        message: str,
        node_id: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        all_details = details or {}
        all_details["node_id"] = node_id
        super().__init__(
            message,
            error_code="NODE_VALIDATION_ERROR",
            details=all_details,
        )
        self.node_id = node_id


class EdgeNotFoundError(WorkflowError):
    """Raised when an edge cannot be found."""
    
    def __init__(
        self,
        edge_id: Optional[str] = None,
        source_id: Optional[str] = None,
        target_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        if edge_id:
            message = f"Edge not found: {edge_id}"
        else:
            message = f"Edge not found: {source_id} -> {target_id}"
        super().__init__(
            message,
            error_code="EDGE_NOT_FOUND",
            details=details,
        )
        self.edge_id = edge_id
        self.source_id = source_id
        self.target_id = target_id


class EdgeValidationError(WorkflowError):
    """Raised when edge validation fails."""
    
    def __init__(
        self,
        message: str,
        edge_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        all_details = details or {}
        if edge_id:
            all_details["edge_id"] = edge_id
        super().__init__(
            message,
            error_code="EDGE_VALIDATION_ERROR",
            details=all_details,
        )
        self.edge_id = edge_id


class RoutingError(WorkflowError):
    """Raised when routing between nodes fails."""
    
    def __init__(
        self,
        message: str,
        source_node_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        all_details = details or {}
        if source_node_id:
            all_details["source_node_id"] = source_node_id
        super().__init__(
            message,
            error_code="ROUTING_ERROR",
            details=all_details,
        )
        self.source_node_id = source_node_id


class ConditionEvaluationError(WorkflowError):
    """Raised when evaluating an edge condition fails."""
    
    def __init__(
        self,
        message: str,
        condition: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        all_details = details or {}
        if condition:
            all_details["condition"] = condition
        super().__init__(
            message,
            error_code="CONDITION_EVALUATION_ERROR",
            details=all_details,
        )
        self.condition = condition


class TransformError(WorkflowError):
    """Raised when data transformation between nodes fails."""
    
    def __init__(
        self,
        message: str,
        transform_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        all_details = details or {}
        if transform_type:
            all_details["transform_type"] = transform_type
        super().__init__(
            message,
            error_code="TRANSFORM_ERROR",
            details=all_details,
        )
        self.transform_type = transform_type


class WorkflowTimeoutError(WorkflowError):
    """Raised when workflow execution times out."""
    
    def __init__(
        self,
        timeout_seconds: float,
        workflow_id: Optional[str] = None,
        node_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        all_details = details or {}
        all_details["timeout_seconds"] = timeout_seconds
        if workflow_id:
            all_details["workflow_id"] = workflow_id
        if node_id:
            all_details["node_id"] = node_id
        super().__init__(
            f"Execution timed out after {timeout_seconds} seconds",
            error_code="WORKFLOW_TIMEOUT",
            details=all_details,
        )
        self.timeout_seconds = timeout_seconds
        self.workflow_id = workflow_id
        self.node_id = node_id


class MaxIterationsError(WorkflowError):
    """Raised when maximum iterations are exceeded."""
    
    def __init__(
        self,
        max_iterations: int,
        workflow_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        all_details = details or {}
        all_details["max_iterations"] = max_iterations
        if workflow_id:
            all_details["workflow_id"] = workflow_id
        super().__init__(
            f"Maximum iterations ({max_iterations}) exceeded",
            error_code="MAX_ITERATIONS_EXCEEDED",
            details=all_details,
        )
        self.max_iterations = max_iterations
        self.workflow_id = workflow_id


class CycleDetectedError(WorkflowError):
    """Raised when an infinite cycle is detected in the workflow."""
    
    def __init__(
        self,
        cycle_path: List[str],
        details: Optional[Dict[str, Any]] = None,
    ):
        all_details = details or {}
        all_details["cycle_path"] = cycle_path
        super().__init__(
            f"Cycle detected in workflow: {' -> '.join(cycle_path)}",
            error_code="CYCLE_DETECTED",
            details=all_details,
        )
        self.cycle_path = cycle_path


class ParallelExecutionError(WorkflowError):
    """Raised when parallel node execution fails."""
    
    def __init__(
        self,
        message: str,
        failed_nodes: Optional[List[str]] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        all_details = details or {}
        if failed_nodes:
            all_details["failed_nodes"] = failed_nodes
        super().__init__(
            message,
            error_code="PARALLEL_EXECUTION_ERROR",
            details=all_details,
        )
        self.failed_nodes = failed_nodes or []


class WebhookError(WorkflowError):
    """Raised when a webhook call fails."""
    
    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        all_details = details or {}
        if url:
            all_details["url"] = url
        if status_code:
            all_details["status_code"] = status_code
        super().__init__(
            message,
            error_code="WEBHOOK_ERROR",
            details=all_details,
        )
        self.url = url
        self.status_code = status_code


class SubworkflowError(WorkflowError):
    """Raised when a subworkflow execution fails."""
    
    def __init__(
        self,
        message: str,
        subworkflow_id: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        all_details = details or {}
        all_details["subworkflow_id"] = subworkflow_id
        super().__init__(
            message,
            error_code="SUBWORKFLOW_ERROR",
            details=all_details,
        )
        self.subworkflow_id = subworkflow_id


class WorkflowStateError(WorkflowError):
    """Raised when workflow is in invalid state for an operation."""
    
    def __init__(
        self,
        message: str,
        current_state: str,
        expected_states: Optional[List[str]] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        all_details = details or {}
        all_details["current_state"] = current_state
        if expected_states:
            all_details["expected_states"] = expected_states
        super().__init__(
            message,
            error_code="WORKFLOW_STATE_ERROR",
            details=all_details,
        )
        self.current_state = current_state
        self.expected_states = expected_states or []

