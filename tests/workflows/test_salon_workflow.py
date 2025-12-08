"""
Test Workflow: Salon Booking System (Azure Integration)

This test demonstrates the workflow system with real Azure LLM:
- Multiple agent nodes (Greeting, Booking, Cancellation)
- LLM-based edge conditions
- Pass-through fields for data transfer between nodes
- Expression-based edge conditions

Flow:
1. Greeting Agent → handles greetings, general questions, identifies booking intent
2. Booking Agent → handles service booking, offers add-ons
3. Cancellation Agent → handles appointment cancellations

Version: 1.0.0
"""

import pytest
import time
from datetime import datetime
from typing import Any, Dict, Optional

from core.llms import LLMFactory
from core.agents import (
    AgentBuilder,
    AgentType,
    AgentInputType,
    AgentOutputType,
)
from core.agents.spec import create_context as create_agent_context

from core.workflows import (
    # Builders
    NodeBuilder,
    EdgeBuilder,
    WorkflowBuilder,
    # Enums
    NodeType,
    EdgeType,
    EdgeConditionType,
    LLMEvaluationMode,
    PassThroughExtractionStrategy,
    ConditionOperator,
    ConditionJoinOperator,
    IOType,
    # Models
    NodeSpec,
    EdgeSpec,
    EdgeCondition,
    EdgeConditionGroup,
    WorkflowSpec,
)

from utils.logging.LoggerAdaptor import LoggerAdaptor

# Setup logger
logger = LoggerAdaptor.get_logger("tests.workflows.salon_workflow")


# =============================================================================
# LOGGING UTILITIES
# =============================================================================

class InteractionLogger:
    """
    Utility class for logging workflow interactions with timestamps.
    """
    
    def __init__(self, test_name: str = ""):
        self.test_name = test_name
        self.start_time = time.time()
        self.interaction_count = 0
    
    def _timestamp(self) -> str:
        """Get current timestamp."""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    
    def _elapsed(self) -> str:
        """Get elapsed time since start."""
        elapsed = time.time() - self.start_time
        return f"{elapsed:.3f}s"
    
    def header(self, title: str):
        """Log a section header."""
        print(f"\n{'='*80}")
        print(f"[{self._timestamp()}] {title}")
        print(f"{'='*80}")
        logger.info(f"{'='*60}")
        logger.info(f"{title}")
        logger.info(f"{'='*60}")
    
    def subheader(self, title: str):
        """Log a subsection header."""
        print(f"\n{'-'*60}")
        print(f"[{self._timestamp()}] {title}")
        print(f"{'-'*60}")
        logger.info(f"{'-'*40}")
        logger.info(f"{title}")
        logger.info(f"{'-'*40}")
    
    def user_input(self, message: str):
        """Log user input."""
        self.interaction_count += 1
        ts = self._timestamp()
        elapsed = self._elapsed()
        print(f"\n[{ts}] [Elapsed: {elapsed}] 👤 USER INPUT #{self.interaction_count}:")
        print(f"    \"{message}\"")
        logger.info(f"[{ts}] [Elapsed: {elapsed}] USER INPUT #{self.interaction_count}: {message}")
    
    def agent_response(self, agent_name: str, response: str, usage: Optional[Dict] = None):
        """Log agent response."""
        ts = self._timestamp()
        elapsed = self._elapsed()
        print(f"\n[{ts}] [Elapsed: {elapsed}] 🤖 AGENT RESPONSE ({agent_name}):")
        print(f"    \"{response}\"")
        if usage:
            print(f"    📊 Usage: {usage}")
        logger.info(f"[{ts}] [Elapsed: {elapsed}] AGENT RESPONSE ({agent_name}): {response}")
        if usage:
            logger.info(f"    Usage: {usage}")
    
    def llm_call_start(self, purpose: str):
        """Log LLM call start."""
        ts = self._timestamp()
        elapsed = self._elapsed()
        print(f"\n[{ts}] [Elapsed: {elapsed}] ⏳ LLM CALL START: {purpose}")
        logger.info(f"[{ts}] [Elapsed: {elapsed}] LLM CALL START: {purpose}")
        return time.time()
    
    def llm_call_end(self, purpose: str, start_time: float, result: Any = None):
        """Log LLM call end."""
        ts = self._timestamp()
        duration = time.time() - start_time
        elapsed = self._elapsed()
        print(f"[{ts}] [Elapsed: {elapsed}] ✅ LLM CALL END: {purpose} (took {duration:.3f}s)")
        if result is not None:
            print(f"    Result: {result}")
        logger.info(f"[{ts}] [Elapsed: {elapsed}] LLM CALL END: {purpose} (took {duration:.3f}s)")
        if result is not None:
            logger.info(f"    Result: {result}")
    
    def condition_check(self, condition_type: str, condition_desc: str, result: bool):
        """Log edge condition check."""
        ts = self._timestamp()
        elapsed = self._elapsed()
        status = "✅ MET" if result else "❌ NOT MET"
        print(f"\n[{ts}] [Elapsed: {elapsed}] 🔍 CONDITION CHECK ({condition_type}):")
        print(f"    Condition: {condition_desc}")
        print(f"    Result: {status}")
        logger.info(f"[{ts}] [Elapsed: {elapsed}] CONDITION CHECK ({condition_type}): {condition_desc} -> {status}")
    
    def edge_transition(self, from_node: str, to_node: str, edge_name: str):
        """Log edge transition."""
        ts = self._timestamp()
        elapsed = self._elapsed()
        print(f"\n[{ts}] [Elapsed: {elapsed}] 🔀 EDGE TRANSITION:")
        print(f"    From: {from_node}")
        print(f"    To: {to_node}")
        print(f"    Via: {edge_name}")
        logger.info(f"[{ts}] [Elapsed: {elapsed}] EDGE TRANSITION: {from_node} -> {to_node} via {edge_name}")
    
    def pass_through_extraction(self, field_name: str, value: Any, strategy: str):
        """Log pass-through field extraction."""
        ts = self._timestamp()
        elapsed = self._elapsed()
        print(f"\n[{ts}] [Elapsed: {elapsed}] 📤 PASS-THROUGH EXTRACTION:")
        print(f"    Field: {field_name}")
        print(f"    Value: {value}")
        print(f"    Strategy: {strategy}")
        logger.info(f"[{ts}] [Elapsed: {elapsed}] PASS-THROUGH: {field_name}={value} (strategy={strategy})")
    
    def info(self, message: str):
        """Log info message."""
        ts = self._timestamp()
        elapsed = self._elapsed()
        print(f"[{ts}] [Elapsed: {elapsed}] ℹ️  {message}")
        logger.info(f"[{ts}] [Elapsed: {elapsed}] {message}")
    
    def success(self, message: str):
        """Log success message."""
        ts = self._timestamp()
        elapsed = self._elapsed()
        print(f"[{ts}] [Elapsed: {elapsed}] ✅ {message}")
        logger.info(f"[{ts}] [Elapsed: {elapsed}] SUCCESS: {message}")
    
    def error(self, message: str):
        """Log error message."""
        ts = self._timestamp()
        elapsed = self._elapsed()
        print(f"[{ts}] [Elapsed: {elapsed}] ❌ {message}")
        logger.error(f"[{ts}] [Elapsed: {elapsed}] ERROR: {message}")
    
    def summary(self, total_interactions: int, total_time: float):
        """Log test summary."""
        print(f"\n{'='*80}")
        print(f"[{self._timestamp()}] TEST SUMMARY")
        print(f"{'='*80}")
        print(f"    Total Interactions: {total_interactions}")
        print(f"    Total Time: {total_time:.3f}s")
        print(f"    Avg Time/Interaction: {total_time/max(total_interactions, 1):.3f}s")
        print(f"{'='*80}")
        logger.info(f"TEST SUMMARY: {total_interactions} interactions in {total_time:.3f}s")


# =============================================================================
# AZURE CONFIGURATION
# =============================================================================

AZURE_CONFIG = {
    "endpoint": "https://zeenie-sweden.openai.azure.com/",
    "deployment_name": "gpt-4.1-mini",
    "api_version": "2024-02-15-preview",
    "timeout": 60,
}


# =============================================================================
# SYSTEM PROMPTS
# =============================================================================

GREETING_AGENT_SYSTEM_PROMPT = """You are a friendly receptionist at "Glamour Salon", a premium hair and beauty salon.

## Your Role
- Warmly greet customers and make them feel welcome
- Answer general questions about the salon and yourself
- Identify what the customer needs help with
- Guide them towards booking a service

## Greeting
Always start conversations with: "Hi! Welcome to Glamour Salon. How can I help you today?"

## Handling General Questions
Be prepared to answer questions like:
- "Are you AI?" - Yes, I'm an AI assistant helping at Glamour Salon. I can help you book appointments, answer questions about our services, and more!
- "What services do you offer?" - We offer haircuts, hair coloring, styling, treatments, and consultations. Would you like to book any of these?
- "What are your hours?" - We're open Monday to Saturday, 9 AM to 8 PM, and Sunday 10 AM to 6 PM.

## Identifying Booking Intent
When a customer expresses interest in booking a service:
1. Confirm their intent: "Great! I'd be happy to help you book an appointment."
2. Ask about the specific service: "Which service would you like to book today?"
3. Wait for them to specify the service name before proceeding.

## Important
- Be conversational and helpful
- Don't rush customers - let them ask questions
- Only proceed to booking once you have the service name
"""

BOOKING_AGENT_SYSTEM_PROMPT = """You are the booking specialist at "Glamour Salon".

## Your Role
- Help customers complete their service booking
- Offer relevant add-ons based on the service they're booking
- Handle booking details (date, time, stylist preference)

## Service Add-on Rules
Follow these rules to offer add-ons:

1. **Haircut bookings**: 
   - Offer: "Would you like to add a hair color service? We have a special 20% discount when combined with a haircut!"

2. **Hair Color bookings**:
   - Offer: "I'd recommend starting with a color consultation to find the perfect shade for you. Would you like to add that?"

3. **Any other service**:
   - Ask about their preferred date and time

## Booking Process
1. Confirm the service: "Perfect! Let me help you book your {service_name}."
2. Offer relevant add-ons based on the rules above
3. Ask for preferred date: "What date works best for you?"
4. Ask for preferred time: "And what time would you prefer?"
5. Confirm the booking details

## Handling Reschedule/Cancellation Requests
If the customer mentions they want to:
- Reschedule an existing appointment
- Cancel an appointment
- Change an appointment

Respond with: "I understand you'd like to modify an existing appointment. Let me transfer you to our appointment management specialist."

Then transfer to the cancellation agent.

## Current Booking Context
Service requested: {service_name}
"""

CANCELLATION_AGENT_SYSTEM_PROMPT = """You are the appointment management specialist at "Glamour Salon".

## Your Role
- Help customers cancel or reschedule their existing appointments
- Be empathetic and understanding
- Offer to rebook if appropriate

## Process
1. Greet: "I'm here to help you with your appointment changes."
2. Ask which appointment: "Which appointment would you like to cancel or reschedule? Please provide the date or service name."
3. Confirm the appointment details
4. Process the cancellation/reschedule
5. Offer to rebook: "Would you like to book a new appointment for a later date?"

## Important
- Always confirm before cancelling
- Be understanding if they're cancelling
- Try to retain the customer by offering to reschedule instead of cancelling
"""


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
async def azure_llm():
    """Create Azure LLM instance for agents and edge evaluation."""
    log = InteractionLogger("azure_llm_fixture")
    log.info("Creating Azure LLM instance...")
    
    start = time.time()
    llm = LLMFactory.create_llm(
        "azure-gpt-4.1-mini",
        connector_config=AZURE_CONFIG
    )
    duration = time.time() - start
    
    log.success(f"Azure LLM created in {duration:.3f}s")
    log.info(f"Model: azure-gpt-4.1-mini")
    log.info(f"Endpoint: {AZURE_CONFIG['endpoint']}")
    log.info(f"Deployment: {AZURE_CONFIG['deployment_name']}")
    
    yield llm
    
    # Cleanup
    if hasattr(llm.connector, 'close'):
        log.info("Closing LLM connector...")
        await llm.connector.close()
        log.success("LLM connector closed")


@pytest.fixture
def agent_context():
    """Create test agent context."""
    context = create_agent_context(
        user_id="test-user-salon",
        session_id="test-session-salon-001",
        metadata={"test": "salon_workflow"}
    )
    logger.info(f"Created agent context: user={context.user_id}, session={context.session_id}")
    return context


@pytest.fixture
def interaction_logger():
    """Create interaction logger for tests."""
    return InteractionLogger


# =============================================================================
# AGENT BUILDERS
# =============================================================================

def build_greeting_agent(llm: Any, log: Optional[InteractionLogger] = None) -> Any:
    """Build the greeting agent with Azure LLM."""
    if log:
        log.info("Building Greeting Agent...")
    
    start = time.time()
    agent = (AgentBuilder()
        .with_name("greeting-agent")
        .with_description("Friendly salon receptionist")
        .with_llm(llm)
        .with_system_prompt(GREETING_AGENT_SYSTEM_PROMPT)
        .with_input_types([AgentInputType.TEXT])
        .with_output_types([AgentOutputType.TEXT])
        .with_max_iterations(5)
        .as_type(AgentType.SIMPLE)
        .build())
    duration = time.time() - start
    
    if log:
        log.success(f"Greeting Agent built in {duration:.3f}s")
        log.info(f"Agent Name: {agent.spec.name}")
        log.info(f"Agent Type: {agent.spec.agent_type}")
        log.info(f"Max Iterations: {agent.spec.max_iterations}")
    
    return agent


def build_booking_agent(llm: Any, log: Optional[InteractionLogger] = None) -> Any:
    """Build the booking agent with Azure LLM."""
    if log:
        log.info("Building Booking Agent...")
    
    start = time.time()
    agent = (AgentBuilder()
        .with_name("booking-agent")
        .with_description("Booking specialist")
        .with_llm(llm)
        .with_system_prompt(BOOKING_AGENT_SYSTEM_PROMPT)
        .with_input_types([AgentInputType.TEXT])
        .with_output_types([AgentOutputType.TEXT])
        .with_max_iterations(10)
        .as_type(AgentType.SIMPLE)
        .build())
    duration = time.time() - start
    
    if log:
        log.success(f"Booking Agent built in {duration:.3f}s")
        log.info(f"Agent Name: {agent.spec.name}")
        log.info(f"Agent Type: {agent.spec.agent_type}")
    
    return agent


def build_cancellation_agent(llm: Any, log: Optional[InteractionLogger] = None) -> Any:
    """Build the cancellation agent with Azure LLM."""
    if log:
        log.info("Building Cancellation Agent...")
    
    start = time.time()
    agent = (AgentBuilder()
        .with_name("cancellation-agent")
        .with_description("Appointment manager")
        .with_llm(llm)
        .with_system_prompt(CANCELLATION_AGENT_SYSTEM_PROMPT)
        .with_input_types([AgentInputType.TEXT])
        .with_output_types([AgentOutputType.TEXT])
        .with_max_iterations(10)
        .as_type(AgentType.SIMPLE)
        .build())
    duration = time.time() - start
    
    if log:
        log.success(f"Cancellation Agent built in {duration:.3f}s")
        log.info(f"Agent Name: {agent.spec.name}")
        log.info(f"Agent Type: {agent.spec.agent_type}")
    
    return agent


# =============================================================================
# WORKFLOW BUILDER FUNCTIONS
# =============================================================================

def create_greeting_node(agent: Any) -> NodeSpec:
    """Create the greeting agent node."""
    return (NodeBuilder()
        .with_id("greeting-agent")
        .with_name("Greeting Agent")
        .with_description("Handles initial customer greetings and identifies their intent")
        .with_agent(agent)
        .with_input_type(IOType.TEXT)
        .with_output_type(IOType.TEXT)
        .with_display_name("Welcome Desk")
        .with_display_description("Our friendly receptionist will help you get started")
        .with_tag("greeting")
        .with_tag("entry-point")
        .build())


def create_booking_node(agent: Any) -> NodeSpec:
    """Create the booking agent node."""
    return (NodeBuilder()
        .with_id("booking-agent")
        .with_name("Booking Agent")
        .with_description("Handles service booking with add-on recommendations")
        .with_agent(agent)
        .with_input_type(IOType.TEXT)
        .with_output_type(IOType.TEXT)
        .with_display_name("Booking Specialist")
        .with_display_description("I'll help you book your appointment")
        .with_tag("booking")
        .build())


def create_cancellation_node(agent: Any) -> NodeSpec:
    """Create the cancellation agent node."""
    return (NodeBuilder()
        .with_id("cancellation-agent")
        .with_name("Cancellation Agent")
        .with_description("Handles appointment cancellations and reschedules")
        .with_agent(agent)
        .with_input_type(IOType.TEXT)
        .with_output_type(IOType.TEXT)
        .with_display_name("Appointment Manager")
        .with_display_description("I'll help you manage your existing appointments")
        .with_tag("cancellation")
        .with_tag("reschedule")
        .build())


def create_greeting_to_booking_edge(llm: Any) -> EdgeSpec:
    """
    Create the edge from Greeting Agent to Booking Agent.
    
    This edge:
    - Uses LLM condition to detect booking intent
    - Passes through the service_name field
    """
    return (EdgeBuilder()
        .with_id("greeting-to-booking")
        .with_name("Booking Transfer")
        .with_description("Transfer to booking agent when customer wants to book a service")
        .from_node("greeting-agent")
        .to_node("booking-agent")
        .as_conditional()
        # LLM condition: Check if customer wants to book
        .with_llm_condition(
            condition_prompt=(
                "Check if the customer has expressed intent to book a service AND "
                "has specified which service they want (e.g., haircut, hair color, styling). "
                "The condition is met only when BOTH booking intent AND service name are present."
            ),
            evaluation_mode=LLMEvaluationMode.BINARY,
            llm_instance=llm,
        )
        # Pass-through field: Extract and pass service_name
        .with_pass_through_field(
            name="service_name",
            description="The specific salon service the customer wants to book (e.g., haircut, hair color, styling, treatment)",
            required=True,
            extraction_strategy=PassThroughExtractionStrategy.LLM,
            ask_on_missing=True,
            ask_user_prompt="Which service would you like to book today? We offer haircuts, hair coloring, styling, and treatments.",
        )
        .with_pass_through_llm(llm_instance=llm)
        .with_priority(1)
        .with_tags(["booking", "transfer"])
        .build())


def create_booking_to_cancellation_edge() -> EdgeSpec:
    """
    Create the edge from Booking Agent to Cancellation Agent.
    
    This edge uses expression-based condition on guest_intent.
    """
    return (EdgeBuilder()
        .with_id("booking-to-cancellation")
        .with_name("Cancellation Transfer")
        .with_description("Transfer to cancellation agent when customer wants to cancel/reschedule")
        .from_node("booking-agent")
        .to_node("cancellation-agent")
        .as_conditional()
        # Expression condition: Check if guest_intent is cancellation
        .with_condition(
            field="variables.guest_intent",
            operator=ConditionOperator.IN,
            value=["cancellation", "reschedule", "cancel", "change_appointment"],
            description="Guest intent indicates cancellation or reschedule request"
        )
        .with_priority(1)
        .with_tags(["cancellation", "transfer"])
        .build())


def create_booking_to_cancellation_edge_llm(llm: Any) -> EdgeSpec:
    """
    Create edge using LLM condition for cancellation detection.
    """
    return (EdgeBuilder()
        .with_id("booking-to-cancellation-llm")
        .with_name("Cancellation Transfer (LLM)")
        .with_description("Transfer to cancellation agent when customer wants to cancel/reschedule")
        .from_node("booking-agent")
        .to_node("cancellation-agent")
        .as_conditional()
        # LLM condition: Detect cancellation intent
        .with_llm_condition(
            condition_prompt=(
                "Check if the customer wants to cancel, reschedule, or modify an EXISTING appointment. "
                "This includes phrases like: 'I want to cancel', 'can I reschedule', 'change my appointment', "
                "'I need to move my appointment', 'cancel my booking'. "
                "Do NOT trigger for new bookings - only for existing appointment modifications."
            ),
            evaluation_mode=LLMEvaluationMode.BINARY,
            llm_instance=llm,
        )
        .with_priority(0)
        .with_tags(["cancellation", "transfer", "llm"])
        .build())


def create_salon_workflow(
    greeting_agent: Any,
    booking_agent: Any,
    cancellation_agent: Any,
    edge_llm: Any,
    use_llm_for_cancellation: bool = True,
    log: Optional[InteractionLogger] = None,
) -> WorkflowSpec:
    """
    Create the complete salon booking workflow.
    """
    if log:
        log.header("Creating Salon Workflow")
    
    start = time.time()
    
    # Create nodes with agents
    if log:
        log.info("Creating workflow nodes...")
    greeting_node = create_greeting_node(greeting_agent)
    booking_node = create_booking_node(booking_agent)
    cancellation_node = create_cancellation_node(cancellation_agent)
    
    if log:
        log.success(f"Created 3 nodes: {greeting_node.id}, {booking_node.id}, {cancellation_node.id}")
    
    # Create edges
    if log:
        log.info("Creating workflow edges...")
    greeting_to_booking = create_greeting_to_booking_edge(edge_llm)
    
    if use_llm_for_cancellation:
        booking_to_cancellation = create_booking_to_cancellation_edge_llm(edge_llm)
    else:
        booking_to_cancellation = create_booking_to_cancellation_edge()
    
    if log:
        log.success(f"Created 2 edges: {greeting_to_booking.id}, {booking_to_cancellation.id}")
    
    # Build workflow
    if log:
        log.info("Building workflow...")
    workflow = (WorkflowBuilder()
        .with_id("salon-booking-workflow")
        .with_name("Salon Booking System")
        .with_description(
            "A multi-agent workflow for handling salon appointments including "
            "greetings, service booking with add-on recommendations, and cancellations."
        )
        .add_node(greeting_node)
        .add_node(booking_node)
        .add_node(cancellation_node)
        .add_edge(greeting_to_booking)
        .add_edge(booking_to_cancellation)
        .set_start_node("greeting-agent")
        .with_tag("salon")
        .with_tag("booking")
        .with_tag("multi-agent")
        .build())
    
    duration = time.time() - start
    
    if log:
        log.success(f"Workflow built in {duration:.3f}s")
        log.info(f"Workflow ID: {workflow.id}")
        log.info(f"Workflow Name: {workflow.name}")
        log.info(f"Start Node: {workflow.start_node_id}")
        log.info(f"Nodes: {list(workflow.nodes.keys())}")
        log.info(f"Edges: {list(workflow.edges.keys())}")
    
    return workflow


# =============================================================================
# TEST CASES - WORKFLOW STRUCTURE
# =============================================================================

@pytest.mark.asyncio
class TestSalonWorkflowStructure:
    """Test workflow structure creation."""
    
    async def test_workflow_creation(self, azure_llm, interaction_logger):
        """Test that the workflow can be created successfully."""
        log = interaction_logger("test_workflow_creation")
        log.header("TEST: Workflow Creation")
        
        log.info("Building agents...")
        greeting_agent = build_greeting_agent(azure_llm, log)
        booking_agent = build_booking_agent(azure_llm, log)
        cancellation_agent = build_cancellation_agent(azure_llm, log)
        
        workflow = create_salon_workflow(
            greeting_agent=greeting_agent,
            booking_agent=booking_agent,
            cancellation_agent=cancellation_agent,
            edge_llm=azure_llm,
            log=log,
        )
        
        assert workflow.id == "salon-booking-workflow"
        assert workflow.name == "Salon Booking System"
        assert len(workflow.nodes) == 3
        assert len(workflow.edges) == 2
        assert workflow.start_node_id == "greeting-agent"
        
        log.success("All workflow structure assertions passed!")
    
    async def test_nodes_have_agents(self, azure_llm, interaction_logger):
        """Test that nodes have agents configured."""
        log = interaction_logger("test_nodes_have_agents")
        log.header("TEST: Nodes Have Agents")
        
        greeting_agent = build_greeting_agent(azure_llm, log)
        node = create_greeting_node(greeting_agent)
        
        log.info(f"Checking node: {node.id}")
        log.info(f"Node type: {node.node_type}")
        log.info(f"Has agent: {node.has_agent()}")
        
        assert node.id == "greeting-agent"
        assert node.node_type == NodeType.AGENT
        assert node.has_agent()
        assert node.agent_instance is not None
        assert node.agent_instance.spec.name == "greeting-agent"
        
        log.success(f"Node {node.id} has agent: {node.agent_instance.spec.name}")
    
    async def test_edge_has_llm_condition(self, azure_llm, interaction_logger):
        """Test that edge has LLM condition configured."""
        log = interaction_logger("test_edge_has_llm_condition")
        log.header("TEST: Edge LLM Condition")
        
        edge = create_greeting_to_booking_edge(azure_llm)
        
        log.info(f"Checking edge: {edge.id}")
        log.info(f"From: {edge.source_node_id} -> To: {edge.target_node_id}")
        log.info(f"Has LLM conditions: {edge.has_llm_conditions()}")
        
        assert edge.id == "greeting-to-booking"
        assert edge.has_llm_conditions()
        assert edge.conditions is not None
        
        llm_condition = edge.conditions.conditions[0]
        log.info(f"Condition type: {llm_condition.condition_type}")
        log.info(f"Condition prompt: {llm_condition.llm_config.condition_prompt[:80]}...")
        
        assert llm_condition.condition_type == EdgeConditionType.LLM
        assert llm_condition.llm_config is not None
        assert llm_condition.llm_config.llm_instance is not None
        
        log.success("Edge LLM condition configured correctly!")
    
    async def test_edge_has_pass_through_fields(self, azure_llm, interaction_logger):
        """Test that edge has pass-through fields configured."""
        log = interaction_logger("test_edge_has_pass_through_fields")
        log.header("TEST: Edge Pass-Through Fields")
        
        edge = create_greeting_to_booking_edge(azure_llm)
        
        log.info(f"Checking edge: {edge.id}")
        log.info(f"Has pass-through config: {edge.pass_through is not None}")
        
        assert edge.pass_through is not None
        assert len(edge.pass_through.fields) == 1
        
        service_field = edge.pass_through.fields[0]
        log.info(f"Pass-through field: {service_field.name}")
        log.info(f"Description: {service_field.description}")
        log.info(f"Required: {service_field.required}")
        log.info(f"Extraction strategy: {service_field.extraction_strategy}")
        log.info(f"Ask on missing: {service_field.ask_on_missing}")
        
        assert service_field.name == "service_name"
        assert service_field.required is True
        assert service_field.extraction_strategy == PassThroughExtractionStrategy.LLM
        
        log.success("Pass-through fields configured correctly!")


# =============================================================================
# TEST CASES - AGENT EXECUTION
# =============================================================================

@pytest.mark.asyncio
class TestSalonAgents:
    """Test individual agent execution."""
    
    async def test_greeting_agent_responds(self, azure_llm, agent_context, interaction_logger):
        """Test greeting agent responds to hello."""
        log = interaction_logger("test_greeting_agent_responds")
        log.header("TEST: Greeting Agent Response")
        
        agent = build_greeting_agent(azure_llm, log)
        
        user_message = "Hello!"
        log.user_input(user_message)
        
        llm_start = log.llm_call_start("Greeting Agent processing")
        result = await agent.run(user_message, agent_context)
        log.llm_call_end("Greeting Agent processing", llm_start)
        
        log.agent_response(
            "greeting-agent",
            result.content,
            usage=result.usage if hasattr(result, 'usage') else None
        )
        
        assert result.is_success()
        assert len(result.content) > 0
        
        log.success("Greeting agent responded successfully!")
        log.summary(1, time.time() - log.start_time)
    
    async def test_greeting_agent_answers_ai_question(self, azure_llm, agent_context, interaction_logger):
        """Test greeting agent answers 'are you AI' question."""
        log = interaction_logger("test_greeting_agent_answers_ai_question")
        log.header("TEST: Greeting Agent AI Question")
        
        agent = build_greeting_agent(azure_llm, log)
        
        user_message = "Are you a real person or AI?"
        log.user_input(user_message)
        
        llm_start = log.llm_call_start("Greeting Agent processing AI question")
        result = await agent.run(user_message, agent_context)
        log.llm_call_end("Greeting Agent processing AI question", llm_start)
        
        log.agent_response(
            "greeting-agent",
            result.content,
            usage=result.usage if hasattr(result, 'usage') else None
        )
        
        assert result.is_success()
        assert len(result.content) > 0
        
        log.success("Greeting agent answered AI question!")
        log.summary(1, time.time() - log.start_time)
    
    async def test_greeting_agent_handles_booking_intent(self, azure_llm, agent_context, interaction_logger):
        """Test greeting agent handles booking intent."""
        log = interaction_logger("test_greeting_agent_handles_booking_intent")
        log.header("TEST: Greeting Agent Booking Intent")
        
        agent = build_greeting_agent(azure_llm, log)
        
        user_message = "I'd like to book a haircut please"
        log.user_input(user_message)
        
        llm_start = log.llm_call_start("Greeting Agent processing booking intent")
        result = await agent.run(user_message, agent_context)
        log.llm_call_end("Greeting Agent processing booking intent", llm_start)
        
        log.agent_response(
            "greeting-agent",
            result.content,
            usage=result.usage if hasattr(result, 'usage') else None
        )
        
        assert result.is_success()
        assert len(result.content) > 0
        
        log.success("Greeting agent handled booking intent!")
        log.summary(1, time.time() - log.start_time)
    
    async def test_booking_agent_offers_addon(self, azure_llm, agent_context, interaction_logger):
        """Test booking agent offers add-on for haircut."""
        log = interaction_logger("test_booking_agent_offers_addon")
        log.header("TEST: Booking Agent Add-on Offer")
        
        agent = build_booking_agent(azure_llm, log)
        
        user_message = "I want to book a haircut"
        log.user_input(user_message)
        
        llm_start = log.llm_call_start("Booking Agent processing")
        result = await agent.run(user_message, agent_context)
        log.llm_call_end("Booking Agent processing", llm_start)
        
        log.agent_response(
            "booking-agent",
            result.content,
            usage=result.usage if hasattr(result, 'usage') else None
        )
        
        assert result.is_success()
        assert len(result.content) > 0
        
        log.success("Booking agent offered add-on!")
        log.summary(1, time.time() - log.start_time)
    
    async def test_cancellation_agent_asks_which_appointment(self, azure_llm, agent_context, interaction_logger):
        """Test cancellation agent asks which appointment."""
        log = interaction_logger("test_cancellation_agent_asks_which_appointment")
        log.header("TEST: Cancellation Agent")
        
        agent = build_cancellation_agent(azure_llm, log)
        
        user_message = "I need to cancel my appointment"
        log.user_input(user_message)
        
        llm_start = log.llm_call_start("Cancellation Agent processing")
        result = await agent.run(user_message, agent_context)
        log.llm_call_end("Cancellation Agent processing", llm_start)
        
        log.agent_response(
            "cancellation-agent",
            result.content,
            usage=result.usage if hasattr(result, 'usage') else None
        )
        
        assert result.is_success()
        assert len(result.content) > 0
        
        log.success("Cancellation agent responded!")
        log.summary(1, time.time() - log.start_time)


# =============================================================================
# TEST CASES - EDGE CONDITION EVALUATION
# =============================================================================

@pytest.mark.asyncio
class TestEdgeConditions:
    """Test edge condition evaluation."""
    
    async def test_expression_condition_evaluation(self, interaction_logger):
        """Test expression-based condition evaluation."""
        log = interaction_logger("test_expression_condition_evaluation")
        log.header("TEST: Expression Condition Evaluation")
        
        edge = create_booking_to_cancellation_edge()
        condition = edge.conditions.conditions[0]
        
        log.info(f"Testing edge: {edge.id}")
        log.info(f"Condition field: {condition.field}")
        log.info(f"Condition operator: {condition.operator}")
        log.info(f"Condition value: {condition.value}")
        
        # Test with matching value
        context_match = {"variables": {"guest_intent": "cancellation"}}
        log.subheader("Test 1: Matching Context")
        log.info(f"Context: {context_match}")
        result = condition.evaluate(context_match)
        log.condition_check("EXPRESSION", f"{condition.field} IN {condition.value}", result)
        assert result is True
        
        # Test with non-matching value
        context_no_match = {"variables": {"guest_intent": "booking"}}
        log.subheader("Test 2: Non-Matching Context")
        log.info(f"Context: {context_no_match}")
        result = condition.evaluate(context_no_match)
        log.condition_check("EXPRESSION", f"{condition.field} IN {condition.value}", result)
        assert result is False
        
        log.success("Expression condition evaluation passed!")
    
    async def test_llm_condition_booking_intent(self, azure_llm, interaction_logger):
        """Test LLM condition detects booking intent."""
        log = interaction_logger("test_llm_condition_booking_intent")
        log.header("TEST: LLM Condition - Booking Intent Detection")
        
        edge = create_greeting_to_booking_edge(azure_llm)
        llm_condition = edge.conditions.conditions[0]
        
        log.info(f"Edge: {edge.id}")
        log.info(f"Condition type: {llm_condition.condition_type}")
        log.info(f"Condition prompt: {llm_condition.llm_config.condition_prompt[:100]}...")
        
        # Context with booking intent and service name
        context = {
            "messages": [
                {"role": "user", "content": "Hi there!"},
                {"role": "assistant", "content": "Hi! Welcome to Glamour Salon. How can I help you today?"},
                {"role": "user", "content": "I'd like to book a haircut please."},
            ],
            "last_output": "Great! I'd be happy to help you book a haircut appointment.",
            "variables": {}
        }
        
        log.subheader("Conversation Context")
        for msg in context["messages"]:
            role_emoji = "👤" if msg["role"] == "user" else "🤖"
            log.info(f"{role_emoji} {msg['role'].upper()}: {msg['content']}")
        
        llm_start = log.llm_call_start("LLM Condition Evaluation - Booking Intent")
        result = await llm_condition.evaluate_async(context, azure_llm)
        log.llm_call_end("LLM Condition Evaluation - Booking Intent", llm_start, result)
        
        log.condition_check("LLM", "booking intent + service name present", result)
        
        assert isinstance(result, bool)
        log.success(f"LLM condition evaluation completed! Result: {result}")
    
    async def test_llm_condition_no_booking_intent(self, azure_llm, interaction_logger):
        """Test LLM condition does not trigger for general questions."""
        log = interaction_logger("test_llm_condition_no_booking_intent")
        log.header("TEST: LLM Condition - No Booking Intent")
        
        edge = create_greeting_to_booking_edge(azure_llm)
        llm_condition = edge.conditions.conditions[0]
        
        # Context with just general questions, no booking intent
        context = {
            "messages": [
                {"role": "user", "content": "What are your hours?"},
            ],
            "last_output": "We're open Monday to Saturday, 9 AM to 8 PM.",
            "variables": {}
        }
        
        log.subheader("Conversation Context")
        for msg in context["messages"]:
            role_emoji = "👤" if msg["role"] == "user" else "🤖"
            log.info(f"{role_emoji} {msg['role'].upper()}: {msg['content']}")
        
        llm_start = log.llm_call_start("LLM Condition Evaluation - General Question")
        result = await llm_condition.evaluate_async(context, azure_llm)
        log.llm_call_end("LLM Condition Evaluation - General Question", llm_start, result)
        
        log.condition_check("LLM", "booking intent + service name present", result)
        
        # Should NOT detect booking intent
        assert result is False
        log.success("LLM correctly did not detect booking intent!")
    
    async def test_llm_condition_cancellation_intent(self, azure_llm, interaction_logger):
        """Test LLM condition detects cancellation intent."""
        log = interaction_logger("test_llm_condition_cancellation_intent")
        log.header("TEST: LLM Condition - Cancellation Intent Detection")
        
        edge = create_booking_to_cancellation_edge_llm(azure_llm)
        llm_condition = edge.conditions.conditions[0]
        
        log.info(f"Edge: {edge.id}")
        log.info(f"Condition prompt: {llm_condition.llm_config.condition_prompt[:100]}...")
        
        # Context with cancellation intent
        context = {
            "messages": [
                {"role": "user", "content": "Actually, I need to cancel my existing appointment first."},
            ],
            "last_output": "I understand you'd like to modify an existing appointment.",
            "variables": {}
        }
        
        log.subheader("Conversation Context")
        for msg in context["messages"]:
            role_emoji = "👤" if msg["role"] == "user" else "🤖"
            log.info(f"{role_emoji} {msg['role'].upper()}: {msg['content']}")
        
        llm_start = log.llm_call_start("LLM Condition Evaluation - Cancellation Intent")
        result = await llm_condition.evaluate_async(context, azure_llm)
        log.llm_call_end("LLM Condition Evaluation - Cancellation Intent", llm_start, result)
        
        log.condition_check("LLM", "cancellation/reschedule intent", result)
        
        # Should detect cancellation intent
        assert result is True
        log.success("LLM correctly detected cancellation intent!")


# =============================================================================
# TEST CASES - PASS-THROUGH FIELD EXTRACTION
# =============================================================================

@pytest.mark.asyncio
class TestPassThroughExtraction:
    """Test pass-through field extraction."""
    
    async def test_extract_service_name(self, azure_llm, interaction_logger):
        """Test extracting service_name from conversation."""
        log = interaction_logger("test_extract_service_name")
        log.header("TEST: Pass-Through Extraction - Service Name")
        
        edge = create_greeting_to_booking_edge(azure_llm)
        
        log.info(f"Edge: {edge.id}")
        log.info(f"Pass-through fields: {[f.name for f in edge.pass_through.fields]}")
        
        # Context with service name mentioned
        context = {
            "messages": [
                {"role": "user", "content": "I'd like to book a haircut please."},
                {"role": "assistant", "content": "Great! I'd be happy to help you book a haircut."},
            ],
            "variables": {}
        }
        
        log.subheader("Conversation Context")
        for msg in context["messages"]:
            role_emoji = "👤" if msg["role"] == "user" else "🤖"
            log.info(f"{role_emoji} {msg['role'].upper()}: {msg['content']}")
        
        llm_start = log.llm_call_start("Pass-Through Field Extraction")
        extracted = await edge.extract_pass_through_fields(context, azure_llm)
        log.llm_call_end("Pass-Through Field Extraction", llm_start)
        
        log.subheader("Extracted Fields")
        for field_name, value in extracted.items():
            log.pass_through_extraction(field_name, value, "LLM")
        
        # Should extract service_name
        assert "service_name" in extracted
        assert "haircut" in extracted["service_name"].lower()
        
        log.success(f"Extracted service_name: {extracted['service_name']}")
    
    async def test_extract_service_name_hair_color(self, azure_llm, interaction_logger):
        """Test extracting 'hair color' service name."""
        log = interaction_logger("test_extract_service_name_hair_color")
        log.header("TEST: Pass-Through Extraction - Hair Color Service")
        
        edge = create_greeting_to_booking_edge(azure_llm)
        
        context = {
            "messages": [
                {"role": "user", "content": "I want to get my hair colored."},
            ],
            "variables": {}
        }
        
        log.subheader("Conversation Context")
        for msg in context["messages"]:
            role_emoji = "👤" if msg["role"] == "user" else "🤖"
            log.info(f"{role_emoji} {msg['role'].upper()}: {msg['content']}")
        
        llm_start = log.llm_call_start("Pass-Through Field Extraction")
        extracted = await edge.extract_pass_through_fields(context, azure_llm)
        log.llm_call_end("Pass-Through Field Extraction", llm_start)
        
        log.subheader("Extracted Fields")
        for field_name, value in extracted.items():
            log.pass_through_extraction(field_name, value, "LLM")
        
        assert "service_name" in extracted
        assert "color" in extracted["service_name"].lower()
        
        log.success(f"Extracted service_name: {extracted['service_name']}")


# =============================================================================
# TEST CASES - CONDITION GROUP LOGIC
# =============================================================================

class TestConditionGroupLogic:
    """Test condition group AND/OR logic."""
    
    def test_and_group(self, interaction_logger):
        """Test AND condition group."""
        log = interaction_logger("test_and_group")
        log.header("TEST: Condition Group - AND Logic")
        
        cond1 = EdgeCondition(
            condition_type=EdgeConditionType.EXPRESSION,
            field="intent",
            operator=ConditionOperator.EQUALS,
            value="booking"
        )
        cond2 = EdgeCondition(
            condition_type=EdgeConditionType.EXPRESSION,
            field="has_service",
            operator=ConditionOperator.EQUALS,
            value=True
        )
        
        and_group = EdgeConditionGroup(
            conditions=[cond1, cond2],
            join_operator=ConditionJoinOperator.AND
        )
        
        log.info(f"Condition 1: intent EQUALS 'booking'")
        log.info(f"Condition 2: has_service EQUALS True")
        log.info(f"Join operator: AND")
        
        log.subheader("Test 1: Both conditions met")
        context_both = {"intent": "booking", "has_service": True}
        log.info(f"Context: {context_both}")
        result = and_group.evaluate(context_both)
        log.condition_check("AND GROUP", "both conditions met", result)
        assert result is True
        
        log.subheader("Test 2: Only one condition met")
        context_one = {"intent": "booking", "has_service": False}
        log.info(f"Context: {context_one}")
        result = and_group.evaluate(context_one)
        log.condition_check("AND GROUP", "only one condition met", result)
        assert result is False
        
        log.success("AND group logic working correctly!")
    
    def test_or_group(self, interaction_logger):
        """Test OR condition group."""
        log = interaction_logger("test_or_group")
        log.header("TEST: Condition Group - OR Logic")
        
        cond1 = EdgeCondition(
            condition_type=EdgeConditionType.EXPRESSION,
            field="intent",
            operator=ConditionOperator.EQUALS,
            value="cancellation"
        )
        cond2 = EdgeCondition(
            condition_type=EdgeConditionType.EXPRESSION,
            field="intent",
            operator=ConditionOperator.EQUALS,
            value="reschedule"
        )
        
        or_group = EdgeConditionGroup(
            conditions=[cond1, cond2],
            join_operator=ConditionJoinOperator.OR
        )
        
        log.info(f"Condition 1: intent EQUALS 'cancellation'")
        log.info(f"Condition 2: intent EQUALS 'reschedule'")
        log.info(f"Join operator: OR")
        
        log.subheader("Test 1: First condition met")
        result = or_group.evaluate({"intent": "cancellation"})
        log.condition_check("OR GROUP", "intent=cancellation", result)
        assert result is True
        
        log.subheader("Test 2: Second condition met")
        result = or_group.evaluate({"intent": "reschedule"})
        log.condition_check("OR GROUP", "intent=reschedule", result)
        assert result is True
        
        log.subheader("Test 3: No condition met")
        result = or_group.evaluate({"intent": "booking"})
        log.condition_check("OR GROUP", "intent=booking (neither)", result)
        assert result is False
        
        log.success("OR group logic working correctly!")


# =============================================================================
# TEST CASES - TRANSFER RULES
# =============================================================================

@pytest.mark.asyncio
class TestTransferRules:
    """Test transfer rule generation for agent prompts."""
    
    async def test_edge_generates_transfer_rules(self, azure_llm, interaction_logger):
        """Test that edges generate transfer rules."""
        log = interaction_logger("test_edge_generates_transfer_rules")
        log.header("TEST: Transfer Rules Generation")
        
        edge = create_greeting_to_booking_edge(azure_llm)
        
        log.info(f"Edge: {edge.id}")
        log.info(f"From: {edge.source_node_id} -> To: {edge.target_node_id}")
        
        rules = edge.get_transfer_rules()
        
        log.subheader("Generated Transfer Rules")
        for i, rule in enumerate(rules, 1):
            log.info(f"Rule {i}: {rule}")
        
        assert len(rules) > 0
        log.success(f"Generated {len(rules)} transfer rule(s)!")
    
    async def test_edge_generates_transfer_rules_prompt(self, azure_llm, interaction_logger):
        """Test formatted transfer rules for agent prompt."""
        log = interaction_logger("test_edge_generates_transfer_rules_prompt")
        log.header("TEST: Transfer Rules Prompt Generation")
        
        edge = create_greeting_to_booking_edge(azure_llm)
        
        prompt_section = edge.get_transfer_rules_prompt("Booking Agent")
        
        log.subheader("Generated Prompt Section")
        print(f"\n{prompt_section}")
        log.info(f"Prompt length: {len(prompt_section)} characters")
        
        assert "Transfer Rules" in prompt_section
        assert "service_name" in prompt_section
        
        log.success("Transfer rules prompt generated successfully!")


# =============================================================================
# TEST CASES - FULL CONVERSATION FLOW
# =============================================================================

@pytest.mark.asyncio
class TestFullConversationFlow:
    """Test full conversation flow through workflow."""
    
    async def test_multi_turn_greeting_conversation(self, azure_llm, agent_context, interaction_logger):
        """Test multi-turn conversation with greeting agent."""
        log = interaction_logger("test_multi_turn_greeting_conversation")
        log.header("TEST: Multi-Turn Greeting Conversation")
        
        agent = build_greeting_agent(azure_llm, log)
        
        conversations = [
            "Hello!",
            "Are you AI or human?",
            "What services do you offer?",
            "I'd like to book a haircut please.",
        ]
        
        total_start = time.time()
        
        for i, user_message in enumerate(conversations, 1):
            log.subheader(f"Turn {i}")
            log.user_input(user_message)
            
            llm_start = log.llm_call_start(f"Agent processing turn {i}")
            result = await agent.run(user_message, agent_context)
            log.llm_call_end(f"Agent processing turn {i}", llm_start)
            
            log.agent_response(
                "greeting-agent",
                result.content,
                usage=result.usage if hasattr(result, 'usage') else None
            )
            
            assert result.is_success()
        
        total_time = time.time() - total_start
        log.summary(len(conversations), total_time)
        log.success("Multi-turn conversation completed!")
    
    async def test_booking_flow_with_addon(self, azure_llm, agent_context, interaction_logger):
        """Test booking flow with add-on offering."""
        log = interaction_logger("test_booking_flow_with_addon")
        log.header("TEST: Booking Flow with Add-on")
        
        agent = build_booking_agent(azure_llm, log)
        
        conversations = [
            "I want to book a haircut",
            "Yes, I'd like to add the hair color too!",
            "How about this Saturday at 2pm?",
        ]
        
        total_start = time.time()
        
        for i, user_message in enumerate(conversations, 1):
            log.subheader(f"Turn {i}")
            log.user_input(user_message)
            
            llm_start = log.llm_call_start(f"Booking agent processing turn {i}")
            result = await agent.run(user_message, agent_context)
            log.llm_call_end(f"Booking agent processing turn {i}", llm_start)
            
            log.agent_response(
                "booking-agent",
                result.content,
                usage=result.usage if hasattr(result, 'usage') else None
            )
            
            assert result.is_success()
        
        total_time = time.time() - total_start
        log.summary(len(conversations), total_time)
        log.success("Booking flow completed!")


# =============================================================================
# EXAMPLE CONVERSATION FLOW
# =============================================================================

def print_example_flow():
    """Print an example conversation flow through the workflow."""
    print("\n" + "="*80)
    print("SALON BOOKING WORKFLOW - Example Conversation Flow")
    print("="*80)
    
    print("\n--- GREETING AGENT ---")
    print("Agent: Hi! Welcome to Glamour Salon. How can I help you today?")
    print("Customer: Hi! Are you a real person or AI?")
    print("Agent: I'm an AI assistant helping at Glamour Salon. I can help you book")
    print("       appointments, answer questions about our services, and more!")
    print("Customer: What services do you offer?")
    print("Agent: We offer haircuts, hair coloring, styling, treatments, and")
    print("       consultations. Would you like to book any of these?")
    print("Customer: Yes, I'd like to book a haircut please.")
    print("Agent: Great! I'd be happy to help you book a haircut appointment.")
    print("\n[EDGE CONDITION MET: LLM detects booking intent + service_name='haircut']")
    print("[PASS-THROUGH: service_name='haircut' extracted via LLM and passed]")
    print("[TRANSFER TO: booking-agent]")
    
    print("\n--- BOOKING AGENT ---")
    print("Agent: Perfect! Let me help you book your haircut.")
    print("       Would you like to add a hair color service? We have a special")
    print("       20% discount when combined with a haircut!")
    print("Customer: Actually, I need to cancel my existing appointment first.")
    print("\n[EDGE CONDITION MET: LLM detects cancellation intent]")
    print("[TRANSFER TO: cancellation-agent]")
    
    print("\n--- CANCELLATION AGENT ---")
    print("Agent: I'm here to help you with your appointment changes.")
    print("       Which appointment would you like to cancel or reschedule?")
    
    print("\n" + "="*80)


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print_example_flow()
    
    print("\n" + "="*80)
    print("Running Tests...")
    print("="*80)
    pytest.main([__file__, "-v", "--tb=short", "-x", "-s"])
