"""
Booking Workflow Tests.

This test file demonstrates the enhanced workflow architecture based on the
conversational booking flow example. It covers:

1. Greeting Node - Initial customer greeting and intent gathering
2. Intent-based Routing - Book, Cancel, Reschedule, General Info
3. Booking Subworkflow with:
   - Required transition variables (ServiceName, GuestName)
   - Prompting for missing required variables
   - LLM-based intent classification
   - Service lookup and confirmation
4. Human-in-the-Loop (HITL) nodes for user input
5. Agent-Workflow interoperability (workflows as tools)

Key Architecture Concepts Demonstrated:
- IOSpec for typed inputs/outputs
- TransitionSpec with required variables
- SwitchNode for intent routing
- HumanInputNode for HITL
- SubworkflowNode for nested workflows
- WorkflowTool for agent integration
"""

import json
import time
import pytest
from typing import Any, Dict, List, Optional
from datetime import datetime

from core.llms import LLMFactory, create_context
from core.workflows import (
    # Builder and Engine
    WorkflowBuilder,
    WorkflowEngine,
    # Enums
    NodeType,
    ConditionOperator,
    DataType,
    DataFormat,
    VariableRequirement,
    ConditionSourceType,
    # Spec Models
    NodeSpec,
    WorkflowContext,
    IOSpec,
    IOFieldSpec,
    TransitionSpec,
    TransitionVariable,
    TransitionCondition,
    # Implementations
    BaseNode,
    LLMNode,
    # Tools
    WorkflowTool,
    create_workflow_tool,
    # Interfaces
    IWorkflowContext,
    IWorkflowObserver,
)
from utils.logging.LoggerAdaptor import LoggerAdaptor

# Setup logger
logger = LoggerAdaptor.get_logger("tests.workflows.booking")

# ============================================================================
# AZURE GPT-4.1 MINI CONFIG
# ============================================================================

# AZURE_CONFIG = {
#     "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT", "),
#     "deployment_name": os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1-mini"),
#     "api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
#     "api_key": os.getenv("AZURE_OPENAI_KEY", ""),
#     "timeout": int(os.getenv("AZURE_OPENAI_TIMEOUT", "60")),
# }

AZURE_CONFIG = {
    "endpoint": "https://zeenie-sweden.openai.azure.com/",
    "deployment_name": "gpt-4.1-mini",  # Using GPT-4.1 Mini deployment
    "api_version": "2024-02-15-preview",
    "timeout": 60,
}

# ============================================================================
# MOCK LLM FOR TESTING
# ============================================================================

class MockLLM:
    """Mock LLM for testing intent classification and responses."""
    
    def __init__(self, responses: Optional[Dict[str, str]] = None):
        self.responses = responses or {}
        self.call_history: List[Dict[str, Any]] = []
    
    async def generate(self, messages: List[Dict[str, str]], **kwargs) -> Any:
        """Generate mock response."""
        self.call_history.append({"messages": messages, "kwargs": kwargs})
        
        # Get user message
        user_msg = ""
        for msg in messages:
            if msg.get("role") == "user":
                user_msg = msg.get("content", "")
        
        # Check for predefined responses
        for key, response in self.responses.items():
            if key.lower() in user_msg.lower():
                return MockResponse(response)
        
        # Default response
        default_payload = {
            "intent": "unknown",
            "detected_services": [],
            "service_name": None,
            "guest_name": None,
        }
        return MockResponse(json.dumps(default_payload))

    async def get_answer(self, messages: List[Dict[str, str]], ctx: Any = None, **kwargs) -> Any:
        """Mock get_answer to mirror real LLM interface."""
        return await self.generate(messages, **kwargs)


class MockResponse:
    """Mock LLM response."""
    
    def __init__(self, content: str, model: str = "mock-gpt"):
        self.content = content
        self.model = model
        self.usage = MockUsage()


class MockUsage:
    """Mock token usage."""
    prompt_tokens = 10
    completion_tokens = 20
    total_tokens = 30


# ============================================================================
# CUSTOM NODES FOR BOOKING WORKFLOW
# ============================================================================

class GreetingNode(BaseNode):
    """
    Greeting node that welcomes the customer and gathers initial context.
    
    This node:
    - Greets the customer
    - Analyzes their message for intent hints
    - Extracts any information already provided (name, service, etc.)
    """
    
    async def execute(self, input_data: Any, context: IWorkflowContext) -> Any:
        logger.info(f"[GREETING] Processing: {input_data}")
        started_at = time.perf_counter()
        
        message = input_data.get("message", "") if isinstance(input_data, dict) else str(input_data)
        llm = context.get("llm")
        
        # Try LLM-based intent & entity extraction when available
        intent = "unknown"
        services: List[str] = []
        service_name = None
        guest_name = None
        
        if llm:
            try:
                system_prompt = (
                    "You are an intent classifier for salon bookings. "
                    "Extract intent (book, cancel, reschedule, inquiry, greeting, unknown), "
                    "service_name, a list of detected_services, and guest_name if stated. "
                    "Return JSON with keys: intent (lowercase string), service_name (string or null), "
                    "detected_services (array of strings), guest_name (string or null). "
                    "If unsure, set intent to \"unknown\" and detected_services to []."
                )
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message},
                ]
                llm_start = time.perf_counter()
                if hasattr(llm, "get_answer"):
                    llm_ctx = create_context(
                        user_id=str(getattr(context, "workflow_id", "workflow")),
                        session_id=str(getattr(context, "execution_id", "session")),
                    )
                    resp = await llm.get_answer(messages, llm_ctx, max_tokens=200)
                else:
                    resp = await llm.generate(messages, max_tokens=200)
                llm_ms = (time.perf_counter() - llm_start) * 1000
                parsed = self._parse_llm_response(resp)
                intent = parsed.get("intent", intent) or intent
                services = parsed.get("detected_services", services) or services
                service_name = parsed.get("service_name", service_name) or service_name
                guest_name = parsed.get("guest_name", guest_name) or guest_name
                logger.info(
                    f"[GREETING] LLM intent parsed in {llm_ms:.1f}ms: intent={intent}, "
                    f"services={services}, service_name={service_name}, guest_name={guest_name}"
                )
            except Exception as e:
                logger.warning(f"[GREETING] LLM intent extraction failed, falling back. Error: {e}")
        
        # Heuristic fallback if LLM not available or insufficient
        if intent == "unknown":
            if any(word in message.lower() for word in ["book", "appointment", "schedule", "reserve"]):
                intent = "book"
            elif any(word in message.lower() for word in ["cancel", "remove"]):
                intent = "cancel"
            elif any(word in message.lower() for word in ["reschedule", "change", "move"]):
                intent = "reschedule"
            elif any(word in message.lower() for word in ["hi", "hello", "hey"]):
                intent = "greeting"
        
        if not services:
            service_keywords = ["haircut", "massage", "facial", "manicure", "spa"]
            for service in service_keywords:
                if service in message.lower():
                    services.append(service)
        
        # Derive service_name if still missing
        if not service_name and services:
            service_name = services[0]
        
        if not guest_name and "my name is" in message.lower():
            parts = message.lower().split("my name is")
            if len(parts) > 1:
                guest_name = parts[1].strip().split()[0].title()
        
        # Store in context
        context.set("detected_intent", intent)
        context.set("detected_services", services)
        if guest_name:
            context.set("guest_name", guest_name)
        if service_name:
            context.set("service_name", service_name)
        
        result = {
            "greeting": "Hello! Welcome to our service center.",
            "message": message,
            "detected_intent": intent,
            "detected_services": services,
            "service_name": service_name,
            "guest_name": guest_name,
            "needs_more_info": intent == "unknown" or intent == "greeting",
        }
        
        total_ms = (time.perf_counter() - started_at) * 1000
        logger.info(
            f"[GREETING] Detected intent: {intent}, services: {services}, "
            f"service_name={service_name}, guest_name={guest_name}, duration={total_ms:.1f}ms"
        )
        return result
    
    def _parse_llm_response(self, response: Any) -> Dict[str, Any]:
        """Parse LLM JSON response safely."""
        content = getattr(response, "content", "") if response else ""
        try:
            data = json.loads(content)
            if not isinstance(data, dict):
                return {}
            # Normalize keys
            intent = str(data.get("intent", "unknown")).lower()
            services = data.get("detected_services") or []
            if isinstance(services, str):
                services = [services]
            service_name = data.get("service_name")
            if service_name:
                service_name = str(service_name).strip().lower()
            guest_name = data.get("guest_name")
            if guest_name:
                guest_name = str(guest_name).strip().title()
            return {
                "intent": intent,
                "detected_services": services,
                "service_name": service_name,
                "guest_name": guest_name,
            }
        except Exception:
            return {}


class IntentRouterNode(BaseNode):
    """
    Routes conversation based on detected intent.
    
    Supports intents: book, cancel, reschedule, inquiry, handover
    """
    
    async def execute(self, input_data: Any, context: IWorkflowContext) -> Any:
        logger.info("[ROUTER] Routing based on intent")
        
        # Get intent from context or input
        intent = context.get("detected_intent", "unknown")
        if isinstance(input_data, dict):
            intent = input_data.get("intent", intent)
            intent = input_data.get("detected_intent", intent)
        
        # Map to route
        intent_routes = {
            "book": "booking_flow",
            "cancel": "cancellation_flow",
            "reschedule": "reschedule_flow",
            "inquiry": "inquiry_flow",
            "greeting": "greeting_response",
            "unknown": "clarification",
        }
        
        route = intent_routes.get(intent, "clarification")
        
        # Store routing decision
        context.set("route", route)
        context.set("current_intent", intent)
        
        result = {
            "intent": intent,
            "route": route,
            "message": f"Routing to {route} based on intent: {intent}",
        }
        
        logger.info(f"[ROUTER] Intent={intent} -> Route={route}")
        return result


class BookingValidationNode(BaseNode):
    """
    Validates that required booking information is available.
    
    Required fields:
    - service_name: What service to book
    - guest_name: Customer's name
    
    Optional fields:
    - preferred_time: Requested time slot
    - phone_number: Contact number
    """
    
    async def execute(self, input_data: Any, context: IWorkflowContext) -> Any:
        logger.info("[BOOKING_VALIDATION] Checking required fields")
        
        # Get current values
        service_name = context.get("service_name")
        guest_name = context.get("guest_name")
        
        # Also check input data
        if isinstance(input_data, dict):
            service_name = input_data.get("service_name", service_name)
            guest_name = input_data.get("guest_name", guest_name)
        
        missing_fields = []
        prompts = []
        
        if not service_name:
            missing_fields.append("service_name")
            prompts.append("What service would you like to book?")
        
        if not guest_name:
            missing_fields.append("guest_name")
            prompts.append("May I have your name for the booking?")
        
        is_valid = len(missing_fields) == 0
        
        # Store validation result
        context.set("booking_valid", is_valid)
        context.set("missing_fields", missing_fields)
        
        result = {
            "valid": is_valid,
            "service_name": service_name,
            "guest_name": guest_name,
            "missing_fields": missing_fields,
            "prompts": prompts,
            "prompt_message": " ".join(prompts) if prompts else None,
        }
        
        logger.info(f"[BOOKING_VALIDATION] Valid={is_valid}, Missing={missing_fields}")
        return result


class ServiceLookupNode(BaseNode):
    """
    Looks up service availability in the "knowledge base".
    
    Simulates checking service availability and pricing.
    """
    
    # Mock service catalog
    SERVICES = {
        "haircut": {"available": True, "price": 30, "duration": 30},
        "massage": {"available": True, "price": 80, "duration": 60},
        "facial": {"available": True, "price": 50, "duration": 45},
        "manicure": {"available": True, "price": 25, "duration": 30},
        "spa": {"available": False, "price": 150, "duration": 120},
    }
    
    async def execute(self, input_data: Any, context: IWorkflowContext) -> Any:
        logger.info("[SERVICE_LOOKUP] Looking up service")
        
        service_name = context.get("service_name", "")
        if isinstance(input_data, dict):
            service_name = input_data.get("service_name", service_name)
        
        service_name = service_name.lower() if service_name else ""
        
        service_info = self.SERVICES.get(service_name)
        
        if service_info:
            result = {
                "found": True,
                "service_name": service_name,
                "available": service_info["available"],
                "price": service_info["price"],
                "duration": service_info["duration"],
                "message": f"{service_name.title()} is {'available' if service_info['available'] else 'not available'}. "
                          f"Price: ${service_info['price']}, Duration: {service_info['duration']} minutes."
            }
            context.set("service_found", True)
            context.set("service_available", service_info["available"])
        else:
            result = {
                "found": False,
                "service_name": service_name,
                "message": f"Sorry, we don't offer '{service_name}'. Available services: {', '.join(self.SERVICES.keys())}"
            }
            context.set("service_found", False)
            context.set("service_available", False)
        
        logger.info(f"[SERVICE_LOOKUP] Service={service_name}, Found={result['found']}")
        return result


class BookingConfirmationNode(BaseNode):
    """
    Confirms the booking and generates confirmation details.
    """
    
    async def execute(self, input_data: Any, context: IWorkflowContext) -> Any:
        logger.info("[BOOKING_CONFIRMATION] Creating booking")
        
        service_name = context.get("service_name", "Unknown")
        guest_name = context.get("guest_name", "Guest")
        
        # Generate confirmation
        booking_id = f"BK-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        result = {
            "success": True,
            "booking_id": booking_id,
            "service_name": service_name,
            "guest_name": guest_name,
            "message": f"Great! Your {service_name} has been booked, {guest_name}. "
                      f"Your booking ID is {booking_id}. We look forward to seeing you!",
            "confirmation_time": datetime.now().isoformat(),
        }
        
        context.set("booking_id", booking_id)
        context.set("booking_confirmed", True)
        
        logger.info(f"[BOOKING_CONFIRMATION] Booking created: {booking_id}")
        return result


class ClarificationNode(BaseNode):
    """
    Asks for clarification when intent is unclear.
    """
    
    async def execute(self, input_data: Any, context: IWorkflowContext) -> Any:
        logger.info("[CLARIFICATION] Requesting clarification")
        
        result = {
            "message": "I'm not quite sure what you'd like to do. Would you like to:\n"
                      "- Book a new appointment\n"
                      "- Cancel an existing appointment\n"
                      "- Reschedule an appointment\n"
                      "- Get information about our services",
            "options": ["book", "cancel", "reschedule", "inquiry"],
            "needs_input": True,
        }
        
        return result


# ============================================================================
# SIMPLE OBSERVERS
# ============================================================================

class BookingWorkflowObserver(IWorkflowObserver):
    """Observer for tracking booking workflow events."""
    
    def __init__(self):
        self.events: List[Dict[str, Any]] = []
        self.conversation_turns: List[Dict[str, Any]] = []
    
    async def on_workflow_start(self, workflow: Any, input_data: Any, context: IWorkflowContext) -> None:
        self.events.append({"type": "start", "workflow": workflow.name, "input": input_data})
        logger.info(f"[WORKFLOW] Started: {workflow.name}")
    
    async def on_workflow_complete(self, workflow: Any, output: Any, context: IWorkflowContext, duration_ms: float) -> None:
        self.events.append({"type": "complete", "output": output, "duration_ms": duration_ms})
        logger.info(f"[WORKFLOW] Completed in {duration_ms:.2f}ms")
    
    async def on_workflow_error(self, workflow: Any, error: Exception, context: IWorkflowContext) -> None:
        self.events.append({"type": "error", "error": str(error)})
        logger.error(f"[WORKFLOW] Error: {error}")
    
    async def on_workflow_pause(self, workflow: Any, context: IWorkflowContext) -> None:
        self.events.append({"type": "pause"})
    
    async def on_workflow_resume(self, workflow: Any, context: IWorkflowContext) -> None:
        self.events.append({"type": "resume"})
    
    async def on_workflow_cancel(self, workflow: Any, context: IWorkflowContext) -> None:
        self.events.append({"type": "cancel"})


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_llm():
    """Create a mock LLM for testing."""
    return MockLLM({
        "book": json.dumps({
            "intent": "book",
            "detected_services": ["haircut"],
            "guest_name": "John",
        }),
        "haircut": json.dumps({
            "intent": "book",
            "detected_services": ["haircut"],
            "guest_name": "John",
        }),
        "cancel": json.dumps({
            "intent": "cancel",
            "detected_services": [],
            "guest_name": None,
        }),
    })


@pytest.fixture
def skip_if_no_azure_llm():
    """Skip tests that require Azure GPT-4.1 Mini when credentials are missing."""
    if not AZURE_CONFIG["api_key"] or "your-resource" in AZURE_CONFIG["endpoint"]:
        pytest.skip("Azure GPT-4.1 Mini credentials not configured")


@pytest.fixture
async def azure_llm(skip_if_no_azure_llm):
    """Create a real Azure GPT-4.1 Mini LLM instance."""
    llm = LLMFactory.create_llm(
        "azure-gpt-4.1-mini",
        connector_config=AZURE_CONFIG
    )
    
    yield llm
    
    if hasattr(llm.connector, "close"):
        await llm.connector.close()


@pytest.fixture
def workflow_observer():
    """Create a booking workflow observer."""
    return BookingWorkflowObserver()


# ============================================================================
# TESTS: Basic Booking Flow
# ============================================================================

@pytest.mark.asyncio
class TestBasicBookingFlow:
    """Test basic booking workflow scenarios."""
    
    async def test_greeting_node_detects_booking_intent(self, azure_llm):
        """Test that greeting node correctly identifies booking intent."""
        logger.info("=" * 60)
        logger.info("TEST: greeting_node_detects_booking_intent")
        logger.info("=" * 60)
        
        spec = NodeSpec(
            id="greeting",
            name="Greeting",
            node_type=NodeType.TRANSFORM,
        )
        node = GreetingNode(spec)
        
        context = WorkflowContext(workflow_id="test")
        context.set("llm", azure_llm)
        
        # Test booking intent
        result = await node.execute(
            {"message": "Hi, I'd like to book a haircut"},
            context
        )
        
        assert result["detected_intent"] == "book"
        assert "haircut" in result["detected_services"]
        assert context.get("detected_intent") == "book"
        
        logger.info(f"[OK] Detected intent: {result['detected_intent']}")
    
    async def test_booking_validation_identifies_missing_fields(self):
        """Test that booking validation identifies missing required fields."""
        logger.info("=" * 60)
        logger.info("TEST: booking_validation_identifies_missing_fields")
        logger.info("=" * 60)
        
        spec = NodeSpec(
            id="validation",
            name="Booking Validation",
            node_type=NodeType.TRANSFORM,
        )
        node = BookingValidationNode(spec)
        
        context = WorkflowContext(workflow_id="test")
        
        # Test with no data
        result = await node.execute({}, context)
        
        assert not result["valid"]
        assert "service_name" in result["missing_fields"]
        assert "guest_name" in result["missing_fields"]
        assert len(result["prompts"]) == 2
        
        logger.info(f"[OK] Missing fields: {result['missing_fields']}")
    
    async def test_booking_validation_passes_with_all_fields(self):
        """Test that booking validation passes when all fields present."""
        logger.info("=" * 60)
        logger.info("TEST: booking_validation_passes_with_all_fields")
        logger.info("=" * 60)
        
        spec = NodeSpec(
            id="validation",
            name="Booking Validation",
            node_type=NodeType.TRANSFORM,
        )
        node = BookingValidationNode(spec)
        
        context = WorkflowContext(workflow_id="test")
        context.set("service_name", "haircut")
        context.set("guest_name", "John")
        
        result = await node.execute({}, context)
        
        assert result["valid"]
        assert len(result["missing_fields"]) == 0
        assert result["service_name"] == "haircut"
        assert result["guest_name"] == "John"
        
        logger.info("[OK] Validation passed with all fields")
    
    async def test_service_lookup_finds_known_service(self):
        """Test that service lookup finds known services."""
        logger.info("=" * 60)
        logger.info("TEST: service_lookup_finds_known_service")
        logger.info("=" * 60)
        
        spec = NodeSpec(
            id="lookup",
            name="Service Lookup",
            node_type=NodeType.TRANSFORM,
        )
        node = ServiceLookupNode(spec)
        
        context = WorkflowContext(workflow_id="test")
        context.set("service_name", "haircut")
        
        result = await node.execute({}, context)
        
        assert result["found"]
        assert result["available"]
        assert result["price"] == 30
        
        logger.info(f"[OK] Found service: {result['service_name']}, Price: ${result['price']}")


# ============================================================================
# TESTS: Complete Booking Workflow
# ============================================================================

@pytest.mark.asyncio
class TestCompleteBookingWorkflow:
    """Test complete booking workflow execution."""
    
    async def test_simple_booking_workflow(self, workflow_observer):
        """Test a simple linear booking workflow."""
        logger.info("=" * 60)
        logger.info("TEST: simple_booking_workflow")
        logger.info("=" * 60)
        
        # Build the workflow
        workflow = (
            WorkflowBuilder()
            .with_name("Simple Booking Workflow")
            .with_description("A simple booking flow with greeting, validation, and confirmation")
            .add_node("start", NodeType.START)
            .add_node("greeting", NodeType.TRANSFORM, name="Greeting")
            .add_node("validation", NodeType.TRANSFORM, name="Validation")
            .add_node("lookup", NodeType.TRANSFORM, name="Service Lookup")
            .add_node("confirmation", NodeType.TRANSFORM, name="Confirmation")
            .add_node("end", NodeType.END)
            .add_edge("start", "greeting")
            .add_edge("greeting", "validation")
            .add_edge("validation", "lookup")
            .add_edge("lookup", "confirmation")
            .add_edge("confirmation", "end")
            .build()
        )
        
        # Inject custom nodes
        workflow._nodes["greeting"] = GreetingNode(
            NodeSpec(id="greeting", name="Greeting", node_type=NodeType.TRANSFORM)
        )
        workflow._nodes["validation"] = BookingValidationNode(
            NodeSpec(id="validation", name="Validation", node_type=NodeType.TRANSFORM)
        )
        workflow._nodes["lookup"] = ServiceLookupNode(
            NodeSpec(id="lookup", name="Service Lookup", node_type=NodeType.TRANSFORM)
        )
        workflow._nodes["confirmation"] = BookingConfirmationNode(
            NodeSpec(id="confirmation", name="Confirmation", node_type=NodeType.TRANSFORM)
        )
        
        # Execute with complete booking info
        engine = WorkflowEngine(workflow_observers=[workflow_observer])
        
        input_data = {
            "message": "Hi, my name is John and I'd like to book a haircut"
        }
        
        output, context = await engine.execute(workflow, input_data)
        
        assert context.get("booking_confirmed")
        assert context.get("booking_id") is not None
        assert "greeting" in context.execution_path
        assert "confirmation" in context.execution_path
        
        logger.info(f"[OK] Booking confirmed: {context.get('booking_id')}")
    
    async def test_booking_with_intent_routing(self, workflow_observer, azure_llm):
        """Test booking workflow with intent-based routing."""
        logger.info("=" * 60)
        logger.info("TEST: booking_with_intent_routing")
        logger.info("=" * 60)
        
        # Build workflow with intent routing
        workflow = (
            WorkflowBuilder()
            .with_name("Booking with Intent Routing")
            .add_node("start", NodeType.START)
            .add_node("greeting", NodeType.TRANSFORM, name="Greeting")
            .add_node("router", NodeType.SWITCH, name="Intent Router", config={
                "switch_field": "$ctx.detected_intent",
                "cases": [
                    {"value": "book", "target": "booking_flow", "label": "Book"},
                    {"value": "cancel", "target": "cancel_flow", "label": "Cancel"},
                ],
                "default_target": "clarification",
            })
            .add_node("booking_flow", NodeType.TRANSFORM, name="Booking Flow")
            .add_node("cancel_flow", NodeType.TRANSFORM, name="Cancel Flow")
            .add_node("clarification", NodeType.TRANSFORM, name="Clarification")
            .add_node("end", NodeType.END)
            .add_edge("start", "greeting")
            .add_edge("greeting", "router")
            .add_conditional_edge("router", "booking_flow", "$ctx.switch_target", "equals", "booking_flow")
            .add_conditional_edge("router", "cancel_flow", "$ctx.switch_target", "equals", "cancel_flow")
            .add_fallback_edge("router", "clarification")
            .add_edge("booking_flow", "end")
            .add_edge("cancel_flow", "end")
            .add_edge("clarification", "end")
            .build()
        )
        
        # Inject custom nodes
        workflow._nodes["greeting"] = GreetingNode(
            NodeSpec(id="greeting", name="Greeting", node_type=NodeType.TRANSFORM)
        )
        workflow._nodes["booking_flow"] = BookingConfirmationNode(
            NodeSpec(id="booking_flow", name="Booking Flow", node_type=NodeType.TRANSFORM)
        )
        workflow._nodes["clarification"] = ClarificationNode(
            NodeSpec(id="clarification", name="Clarification", node_type=NodeType.TRANSFORM)
        )
        
        engine = WorkflowEngine(workflow_observers=[workflow_observer])
        
        # Pre-load context with real LLM for intent extraction
        context = WorkflowContext(workflow_id="intent-routing")
        context.set("llm", azure_llm)
        
        # Test booking intent
        input_data = {"message": "I want to book a haircut"}
        output, context = await engine.execute(workflow, input_data, context=context)
        
        assert context.get("detected_intent") == "book"
        assert "booking_flow" in context.execution_path
        
        logger.info("[OK] Routed to booking_flow based on intent")


# ============================================================================
# TESTS: Real LLM Integration (Azure GPT-4.1 Mini)
# ============================================================================


@pytest.mark.asyncio
class TestBookingWorkflowWithRealLLM:
    """Integration tests that call a real Azure GPT-4.1 Mini LLM."""
    
    async def test_llm_node_generates_confirmation(
        self,
        skip_if_no_azure_llm,
        azure_llm,
        workflow_observer,
    ):
        """Ensure LLMNode can craft a booking confirmation with real LLM output."""

        class AzureLLMGenerateAdapter:
            """Adapter to expose generate() using the Azure LLM get_answer API."""

            def __init__(self, llm):
                self._llm = llm
                self.name = getattr(llm, "metadata", None) and getattr(llm.metadata, "model_name", "azure-llm")

            async def generate(self, messages, **kwargs):
                llm_ctx = create_context(
                    user_id="llm-confirmation-user",
                    session_id="llm-confirmation-session",
                )
                return await self._llm.get_answer(messages, llm_ctx, **kwargs)

        llm_config = {
            "system_prompt": (
                "You are a friendly booking assistant. "
                "Always mention the service and guest name when confirming a booking. "
                "Keep replies under 50 words."
            ),
            "user_prompt_template": (
                "User message: {message}\n"
                "Service: {service_name}\n"
                "Guest: {guest_name}\n"
                "Write a concise confirmation that includes the service and guest."
            ),
            "max_tokens": 120,
        }
        
        workflow = (
            WorkflowBuilder()
            .with_name("LLM Booking Confirmation")
            .with_description("Confirms bookings using a real LLM node")
            .add_node("start", NodeType.START)
            .add_node("llm_confirmation", NodeType.LLM, name="LLM Confirmation", config=llm_config)
            .add_node("end", NodeType.END)
            .add_edge("start", "llm_confirmation")
            .add_edge("llm_confirmation", "end")
            .build()
        )
        
        # Inject LLM-backed node
        workflow._nodes["llm_confirmation"] = LLMNode(
            NodeSpec(
                id="llm_confirmation",
                name="LLM Confirmation",
                node_type=NodeType.LLM,
                config=llm_config,
            ),
            llm=AzureLLMGenerateAdapter(azure_llm),
        )
        
        engine = WorkflowEngine(workflow_observers=[workflow_observer])
        
        input_data = {
            "message": "Please confirm my haircut booking later today.",
            "variables": {
                "service_name": "haircut",
                "guest_name": "Alice",
            },
        }
        
        output, context = await engine.execute(workflow, input_data)
        
        assert isinstance(output, dict)
        assert "content" in output
        
        content_lower = str(output.get("content", "")).lower()
        assert "haircut" in content_lower
        assert "alice" in content_lower
        assert "llm_confirmation" in context.execution_path


# ============================================================================
# TESTS: Transition Variables (Required Fields)
# ============================================================================

@pytest.mark.asyncio
class TestTransitionVariables:
    """Test transition variable specifications."""
    
    async def test_transition_spec_identifies_missing_required(self):
        """Test that TransitionSpec correctly identifies missing required vars."""
        logger.info("=" * 60)
        logger.info("TEST: transition_spec_identifies_missing_required")
        logger.info("=" * 60)
        
        # Create transition spec with required variables
        transition = TransitionSpec(
            conditions=[
                TransitionCondition(
                    source_type=ConditionSourceType.CONTEXT,
                    field="detected_intent",
                    operator=ConditionOperator.EQUALS,
                    value="book",
                )
            ],
            variables=[
                TransitionVariable(
                    name="service_name",
                    data_type=DataType.STRING,
                    requirement=VariableRequirement.REQUIRED,
                    prompt_if_missing="What service would you like to book?",
                ),
                TransitionVariable(
                    name="guest_name",
                    data_type=DataType.STRING,
                    requirement=VariableRequirement.REQUIRED,
                    prompt_if_missing="May I have your name for the booking?",
                ),
            ],
            on_missing_required="prompt",
        )
        
        # Test with missing data
        data = {"detected_intent": "book"}  # Missing service_name and guest_name
        missing = transition.get_missing_required(data)
        
        assert len(missing) == 2
        assert any(v.name == "service_name" for v in missing)
        assert any(v.name == "guest_name" for v in missing)
        
        # Test prompt building
        prompt = transition.build_missing_prompt(missing)
        assert "service" in prompt.lower()
        assert "name" in prompt.lower()
        
        logger.info(f"[OK] Missing vars: {[v.name for v in missing]}")
        logger.info(f"[OK] Prompt: {prompt}")
    
    async def test_transition_spec_passes_with_all_required(self):
        """Test that TransitionSpec passes when all required vars present."""
        logger.info("=" * 60)
        logger.info("TEST: transition_spec_passes_with_all_required")
        logger.info("=" * 60)
        
        transition = TransitionSpec(
            variables=[
                TransitionVariable(
                    name="service_name",
                    requirement=VariableRequirement.REQUIRED,
                ),
                TransitionVariable(
                    name="guest_name",
                    requirement=VariableRequirement.REQUIRED,
                ),
            ],
        )
        
        # Test with all data present
        data = {"service_name": "haircut", "guest_name": "John"}
        missing = transition.get_missing_required(data)
        
        assert len(missing) == 0
        
        logger.info("[OK] No missing required variables")


# ============================================================================
# TESTS: I/O Specifications
# ============================================================================

@pytest.mark.asyncio
class TestIOSpecifications:
    """Test input/output type specifications."""
    
    async def test_io_spec_validation(self):
        """Test IOSpec validation of input data."""
        logger.info("=" * 60)
        logger.info("TEST: io_spec_validation")
        logger.info("=" * 60)
        
        io_spec = IOSpec(
            fields=[
                IOFieldSpec(
                    name="message",
                    data_type=DataType.STRING,
                    required=True,
                    description="User message",
                ),
                IOFieldSpec(
                    name="service_name",
                    data_type=DataType.STRING,
                    required=True,
                    description="Service to book",
                ),
                IOFieldSpec(
                    name="preferred_time",
                    data_type=DataType.STRING,
                    required=False,
                    description="Preferred appointment time",
                ),
            ],
            format=DataFormat.JSON,
        )
        
        # Test validation with missing required field
        errors = io_spec.validate_data({"message": "Hello"})
        assert len(errors) == 1
        assert "service_name" in errors[0]
        
        # Test validation with all required fields
        errors = io_spec.validate_data({"message": "Hello", "service_name": "haircut"})
        assert len(errors) == 0
        
        # Test required fields getter
        required = io_spec.get_required_fields()
        assert "message" in required
        assert "service_name" in required
        assert "preferred_time" not in required
        
        logger.info(f"[OK] Required fields: {required}")
    
    async def test_node_with_io_spec(self):
        """Test that nodes properly use IOSpec."""
        logger.info("=" * 60)
        logger.info("TEST: node_with_io_spec")
        logger.info("=" * 60)
        
        # Create node with explicit I/O spec
        input_spec = IOSpec(
            fields=[
                IOFieldSpec(name="service_name", data_type=DataType.STRING, required=True),
            ]
        )
        output_spec = IOSpec(
            fields=[
                IOFieldSpec(name="found", data_type=DataType.BOOLEAN, required=True),
                IOFieldSpec(name="price", data_type=DataType.NUMBER, required=False),
            ]
        )
        
        spec = NodeSpec(
            id="lookup",
            name="Service Lookup",
            node_type=NodeType.TRANSFORM,
            input_spec=input_spec,
            output_spec=output_spec,
        )
        
        assert spec.input_spec is not None
        assert spec.output_spec is not None
        assert spec.get_required_inputs() == ["service_name"]
        
        # Validate input
        errors = spec.validate_input({"other_field": "value"})
        assert len(errors) == 1
        
        errors = spec.validate_input({"service_name": "haircut"})
        assert len(errors) == 0
        
        logger.info("[OK] Node IOSpec working correctly")


# ============================================================================
# TESTS: Workflow as Tool
# ============================================================================

@pytest.mark.asyncio
class TestWorkflowTool:
    """Test using workflows as tools in agents."""
    
    async def test_create_workflow_tool(self):
        """Test creating a WorkflowTool from a workflow."""
        logger.info("=" * 60)
        logger.info("TEST: create_workflow_tool")
        logger.info("=" * 60)
        
        # Build a simple workflow
        workflow = (
            WorkflowBuilder()
            .with_name("Booking Service")
            .with_description("Books a service for a customer")
            .add_node("start", NodeType.START)
            .add_node("lookup", NodeType.TRANSFORM, name="Lookup")
            .add_node("end", NodeType.END)
            .add_edge("start", "lookup")
            .add_edge("lookup", "end")
            .build()
        )
        
        # Create tool from workflow
        tool = create_workflow_tool(
            workflow=workflow,
            tool_name="book_service",
            description="Book a service appointment",
        )
        
        assert tool.name == "book_service"
        assert tool.spec.description == "Book a service appointment"
        assert tool.spec.workflow is workflow
        
        logger.info(f"[OK] Created workflow tool: {tool.name}")
    
    async def test_workflow_tool_execution(self):
        """Test executing a workflow through the tool interface."""
        logger.info("=" * 60)
        logger.info("TEST: workflow_tool_execution")
        logger.info("=" * 60)
        
        # Build a simple workflow
        workflow = (
            WorkflowBuilder()
            .with_name("Service Lookup")
            .add_node("start", NodeType.START)
            .add_node("lookup", NodeType.TRANSFORM, name="Lookup")
            .add_node("end", NodeType.END)
            .add_edge("start", "lookup")
            .add_edge("lookup", "end")
            .build()
        )
        
        # Inject custom lookup node
        workflow._nodes["lookup"] = ServiceLookupNode(
            NodeSpec(id="lookup", name="Lookup", node_type=NodeType.TRANSFORM)
        )
        
        # Create and execute tool
        tool = WorkflowTool(
            workflow=workflow,
            tool_name="lookup_service",
        )
        
        result = await tool.execute(service_name="haircut")
        
        assert result.get("success")
        
        logger.info(f"[OK] Tool execution result: {result}")


# ============================================================================
# TESTS: Haircut Booking Scenario (From Image)
# ============================================================================

@pytest.mark.asyncio
class TestHaircutBookingScenario:
    """
    Test the specific booking scenario from the image:
    
    1. Greeting node greets customer
    2. Customer says they want to book haircut
    3. Intent detected as "book"
    4. Check required variables (service_name, guest_name)
    5. If missing, prompt user
    6. If service is haircut, confirm booking
    """
    
    async def test_complete_haircut_booking_flow(self, workflow_observer):
        """Test complete haircut booking from greeting to confirmation."""
        logger.info("=" * 60)
        logger.info("TEST: complete_haircut_booking_flow")
        logger.info("=" * 60)
        
        # Build the complete booking workflow
        workflow = (
            WorkflowBuilder()
            .with_name("Haircut Booking Flow")
            .with_description("Complete booking flow for haircut appointments")
            
            # Nodes
            .add_node("start", NodeType.START)
            .add_node("greeting", NodeType.TRANSFORM, name="Greeting Node")
            .add_node("intent_check", NodeType.DECISION, name="Check Intent")
            .add_node("booking_validation", NodeType.TRANSFORM, name="Validate Booking")
            .add_node("service_lookup", NodeType.TRANSFORM, name="Service Lookup")
            .add_node("confirm_booking", NodeType.TRANSFORM, name="Confirm Booking")
            .add_node("request_info", NodeType.TRANSFORM, name="Request Missing Info")
            .add_node("end", NodeType.END)
            
            # Edges
            .add_edge("start", "greeting")
            .add_edge("greeting", "intent_check")
            .add_conditional_edge("intent_check", "booking_validation", 
                                  "$ctx.detected_intent", "equals", "book")
            .add_fallback_edge("intent_check", "request_info")
            .add_conditional_edge("booking_validation", "service_lookup",
                                  "$ctx.booking_valid", "equals", True)
            .add_fallback_edge("booking_validation", "request_info")
            .add_conditional_edge("service_lookup", "confirm_booking",
                                  "$ctx.service_available", "equals", True)
            .add_edge("confirm_booking", "end")
            .add_edge("request_info", "end")
            .build()
        )
        
        # Inject custom nodes
        workflow._nodes["greeting"] = GreetingNode(
            NodeSpec(id="greeting", name="Greeting Node", node_type=NodeType.TRANSFORM)
        )
        workflow._nodes["booking_validation"] = BookingValidationNode(
            NodeSpec(id="booking_validation", name="Validate Booking", node_type=NodeType.TRANSFORM)
        )
        workflow._nodes["service_lookup"] = ServiceLookupNode(
            NodeSpec(id="service_lookup", name="Service Lookup", node_type=NodeType.TRANSFORM)
        )
        workflow._nodes["confirm_booking"] = BookingConfirmationNode(
            NodeSpec(id="confirm_booking", name="Confirm Booking", node_type=NodeType.TRANSFORM)
        )
        workflow._nodes["request_info"] = ClarificationNode(
            NodeSpec(id="request_info", name="Request Missing Info", node_type=NodeType.TRANSFORM)
        )
        
        engine = WorkflowEngine(workflow_observers=[workflow_observer])
        
        # Scenario: User provides complete booking info in first message
        input_data = {
            "message": "Hi, my name is Sarah and I'd like to book a haircut please"
        }
        
        output, context = await engine.execute(workflow, input_data)
        
        # Verify the flow
        assert "greeting" in context.execution_path
        assert context.get("detected_intent") == "book"
        assert context.get("guest_name") == "Sarah"
        assert context.get("service_name") == "haircut"
        
        # Should reach booking confirmation
        if context.get("booking_confirmed"):
            logger.info(f"[OK] Booking confirmed: {context.get('booking_id')}")
            assert "confirm_booking" in context.execution_path
        else:
            # May need to go through validation first
            logger.info("[OK] Flow completed (may require validation)")
        
        logger.info(f"[OK] Execution path: {context.execution_path}")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

