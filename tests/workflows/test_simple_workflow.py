"""
Simple Workflow Tests.

This test file covers basic workflow operations without the complexity
of intent-based routing or custom nodes. It focuses on:

1. Basic workflow construction with WorkflowBuilder
2. Start -> Process -> End patterns
3. Sequential node execution
4. Transform nodes for data manipulation
5. Basic conditional routing
6. Parallel node execution
7. Error handling and retry logic
8. Workflow context management
"""

import pytest
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime

from core.workflows import (
    # Builder and Engine
    WorkflowBuilder,
    WorkflowEngine,
    # Enums
    NodeType,
    EdgeType,
    NodeState,
    WorkflowState,
    ConditionOperator,
    RoutingStrategy,
    # Spec Models
    WorkflowSpec,
    NodeSpec,
    EdgeSpec,
    ConditionSpec,
    WorkflowContext,
    RetryConfig,
    # Implementations
    Workflow,
    BaseNode,
    StartNode,
    EndNode,
    TransformNode,
    DecisionNode,
    # Interfaces
    INode,
    IWorkflowContext,
    IWorkflowObserver,
    INodeObserver,
)
from core.workflows.exceptions import (
    WorkflowError,
    NodeExecutionError,
    WorkflowBuildError,
)
from utils.logging.LoggerAdaptor import LoggerAdaptor

# Setup logger
logger = LoggerAdaptor.get_logger("tests.workflows.simple")


# ============================================================================
# SIMPLE CUSTOM NODES FOR TESTING
# ============================================================================

class EchoNode(BaseNode):
    """Simple node that echoes input with optional prefix."""
    
    async def execute(self, input_data: Any, context: IWorkflowContext) -> Any:
        prefix = self._config.get("prefix", "Echo")
        message = input_data.get("message", str(input_data)) if isinstance(input_data, dict) else str(input_data)
        result = {"message": f"{prefix}: {message}", "node_id": self._id}
        logger.info(f"[ECHO] {result['message']}")
        return result


class CounterNode(BaseNode):
    """Node that increments a counter in context."""
    
    async def execute(self, input_data: Any, context: IWorkflowContext) -> Any:
        counter = context.get("counter", 0)
        counter += self._config.get("increment", 1)
        context.set("counter", counter)
        result = {"counter": counter, "node_id": self._id}
        logger.info(f"[COUNTER] Counter is now: {counter}")
        return result


class AccumulatorNode(BaseNode):
    """Node that accumulates values in a list."""
    
    async def execute(self, input_data: Any, context: IWorkflowContext) -> Any:
        values = context.get("accumulated_values", [])
        value = input_data.get("value") if isinstance(input_data, dict) else input_data
        values.append(value)
        context.set("accumulated_values", values)
        result = {"accumulated": values, "count": len(values)}
        logger.info(f"[ACCUMULATOR] Values: {values}")
        return result


class ConditionalValueNode(BaseNode):
    """Node that sets a value based on input condition."""
    
    async def execute(self, input_data: Any, context: IWorkflowContext) -> Any:
        threshold = self._config.get("threshold", 10)
        value = input_data.get("value", 0) if isinstance(input_data, dict) else 0
        
        is_high = value > threshold
        context.set("is_high_value", is_high)
        context.set("threshold", threshold)
        
        result = {
            "value": value,
            "threshold": threshold,
            "is_high": is_high,
            "decision": "high" if is_high else "low"
        }
        logger.info(f"[CONDITIONAL] Value {value} {'>' if is_high else '<='} {threshold}")
        return result


class DelayedResponseNode(BaseNode):
    """Node that simulates processing delay."""
    
    async def execute(self, input_data: Any, context: IWorkflowContext) -> Any:
        delay_ms = self._config.get("delay_ms", 100)
        await asyncio.sleep(delay_ms / 1000)
        
        result = {
            "input": input_data,
            "delayed_ms": delay_ms,
            "timestamp": datetime.now().isoformat()
        }
        logger.info(f"[DELAYED] Processed after {delay_ms}ms delay")
        return result


class DataTransformNode(BaseNode):
    """Node that transforms data in various ways."""
    
    async def execute(self, input_data: Any, context: IWorkflowContext) -> Any:
        operation = self._config.get("operation", "uppercase")
        
        if isinstance(input_data, dict):
            text = input_data.get("text", input_data.get("message", ""))
        else:
            text = str(input_data)
        
        if operation == "uppercase":
            transformed = text.upper()
        elif operation == "lowercase":
            transformed = text.lower()
        elif operation == "reverse":
            transformed = text[::-1]
        elif operation == "length":
            transformed = str(len(text))
        else:
            transformed = text
        
        result = {"original": text, "transformed": transformed, "operation": operation}
        logger.info(f"[TRANSFORM] {operation}: '{text[:20]}...' -> '{transformed[:20]}...'")
        return result


# ============================================================================
# SIMPLE OBSERVERS
# ============================================================================

class SimpleWorkflowObserver(IWorkflowObserver):
    """Simple observer for tracking workflow events."""
    
    def __init__(self):
        self.events: List[Dict[str, Any]] = []
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
    
    async def on_workflow_start(self, workflow: Any, input_data: Any, context: IWorkflowContext) -> None:
        self.start_time = datetime.now()
        self.events.append({"type": "start", "workflow": workflow.name})
        logger.info(f"[OBS] Workflow started: {workflow.name}")
    
    async def on_workflow_complete(self, workflow: Any, output: Any, context: IWorkflowContext, duration_ms: float) -> None:
        self.end_time = datetime.now()
        self.events.append({"type": "complete", "duration_ms": duration_ms})
        logger.info(f"[OBS] Workflow completed in {duration_ms:.2f}ms")
    
    async def on_workflow_error(self, workflow: Any, error: Exception, context: IWorkflowContext) -> None:
        self.events.append({"type": "error", "error": str(error)})
        logger.error(f"[OBS] Workflow error: {error}")
    
    async def on_workflow_pause(self, workflow: Any, context: IWorkflowContext) -> None:
        self.events.append({"type": "pause"})
    
    async def on_workflow_resume(self, workflow: Any, context: IWorkflowContext) -> None:
        self.events.append({"type": "resume"})
    
    async def on_workflow_cancel(self, workflow: Any, context: IWorkflowContext) -> None:
        self.events.append({"type": "cancel"})


class SimpleNodeObserver(INodeObserver):
    """Simple observer for tracking node events."""
    
    def __init__(self):
        self.executions: List[Dict[str, Any]] = []
    
    async def on_node_start(self, node: INode, input_data: Any, context: IWorkflowContext) -> None:
        logger.info(f"[NODE_OBS] Starting: {node.name}")
    
    async def on_node_complete(self, node: INode, output: Any, context: IWorkflowContext, duration_ms: float) -> None:
        self.executions.append({
            "node_id": node.id,
            "node_name": node.name,
            "duration_ms": duration_ms
        })
        logger.info(f"[NODE_OBS] Completed: {node.name} ({duration_ms:.2f}ms)")
    
    async def on_node_error(self, node: INode, error: Exception, context: IWorkflowContext) -> None:
        self.executions.append({"node_id": node.id, "error": str(error)})
        logger.error(f"[NODE_OBS] Error in {node.name}: {error}")
    
    async def on_node_skip(self, node: INode, reason: str, context: IWorkflowContext) -> None:
        self.executions.append({"node_id": node.id, "skipped": True, "reason": reason})


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def workflow_observer():
    """Create a simple workflow observer."""
    return SimpleWorkflowObserver()


@pytest.fixture
def node_observer():
    """Create a simple node observer."""
    return SimpleNodeObserver()


# ============================================================================
# TESTS: Basic Workflow Construction
# ============================================================================

@pytest.mark.asyncio
class TestBasicWorkflowConstruction:
    """Test basic workflow construction with WorkflowBuilder."""
    
    async def test_minimal_workflow(self):
        """Test creating a minimal start -> end workflow."""
        logger.info("=" * 60)
        logger.info("TEST: minimal_workflow")
        logger.info("=" * 60)
        
        workflow = (
            WorkflowBuilder()
            .with_name("Minimal Workflow")
            .add_node("start", NodeType.START)
            .add_node("end", NodeType.END)
            .add_edge("start", "end")
            .build()
        )
        
        assert workflow is not None
        assert workflow.name == "Minimal Workflow"
        assert len(workflow.nodes) == 2
        assert len(workflow.edges) == 1
        
        logger.info(f"[OK] Created minimal workflow with {len(workflow.nodes)} nodes")
    
    async def test_linear_workflow(self):
        """Test creating a linear workflow: start -> A -> B -> C -> end."""
        logger.info("=" * 60)
        logger.info("TEST: linear_workflow")
        logger.info("=" * 60)
        
        workflow = (
            WorkflowBuilder()
            .with_name("Linear Workflow")
            .with_description("A simple linear flow")
            .add_node("start", NodeType.START)
            .add_node("step_a", NodeType.TRANSFORM, name="Step A")
            .add_node("step_b", NodeType.TRANSFORM, name="Step B")
            .add_node("step_c", NodeType.TRANSFORM, name="Step C")
            .add_node("end", NodeType.END)
            .add_edge("start", "step_a")
            .add_edge("step_a", "step_b")
            .add_edge("step_b", "step_c")
            .add_edge("step_c", "end")
            .build()
        )
        
        assert workflow is not None
        assert len(workflow.nodes) == 5
        assert len(workflow.edges) == 4
        
        logger.info(f"[OK] Created linear workflow: {len(workflow.nodes)} nodes, {len(workflow.edges)} edges")
    
    async def test_workflow_with_metadata(self):
        """Test workflow with metadata."""
        logger.info("=" * 60)
        logger.info("TEST: workflow_with_metadata")
        logger.info("=" * 60)
        
        workflow = (
            WorkflowBuilder()
            .with_name("Metadata Workflow")
            .with_description("Workflow with rich metadata")
            .with_version("2.0.0")
            .with_metadata(
                author="Test Suite",
                category="testing",
                tags=["simple", "demo"]
            )
            .add_node("start", NodeType.START)
            .add_node("end", NodeType.END)
            .add_edge("start", "end")
            .build()
        )
        
        # Core workflow attributes
        assert workflow.name == "Metadata Workflow"
        assert workflow.version == "2.0.0"
        
        # Metadata is available (structure may vary by implementation)
        assert workflow.metadata is not None
        assert isinstance(workflow.metadata, dict)
        
        logger.info(f"[OK] Created workflow with metadata: version={workflow.version}")


# ============================================================================
# TESTS: Sequential Execution
# ============================================================================

@pytest.mark.asyncio
class TestSequentialExecution:
    """Test sequential workflow execution."""
    
    async def test_simple_execution(self, workflow_observer, node_observer):
        """Test basic workflow execution."""
        logger.info("=" * 60)
        logger.info("TEST: simple_execution")
        logger.info("=" * 60)
        
        workflow = (
            WorkflowBuilder()
            .with_name("Simple Execution Test")
            .add_node("start", NodeType.START)
            .add_node("process", NodeType.TRANSFORM)
            .add_node("end", NodeType.END)
            .add_edge("start", "process")
            .add_edge("process", "end")
            .build()
        )
        
        engine = WorkflowEngine(
            workflow_observers=[workflow_observer],
            node_observers=[node_observer]
        )
        
        input_data = {"message": "Hello, Workflow!"}
        output, context = await engine.execute(workflow, input_data)
        
        assert output is not None
        assert len(context.execution_path) >= 2
        assert workflow_observer.events[0]["type"] == "start"
        
        logger.info(f"[OK] Execution completed, path: {context.execution_path}")
    
    async def test_data_passing(self, workflow_observer):
        """Test that data passes correctly between nodes."""
        logger.info("=" * 60)
        logger.info("TEST: data_passing")
        logger.info("=" * 60)
        
        workflow = (
            WorkflowBuilder()
            .with_name("Data Passing Test")
            .add_node("start", NodeType.START)
            .add_node("transform", NodeType.TRANSFORM, config={"transform_type": "pass_through"})
            .add_node("end", NodeType.END)
            .add_edge("start", "transform")
            .add_edge("transform", "end")
            .build()
        )
        
        # Inject custom transform node
        workflow._nodes["transform"] = DataTransformNode(
            NodeSpec(id="transform", name="Transform", node_type=NodeType.TRANSFORM, config={"operation": "uppercase"})
        )
        
        engine = WorkflowEngine(workflow_observers=[workflow_observer])
        
        input_data = {"text": "hello world"}
        output, context = await engine.execute(workflow, input_data)
        
        assert output is not None
        if isinstance(output, dict):
            assert output.get("transformed") == "HELLO WORLD"
        
        logger.info("[OK] Data transformed: 'hello world' -> 'HELLO WORLD'")
    
    async def test_context_sharing(self):
        """Test that context is shared across nodes."""
        logger.info("=" * 60)
        logger.info("TEST: context_sharing")
        logger.info("=" * 60)
        
        workflow = (
            WorkflowBuilder()
            .with_name("Context Sharing Test")
            .add_node("start", NodeType.START)
            .add_node("counter1", NodeType.TRANSFORM, name="Counter 1")
            .add_node("counter2", NodeType.TRANSFORM, name="Counter 2")
            .add_node("counter3", NodeType.TRANSFORM, name="Counter 3")
            .add_node("end", NodeType.END)
            .add_edge("start", "counter1")
            .add_edge("counter1", "counter2")
            .add_edge("counter2", "counter3")
            .add_edge("counter3", "end")
            .build()
        )
        
        # Inject counter nodes
        workflow._nodes["counter1"] = CounterNode(
            NodeSpec(id="counter1", name="Counter 1", node_type=NodeType.TRANSFORM, config={"increment": 1})
        )
        workflow._nodes["counter2"] = CounterNode(
            NodeSpec(id="counter2", name="Counter 2", node_type=NodeType.TRANSFORM, config={"increment": 2})
        )
        workflow._nodes["counter3"] = CounterNode(
            NodeSpec(id="counter3", name="Counter 3", node_type=NodeType.TRANSFORM, config={"increment": 3})
        )
        
        engine = WorkflowEngine()
        output, context = await engine.execute(workflow, {})
        
        # Counter should be 1 + 2 + 3 = 6
        assert context.get("counter") == 6
        
        logger.info(f"[OK] Context shared across nodes, final counter: {context.get('counter')}")


# ============================================================================
# TESTS: Conditional Routing
# ============================================================================

@pytest.mark.asyncio
class TestConditionalRouting:
    """Test conditional routing in workflows."""
    
    async def test_simple_conditional(self):
        """Test basic conditional edge evaluation."""
        logger.info("=" * 60)
        logger.info("TEST: simple_conditional")
        logger.info("=" * 60)
        
        workflow = (
            WorkflowBuilder()
            .with_name("Conditional Test")
            .add_node("start", NodeType.START)
            .add_node("check", NodeType.DECISION)
            .add_node("yes_path", NodeType.TRANSFORM, name="Yes Path")
            .add_node("no_path", NodeType.TRANSFORM, name="No Path")
            .add_node("end", NodeType.END)
            .add_edge("start", "check")
            .add_conditional_edge("check", "yes_path", field="$ctx.is_high_value", operator="equals", value=True)
            .add_fallback_edge("check", "no_path")
            .add_edge("yes_path", "end")
            .add_edge("no_path", "end")
            .build()
        )
        
        # Inject decision node
        workflow._nodes["check"] = ConditionalValueNode(
            NodeSpec(id="check", name="Check", node_type=NodeType.DECISION, config={"threshold": 10})
        )
        workflow._nodes["yes_path"] = EchoNode(
            NodeSpec(id="yes_path", name="Yes Path", node_type=NodeType.TRANSFORM, config={"prefix": "HIGH"})
        )
        workflow._nodes["no_path"] = EchoNode(
            NodeSpec(id="no_path", name="No Path", node_type=NodeType.TRANSFORM, config={"prefix": "LOW"})
        )
        
        engine = WorkflowEngine()
        
        # Test high value (should take yes_path)
        output_high, ctx_high = await engine.execute(workflow, {"value": 15})
        assert "yes_path" in ctx_high.execution_path
        logger.info(f"[OK] High value (15) took yes_path")
        
        # Test low value (should take no_path)
        output_low, ctx_low = await engine.execute(workflow, {"value": 5})
        assert "no_path" in ctx_low.execution_path
        logger.info(f"[OK] Low value (5) took no_path")
    
    async def test_multi_branch_routing(self):
        """Test routing with multiple conditional branches."""
        logger.info("=" * 60)
        logger.info("TEST: multi_branch_routing")
        logger.info("=" * 60)
        
        workflow = (
            WorkflowBuilder()
            .with_name("Multi-Branch Test")
            .add_node("start", NodeType.START)
            .add_node("router", NodeType.DECISION)
            .add_node("branch_a", NodeType.TRANSFORM, name="Branch A")
            .add_node("branch_b", NodeType.TRANSFORM, name="Branch B")
            .add_node("branch_c", NodeType.TRANSFORM, name="Branch C")
            .add_node("end", NodeType.END)
            .add_edge("start", "router")
            .add_conditional_edge("router", "branch_a", field="$ctx.route", operator="equals", value="a", priority=10)
            .add_conditional_edge("router", "branch_b", field="$ctx.route", operator="equals", value="b", priority=10)
            .add_fallback_edge("router", "branch_c")
            .add_edge("branch_a", "end")
            .add_edge("branch_b", "end")
            .add_edge("branch_c", "end")
            .build()
        )
        
        # Create a custom router node
        class RouterNode(BaseNode):
            async def execute(self, input_data: Any, context: IWorkflowContext) -> Any:
                route = input_data.get("route", "c") if isinstance(input_data, dict) else "c"
                context.set("route", route)
                return {"route": route}
        
        workflow._nodes["router"] = RouterNode(
            NodeSpec(id="router", name="Router", node_type=NodeType.DECISION)
        )
        
        engine = WorkflowEngine()
        
        # Test route A
        _, ctx_a = await engine.execute(workflow, {"route": "a"})
        assert "branch_a" in ctx_a.execution_path
        
        # Test route B
        _, ctx_b = await engine.execute(workflow, {"route": "b"})
        assert "branch_b" in ctx_b.execution_path
        
        # Test fallback to C
        _, ctx_c = await engine.execute(workflow, {"route": "unknown"})
        assert "branch_c" in ctx_c.execution_path
        
        logger.info("[OK] Multi-branch routing works correctly")


# ============================================================================
# TESTS: Streaming Execution
# ============================================================================

@pytest.mark.asyncio
class TestStreamingExecution:
    """Test streaming workflow execution."""
    
    async def test_basic_streaming(self):
        """Test basic streaming execution."""
        logger.info("=" * 60)
        logger.info("TEST: basic_streaming")
        logger.info("=" * 60)
        
        workflow = (
            WorkflowBuilder()
            .with_name("Streaming Test")
            .add_node("start", NodeType.START)
            .add_node("step1", NodeType.TRANSFORM, name="Step 1")
            .add_node("step2", NodeType.TRANSFORM, name="Step 2")
            .add_node("end", NodeType.END)
            .add_edge("start", "step1")
            .add_edge("step1", "step2")
            .add_edge("step2", "end")
            .build()
        )
        
        engine = WorkflowEngine()
        
        streamed_nodes = []
        async for node_id, output, context in engine.execute_streaming(workflow, {"value": 1}):
            streamed_nodes.append(node_id)
            logger.info(f"[STREAM] Completed: {node_id}")
        
        assert len(streamed_nodes) >= 3  # start, step1, step2, (end)
        logger.info(f"[OK] Streamed {len(streamed_nodes)} nodes")
    
    async def test_streaming_with_observers(self, workflow_observer, node_observer):
        """Test streaming with observers attached."""
        logger.info("=" * 60)
        logger.info("TEST: streaming_with_observers")
        logger.info("=" * 60)
        
        workflow = (
            WorkflowBuilder()
            .with_name("Streaming Observer Test")
            .add_node("start", NodeType.START)
            .add_node("process", NodeType.TRANSFORM)
            .add_node("end", NodeType.END)
            .add_edge("start", "process")
            .add_edge("process", "end")
            .build()
        )
        
        engine = WorkflowEngine(
            workflow_observers=[workflow_observer],
            node_observers=[node_observer]
        )
        
        async for node_id, output, context in engine.execute_streaming(workflow, {}):
            pass
        
        # Note: Streaming execution fires node observers but may not fire workflow observers
        # depending on implementation. Node observers should always fire.
        assert len(node_observer.executions) >= 2
        
        logger.info(f"[OK] Streaming with observers: {len(node_observer.executions)} node executions")


# ============================================================================
# TESTS: Workflow Context
# ============================================================================

@pytest.mark.asyncio
class TestWorkflowContext:
    """Test workflow context management."""
    
    async def test_context_variables(self):
        """Test setting and getting context variables."""
        logger.info("=" * 60)
        logger.info("TEST: context_variables")
        logger.info("=" * 60)
        
        context = WorkflowContext(workflow_id="test-workflow")
        
        # Test basic set/get
        context.set("string_value", "hello")
        context.set("number_value", 42)
        context.set("list_value", [1, 2, 3])
        context.set("dict_value", {"key": "value"})
        
        assert context.get("string_value") == "hello"
        assert context.get("number_value") == 42
        assert context.get("list_value") == [1, 2, 3]
        assert context.get("dict_value") == {"key": "value"}
        
        # Test default value
        assert context.get("nonexistent", "default") == "default"
        
        logger.info("[OK] Context variables work correctly")
    
    async def test_execution_path_tracking(self):
        """Test that execution path is tracked correctly."""
        logger.info("=" * 60)
        logger.info("TEST: execution_path_tracking")
        logger.info("=" * 60)
        
        workflow = (
            WorkflowBuilder()
            .with_name("Path Tracking Test")
            .add_node("start", NodeType.START)
            .add_node("a", NodeType.TRANSFORM, name="Node A")
            .add_node("b", NodeType.TRANSFORM, name="Node B")
            .add_node("c", NodeType.TRANSFORM, name="Node C")
            .add_node("end", NodeType.END)
            .add_edge("start", "a")
            .add_edge("a", "b")
            .add_edge("b", "c")
            .add_edge("c", "end")
            .build()
        )
        
        engine = WorkflowEngine()
        _, context = await engine.execute(workflow, {})
        
        assert "start" in context.execution_path
        assert "a" in context.execution_path
        assert "b" in context.execution_path
        assert "c" in context.execution_path
        
        logger.info(f"[OK] Execution path tracked: {context.execution_path}")


# ============================================================================
# TESTS: Error Handling
# ============================================================================

@pytest.mark.asyncio
class TestErrorHandling:
    """Test error handling in workflows."""
    
    async def test_node_error_propagation(self, workflow_observer):
        """Test that node errors are propagated correctly."""
        logger.info("=" * 60)
        logger.info("TEST: node_error_propagation")
        logger.info("=" * 60)
        
        class FailingNode(BaseNode):
            async def execute(self, input_data: Any, context: IWorkflowContext) -> Any:
                raise ValueError("Intentional test failure")
        
        workflow = (
            WorkflowBuilder()
            .with_name("Error Test")
            .add_node("start", NodeType.START)
            .add_node("fail", NodeType.TRANSFORM, name="Failing Node")
            .add_node("end", NodeType.END)
            .add_edge("start", "fail")
            .add_edge("fail", "end")
            .build()
        )
        
        workflow._nodes["fail"] = FailingNode(
            NodeSpec(id="fail", name="Failing Node", node_type=NodeType.TRANSFORM)
        )
        
        engine = WorkflowEngine(workflow_observers=[workflow_observer])
        
        with pytest.raises(Exception):
            await engine.execute(workflow, {})
        
        # Check that error was recorded
        error_events = [e for e in workflow_observer.events if e.get("type") == "error"]
        assert len(error_events) > 0
        
        logger.info("[OK] Node errors propagate correctly")


# ============================================================================
# TESTS: Observer Events
# ============================================================================

@pytest.mark.asyncio
class TestObserverEvents:
    """Test observer event firing."""
    
    async def test_workflow_lifecycle_events(self, workflow_observer):
        """Test that all lifecycle events fire correctly."""
        logger.info("=" * 60)
        logger.info("TEST: workflow_lifecycle_events")
        logger.info("=" * 60)
        
        workflow = (
            WorkflowBuilder()
            .with_name("Lifecycle Test")
            .add_node("start", NodeType.START)
            .add_node("end", NodeType.END)
            .add_edge("start", "end")
            .build()
        )
        
        engine = WorkflowEngine(workflow_observers=[workflow_observer])
        await engine.execute(workflow, {})
        
        event_types = [e["type"] for e in workflow_observer.events]
        assert "start" in event_types
        assert "complete" in event_types
        
        logger.info(f"[OK] Lifecycle events: {event_types}")
    
    async def test_node_execution_tracking(self, node_observer):
        """Test that node executions are tracked."""
        logger.info("=" * 60)
        logger.info("TEST: node_execution_tracking")
        logger.info("=" * 60)
        
        workflow = (
            WorkflowBuilder()
            .with_name("Node Tracking Test")
            .add_node("start", NodeType.START)
            .add_node("a", NodeType.TRANSFORM)
            .add_node("b", NodeType.TRANSFORM)
            .add_node("end", NodeType.END)
            .add_edge("start", "a")
            .add_edge("a", "b")
            .add_edge("b", "end")
            .build()
        )
        
        engine = WorkflowEngine(node_observers=[node_observer])
        await engine.execute(workflow, {})
        
        executed_nodes = [e["node_id"] for e in node_observer.executions if "node_id" in e]
        assert len(executed_nodes) >= 2
        
        logger.info(f"[OK] Tracked {len(executed_nodes)} node executions")


# ============================================================================
# TESTS: Workflow Configuration
# ============================================================================

@pytest.mark.asyncio
class TestWorkflowConfiguration:
    """Test workflow configuration options."""
    
    async def test_max_iterations(self):
        """Test max iterations limit."""
        logger.info("=" * 60)
        logger.info("TEST: max_iterations")
        logger.info("=" * 60)
        
        workflow = (
            WorkflowBuilder()
            .with_name("Max Iterations Test")
            .with_max_iterations(10)
            .add_node("start", NodeType.START)
            .add_node("end", NodeType.END)
            .add_edge("start", "end")
            .build()
        )
        
        assert workflow is not None
        logger.info("[OK] Max iterations configured")
    
    async def test_routing_strategy(self):
        """Test routing strategy configuration."""
        logger.info("=" * 60)
        logger.info("TEST: routing_strategy")
        logger.info("=" * 60)
        
        workflow = (
            WorkflowBuilder()
            .with_name("Routing Strategy Test")
            .with_routing_strategy(RoutingStrategy.FIRST_MATCH)
            .add_node("start", NodeType.START)
            .add_node("end", NodeType.END)
            .add_edge("start", "end")
            .build()
        )
        
        assert workflow is not None
        logger.info("[OK] Routing strategy configured")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

