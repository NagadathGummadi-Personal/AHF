"""
Conversational AI Workflow Test.

This test demonstrates how to build a conversational AI workflow with 
intent-based routing similar to ElevenLabs' workflow structure.

Features tested:
1. Multiple agent nodes (Greeter, Booking, FAQ, Support)
2. Decision nodes for intent-based routing
3. Conditional edges with priority-based routing
4. Custom node types with factory registration
5. Workflow context and variable passing
6. Full workflow execution with observers
7. Multi-turn conversation simulation
"""

import pytest
from typing import Any, Dict, List, Optional
from datetime import datetime

from core.workflows import (
    # Builder and Engine
    WorkflowBuilder,
    WorkflowEngine,
    # Enums
    NodeType,
    EdgeType,
    ConditionOperator,
    # Spec Models
    NodeSpec,
    EdgeSpec,
    ConditionSpec,
    WorkflowContext,
    # Implementations
    Workflow,
    BaseNode,
    # Factories
    NodeFactory,
    # Interfaces
    INode,
    IWorkflowContext,
    IWorkflowObserver,
    INodeObserver,
)
from utils.logging.LoggerAdaptor import LoggerAdaptor

# Setup logger
logger = LoggerAdaptor.get_logger("tests.workflows.conversational")


# ============================================================================
# CUSTOM NODE TYPES - Intent-Based Routing Nodes
# ============================================================================

class GreeterNode(BaseNode):
    """
    Custom node for greeting users and passing input to intent classifier.
    
    This is the entry point of the conversation flow.
    """
    
    def __init__(self, spec: NodeSpec, first_message: Optional[str] = None):
        super().__init__(spec)
        logger.debug(f"[GREETER:INIT] Initializing GreeterNode: {spec.name}")
        self._first_message = first_message or self._config.get(
            "first_message", 
            "Hello! How can I help you today?"
        )
        logger.debug(f"[GREETER:INIT] First message: '{self._first_message[:50]}...'")
    
    async def execute(self, input_data: Any, context: IWorkflowContext) -> Any:
        """Execute the greeter node."""
        logger.info("+" + "-" * 68 + "+")
        logger.info(f"| [GREETER] Executing node: {self._name}".ljust(69) + "|")
        logger.info("+" + "-" * 68 + "+")
        
        # Check if new conversation
        is_new = context.get("is_new_conversation", True)
        user_name = context.get("user_name", "there")
        
        logger.info(f"[GREETER] is_new_conversation: {is_new}, user_name: {user_name}")
        
        # Generate greeting
        if is_new:
            greeting = self._first_message
            context.set("is_new_conversation", False)
            context.set("conversation_started_at", datetime.now().isoformat())
            logger.info(f"[GREETER] New conversation - using first message")
        else:
            greeting = f"Welcome back, {user_name}! How can I help you today?"
            logger.info(f"[GREETER] Returning user - personalized greeting")
        
        # Extract user input
        user_input = input_data.get("user_input", "") if isinstance(input_data, dict) else str(input_data)
        
        result = {
            "greeting": greeting,
            "user_input": user_input,
            "timestamp": datetime.now().isoformat(),
            "node_id": self._id,
        }
        
        logger.info(f"[GREETER:DONE] Greeting: '{greeting[:50]}...', Input: '{user_input[:30]}...'")
        return result


class IntentClassifierNode(BaseNode):
    """
    Custom node for classifying user intent.
    
    Determines which specialized agent should handle the request.
    Uses keyword-based classification (can be replaced with LLM-based).
    """
    
    INTENTS = [
        "booking",        # Scheduling appointments
        "faq",            # General questions
        "support",        # Technical support
        "feedback",       # Feedback/complaints
        "transfer",       # Transfer to human
        "goodbye",        # End conversation
        "unknown",        # Cannot determine
    ]
    
    def __init__(self, spec: NodeSpec, intent_keywords: Optional[Dict[str, List[str]]] = None):
        super().__init__(spec)
        logger.debug(f"[INTENT:INIT] Initializing IntentClassifierNode: {spec.name}")
        self._intent_keywords = intent_keywords or {
            "booking": ["book", "schedule", "appointment", "reserve", "meeting", "calendar"],
            "faq": ["question", "what is", "how do", "tell me", "explain", "info", "hours", "location", "pricing"],
            "support": ["help", "problem", "issue", "error", "broken", "not working", "fix"],
            "feedback": ["feedback", "complaint", "suggest", "review", "rate"],
            "transfer": ["human", "agent", "person", "operator", "representative"],
            "goodbye": ["bye", "goodbye", "end", "quit", "exit", "done", "thank you"],
        }
        logger.debug(f"[INTENT:INIT] Configured {len(self._intent_keywords)} intent categories")
    
    async def execute(self, input_data: Any, context: IWorkflowContext) -> Any:
        """Classify the user's intent."""
        logger.info("+" + "-" * 68 + "+")
        logger.info(f"| [INTENT] Executing node: {self._name}".ljust(69) + "|")
        logger.info("+" + "-" * 68 + "+")
        
        # Extract user input
        user_input = ""
        if isinstance(input_data, dict):
            user_input = input_data.get("user_input", "")
        elif isinstance(input_data, str):
            user_input = input_data
        
        logger.info(f"[INTENT] User input: '{user_input[:60]}...'")
        
        user_input_lower = user_input.lower()
        
        # Keyword-based classification
        detected_intent = "unknown"
        confidence = 0.0
        matched_keyword = None
        
        for intent, keywords in self._intent_keywords.items():
            for keyword in keywords:
                if keyword in user_input_lower:
                    detected_intent = intent
                    confidence = 0.8
                    matched_keyword = keyword
                    logger.info(f"[INTENT] MATCH! keyword='{keyword}' -> intent='{intent}'")
                    break
            if detected_intent != "unknown":
                break
        
        # Fallback to FAQ for non-trivial input
        if detected_intent == "unknown" and len(user_input) > 5:
            detected_intent = "faq"
            confidence = 0.5
            logger.info(f"[INTENT] Fallback to 'faq' for unknown input")
        
        # Store in context for routing
        context.set("detected_intent", detected_intent)
        context.set("intent_confidence", confidence)
        
        result = {
            "intent": detected_intent,
            "confidence": confidence,
            "user_input": user_input,
            "matched_keyword": matched_keyword,
            "available_intents": self.INTENTS,
        }
        
        logger.info(f"[INTENT:DONE] Intent: '{detected_intent}' (confidence: {confidence:.2f})")
        return result


class BookingAgentNode(BaseNode):
    """
    Specialized agent node for handling booking requests.
    """
    
    def __init__(self, spec: NodeSpec):
        super().__init__(spec)
        logger.debug(f"[BOOKING:INIT] Initializing BookingAgentNode: {spec.name}")
        self._available_slots = self._config.get("available_slots", [
            "Monday 10:00 AM",
            "Monday 2:00 PM", 
            "Tuesday 11:00 AM",
            "Wednesday 3:00 PM",
            "Friday 9:00 AM",
        ])
        logger.debug(f"[BOOKING:INIT] Configured {len(self._available_slots)} available slots")
    
    async def execute(self, input_data: Any, context: IWorkflowContext) -> Any:
        """Handle booking request."""
        logger.info("+" + "-" * 68 + "+")
        logger.info(f"| [BOOKING] Executing node: {self._name}".ljust(69) + "|")
        logger.info("+" + "-" * 68 + "+")
        
        user_input = input_data.get("user_input", "") if isinstance(input_data, dict) else str(input_data)
        
        slots_to_offer = self._available_slots[:3]
        response = f"I'd be happy to help you book an appointment. Here are our available slots: {', '.join(slots_to_offer)}. Which would you prefer?"
        
        result = {
            "response": response,
            "available_slots": self._available_slots,
            "action": "booking_offered",
            "user_input": user_input,
        }
        
        logger.info(f"[BOOKING:DONE] Offered {len(self._available_slots)} slots")
        return result


class FAQAgentNode(BaseNode):
    """
    Specialized agent node for handling FAQ/general questions.
    """
    
    def __init__(self, spec: NodeSpec):
        super().__init__(spec)
        logger.debug(f"[FAQ:INIT] Initializing FAQAgentNode: {spec.name}")
        self._knowledge_base = self._config.get("knowledge_base", {
            "hours": "We're open Monday to Friday, 9 AM to 5 PM.",
            "location": "We're located at 123 Main Street, Suite 100.",
            "contact": "You can reach us at support@example.com or call 1-800-EXAMPLE.",
            "pricing": "Our pricing starts at $99/month. Visit our website for full details.",
        })
        logger.debug(f"[FAQ:INIT] Knowledge base topics: {list(self._knowledge_base.keys())}")
    
    async def execute(self, input_data: Any, context: IWorkflowContext) -> Any:
        """Answer FAQ question."""
        logger.info("+" + "-" * 68 + "+")
        logger.info(f"| [FAQ] Executing node: {self._name}".ljust(69) + "|")
        logger.info("+" + "-" * 68 + "+")
        
        user_input = input_data.get("user_input", "") if isinstance(input_data, dict) else str(input_data)
        user_input_lower = user_input.lower()
        
        response = "I'm not sure about that. Let me transfer you to someone who can help better."
        matched_topic = None
        
        for topic, answer in self._knowledge_base.items():
            if topic in user_input_lower:
                response = answer
                matched_topic = topic
                logger.info(f"[FAQ] MATCH! topic='{topic}'")
                break
        
        action = "faq_answered" if matched_topic else "faq_not_found"
        
        result = {
            "response": response,
            "matched_topic": matched_topic,
            "action": action,
            "user_input": user_input,
        }
        
        logger.info(f"[FAQ:DONE] Topic: {matched_topic}, Action: {action}")
        return result


class SupportAgentNode(BaseNode):
    """
    Specialized agent node for handling support requests.
    """
    
    def __init__(self, spec: NodeSpec):
        super().__init__(spec)
        logger.debug(f"[SUPPORT:INIT] Initializing SupportAgentNode: {spec.name}")
        self._escalation_keywords = self._config.get("escalation_keywords", [
            "urgent", "critical", "immediately", "emergency"
        ])
        logger.debug(f"[SUPPORT:INIT] Escalation keywords: {self._escalation_keywords}")
    
    async def execute(self, input_data: Any, context: IWorkflowContext) -> Any:
        """Handle support request."""
        logger.info("+" + "-" * 68 + "+")
        logger.info(f"| [SUPPORT] Executing node: {self._name}".ljust(69) + "|")
        logger.info("+" + "-" * 68 + "+")
        
        user_input = input_data.get("user_input", "") if isinstance(input_data, dict) else str(input_data)
        user_input_lower = user_input.lower()
        
        # Check for escalation
        matched_keywords = [kw for kw in self._escalation_keywords if kw in user_input_lower]
        needs_escalation = len(matched_keywords) > 0
        
        if needs_escalation:
            response = "I understand this is urgent. Let me connect you with a senior support specialist right away."
            action = "escalated"
        else:
            response = "I'm here to help! Could you please describe the issue you're experiencing in more detail?"
            action = "support_started"
        
        # Create support ticket
        ticket_id = f"TKT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        context.set("support_ticket_id", ticket_id)
        
        result = {
            "response": response,
            "action": action,
            "ticket_id": ticket_id,
            "needs_escalation": needs_escalation,
            "user_input": user_input,
        }
        
        logger.info(f"[SUPPORT:DONE] Ticket: {ticket_id}, Action: {action}, Escalated: {needs_escalation}")
        return result


class GoodbyeNode(BaseNode):
    """
    Node for ending conversations gracefully.
    """
    
    def __init__(self, spec: NodeSpec):
        super().__init__(spec)
        logger.debug(f"[GOODBYE:INIT] Initializing GoodbyeNode: {spec.name}")
        self._farewell_messages = self._config.get("farewell_messages", [
            "Thank you for contacting us! Have a great day!",
            "Goodbye! Feel free to reach out if you need anything else.",
            "Take care! We're always here to help.",
        ])
    
    async def execute(self, input_data: Any, context: IWorkflowContext) -> Any:
        """Say goodbye to user."""
        logger.info("+" + "-" * 68 + "+")
        logger.info(f"| [GOODBYE] Executing node: {self._name}".ljust(69) + "|")
        logger.info("+" + "-" * 68 + "+")
        
        response = self._farewell_messages[0]
        context.set("conversation_ended", True)
        context.set("conversation_ended_at", datetime.now().isoformat())
        
        result = {
            "response": response,
            "action": "conversation_ended",
        }
        
        logger.info(f"[GOODBYE:DONE] Conversation ended")
        return result


class ResponseFormatterNode(BaseNode):
    """
    Node for formatting the final response.
    
    Adds optional closing message and formats output consistently.
    """
    
    def __init__(self, spec: NodeSpec):
        super().__init__(spec)
        logger.debug(f"[FORMATTER:INIT] Initializing ResponseFormatterNode: {spec.name}")
        self._add_closing = self._config.get("add_closing", True)
        self._closing_message = self._config.get("closing_message", "Is there anything else I can help you with?")
    
    async def execute(self, input_data: Any, context: IWorkflowContext) -> Any:
        """Format the response for output."""
        logger.info("+" + "-" * 68 + "+")
        logger.info(f"| [FORMATTER] Executing node: {self._name}".ljust(69) + "|")
        logger.info("+" + "-" * 68 + "+")
        
        # Extract response from input
        response = ""
        if isinstance(input_data, dict):
            response = input_data.get("response", str(input_data))
        else:
            response = str(input_data)
        
        # Add closing message if appropriate
        detected_intent = context.get("detected_intent")
        formatted_response = response
        
        if self._add_closing and detected_intent not in ["goodbye", "transfer"]:
            formatted_response = f"{response} {self._closing_message}"
            logger.info(f"[FORMATTER] Added closing message")
        
        result = {
            "text": formatted_response,
            "intent": detected_intent,
            "conversation_id": context.execution_id,
        }
        
        logger.info(f"[FORMATTER:DONE] Response length: {len(formatted_response)} chars")
        return result


# ============================================================================
# OBSERVERS FOR TRACKING
# ============================================================================

class ConversationObserver(IWorkflowObserver):
    """Observer that tracks conversation flow."""
    
    def __init__(self):
        self.events: List[Dict[str, Any]] = []
        logger.debug("[WORKFLOW_OBS:INIT] ConversationObserver initialized")
    
    async def on_workflow_start(
        self, workflow: Any, input_data: Any, context: IWorkflowContext
    ) -> None:
        event = {
            "event": "workflow_start",
            "workflow_name": workflow.name,
            "timestamp": datetime.now().isoformat(),
            "input": str(input_data)[:100],
        }
        self.events.append(event)
        logger.info("=" * 70)
        logger.info(f"[WORKFLOW_OBS] >>> WORKFLOW START: {workflow.name}")
        logger.info(f"[WORKFLOW_OBS]     Execution ID: {context.execution_id}")
        logger.info("=" * 70)
    
    async def on_workflow_complete(
        self, workflow: Any, output: Any, context: IWorkflowContext, duration_ms: float
    ) -> None:
        event = {
            "event": "workflow_complete",
            "workflow_name": workflow.name,
            "timestamp": datetime.now().isoformat(),
            "duration_ms": duration_ms,
        }
        self.events.append(event)
        logger.info("=" * 70)
        logger.info(f"[WORKFLOW_OBS] <<< WORKFLOW COMPLETE: {workflow.name}")
        logger.info(f"[WORKFLOW_OBS]     Duration: {duration_ms:.2f}ms")
        logger.info(f"[WORKFLOW_OBS]     Path: {' -> '.join(context.execution_path)}")
        logger.info("=" * 70)
    
    async def on_workflow_error(
        self, workflow: Any, error: Exception, context: IWorkflowContext
    ) -> None:
        self.events.append({"event": "workflow_error", "error": str(error)})
        logger.error(f"[WORKFLOW_OBS] !!! ERROR: {error}")
    
    async def on_workflow_pause(self, workflow: Any, context: IWorkflowContext) -> None:
        self.events.append({"event": "workflow_pause"})
    
    async def on_workflow_resume(self, workflow: Any, context: IWorkflowContext) -> None:
        self.events.append({"event": "workflow_resume"})
    
    async def on_workflow_cancel(self, workflow: Any, context: IWorkflowContext) -> None:
        self.events.append({"event": "workflow_cancel"})


class NodeTrackingObserver(INodeObserver):
    """Observer that tracks node executions."""
    
    def __init__(self):
        self.node_executions: List[Dict[str, Any]] = []
        logger.debug("[NODE_OBS:INIT] NodeTrackingObserver initialized")
    
    async def on_node_start(
        self, node: INode, input_data: Any, context: IWorkflowContext
    ) -> None:
        logger.info(f"[NODE_OBS] >>> NODE START: {node.name} (type={node.node_type.value})")
    
    async def on_node_complete(
        self, node: INode, output: Any, context: IWorkflowContext, duration_ms: float
    ) -> None:
        record = {
            "node_id": node.id,
            "node_name": node.name,
            "node_type": node.node_type.value,
            "duration_ms": duration_ms,
        }
        self.node_executions.append(record)
        logger.info(f"[NODE_OBS] <<< NODE COMPLETE: {node.name} ({duration_ms:.2f}ms)")
    
    async def on_node_error(
        self, node: INode, error: Exception, context: IWorkflowContext
    ) -> None:
        self.node_executions.append({"node_id": node.id, "error": str(error)})
        logger.error(f"[NODE_OBS] !!! NODE ERROR: {node.name} - {error}")
    
    async def on_node_skip(
        self, node: INode, reason: str, context: IWorkflowContext
    ) -> None:
        self.node_executions.append({"node_id": node.id, "skipped": True, "reason": reason})
        logger.info(f"[NODE_OBS] --- NODE SKIPPED: {node.name} ({reason})")


# ============================================================================
# NODE FACTORY REGISTRATION
# ============================================================================

def register_custom_nodes() -> NodeFactory:
    """Register all custom node types with the factory."""
    logger.info("+" + "=" * 68 + "+")
    logger.info("| REGISTERING CUSTOM NODE TYPES".ljust(69) + "|")
    logger.info("+" + "=" * 68 + "+")
    
    factory = NodeFactory()
    
    custom_nodes = [
        ("greeter", GreeterNode, "Greeter Agent", "Greets users and initiates conversation"),
        ("intent_classifier", IntentClassifierNode, "Intent Classifier", "Classifies user intent for routing"),
        ("booking_agent", BookingAgentNode, "Booking Agent", "Handles appointment bookings"),
        ("faq_agent", FAQAgentNode, "FAQ Agent", "Answers frequently asked questions"),
        ("support_agent", SupportAgentNode, "Support Agent", "Handles support requests"),
        ("goodbye_agent", GoodbyeNode, "Goodbye Agent", "Ends conversations gracefully"),
        ("response_formatter", ResponseFormatterNode, "Response Formatter", "Formats final response"),
    ]
    
    for type_id, node_class, display_name, description in custom_nodes:
        logger.info(f"[FACTORY] Registering: {type_id} ({display_name})")
        factory.register_custom(
            type_id=type_id,
            node_class=node_class,
            display_name=display_name,
            description=description,
            # IMPORTANT: cls=node_class captures current loop value; removing it causes
            # all factories to use the last class (ResponseFormatterNode) due to closure
            factory_func=lambda spec, cls=node_class, **kwargs: cls(spec, **kwargs),
        )
    
    logger.info(f"[FACTORY] Registered {len(custom_nodes)} custom node types")
    logger.info("+" + "=" * 68 + "+")
    
    return factory


# ============================================================================
# HELPER: Build Conversational Workflow
# ============================================================================

def build_conversational_workflow(
    name: str = "Conversational Agent",
    first_message: str = "Hello! How can I help you today?"
) -> Workflow:
    """
    Build a complete conversational workflow with intent-based routing.
    
    Workflow Structure:
        start -> greeter -> intent_classifier -> [booking|faq|support|goodbye] -> formatter -> end
    """
    workflow = (
        WorkflowBuilder()
        .with_name(name)
        .with_description("Intent-based conversational AI workflow")
        .with_max_iterations(50)
        # Nodes
        .add_node("start", NodeType.START)
        .add_node("greeter", NodeType.AGENT, name="Greeter", config={"first_message": first_message})
        .add_node("intent", NodeType.DECISION, name="Intent Classifier")
        .add_node("booking", NodeType.AGENT, name="Booking Agent")
        .add_node("faq", NodeType.AGENT, name="FAQ Agent")
        .add_node("support", NodeType.AGENT, name="Support Agent")
        .add_node("goodbye", NodeType.AGENT, name="Goodbye Agent")
        .add_node("formatter", NodeType.TRANSFORM, name="Response Formatter")
        .add_node("end", NodeType.END)
        # Flow: start -> greeter -> intent
        .add_edge("start", "greeter")
        .add_edge("greeter", "intent")
        # Intent routing with priorities
        .add_conditional_edge("intent", "booking", "$ctx.detected_intent", "equals", "booking", priority=10)
        .add_conditional_edge("intent", "faq", "$ctx.detected_intent", "equals", "faq", priority=10)
        .add_conditional_edge("intent", "support", "$ctx.detected_intent", "equals", "support", priority=10)
        .add_conditional_edge("intent", "goodbye", "$ctx.detected_intent", "equals", "goodbye", priority=10)
        .add_fallback_edge("intent", "faq", id="intent_faq_fallback")
        # All paths to formatter (except goodbye goes to end)
        .add_edge("booking", "formatter")
        .add_edge("faq", "formatter")
        .add_edge("support", "formatter")
        .add_edge("goodbye", "end")
        .add_edge("formatter", "end")
        .build()
    )
    
    # Inject custom node implementations
    workflow._nodes["greeter"] = GreeterNode(
        NodeSpec(id="greeter", name="Greeter", node_type=NodeType.AGENT),
        first_message=first_message
    )
    workflow._nodes["intent"] = IntentClassifierNode(
        NodeSpec(id="intent", name="Intent Classifier", node_type=NodeType.DECISION)
    )
    workflow._nodes["booking"] = BookingAgentNode(
        NodeSpec(id="booking", name="Booking Agent", node_type=NodeType.AGENT)
    )
    workflow._nodes["faq"] = FAQAgentNode(
        NodeSpec(id="faq", name="FAQ Agent", node_type=NodeType.AGENT)
    )
    workflow._nodes["support"] = SupportAgentNode(
        NodeSpec(id="support", name="Support Agent", node_type=NodeType.AGENT)
    )
    workflow._nodes["goodbye"] = GoodbyeNode(
        NodeSpec(id="goodbye", name="Goodbye Agent", node_type=NodeType.AGENT)
    )
    workflow._nodes["formatter"] = ResponseFormatterNode(
        NodeSpec(id="formatter", name="Response Formatter", node_type=NodeType.TRANSFORM)
    )
    
    return workflow


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def custom_node_factory():
    """Create and register custom node factory."""
    return register_custom_nodes()


@pytest.fixture
def workflow_observer():
    """Create workflow observer for testing."""
    return ConversationObserver()


@pytest.fixture
def node_observer():
    """Create node observer for testing."""
    return NodeTrackingObserver()


@pytest.fixture
def conversational_workflow():
    """Create a pre-built conversational workflow."""
    return build_conversational_workflow()


# ============================================================================
# TESTS: WorkflowBuilder
# ============================================================================

@pytest.mark.asyncio
class TestWorkflowBuilder:
    """Test WorkflowBuilder functionality."""
    
    async def test_simple_workflow_creation(self):
        """Test creating a simple start -> end workflow."""
        logger.info("+" + "=" * 68 + "+")
        logger.info("| TEST: simple_workflow_creation".ljust(69) + "|")
        logger.info("+" + "=" * 68 + "+")
        
        workflow = (
            WorkflowBuilder()
            .with_name("Simple Test Workflow")
            .with_description("A minimal workflow for testing")
            .add_node("start", NodeType.START, name="Begin")
            .add_node("end", NodeType.END, name="Finish")
            .add_edge("start", "end")
            .build()
        )
        
        assert workflow is not None
        assert workflow.name == "Simple Test Workflow"
        assert len(workflow.nodes) == 2
        logger.info(f"[OK] Created workflow: {workflow.name}")
        logger.info(f"[OK] Nodes: {len(workflow.nodes)}, Edges: {len(workflow.edges)}")
    
    async def test_workflow_with_decision_node(self):
        """Test workflow with conditional routing."""
        logger.info("+" + "=" * 68 + "+")
        logger.info("| TEST: workflow_with_decision_node".ljust(69) + "|")
        logger.info("+" + "=" * 68 + "+")
        
        workflow = (
            WorkflowBuilder()
            .with_name("Decision Workflow")
            .add_node("start", NodeType.START)
            .add_node("check", NodeType.DECISION, config={
                "conditions": [{"field": "value", "operator": "greater_than", "value": 10}]
            })
            .add_node("high", NodeType.TRANSFORM, name="High Value Handler")
            .add_node("low", NodeType.TRANSFORM, name="Low Value Handler")
            .add_node("end", NodeType.END)
            .add_edge("start", "check")
            .add_conditional_edge("check", "high", field="decision_result", operator="equals", value=True)
            .add_fallback_edge("check", "low")
            .add_edge("high", "end")
            .add_edge("low", "end")
            .build()
        )
        
        assert workflow is not None
        assert len(workflow.nodes) == 5
        assert len(workflow.edges) == 5
        logger.info(f"[OK] Decision workflow created with {len(workflow.nodes)} nodes")


# ============================================================================
# TESTS: Custom Node Implementations
# ============================================================================

@pytest.mark.asyncio
class TestCustomNodes:
    """Test custom node implementations."""
    
    async def test_greeter_node(self):
        """Test the greeter node execution."""
        logger.info("+" + "=" * 68 + "+")
        logger.info("| TEST: greeter_node".ljust(69) + "|")
        logger.info("+" + "=" * 68 + "+")
        
        spec = NodeSpec(
            id="greeter_test",
            name="Test Greeter",
            node_type=NodeType.AGENT,
            config={"first_message": "Welcome to our service!"}
        )
        
        node = GreeterNode(spec, first_message="Welcome to our service!")
        context = WorkflowContext(workflow_id="test_workflow")
        
        result = await node.execute({"user_input": "Hello"}, context)
        
        assert "greeting" in result
        assert result["greeting"] == "Welcome to our service!"
        assert context.get("is_new_conversation") == False
        logger.info(f"[OK] Greeter result: {result['greeting']}")
    
    async def test_intent_classifier_node(self):
        """Test the intent classifier node with various inputs."""
        logger.info("+" + "=" * 68 + "+")
        logger.info("| TEST: intent_classifier_node".ljust(69) + "|")
        logger.info("+" + "=" * 68 + "+")
        
        spec = NodeSpec(
            id="intent_test",
            name="Test Intent Classifier",
            node_type=NodeType.DECISION,
        )
        
        node = IntentClassifierNode(spec)
        
        test_cases = [
            ("I want to book an appointment", "booking"),
            ("What are your hours?", "faq"),
            ("I have a problem with my account", "support"),
            ("goodbye", "goodbye"),
            ("connect me to a human", "transfer"),
        ]
        
        for user_input, expected_intent in test_cases:
            context = WorkflowContext(workflow_id="test")
            result = await node.execute({"user_input": user_input}, context)
            logger.info(f"[TEST] '{user_input[:30]}...' -> {result['intent']}")
            assert result["intent"] == expected_intent, f"Expected {expected_intent}, got {result['intent']}"
        
        logger.info(f"[OK] All {len(test_cases)} intent tests passed")
    
    async def test_booking_agent_node(self):
        """Test the booking agent node."""
        logger.info("+" + "=" * 68 + "+")
        logger.info("| TEST: booking_agent_node".ljust(69) + "|")
        logger.info("+" + "=" * 68 + "+")
        
        spec = NodeSpec(
            id="booking_test",
            name="Test Booking Agent",
            node_type=NodeType.AGENT,
            config={"available_slots": ["Monday 10AM", "Tuesday 2PM"]}
        )
        
        node = BookingAgentNode(spec)
        context = WorkflowContext(workflow_id="test")
        
        result = await node.execute({"user_input": "I want to book"}, context)
        
        assert "response" in result
        assert "available_slots" in result
        assert result["action"] == "booking_offered"
        logger.info(f"[OK] Booking response: {result['response'][:50]}...")
    
    async def test_faq_agent_node(self):
        """Test the FAQ agent node with known topics."""
        logger.info("+" + "=" * 68 + "+")
        logger.info("| TEST: faq_agent_node".ljust(69) + "|")
        logger.info("+" + "=" * 68 + "+")
        
        spec = NodeSpec(id="faq_test", name="Test FAQ Agent", node_type=NodeType.AGENT)
        node = FAQAgentNode(spec)
        context = WorkflowContext(workflow_id="test")
        
        result = await node.execute({"user_input": "What are your hours?"}, context)
        
        assert result["matched_topic"] == "hours"
        assert result["action"] == "faq_answered"
        logger.info(f"[OK] FAQ matched topic: {result['matched_topic']}")
    
    async def test_support_agent_escalation(self):
        """Test support agent escalation for urgent issues."""
        logger.info("+" + "=" * 68 + "+")
        logger.info("| TEST: support_agent_escalation".ljust(69) + "|")
        logger.info("+" + "=" * 68 + "+")
        
        spec = NodeSpec(id="support_test", name="Test Support Agent", node_type=NodeType.AGENT)
        node = SupportAgentNode(spec)
        context = WorkflowContext(workflow_id="test")
        
        # Test urgent escalation
        result = await node.execute({"user_input": "This is urgent! My account is broken!"}, context)
        
        assert result["needs_escalation"] == True
        assert result["action"] == "escalated"
        assert context.get("support_ticket_id") is not None
        logger.info(f"[OK] Urgent issue escalated, ticket: {result['ticket_id']}")


# ============================================================================
# TESTS: Workflow Execution
# ============================================================================

@pytest.mark.asyncio
class TestWorkflowExecution:
    """Test complete workflow execution."""
    
    async def test_booking_intent_workflow(self, workflow_observer, node_observer):
        """Test full workflow with booking intent."""
        logger.info("+" + "=" * 68 + "+")
        logger.info("| TEST: booking_intent_workflow".ljust(69) + "|")
        logger.info("+" + "=" * 68 + "+")
        
        workflow = build_conversational_workflow()
        
        engine = WorkflowEngine(
            workflow_observers=[workflow_observer],
            node_observers=[node_observer],
        )
        
        input_data = {"user_input": "I want to book an appointment for next week"}
        output, final_context = await engine.execute(workflow, input_data)
        
        # Verify routing
        assert final_context.get("detected_intent") == "booking"
        assert "greeter" in final_context.execution_path
        assert "intent" in final_context.execution_path
        assert "booking" in final_context.execution_path
        assert "formatter" in final_context.execution_path
        
        # Verify output
        assert output is not None
        assert isinstance(output, dict)
        assert "text" in output
        
        logger.info(f"[OK] Booking workflow completed successfully")
        logger.info(f"[OK] Execution path: {' -> '.join(final_context.execution_path)}")
    
    async def test_support_intent_workflow(self, workflow_observer, node_observer):
        """Test workflow with support intent."""
        logger.info("+" + "=" * 68 + "+")
        logger.info("| TEST: support_intent_workflow".ljust(69) + "|")
        logger.info("+" + "=" * 68 + "+")
        
        workflow = build_conversational_workflow()
        
        engine = WorkflowEngine(
            workflow_observers=[workflow_observer],
            node_observers=[node_observer],
        )
        
        input_data = {"user_input": "I have a problem with my account, it's not working"}
        output, context = await engine.execute(workflow, input_data)
        
        assert context.get("detected_intent") == "support"
        assert "support" in context.execution_path
        assert context.get("support_ticket_id") is not None
        
        logger.info(f"[OK] Support ticket created: {context.get('support_ticket_id')}")
    
    async def test_faq_intent_workflow(self, workflow_observer, node_observer):
        """Test workflow with FAQ intent."""
        logger.info("+" + "=" * 68 + "+")
        logger.info("| TEST: faq_intent_workflow".ljust(69) + "|")
        logger.info("+" + "=" * 68 + "+")
        
        workflow = build_conversational_workflow()
        engine = WorkflowEngine()
        
        input_data = {"user_input": "What are your business hours?"}
        output, context = await engine.execute(workflow, input_data)
        
        assert context.get("detected_intent") == "faq"
        assert "faq" in context.execution_path
        
        logger.info(f"[OK] FAQ workflow completed")
    
    async def test_goodbye_intent_workflow(self, workflow_observer, node_observer):
        """Test workflow with goodbye intent (should skip formatter)."""
        logger.info("+" + "=" * 68 + "+")
        logger.info("| TEST: goodbye_intent_workflow".ljust(69) + "|")
        logger.info("+" + "=" * 68 + "+")
        
        workflow = build_conversational_workflow()
        engine = WorkflowEngine()
        
        input_data = {"user_input": "goodbye, thank you!"}
        output, context = await engine.execute(workflow, input_data)
        
        assert context.get("detected_intent") == "goodbye"
        assert "goodbye" in context.execution_path
        # Goodbye should go directly to end, not through formatter
        assert "formatter" not in context.execution_path
        assert context.get("conversation_ended") == True
        
        logger.info(f"[OK] Goodbye workflow completed, conversation ended")


# ============================================================================
# TESTS: Edge Conditions
# ============================================================================

@pytest.mark.asyncio
class TestEdgeConditions:
    """Test edge conditions and routing."""
    
    async def test_conditional_edge_evaluation(self):
        """Test that conditional edges evaluate correctly."""
        logger.info("+" + "=" * 68 + "+")
        logger.info("| TEST: conditional_edge_evaluation".ljust(69) + "|")
        logger.info("+" + "=" * 68 + "+")
        
        from core.workflows.edges import ConditionalEdge
        
        spec = EdgeSpec(
            id="test_edge",
            source_id="a",
            target_id="b",
            edge_type=EdgeType.CONDITIONAL,
            conditions=[
                ConditionSpec(
                    field="$ctx.intent",
                    operator=ConditionOperator.EQUALS,
                    value="booking",
                )
            ]
        )
        
        edge = ConditionalEdge(spec)
        
        # Test matching condition
        context_match = WorkflowContext(workflow_id="test")
        context_match.set("intent", "booking")
        assert edge.can_traverse(context_match) == True
        logger.info("[OK] Edge traversable when intent='booking'")
        
        # Test non-matching condition
        context_no_match = WorkflowContext(workflow_id="test")
        context_no_match.set("intent", "support")
        assert edge.can_traverse(context_no_match) == False
        logger.info("[OK] Edge not traversable when intent='support'")


# ============================================================================
# TESTS: Node Factory
# ============================================================================

@pytest.mark.asyncio  
class TestNodeFactory:
    """Test node factory registration and creation."""
    
    async def test_register_and_create_custom_node(self, custom_node_factory):
        """Test registering and creating custom nodes."""
        logger.info("+" + "=" * 68 + "+")
        logger.info("| TEST: register_and_create_custom_node".ljust(69) + "|")
        logger.info("+" + "=" * 68 + "+")
        
        # Check custom types are registered
        assert custom_node_factory.is_registered("greeter")
        assert custom_node_factory.is_registered("intent_classifier")
        assert custom_node_factory.is_registered("booking_agent")
        assert custom_node_factory.is_registered("faq_agent")
        assert custom_node_factory.is_registered("support_agent")
        
        logger.info("[OK] All custom types registered successfully")
        
        # Create node via factory
        registration = custom_node_factory.get_registration("greeter")
        assert registration is not None
        
        spec = NodeSpec(id="factory_greeter", name="Factory Greeter", node_type=NodeType.CUSTOM)
        node = registration.factory_func(spec)
        
        assert node is not None
        assert isinstance(node, GreeterNode)
        logger.info(f"[OK] Created node via factory: {node.name}")


# ============================================================================
# TESTS: Streaming Execution
# ============================================================================

@pytest.mark.asyncio
class TestWorkflowStreaming:
    """Test workflow streaming execution."""
    
    async def test_streaming_execution(self):
        """Test streaming workflow execution."""
        logger.info("+" + "=" * 68 + "+")
        logger.info("| TEST: streaming_execution".ljust(69) + "|")
        logger.info("+" + "=" * 68 + "+")
        
        workflow = (
            WorkflowBuilder()
            .with_name("Streaming Test")
            .add_node("start", NodeType.START)
            .add_node("transform", NodeType.TRANSFORM, config={"transform_type": "pass_through"})
            .add_node("end", NodeType.END)
            .add_edge("start", "transform")
            .add_edge("transform", "end")
            .build()
        )
        
        engine = WorkflowEngine()
        
        stream_results = []
        async for node_id, output, context in engine.execute_streaming(workflow, {"data": "test"}):
            stream_results.append({"node_id": node_id, "has_output": output is not None})
            logger.info(f"[STREAM] Node completed: {node_id}")
        
        assert len(stream_results) >= 2
        logger.info(f"[OK] Streaming completed with {len(stream_results)} results")


# ============================================================================
# TESTS: Multi-Turn Conversation
# ============================================================================

@pytest.mark.asyncio
class TestMultiTurnConversation:
    """Test multi-turn conversation scenarios."""
    
    async def test_multi_turn_conversation(self, workflow_observer, node_observer):
        """Test a multi-turn conversation through the workflow."""
        logger.info("+" + "=" * 68 + "+")
        logger.info("| TEST: multi_turn_conversation".ljust(69) + "|")
        logger.info("+" + "=" * 68 + "+")
        
        workflow = build_conversational_workflow(
            name="Multi-Turn Test",
            first_message="Welcome! How can I assist you?"
        )
        
        engine = WorkflowEngine(
            workflow_observers=[workflow_observer],
            node_observers=[node_observer],
        )
        
        # Simulate multiple conversation turns
        conversation_turns = [
            {"user_input": "Hello, I need some help", "expected_intent": "support"},
            {"user_input": "What are your business hours?", "expected_intent": "faq"},
            {"user_input": "I want to schedule an appointment", "expected_intent": "booking"},
            {"user_input": "I have a problem with my account", "expected_intent": "support"},
        ]
        
        logger.info("-" * 70)
        logger.info("[CONVERSATION] Starting multi-turn conversation")
        logger.info("-" * 70)
        
        for i, turn in enumerate(conversation_turns):
            user_input = turn["user_input"]
            expected_intent = turn["expected_intent"]
            
            logger.info(f"\n[TURN {i+1}] User: {user_input}")
            
            output, context = await engine.execute(workflow, {"user_input": user_input})
            
            detected_intent = context.get("detected_intent")
            logger.info(f"[TURN {i+1}] Intent: {detected_intent}")
            logger.info(f"[TURN {i+1}] Path: {' -> '.join(context.execution_path)}")
            
            assert detected_intent == expected_intent, f"Turn {i+1}: expected {expected_intent}, got {detected_intent}"
            
            if isinstance(output, dict) and "text" in output:
                logger.info(f"[TURN {i+1}] Response: {output['text'][:60]}...")
        
        # Verify observer stats
        logger.info("-" * 70)
        logger.info("[STATS] Conversation Summary")
        logger.info(f"        Total turns: {len(conversation_turns)}")
        logger.info(f"        Workflow events: {len(workflow_observer.events)}")
        logger.info(f"        Node executions: {len(node_observer.node_executions)}")
        
        logger.info("+" + "=" * 68 + "+")
        logger.info("| TEST PASSED: multi_turn_conversation".ljust(69) + "|")
        logger.info("+" + "=" * 68 + "+")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
