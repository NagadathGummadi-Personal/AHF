"""
Math Workflow Tests.

This test demonstrates a simple math workflow with:
1. Parser Node - Understands user input and extracts numbers/operation
2. Calculator Node - Executes math using Add/Subtract tools from core.tools
3. Formatter Node - Formats output based on user preference (English or JSON)

Features tested:
1. Tool integration using core.tools (FunctionToolSpec, FunctionToolExecutor)
2. Multi-step processing workflow
3. Output formatting based on user preference
4. Context passing between nodes
5. Tool execution within workflow nodes
"""

import pytest
import json
import re
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime

from core.workflows import (    
    WorkflowBuilder,
    WorkflowEngine,
    NodeType,
    NodeSpec,
    WorkflowContext,
    Workflow,
    BaseNode,
    INode,
    IWorkflowContext,
    IWorkflowObserver,
    INodeObserver,
)

# Import core tools infrastructure
from core.tools import (
    ToolType,
    ToolReturnType,
    ToolReturnTarget,
    FunctionToolSpec,
    ToolContext,
    ToolResult,
    FunctionToolExecutor,
    NoOpValidator,
    NoOpSecurity,
)
from core.tools.spec.tool_parameters import NumericParameter

from utils.logging.LoggerAdaptor import LoggerAdaptor

# Setup logger
logger = LoggerAdaptor.get_logger("tests.workflows.math")


# ============================================================================
# TOOLS - Add and Subtract using core.tools infrastructure
# ============================================================================

# Define the async functions for our tools
async def add_function(args: Dict[str, Any]) -> Dict[str, Any]:
    """Add two numbers."""
    a = args.get("a", 0)
    b = args.get("b", 0)
    result = a + b
    logger.info(f"[TOOL:ADD] {a} + {b} = {result}")
    return {
        "operation": "addition",
        "operands": {"a": a, "b": b},
        "result": result
    }


async def subtract_function(args: Dict[str, Any]) -> Dict[str, Any]:
    """Subtract two numbers."""
    a = args.get("a", 0)
    b = args.get("b", 0)
    result = a - b
    logger.info(f"[TOOL:SUBTRACT] {a} - {b} = {result}")
    return {
        "operation": "subtraction",
        "operands": {"a": a, "b": b},
        "result": result
    }


# Create tool specifications using FunctionToolSpec
def create_add_tool_spec() -> FunctionToolSpec:
    """Create the Add tool specification."""
    return FunctionToolSpec(
        id="add-tool-v1",
        tool_name="add",
        description="Adds two numbers together. Returns the sum of a + b.",
        parameters=[
            NumericParameter(
                name="a",
                description="First number to add",
                required=True,
            ),
            NumericParameter(
                name="b",
                description="Second number to add",
                required=True,
            ),
        ],
        return_type=ToolReturnType.JSON,
        return_target=ToolReturnTarget.LLM,
        examples=[
            {"input": {"a": 5, "b": 3}, "output": {"result": 8}},
            {"input": {"a": 10, "b": 20}, "output": {"result": 30}},
        ],
    )


def create_subtract_tool_spec() -> FunctionToolSpec:
    """Create the Subtract tool specification."""
    return FunctionToolSpec(
        id="subtract-tool-v1",
        tool_name="subtract",
        description="Subtracts the second number from the first. Returns a - b.",
        parameters=[
            NumericParameter(
                name="a",
                description="Number to subtract from",
                required=True,
            ),
            NumericParameter(
                name="b",
                description="Number to subtract",
                required=True,
            ),
        ],
        return_type=ToolReturnType.JSON,
        return_target=ToolReturnTarget.LLM,
        examples=[
            {"input": {"a": 10, "b": 4}, "output": {"result": 6}},
            {"input": {"a": 100, "b": 37}, "output": {"result": 63}},
        ],
    )


class MathToolRegistry:
    """
    Registry for math tools using core.tools infrastructure.
    
    Manages FunctionToolExecutors for Add and Subtract operations.
    """
    
    def __init__(self):
        self._executors: Dict[str, FunctionToolExecutor] = {}
        self._specs: Dict[str, FunctionToolSpec] = {}
        self._validator = NoOpValidator()
        self._security = NoOpSecurity()
        self._setup_tools()
    
    def _setup_tools(self):
        """Initialize the math tools."""
        # Add tool
        add_spec = create_add_tool_spec()
        self._specs["add"] = add_spec
        self._executors["add"] = FunctionToolExecutor(
            spec=add_spec,
            func=add_function,
        )
        
        # Subtract tool
        subtract_spec = create_subtract_tool_spec()
        self._specs["subtract"] = subtract_spec
        self._executors["subtract"] = FunctionToolExecutor(
            spec=subtract_spec,
            func=subtract_function,
        )
        
        logger.debug(f"[REGISTRY] Initialized tools: {self.list_tools()}")
    
    def list_tools(self) -> List[str]:
        """List all registered tool names."""
        return list(self._executors.keys())
    
    def get_spec(self, name: str) -> Optional[FunctionToolSpec]:
        """Get tool specification by name."""
        return self._specs.get(name)
    
    def get_executor(self, name: str) -> Optional[FunctionToolExecutor]:
        """Get tool executor by name."""
        return self._executors.get(name)
    
    async def execute(self, tool_name: str, args: Dict[str, Any], ctx: Optional[ToolContext] = None) -> ToolResult:
        """
        Execute a tool by name.
        
        Args:
            tool_name: Name of the tool to execute
            args: Arguments for the tool
            ctx: Optional tool context
            
        Returns:
            ToolResult with execution output
        """
        executor = self.get_executor(tool_name)
        if not executor:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        # Create default context if not provided
        if ctx is None:
            ctx = ToolContext()
        
        # Inject validator and security into context
        ctx.validator = self._validator
        ctx.security = self._security
        
        return await executor.execute(args, ctx)


# Factory function to create the registry
def create_math_tools() -> MathToolRegistry:
    """Create a tool registry with math tools."""
    return MathToolRegistry()


# ============================================================================
# CUSTOM NODES
# ============================================================================

class MathParserNode(BaseNode):
    """
    Node that parses user input to extract:
    - Numbers to operate on
    - Operation (add/subtract)
    - Desired output format (english/json)
    
    Examples:
    - "Add 5 and 3" -> operation=add, a=5, b=3
    - "What is 10 minus 4?" -> operation=subtract, a=10, b=4
    - "Calculate 7 + 2 and give me JSON" -> operation=add, a=7, b=2, format=json
    """
    
    def __init__(self, spec: NodeSpec):
        super().__init__(spec)
        logger.debug(f"[PARSER:INIT] Initializing MathParserNode: {spec.name}")
        
        # Patterns for parsing
        self._add_patterns = [
            r"add\s+(\d+(?:\.\d+)?)\s+(?:and|to|with|plus|\+)\s+(\d+(?:\.\d+)?)",
            r"(\d+(?:\.\d+)?)\s*\+\s*(\d+(?:\.\d+)?)",
            r"sum\s+(?:of\s+)?(\d+(?:\.\d+)?)\s+(?:and|,)\s+(\d+(?:\.\d+)?)",
            r"what\s+is\s+(\d+(?:\.\d+)?)\s+plus\s+(\d+(?:\.\d+)?)",
        ]
        self._subtract_patterns = [
            r"subtract\s+(\d+(?:\.\d+)?)\s+from\s+(\d+(?:\.\d+)?)",
            r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)",
            r"(\d+(?:\.\d+)?)\s+minus\s+(\d+(?:\.\d+)?)",
            r"what\s+is\s+(\d+(?:\.\d+)?)\s+minus\s+(\d+(?:\.\d+)?)",
            r"difference\s+(?:between|of)\s+(\d+(?:\.\d+)?)\s+(?:and|,)\s+(\d+(?:\.\d+)?)",
        ]
    
    async def execute(self, input_data: Any, context: IWorkflowContext) -> Any:
        """Parse user input to extract math operation details."""
        logger.info("+" + "-" * 68 + "+")
        logger.info(f"| [PARSER] Executing node: {self._name}".ljust(69) + "|")
        logger.info("+" + "-" * 68 + "+")
        
        # Extract user input
        user_input = ""
        if isinstance(input_data, dict):
            user_input = input_data.get("user_input", input_data.get("query", ""))
        else:
            user_input = str(input_data)
        
        user_input_lower = user_input.lower()
        logger.info(f"[PARSER] User input: '{user_input}'")
        
        # Determine output format preference
        output_format = "english"  # default
        if "json" in user_input_lower:
            output_format = "json"
        elif "numeric" in user_input_lower or "number" in user_input_lower:
            output_format = "json"
        
        context.set("output_format", output_format)
        logger.info(f"[PARSER] Output format: {output_format}")
        
        # Try to parse addition
        operation = None
        a, b = None, None
        
        for pattern in self._add_patterns:
            match = re.search(pattern, user_input_lower)
            if match:
                operation = "add"
                a = float(match.group(1))
                b = float(match.group(2))
                logger.info(f"[PARSER] Matched ADD pattern: a={a}, b={b}")
                break
        
        # Try subtraction if not addition
        if not operation:
            for pattern in self._subtract_patterns:
                match = re.search(pattern, user_input_lower)
                if match:
                    operation = "subtract"
                    # Handle "subtract X from Y" pattern (reversed order)
                    if "from" in pattern:
                        b = float(match.group(1))  # X (to subtract)
                        a = float(match.group(2))  # Y (from)
                    else:
                        a = float(match.group(1))
                        b = float(match.group(2))
                    logger.info(f"[PARSER] Matched SUBTRACT pattern: a={a}, b={b}")
                    break
        
        # Store in context
        context.set("operation", operation)
        context.set("operand_a", a)
        context.set("operand_b", b)
        context.set("original_input", user_input)
        
        # Build result
        if operation:
            result = {
                "parsed": True,
                "operation": operation,
                "a": a,
                "b": b,
                "output_format": output_format,
                "original_input": user_input
            }
            logger.info(f"[PARSER:DONE] Parsed: {operation}({a}, {b}), format={output_format}")
        else:
            result = {
                "parsed": False,
                "error": "Could not understand the math operation",
                "hint": "Try: 'Add 5 and 3' or 'What is 10 minus 4?'",
                "original_input": user_input
            }
            logger.warning(f"[PARSER:DONE] Failed to parse input")
        
        return result


class CalculatorNode(BaseNode):
    """
    Node that executes math operations using core.tools.
    
    Uses FunctionToolExecutor for Add and Subtract operations.
    """
    
    def __init__(self, spec: NodeSpec, tool_registry: Optional[MathToolRegistry] = None):
        super().__init__(spec)
        logger.debug(f"[CALC:INIT] Initializing CalculatorNode: {spec.name}")
        self._tools = tool_registry or create_math_tools()
        logger.debug(f"[CALC:INIT] Available tools: {self._tools.list_tools()}")
    
    async def execute(self, input_data: Any, context: IWorkflowContext) -> Any:
        """Execute the math operation using core.tools FunctionToolExecutor."""
        logger.info("+" + "-" * 68 + "+")
        logger.info(f"| [CALCULATOR] Executing node: {self._name}".ljust(69) + "|")
        logger.info("+" + "-" * 68 + "+")
        
        # Check if parsing was successful
        if isinstance(input_data, dict) and not input_data.get("parsed", True):
            logger.warning("[CALCULATOR] Input was not parsed successfully")
            return {
                "success": False,
                "error": input_data.get("error", "Parsing failed"),
                "hint": input_data.get("hint", "")
            }
        
        # Get operation details from input or context
        operation = input_data.get("operation") if isinstance(input_data, dict) else context.get("operation")
        a = input_data.get("a") if isinstance(input_data, dict) else context.get("operand_a")
        b = input_data.get("b") if isinstance(input_data, dict) else context.get("operand_b")
        
        logger.info(f"[CALCULATOR] Operation: {operation}, a={a}, b={b}")
        
        if not operation or a is None or b is None:
            return {
                "success": False,
                "error": "Missing operation or operands"
            }
        
        # Execute the appropriate tool using core.tools infrastructure
        try:
            # Create tool context for execution
            tool_ctx = ToolContext(
                trace_id=context.execution_id,
                session_id=context.workflow_id,
            )
            
            # Execute tool via registry
            tool_result: ToolResult = await self._tools.execute(
                tool_name=operation,
                args={"a": a, "b": b},
                ctx=tool_ctx
            )
            
            # Extract result from ToolResult
            tool_output = tool_result.content
            
            # Store result in context
            context.set("calculation_result", tool_output["result"])
            context.set("tool_used", operation)
            context.set("tool_latency_ms", tool_result.latency_ms)
            
            result = {
                "success": True,
                "operation": operation,
                "a": a,
                "b": b,
                "result": tool_output["result"],
                "tool_output": tool_output,
                "tool_latency_ms": tool_result.latency_ms,
            }
            
            logger.info(f"[CALCULATOR:DONE] Result: {tool_output['result']} (latency: {tool_result.latency_ms}ms)")
            return result
            
        except Exception as e:
            logger.error(f"[CALCULATOR:ERROR] {e}")
            return {
                "success": False,
                "error": str(e)
            }


class OutputFormatterNode(BaseNode):
    """
    Node that formats the calculation result based on user preference.
    
    Formats:
    - "english": Natural language response (e.g., "The sum of 5 and 3 is 8")
    - "json": Structured JSON response
    """
    
    def __init__(self, spec: NodeSpec):
        super().__init__(spec)
        logger.debug(f"[FORMATTER:INIT] Initializing OutputFormatterNode: {spec.name}")
    
    async def execute(self, input_data: Any, context: IWorkflowContext) -> Any:
        """Format the output based on user preference."""
        logger.info("+" + "-" * 68 + "+")
        logger.info(f"| [FORMATTER] Executing node: {self._name}".ljust(69) + "|")
        logger.info("+" + "-" * 68 + "+")
        
        # Check if calculation was successful
        if isinstance(input_data, dict) and not input_data.get("success", True):
            error_msg = input_data.get("error", "Calculation failed")
            hint = input_data.get("hint", "")
            return {
                "formatted": True,
                "format": "error",
                "response": f"Sorry, I couldn't complete the calculation. {error_msg}. {hint}".strip()
            }
        
        # Get format preference
        output_format = context.get("output_format", "english")
        
        # Get calculation details
        operation = input_data.get("operation", context.get("operation"))
        a = input_data.get("a", context.get("operand_a"))
        b = input_data.get("b", context.get("operand_b"))
        result = input_data.get("result", context.get("calculation_result"))
        original_input = context.get("original_input", "")
        tool_latency = input_data.get("tool_latency_ms", context.get("tool_latency_ms"))
        
        logger.info(f"[FORMATTER] Format: {output_format}")
        logger.info(f"[FORMATTER] Operation: {operation}({a}, {b}) = {result}")
        
        if output_format == "json":
            # JSON format
            response = {
                "query": original_input,
                "operation": operation,
                "operands": {"a": a, "b": b},
                "result": result,
                "formatted_result": str(result),
                "tool_latency_ms": tool_latency,
            }
            formatted_output = {
                "formatted": True,
                "format": "json",
                "response": response,
                "response_json": json.dumps(response, indent=2)
            }
            logger.info(f"[FORMATTER:DONE] JSON output generated")
        else:
            # English format
            if operation == "add":
                english_response = f"The sum of {a} and {b} is {result}."
            elif operation == "subtract":
                english_response = f"The difference between {a} and {b} is {result}."
            else:
                english_response = f"The result is {result}."
            
            formatted_output = {
                "formatted": True,
                "format": "english",
                "response": english_response,
                "result": result
            }
            logger.info(f"[FORMATTER:DONE] English: '{english_response}'")
        
        return formatted_output


# ============================================================================
# OBSERVERS
# ============================================================================

class MathWorkflowObserver(IWorkflowObserver):
    """Observer for tracking math workflow execution."""
    
    def __init__(self):
        self.events: List[Dict[str, Any]] = []
        self.calculations: List[Dict[str, Any]] = []
    
    async def on_workflow_start(self, workflow: Any, input_data: Any, context: IWorkflowContext) -> None:
        self.events.append({"type": "start", "input": str(input_data)[:100]})
        logger.info(f"[MATH_OBS] Workflow started")
    
    async def on_workflow_complete(self, workflow: Any, output: Any, context: IWorkflowContext, duration_ms: float) -> None:
        self.events.append({"type": "complete", "duration_ms": duration_ms})
        
        # Record calculation if successful
        if context.get("calculation_result") is not None:
            self.calculations.append({
                "operation": context.get("operation"),
                "a": context.get("operand_a"),
                "b": context.get("operand_b"),
                "result": context.get("calculation_result"),
                "tool_used": context.get("tool_used"),
                "tool_latency_ms": context.get("tool_latency_ms"),
            })
        
        logger.info(f"[MATH_OBS] Workflow completed in {duration_ms:.2f}ms")
    
    async def on_workflow_error(self, workflow: Any, error: Exception, context: IWorkflowContext) -> None:
        self.events.append({"type": "error", "error": str(error)})
        logger.error(f"[MATH_OBS] Error: {error}")
    
    async def on_workflow_pause(self, workflow: Any, context: IWorkflowContext) -> None:
        pass
    
    async def on_workflow_resume(self, workflow: Any, context: IWorkflowContext) -> None:
        pass
    
    async def on_workflow_cancel(self, workflow: Any, context: IWorkflowContext) -> None:
        pass


class ToolUsageObserver(INodeObserver):
    """Observer that tracks tool usage in nodes."""
    
    def __init__(self):
        self.tool_calls: List[Dict[str, Any]] = []
        self.node_executions: List[str] = []
    
    async def on_node_start(self, node: INode, input_data: Any, context: IWorkflowContext) -> None:
        self.node_executions.append(node.name)
        logger.info(f"[TOOL_OBS] Node started: {node.name}")
    
    async def on_node_complete(self, node: INode, output: Any, context: IWorkflowContext, duration_ms: float) -> None:
        # Track tool usage from calculator node
        if isinstance(output, dict) and "tool_output" in output:
            tool_output = output["tool_output"]
            self.tool_calls.append({
                "node": node.name,
                "tool": output.get("operation"),
                "operation": tool_output.get("operation"),
                "result": tool_output.get("result"),
                "latency_ms": output.get("tool_latency_ms"),
            })
            logger.info(f"[TOOL_OBS] Tool used: {output.get('operation')} (latency: {output.get('tool_latency_ms')}ms)")
    
    async def on_node_error(self, node: INode, error: Exception, context: IWorkflowContext) -> None:
        logger.error(f"[TOOL_OBS] Node error: {node.name} - {error}")
    
    async def on_node_skip(self, node: INode, reason: str, context: IWorkflowContext) -> None:
        pass


# ============================================================================
# HELPER: Build Math Workflow
# ============================================================================

def build_math_workflow(tool_registry: Optional[MathToolRegistry] = None) -> Workflow:
    """
    Build the math workflow.
    
    Workflow Structure:
        start -> parser -> calculator -> formatter -> end
    """
    tools = tool_registry or create_math_tools()
    
    workflow = (
        WorkflowBuilder()
        .with_name("Math Calculator Workflow")
        .with_description("Parses user input, calculates using core.tools, formats output")
        .add_node("start", NodeType.START)
        .add_node("parser", NodeType.TRANSFORM, name="Math Parser")
        .add_node("calculator", NodeType.TRANSFORM, name="Calculator")
        .add_node("formatter", NodeType.TRANSFORM, name="Output Formatter")
        .add_node("end", NodeType.END)
        .add_edge("start", "parser")
        .add_edge("parser", "calculator")
        .add_edge("calculator", "formatter")
        .add_edge("formatter", "end")
        .build()
    )
    
    # Inject custom nodes
    workflow._nodes["parser"] = MathParserNode(
        NodeSpec(id="parser", name="Math Parser", node_type=NodeType.TRANSFORM)
    )
    workflow._nodes["calculator"] = CalculatorNode(
        NodeSpec(id="calculator", name="Calculator", node_type=NodeType.TRANSFORM),
        tool_registry=tools
    )
    workflow._nodes["formatter"] = OutputFormatterNode(
        NodeSpec(id="formatter", name="Output Formatter", node_type=NodeType.TRANSFORM)
    )
    
    return workflow


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def tool_registry():
    """Create a tool registry with math tools."""
    return create_math_tools()


@pytest.fixture
def math_workflow(tool_registry):
    """Create the math workflow."""
    return build_math_workflow(tool_registry)


@pytest.fixture
def workflow_observer():
    """Create workflow observer."""
    return MathWorkflowObserver()


@pytest.fixture
def tool_observer():
    """Create tool usage observer."""
    return ToolUsageObserver()


# ============================================================================
# TESTS: Core Tools Integration
# ============================================================================

@pytest.mark.asyncio
class TestCoreToolsIntegration:
    """Test the core.tools integration."""
    
    async def test_add_tool_spec(self):
        """Test the add tool specification."""
        logger.info("=" * 60)
        logger.info("TEST: add_tool_spec")
        logger.info("=" * 60)
        
        spec = create_add_tool_spec()
        
        assert spec.id == "add-tool-v1"
        assert spec.tool_name == "add"
        assert spec.tool_type == ToolType.FUNCTION
        assert len(spec.parameters) == 2
        assert spec.return_type == ToolReturnType.JSON
        
        logger.info(f"[OK] Add tool spec: {spec.tool_name}")
    
    async def test_subtract_tool_spec(self):
        """Test the subtract tool specification."""
        logger.info("=" * 60)
        logger.info("TEST: subtract_tool_spec")
        logger.info("=" * 60)
        
        spec = create_subtract_tool_spec()
        
        assert spec.id == "subtract-tool-v1"
        assert spec.tool_name == "subtract"
        assert spec.tool_type == ToolType.FUNCTION
        assert len(spec.parameters) == 2
        
        logger.info(f"[OK] Subtract tool spec: {spec.tool_name}")
    
    async def test_add_tool_execution(self, tool_registry):
        """Test add tool execution via FunctionToolExecutor."""
        logger.info("=" * 60)
        logger.info("TEST: add_tool_execution")
        logger.info("=" * 60)
        
        ctx = ToolContext()
        result = await tool_registry.execute("add", {"a": 5, "b": 3}, ctx)
        
        assert isinstance(result, ToolResult)
        assert result.content["result"] == 8
        assert result.content["operation"] == "addition"
        
        logger.info(f"[OK] 5 + 3 = {result.content['result']}")
    
    async def test_subtract_tool_execution(self, tool_registry):
        """Test subtract tool execution via FunctionToolExecutor."""
        logger.info("=" * 60)
        logger.info("TEST: subtract_tool_execution")
        logger.info("=" * 60)
        
        ctx = ToolContext()
        result = await tool_registry.execute("subtract", {"a": 10, "b": 4}, ctx)
        
        assert isinstance(result, ToolResult)
        assert result.content["result"] == 6
        assert result.content["operation"] == "subtraction"
        
        logger.info(f"[OK] 10 - 4 = {result.content['result']}")
    
    async def test_tool_registry(self, tool_registry):
        """Test the tool registry functionality."""
        logger.info("=" * 60)
        logger.info("TEST: tool_registry")
        logger.info("=" * 60)
        
        # Check registered tools
        tools = tool_registry.list_tools()
        assert "add" in tools
        assert "subtract" in tools
        
        # Get specs
        add_spec = tool_registry.get_spec("add")
        assert add_spec is not None
        assert add_spec.tool_name == "add"
        
        # Get executors
        add_executor = tool_registry.get_executor("add")
        assert add_executor is not None
        assert isinstance(add_executor, FunctionToolExecutor)
        
        logger.info("[OK] Tool registry works correctly")
    
    async def test_tool_with_decimals(self, tool_registry):
        """Test tools with decimal numbers."""
        logger.info("=" * 60)
        logger.info("TEST: tool_with_decimals")
        logger.info("=" * 60)
        
        ctx = ToolContext()
        
        result = await tool_registry.execute("add", {"a": 2.5, "b": 1.5}, ctx)
        assert result.content["result"] == 4.0
        
        result = await tool_registry.execute("subtract", {"a": 5.5, "b": 2.5}, ctx)
        assert result.content["result"] == 3.0
        
        logger.info("[OK] Decimal operations work correctly")
    
    async def test_tool_with_negative_numbers(self, tool_registry):
        """Test tools with negative numbers."""
        logger.info("=" * 60)
        logger.info("TEST: tool_with_negative_numbers")
        logger.info("=" * 60)
        
        ctx = ToolContext()
        
        result = await tool_registry.execute("add", {"a": -5, "b": 3}, ctx)
        assert result.content["result"] == -2
        
        result = await tool_registry.execute("subtract", {"a": 3, "b": 7}, ctx)
        assert result.content["result"] == -4
        
        logger.info("[OK] Negative number operations work correctly")


# ============================================================================
# TESTS: Parser Node
# ============================================================================

@pytest.mark.asyncio
class TestMathParserNode:
    """Test the math parser node."""
    
    async def test_parse_addition_natural(self):
        """Test parsing natural language addition."""
        logger.info("=" * 60)
        logger.info("TEST: parse_addition_natural")
        logger.info("=" * 60)
        
        spec = NodeSpec(id="parser", name="Parser", node_type=NodeType.TRANSFORM)
        parser = MathParserNode(spec)
        context = WorkflowContext(workflow_id="test")
        
        test_cases = [
            ("Add 5 and 3", 5, 3),
            ("add 10 to 20", 10, 20),
            ("What is 7 plus 8?", 7, 8),
            ("sum of 100 and 50", 100, 50),
        ]
        
        for user_input, expected_a, expected_b in test_cases:
            result = await parser.execute({"user_input": user_input}, context)
            assert result["parsed"] is True
            assert result["operation"] == "add"
            assert result["a"] == expected_a
            assert result["b"] == expected_b
            logger.info(f"[OK] Parsed: '{user_input}' -> add({expected_a}, {expected_b})")
        
        logger.info("[OK] Natural language addition parsing works")
    
    async def test_parse_subtraction_natural(self):
        """Test parsing natural language subtraction."""
        logger.info("=" * 60)
        logger.info("TEST: parse_subtraction_natural")
        logger.info("=" * 60)
        
        spec = NodeSpec(id="parser", name="Parser", node_type=NodeType.TRANSFORM)
        parser = MathParserNode(spec)
        
        test_cases = [
            ("10 minus 4", 10, 4),
            ("What is 20 minus 5?", 20, 5),
            ("Subtract 3 from 10", 10, 3),
            ("difference between 50 and 30", 50, 30),
        ]
        
        for user_input, expected_a, expected_b in test_cases:
            context = WorkflowContext(workflow_id="test")
            result = await parser.execute({"user_input": user_input}, context)
            assert result["parsed"] is True
            assert result["operation"] == "subtract"
            assert result["a"] == expected_a
            assert result["b"] == expected_b
            logger.info(f"[OK] Parsed: '{user_input}' -> subtract({expected_a}, {expected_b})")
        
        logger.info("[OK] Natural language subtraction parsing works")
    
    async def test_parse_symbolic(self):
        """Test parsing symbolic expressions."""
        logger.info("=" * 60)
        logger.info("TEST: parse_symbolic")
        logger.info("=" * 60)
        
        spec = NodeSpec(id="parser", name="Parser", node_type=NodeType.TRANSFORM)
        parser = MathParserNode(spec)
        context = WorkflowContext(workflow_id="test")
        
        # Addition
        result = await parser.execute({"user_input": "5 + 3"}, context)
        assert result["operation"] == "add"
        assert result["a"] == 5 and result["b"] == 3
        
        # Subtraction
        context = WorkflowContext(workflow_id="test")
        result = await parser.execute({"user_input": "10 - 4"}, context)
        assert result["operation"] == "subtract"
        assert result["a"] == 10 and result["b"] == 4
        
        logger.info("[OK] Symbolic parsing works")
    
    async def test_parse_output_format_json(self):
        """Test detecting JSON output format preference."""
        logger.info("=" * 60)
        logger.info("TEST: parse_output_format_json")
        logger.info("=" * 60)
        
        spec = NodeSpec(id="parser", name="Parser", node_type=NodeType.TRANSFORM)
        parser = MathParserNode(spec)
        context = WorkflowContext(workflow_id="test")
        
        result = await parser.execute({"user_input": "Add 5 and 3, give me JSON"}, context)
        assert result["output_format"] == "json"
        
        logger.info("[OK] JSON format preference detected")
    
    async def test_parse_failure(self):
        """Test handling unparseable input."""
        logger.info("=" * 60)
        logger.info("TEST: parse_failure")
        logger.info("=" * 60)
        
        spec = NodeSpec(id="parser", name="Parser", node_type=NodeType.TRANSFORM)
        parser = MathParserNode(spec)
        context = WorkflowContext(workflow_id="test")
        
        result = await parser.execute({"user_input": "What's the weather today?"}, context)
        assert result["parsed"] is False
        assert "error" in result
        
        logger.info("[OK] Parse failure handled correctly")


# ============================================================================
# TESTS: Calculator Node
# ============================================================================

@pytest.mark.asyncio
class TestCalculatorNode:
    """Test the calculator node with core.tools."""
    
    async def test_calculator_addition(self, tool_registry):
        """Test calculator with addition using FunctionToolExecutor."""
        logger.info("=" * 60)
        logger.info("TEST: calculator_addition")
        logger.info("=" * 60)
        
        spec = NodeSpec(id="calc", name="Calculator", node_type=NodeType.TRANSFORM)
        calc = CalculatorNode(spec, tool_registry)
        context = WorkflowContext(workflow_id="test")
        
        input_data = {"parsed": True, "operation": "add", "a": 15, "b": 25}
        result = await calc.execute(input_data, context)
        
        assert result["success"] is True
        assert result["result"] == 40
        assert context.get("calculation_result") == 40
        assert context.get("tool_used") == "add"
        
        logger.info(f"[OK] 15 + 25 = 40")
    
    async def test_calculator_subtraction(self, tool_registry):
        """Test calculator with subtraction using FunctionToolExecutor."""
        logger.info("=" * 60)
        logger.info("TEST: calculator_subtraction")
        logger.info("=" * 60)
        
        spec = NodeSpec(id="calc", name="Calculator", node_type=NodeType.TRANSFORM)
        calc = CalculatorNode(spec, tool_registry)
        context = WorkflowContext(workflow_id="test")
        
        input_data = {"parsed": True, "operation": "subtract", "a": 100, "b": 35}
        result = await calc.execute(input_data, context)
        
        assert result["success"] is True
        assert result["result"] == 65
        assert context.get("tool_used") == "subtract"
        
        logger.info(f"[OK] 100 - 35 = 65")
    
    async def test_calculator_parse_failure(self, tool_registry):
        """Test calculator handling parse failure."""
        logger.info("=" * 60)
        logger.info("TEST: calculator_parse_failure")
        logger.info("=" * 60)
        
        spec = NodeSpec(id="calc", name="Calculator", node_type=NodeType.TRANSFORM)
        calc = CalculatorNode(spec, tool_registry)
        context = WorkflowContext(workflow_id="test")
        
        input_data = {"parsed": False, "error": "Could not parse"}
        result = await calc.execute(input_data, context)
        
        assert result["success"] is False
        
        logger.info("[OK] Calculator handles parse failure")


# ============================================================================
# TESTS: Output Formatter Node
# ============================================================================

@pytest.mark.asyncio
class TestOutputFormatterNode:
    """Test the output formatter node."""
    
    async def test_format_english(self):
        """Test English format output."""
        logger.info("=" * 60)
        logger.info("TEST: format_english")
        logger.info("=" * 60)
        
        spec = NodeSpec(id="fmt", name="Formatter", node_type=NodeType.TRANSFORM)
        formatter = OutputFormatterNode(spec)
        
        context = WorkflowContext(workflow_id="test")
        context.set("output_format", "english")
        
        input_data = {"success": True, "operation": "add", "a": 5, "b": 3, "result": 8}
        result = await formatter.execute(input_data, context)
        
        assert result["format"] == "english"
        assert "sum" in result["response"].lower()
        assert "8" in result["response"]
        
        logger.info(f"[OK] English: {result['response']}")
    
    async def test_format_json(self):
        """Test JSON format output."""
        logger.info("=" * 60)
        logger.info("TEST: format_json")
        logger.info("=" * 60)
        
        spec = NodeSpec(id="fmt", name="Formatter", node_type=NodeType.TRANSFORM)
        formatter = OutputFormatterNode(spec)
        
        context = WorkflowContext(workflow_id="test")
        context.set("output_format", "json")
        context.set("original_input", "Add 5 and 3")
        
        input_data = {"success": True, "operation": "add", "a": 5, "b": 3, "result": 8, "tool_latency_ms": 5}
        result = await formatter.execute(input_data, context)
        
        assert result["format"] == "json"
        assert result["response"]["result"] == 8
        assert "response_json" in result
        
        logger.info(f"[OK] JSON response generated")
    
    async def test_format_error(self):
        """Test error format output."""
        logger.info("=" * 60)
        logger.info("TEST: format_error")
        logger.info("=" * 60)
        
        spec = NodeSpec(id="fmt", name="Formatter", node_type=NodeType.TRANSFORM)
        formatter = OutputFormatterNode(spec)
        context = WorkflowContext(workflow_id="test")
        
        input_data = {"success": False, "error": "Unknown operation"}
        result = await formatter.execute(input_data, context)
        
        assert result["format"] == "error"
        assert "sorry" in result["response"].lower()
        
        logger.info("[OK] Error format works")


# ============================================================================
# TESTS: Full Workflow Execution
# ============================================================================

@pytest.mark.asyncio
class TestMathWorkflowExecution:
    """Test complete math workflow execution with core.tools."""
    
    async def test_addition_workflow_english(self, math_workflow, workflow_observer, tool_observer):
        """Test full addition workflow with English output."""
        logger.info("=" * 60)
        logger.info("TEST: addition_workflow_english")
        logger.info("=" * 60)
        
        engine = WorkflowEngine(
            workflow_observers=[workflow_observer],
            node_observers=[tool_observer]
        )
        
        input_data = {"user_input": "Add 25 and 17"}
        output, context = await engine.execute(math_workflow, input_data)
        
        assert output["formatted"] is True
        assert output["format"] == "english"
        assert "42" in output["response"]
        assert context.get("calculation_result") == 42
        
        # Check tool was used
        assert len(tool_observer.tool_calls) == 1
        assert tool_observer.tool_calls[0]["tool"] == "add"
        
        logger.info(f"[OK] Response: {output['response']}")
    
    async def test_subtraction_workflow_english(self, math_workflow, workflow_observer, tool_observer):
        """Test full subtraction workflow with English output."""
        logger.info("=" * 60)
        logger.info("TEST: subtraction_workflow_english")
        logger.info("=" * 60)
        
        engine = WorkflowEngine(
            workflow_observers=[workflow_observer],
            node_observers=[tool_observer]
        )
        
        input_data = {"user_input": "What is 100 minus 37?"}
        output, context = await engine.execute(math_workflow, input_data)
        
        assert output["format"] == "english"
        assert "63" in output["response"]
        assert context.get("calculation_result") == 63
        
        logger.info(f"[OK] Response: {output['response']}")
    
    async def test_addition_workflow_json(self, math_workflow, workflow_observer):
        """Test addition workflow with JSON output."""
        logger.info("=" * 60)
        logger.info("TEST: addition_workflow_json")
        logger.info("=" * 60)
        
        engine = WorkflowEngine(workflow_observers=[workflow_observer])
        
        input_data = {"user_input": "Add 50 and 25, give me JSON"}
        output, context = await engine.execute(math_workflow, input_data)
        
        assert output["format"] == "json"
        assert output["response"]["result"] == 75
        assert output["response"]["operation"] == "add"
        
        logger.info(f"[OK] JSON Response: {output['response']}")
    
    async def test_symbolic_input(self, math_workflow):
        """Test workflow with symbolic input (5 + 3)."""
        logger.info("=" * 60)
        logger.info("TEST: symbolic_input")
        logger.info("=" * 60)
        
        engine = WorkflowEngine()
        
        output, _ = await engine.execute(math_workflow, {"user_input": "5 + 3"})
        assert "8" in output["response"]
        
        output, _ = await engine.execute(math_workflow, {"user_input": "20 - 7"})
        assert "13" in output["response"]
        
        logger.info("[OK] Symbolic input works")
    
    async def test_decimal_numbers(self, math_workflow):
        """Test workflow with decimal numbers."""
        logger.info("=" * 60)
        logger.info("TEST: decimal_numbers")
        logger.info("=" * 60)
        
        engine = WorkflowEngine()
        
        output, context = await engine.execute(
            math_workflow, 
            {"user_input": "Add 3.5 and 2.5"}
        )
        
        assert context.get("calculation_result") == 6.0
        
        logger.info(f"[OK] Decimal result: {context.get('calculation_result')}")
    
    async def test_invalid_input(self, math_workflow):
        """Test workflow with invalid/unparseable input."""
        logger.info("=" * 60)
        logger.info("TEST: invalid_input")
        logger.info("=" * 60)
        
        engine = WorkflowEngine()
        
        output, _ = await engine.execute(
            math_workflow,
            {"user_input": "Tell me a joke"}
        )
        
        assert output["format"] == "error"
        assert "sorry" in output["response"].lower()
        
        logger.info(f"[OK] Error handled: {output['response']}")
    
    async def test_execution_path(self, math_workflow):
        """Test that execution path is correct."""
        logger.info("=" * 60)
        logger.info("TEST: execution_path")
        logger.info("=" * 60)
        
        engine = WorkflowEngine()
        
        _, context = await engine.execute(
            math_workflow,
            {"user_input": "5 + 5"}
        )
        
        assert "start" in context.execution_path
        assert "parser" in context.execution_path
        assert "calculator" in context.execution_path
        assert "formatter" in context.execution_path
        assert "end" in context.execution_path
        
        logger.info(f"[OK] Execution path: {context.execution_path}")
    
    async def test_multiple_calculations(self, tool_registry, workflow_observer):
        """Test multiple calculations tracking tool usage."""
        logger.info("=" * 60)
        logger.info("TEST: multiple_calculations")
        logger.info("=" * 60)
        
        workflow = build_math_workflow(tool_registry)
        engine = WorkflowEngine(workflow_observers=[workflow_observer])
        
        calculations = [
            ("Add 10 and 5", 15, "add"),
            ("20 - 8", 12, "subtract"),
            ("What is 7 plus 3?", 10, "add"),
            ("Subtract 5 from 25", 20, "subtract"),
        ]
        
        for query, expected, expected_tool in calculations:
            _, context = await engine.execute(workflow, {"user_input": query})
            assert context.get("calculation_result") == expected
            assert context.get("tool_used") == expected_tool
            logger.info(f"[OK] '{query}' = {expected} (tool: {expected_tool})")
        
        # Check observer recorded all calculations
        assert len(workflow_observer.calculations) == len(calculations)
        
        logger.info(f"[OK] All {len(calculations)} calculations completed")


# ============================================================================
# TESTS: Streaming
# ============================================================================

@pytest.mark.asyncio
class TestMathWorkflowStreaming:
    """Test streaming execution of math workflow."""
    
    async def test_streaming_execution(self, math_workflow):
        """Test streaming through math workflow."""
        logger.info("=" * 60)
        logger.info("TEST: streaming_execution")
        logger.info("=" * 60)
        
        engine = WorkflowEngine()
        
        nodes_executed = []
        final_output = None
        
        async for node_id, output, context in engine.execute_streaming(
            math_workflow,
            {"user_input": "Add 7 and 8"}
        ):
            nodes_executed.append(node_id)
            final_output = output
            logger.info(f"[STREAM] Node: {node_id}")
        
        assert "parser" in nodes_executed
        assert "calculator" in nodes_executed
        assert "formatter" in nodes_executed
        assert final_output is not None
        
        logger.info(f"[OK] Streamed {len(nodes_executed)} nodes")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
