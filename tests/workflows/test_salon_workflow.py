"""
Test Workflow: Salon Booking System (Azure Integration)

This test demonstrates the workflow system with real Azure LLM:
- Multiple agent nodes (Greeting, Booking, Cancellation)
- LLM-based edge conditions
- Pass-through fields for data transfer between nodes
- Expression-based edge conditions
- Metrics collection via utils/logging

The logging system:
- Collects metrics into WorkflowMetrics context
- Supports async logging via DelayedLogger
- Configuration loaded from log config files
- Format (JSON/detailed/standard) controlled by config

Flow:
1. Greeting Agent → handles greetings, general questions, identifies booking intent
2. Booking Agent → handles service booking, offers add-ons
3. Cancellation Agent → handles appointment cancellations

Version: 3.0.0
"""

import pytest
from typing import Any

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

from utils.logging import LoggerAdaptor, metrics_context


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
def workflow_logger():
    """Create workflow logger with test configuration."""
    # Use LoggerAdaptor with test environment (loads log_config_test.json)
    logger = LoggerAdaptor.get_logger("test.salon_workflow", environment="test")
    yield logger
    logger.shutdown()


@pytest.fixture
async def azure_llm(workflow_logger):
    """Create Azure LLM instance for agents and edge evaluation."""
    with metrics_context(
        component_type='llm',
        component_id='azure-gpt-4.1-mini',
    ) as ctx:
        llm = LLMFactory.create_llm(
            "azure-gpt-4.1-mini",
            connector_config=AZURE_CONFIG
        )
        ctx.response = "LLM instance created"
    
    yield llm
    
    if hasattr(llm.connector, 'close'):
        await llm.connector.close()


@pytest.fixture
def agent_context():
    """Create test agent context."""
    return create_agent_context(
        user_id="test-user-salon",
        session_id="test-session-salon-001",
        metadata={"test": "salon_workflow"}
    )


# =============================================================================
# AGENT BUILDERS
# =============================================================================

def build_greeting_agent(llm: Any) -> Any:
    """Build the greeting agent with Azure LLM."""
    return (AgentBuilder()
        .with_name("greeting-agent")
        .with_description("Friendly salon receptionist")
        .with_llm(llm)
        .with_system_prompt(GREETING_AGENT_SYSTEM_PROMPT)
        .with_input_types([AgentInputType.TEXT])
        .with_output_types([AgentOutputType.TEXT])
        .with_max_iterations(5)
        .as_type(AgentType.SIMPLE)
        .build())


def build_booking_agent(llm: Any) -> Any:
    """Build the booking agent with Azure LLM."""
    return (AgentBuilder()
        .with_name("booking-agent")
        .with_description("Booking specialist")
        .with_llm(llm)
        .with_system_prompt(BOOKING_AGENT_SYSTEM_PROMPT)
        .with_input_types([AgentInputType.TEXT])
        .with_output_types([AgentOutputType.TEXT])
        .with_max_iterations(10)
        .as_type(AgentType.SIMPLE)
        .build())


def build_cancellation_agent(llm: Any) -> Any:
    """Build the cancellation agent with Azure LLM."""
    return (AgentBuilder()
        .with_name("cancellation-agent")
        .with_description("Appointment manager")
        .with_llm(llm)
        .with_system_prompt(CANCELLATION_AGENT_SYSTEM_PROMPT)
        .with_input_types([AgentInputType.TEXT])
        .with_output_types([AgentOutputType.TEXT])
        .with_max_iterations(10)
        .as_type(AgentType.SIMPLE)
        .build())


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
    """Create the edge from Greeting Agent to Booking Agent."""
    return (EdgeBuilder()
        .with_id("greeting-to-booking")
        .with_name("Booking Transfer")
        .with_description("Transfer to booking agent when customer wants to book a service")
        .from_node("greeting-agent")
        .to_node("booking-agent")
        .as_conditional()
        .with_llm_condition(
            condition_prompt=(
                "Check if the customer has expressed intent to book a service AND "
                "has specified which service they want (e.g., haircut, hair color, styling). "
                "The condition is met only when BOTH booking intent AND service name are present."
            ),
            evaluation_mode=LLMEvaluationMode.BINARY,
            llm_instance=llm,
        )
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
    """Create expression-based edge from Booking to Cancellation."""
    return (EdgeBuilder()
        .with_id("booking-to-cancellation")
        .with_name("Cancellation Transfer")
        .with_description("Transfer to cancellation agent when customer wants to cancel/reschedule")
        .from_node("booking-agent")
        .to_node("cancellation-agent")
        .as_conditional()
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
    """Create LLM-based edge from Booking to Cancellation."""
    return (EdgeBuilder()
        .with_id("booking-to-cancellation-llm")
        .with_name("Cancellation Transfer (LLM)")
        .with_description("Transfer to cancellation agent when customer wants to cancel/reschedule")
        .from_node("booking-agent")
        .to_node("cancellation-agent")
        .as_conditional()
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
) -> WorkflowSpec:
    """Create the complete salon booking workflow."""
    greeting_node = create_greeting_node(greeting_agent)
    booking_node = create_booking_node(booking_agent)
    cancellation_node = create_cancellation_node(cancellation_agent)
    
    greeting_to_booking = create_greeting_to_booking_edge(edge_llm)
    
    if use_llm_for_cancellation:
        booking_to_cancellation = create_booking_to_cancellation_edge_llm(edge_llm)
    else:
        booking_to_cancellation = create_booking_to_cancellation_edge()
    
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
    
    return workflow


# =============================================================================
# TEST CASES - WORKFLOW STRUCTURE
# =============================================================================

@pytest.mark.asyncio
class TestSalonWorkflowStructure:
    """Test workflow structure creation."""
    
    async def test_workflow_creation(self, azure_llm, workflow_logger):
        """Test that the workflow can be created successfully."""
        with metrics_context(component_type='workflow',
            workflow_id="test_workflow_creation",
            workflow_name="Workflow Creation Test"
        ) as ctx:
            greeting_agent = build_greeting_agent(azure_llm)
            booking_agent = build_booking_agent(azure_llm)
            cancellation_agent = build_cancellation_agent(azure_llm)
            
            workflow = create_salon_workflow(
                greeting_agent=greeting_agent,
                booking_agent=booking_agent,
                cancellation_agent=cancellation_agent,
                edge_llm=azure_llm,
            )
            
            assert workflow.id == "salon-booking-workflow"
            assert workflow.name == "Salon Booking System"
            assert len(workflow.nodes) == 3
            assert len(workflow.edges) == 2
            assert workflow.start_node_id == "greeting-agent"
            
            ctx.response = f"Created workflow with {len(workflow.nodes)} nodes"
    
    async def test_nodes_have_agents(self, azure_llm, workflow_logger):
        """Test that nodes have agents configured."""
        with metrics_context(
            component_type='node',
            component_id='greeting-agent',
            component_name='Greeting Agent Test',
        ) as ctx:
            greeting_agent = build_greeting_agent(azure_llm)
            node = create_greeting_node(greeting_agent)
            
            assert node.id == "greeting-agent"
            assert node.node_type == NodeType.AGENT
            assert node.has_agent()
            assert node.agent_instance is not None
            
            ctx.response = f"Node has agent: {node.agent_instance.spec.name}"
    
    async def test_edge_has_llm_condition(self, azure_llm, workflow_logger):
        """Test that edge has LLM condition configured."""
        with metrics_context(
            component_type='edge',
            component_id='greeting-to-booking',
            source_node='greeting-agent',
            target_node='booking-agent',
        ) as ctx:
            edge = create_greeting_to_booking_edge(azure_llm)
            
            assert edge.id == "greeting-to-booking"
            assert edge.has_llm_conditions()
            assert edge.conditions is not None
            
            llm_condition = edge.conditions.conditions[0]
            assert llm_condition.condition_type == EdgeConditionType.LLM
            
            ctx.condition_type = "llm"
            ctx.condition_result = True
            ctx.response = "Edge has LLM condition configured"


# =============================================================================
# TEST CASES - AGENT EXECUTION
# =============================================================================

@pytest.mark.asyncio
class TestSalonAgents:
    """Test individual agent execution with logging."""
    
    async def test_greeting_agent_responds(self, azure_llm, agent_context, workflow_logger):
        """Test greeting agent responds to hello."""
        agent = build_greeting_agent(azure_llm)
        user_message = "Hello!"
        
        with metrics_context(
            component_type='agent',
            component_id='greeting-agent',
            user_message=user_message,
        ) as ctx:
            result = await agent.run(user_message, agent_context)
            ctx.update_from_usage(result.usage) if hasattr(result, 'usage') else None
            ctx.response = str(result.content)
            
            assert result.is_success()
            assert len(result.content) > 0
    
    async def test_greeting_agent_answers_ai_question(self, azure_llm, agent_context, workflow_logger):
        """Test greeting agent answers 'are you AI' question."""
        agent = build_greeting_agent(azure_llm)
        user_message = "Are you a real person or AI?"
        
        with metrics_context(
            component_type='agent',
            component_id='greeting-agent',
            user_message=user_message,
        ) as ctx:
            result = await agent.run(user_message, agent_context)
            ctx.update_from_usage(result.usage) if hasattr(result, 'usage') else None
            ctx.response = str(result.content)
            
            assert result.is_success()
            assert len(result.content) > 0
    
    async def test_greeting_agent_handles_booking_intent(self, azure_llm, agent_context, workflow_logger):
        """Test greeting agent handles booking intent."""
        agent = build_greeting_agent(azure_llm)
        user_message = "I'd like to book a haircut please"
        
        with metrics_context(
            component_type='agent',
            component_id='greeting-agent',
            user_message=user_message,
        ) as ctx:
            result = await agent.run(user_message, agent_context)
            ctx.update_from_usage(result.usage) if hasattr(result, 'usage') else None
            ctx.response = str(result.content)
            
            assert result.is_success()
            assert len(result.content) > 0
    
    async def test_booking_agent_offers_addon(self, azure_llm, agent_context, workflow_logger):
        """Test booking agent offers add-on for haircut."""
        agent = build_booking_agent(azure_llm)
        user_message = "I want to book a haircut"
        
        with metrics_context(
            component_type='agent',
            component_id='booking-agent',
            user_message=user_message,
        ) as ctx:
            result = await agent.run(user_message, agent_context)
            ctx.update_from_usage(result.usage) if hasattr(result, 'usage') else None
            ctx.response = str(result.content)
            
            assert result.is_success()
            assert len(result.content) > 0
    
    async def test_cancellation_agent_asks_which_appointment(self, azure_llm, agent_context, workflow_logger):
        """Test cancellation agent asks which appointment."""
        agent = build_cancellation_agent(azure_llm)
        user_message = "I need to cancel my appointment"
        
        with metrics_context(
            component_type='agent',
            component_id='cancellation-agent',
            user_message=user_message,
        ) as ctx:
            result = await agent.run(user_message, agent_context)
            ctx.update_from_usage(result.usage) if hasattr(result, 'usage') else None
            ctx.response = str(result.content)
            
            assert result.is_success()
            assert len(result.content) > 0


# =============================================================================
# TEST CASES - EDGE CONDITION EVALUATION
# =============================================================================

@pytest.mark.asyncio
class TestEdgeConditions:
    """Test edge condition evaluation."""
    
    async def test_expression_condition_evaluation(self, workflow_logger):
        """Test expression-based condition evaluation."""
        edge = create_booking_to_cancellation_edge()
        condition = edge.conditions.conditions[0]
        
        with metrics_context(
            component_type='condition',
            condition_type='expression',
        ) as ctx:
            context_match = {"variables": {"guest_intent": "cancellation"}}
            result = condition.evaluate(context_match)
            ctx.condition_result = result
            
            assert result is True
        
        with metrics_context(
            component_type='condition',
            condition_type='expression',
        ) as ctx:
            context_no_match = {"variables": {"guest_intent": "booking"}}
            result = condition.evaluate(context_no_match)
            ctx.condition_result = result
            
            assert result is False
    
    async def test_llm_condition_booking_intent(self, azure_llm, workflow_logger):
        """Test LLM condition detects booking intent."""
        edge = create_greeting_to_booking_edge(azure_llm)
        llm_condition = edge.conditions.conditions[0]
        
        context = {
            "messages": [
                {"role": "user", "content": "Hi there!"},
                {"role": "assistant", "content": "Hi! Welcome to Glamour Salon. How can I help you today?"},
                {"role": "user", "content": "I'd like to book a haircut please."},
            ],
            "last_output": "Great! I'd be happy to help you book a haircut appointment.",
            "variables": {}
        }
        
        with metrics_context(
            component_type='condition',
            condition_type='llm',
        ) as ctx:
            result = await llm_condition.evaluate_async(context, azure_llm)
            ctx.condition_result = result
            
            assert isinstance(result, bool)
    
    async def test_llm_condition_no_booking_intent(self, azure_llm, workflow_logger):
        """Test LLM condition does not trigger for general questions."""
        edge = create_greeting_to_booking_edge(azure_llm)
        llm_condition = edge.conditions.conditions[0]
        
        context = {
            "messages": [
                {"role": "user", "content": "What are your hours?"},
            ],
            "last_output": "We're open Monday to Saturday, 9 AM to 8 PM.",
            "variables": {}
        }
        
        with metrics_context(
            component_type='condition',
            condition_type='llm',
        ) as ctx:
            result = await llm_condition.evaluate_async(context, azure_llm)
            ctx.condition_result = result
            
            assert result is False
    
    async def test_llm_condition_cancellation_intent(self, azure_llm, workflow_logger):
        """Test LLM condition detects cancellation intent."""
        edge = create_booking_to_cancellation_edge_llm(azure_llm)
        llm_condition = edge.conditions.conditions[0]
        
        context = {
            "messages": [
                {"role": "user", "content": "Actually, I need to cancel my existing appointment first."},
            ],
            "last_output": "I understand you'd like to modify an existing appointment.",
            "variables": {}
        }
        
        with metrics_context(
            component_type='condition',
            condition_type='llm',
        ) as ctx:
            result = await llm_condition.evaluate_async(context, azure_llm)
            ctx.condition_result = result
            
            assert result is True


# =============================================================================
# TEST CASES - PASS-THROUGH FIELD EXTRACTION
# =============================================================================

@pytest.mark.asyncio
class TestPassThroughExtraction:
    """Test pass-through field extraction with logging."""
    
    async def test_extract_service_name(self, azure_llm, workflow_logger):
        """Test extracting service_name from conversation."""
        edge = create_greeting_to_booking_edge(azure_llm)
        
        context = {
            "messages": [
                {"role": "user", "content": "I'd like to book a haircut please."},
                {"role": "assistant", "content": "Great! I'd be happy to help you book a haircut."},
            ],
            "variables": {}
        }
        
        with metrics_context(component_type='edge',
            edge_id=edge.id,
            source_node=edge.source_node_id,
            target_node=edge.target_node_id
        ) as ctx:
            extracted = await edge.extract_pass_through_fields(context, azure_llm)
            ctx.extracted_fields = extracted
            
            assert "service_name" in extracted
            assert "haircut" in extracted["service_name"].lower()
    
    async def test_extract_service_name_hair_color(self, azure_llm, workflow_logger):
        """Test extracting 'hair color' service name."""
        edge = create_greeting_to_booking_edge(azure_llm)
        
        context = {
            "messages": [
                {"role": "user", "content": "I want to get my hair colored."},
            ],
            "variables": {}
        }
        
        with metrics_context(component_type='edge',edge_id=edge.id) as ctx:
            extracted = await edge.extract_pass_through_fields(context, azure_llm)
            ctx.extracted_fields = extracted
            
            assert "service_name" in extracted
            assert "color" in extracted["service_name"].lower()


# =============================================================================
# TEST CASES - MULTI-TURN CONVERSATIONS
# =============================================================================

@pytest.mark.asyncio
class TestMultiTurnConversations:
    """Test multi-turn conversations with logging."""
    
    async def test_greeting_conversation_flow(self, azure_llm, agent_context, workflow_logger):
        """Test multi-turn conversation with greeting agent."""
        agent = build_greeting_agent(azure_llm)
        
        conversations = [
            "Hello!",
            "Are you AI or human?",
            "What services do you offer?",
            "I'd like to book a haircut please.",
        ]
        
        with metrics_context(component_type='workflow',
            workflow_id="greeting_conversation_flow",
            workflow_name="Greeting Conversation Test"
        ):
            for i, user_message in enumerate(conversations, 1):
                with metrics_context(component_type='agent',
                    agent_id=f"greeting-agent-turn-{i}",
                    user_message=user_message
                ) as ctx:
                    result = await agent.run(user_message, agent_context)
                    if hasattr(result, 'usage'):
                        ctx.update_from_usage(result.usage)
                    ctx.response = str(result.content)
                    
                    assert result.is_success()
    
    async def test_booking_flow_with_addon(self, azure_llm, agent_context, workflow_logger):
        """Test booking flow with add-on offering."""
        agent = build_booking_agent(azure_llm)
        
        conversations = [
            "I want to book a haircut",
            "Yes, I'd like to add the hair color too!",
            "How about this Saturday at 2pm?",
        ]
        
        with metrics_context(component_type='workflow',
            workflow_id="booking_flow_with_addon",
            workflow_name="Booking Flow Test"
        ):
            for i, user_message in enumerate(conversations, 1):
                with metrics_context(component_type='agent',
                    agent_id=f"booking-agent-turn-{i}",
                    user_message=user_message
                ) as ctx:
                    result = await agent.run(user_message, agent_context)
                    if hasattr(result, 'usage'):
                        ctx.update_from_usage(result.usage)
                    ctx.response = str(result.content)
                    
                    assert result.is_success()


# =============================================================================
# TEST CASES - CONDITION GROUP LOGIC
# =============================================================================

class TestConditionGroupLogic:
    """Test condition group AND/OR logic."""
    
    def test_and_group(self, workflow_logger):
        """Test AND condition group."""
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
        
        with metrics_context(component_type='condition',
            condition_type="and_group",
            condition_description="intent=booking AND has_service=true"
        ) as ctx:
            context_both = {"intent": "booking", "has_service": True}
            result = and_group.evaluate(context_both)
            ctx.condition_result = result
            assert result is True
        
        with metrics_context(component_type='condition',
            condition_type="and_group",
            condition_description="intent=booking AND has_service=false"
        ) as ctx:
            context_one = {"intent": "booking", "has_service": False}
            result = and_group.evaluate(context_one)
            ctx.condition_result = result
            assert result is False
    
    def test_or_group(self, workflow_logger):
        """Test OR condition group."""
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
        
        with metrics_context(component_type='condition',
            condition_type="or_group",
            condition_description="intent=cancellation OR intent=reschedule"
        ) as ctx:
            result = or_group.evaluate({"intent": "cancellation"})
            ctx.condition_result = result
            assert result is True
        
        with metrics_context(component_type='condition',
            condition_type="or_group",
            condition_description="intent=booking (neither match)"
        ) as ctx:
            result = or_group.evaluate({"intent": "booking"})
            ctx.condition_result = result
            assert result is False


# =============================================================================
# TEST CASES - INTERRUPT HANDLING
# =============================================================================

class TestInterruptHandling:
    """Tests for interrupt handling in workflows."""
    
    def test_interrupt_manager_creation(self):
        """Test creating an interrupt manager."""
        from core.workflows.interrupt import (
            InterruptManager,
            InterruptConfig,
        )
        
        config = InterruptConfig(
            enabled=True,
            wait_for_followup_ms=500,
        )
        manager = InterruptManager(
            config=config,
            component_id="test-agent",
            component_type="agent",
        )
        
        assert manager.is_enabled is True
        assert manager.is_interrupted() is False
    
    def test_interrupt_signal(self):
        """Test sending interrupt signal."""
        from core.workflows.interrupt import (
            InterruptManager,
            InterruptConfig,
            InterruptReason,
        )
        
        manager = InterruptManager(
            config=InterruptConfig(enabled=True),
            component_id="test-llm",
            component_type="llm",
        )
        
        # Signal interrupt
        manager.signal_interrupt(
            reason=InterruptReason.USER_INTERRUPT,
            new_message="Actually, I changed my mind",
        )
        
        assert manager.is_interrupted() is True
        assert manager.has_followup() is True
        assert manager.get_followup_message() == "Actually, I changed my mind"
    
    def test_stash_partial_response(self):
        """Test stashing partial response."""
        from core.workflows.interrupt import (
            InterruptManager,
            InterruptConfig,
            InterruptReason,
        )
        
        manager = InterruptManager(
            config=InterruptConfig(enabled=True, stash_partial_response=True),
            component_id="test-agent",
            component_type="agent",
        )
        
        # Signal interrupt
        manager.signal_interrupt(reason=InterruptReason.USER_INTERRUPT)
        
        # Stash partial response
        manager.stash_partial_response(
            content="I was about to say that your appointment is scheduled for...",
            conversation_messages=[
                {"role": "user", "content": "Book a haircut"},
                {"role": "assistant", "content": "I'd be happy to help!"},
            ],
            tokens_generated=50,
        )
        
        assert manager.has_stashed_response() is True
        
        stashed = manager.get_stashed_response()
        assert stashed is not None
        assert "appointment is scheduled" in stashed.content
        assert stashed.tokens_generated == 50
    
    def test_interrupt_disabled(self):
        """Test that interrupt does nothing when disabled."""
        from core.workflows.interrupt import (
            InterruptManager,
            InterruptConfig,
        )
        
        manager = InterruptManager(
            config=InterruptConfig(enabled=False),
            component_id="test",
            component_type="test",
        )
        
        manager.signal_interrupt()
        
        assert manager.is_interrupted() is False
    
    def test_clear_interrupt(self):
        """Test clearing interrupt state."""
        from core.workflows.interrupt import (
            InterruptManager,
            InterruptConfig,
        )
        
        manager = InterruptManager(
            config=InterruptConfig(enabled=True),
            component_id="test",
            component_type="test",
        )
        
        manager.signal_interrupt()
        assert manager.is_interrupted() is True
        
        manager.clear_interrupt()
        assert manager.is_interrupted() is False
    
    def test_continuation_messages(self):
        """Test getting continuation messages after interrupt."""
        from core.workflows.interrupt import (
            InterruptManager,
            InterruptConfig,
            InterruptReason,
        )
        
        manager = InterruptManager(
            config=InterruptConfig(
                enabled=True,
                include_conversation_history=True,
                max_history_messages=10,
            ),
            component_id="test-agent",
            component_type="agent",
        )
        
        conversation = [
            {"role": "user", "content": "Book a haircut"},
            {"role": "assistant", "content": "Sure! When would you like?"},
        ]
        
        # Signal interrupt with new message
        manager.signal_interrupt(
            reason=InterruptReason.USER_INTERRUPT,
            new_message="Wait, actually make it a hair coloring",
        )
        
        # Stash partial response
        manager.stash_partial_response(
            content="Your haircut is scheduled for...",
            conversation_messages=conversation,
        )
        
        # Get continuation messages
        messages = manager.get_continuation_messages(conversation)
        
        # Should have conversation history + continuation prompt
        assert len(messages) > 0
        # Last message should be the continuation prompt
        last_msg = messages[-1]
        assert last_msg["role"] == "user"
        assert "interrupted" in last_msg["content"].lower() or "hair coloring" in last_msg["content"]


# =============================================================================
# TEST CASES - WORKING MEMORY INTEGRATION
# =============================================================================

class TestWorkingMemoryIntegration:
    """Tests for working memory integration with workflows."""
    
    def test_workflow_with_memory(self, azure_llm, workflow_logger):
        """Test workflow with working memory."""
        from core.memory import WorkingMemory
        
        memory = WorkingMemory(session_id="salon-workflow-session")
        
        # Simulate workflow execution
        with metrics_context(component_type='workflow',
            workflow_id="salon-workflow",
            workflow_name="Salon with Memory"
        ):
            # Greeting phase
            memory.add_user_message("Hello!")
            memory.set_variable("current_node", "greeting")
            memory.save_checkpoint("start")
            
            memory.add_assistant_message("Welcome to Glamour Salon!")
            
            # Service selection
            memory.add_user_message("I want to book a haircut")
            memory.set_variable("service_name", "haircut")
            memory.set_variable("current_node", "booking")
            memory.save_checkpoint("after-greeting")
            
            # Verify memory state
            history = memory.get_conversation_history()
            assert len(history) == 3
            assert memory.get_variable("service_name") == "haircut"
            
            # Test checkpoint recovery
            memory.restore_from_checkpoint("start")
            assert memory.get_variable("current_node") == "greeting"
    
    def test_memory_state_for_agent(self, azure_llm, agent_context, workflow_logger):
        """Test memory provides state for agent execution."""
        from core.memory import WorkingMemory
        
        memory = WorkingMemory(session_id="agent-session")
        
        # Set up conversation context
        memory.add_system_message(GREETING_AGENT_SYSTEM_PROMPT)
        memory.add_user_message("Hello!")
        
        with metrics_context(component_type='agent',
            agent_id="greeting-agent",
            user_message="Hello!"
        ):
            # Agent can use memory for LLM messages
            llm_messages = memory.get_conversation_history()
            
            assert len(llm_messages) == 2
            assert llm_messages[0]["role"] == "system"
            assert llm_messages[1]["role"] == "user"
    
    def test_memory_checkpoint_workflow_recovery(self, workflow_logger):
        """Test workflow can recover from checkpoints."""
        from core.memory import WorkingMemory
        
        memory = WorkingMemory(session_id="recovery-test")
        
        # Simulate partial workflow execution
        memory.add_user_message("Book haircut")
        memory.set_state("workflow_step", 1)
        memory.set_variable("intent", "booking")
        memory.save_checkpoint("step-1")
        
        memory.add_assistant_message("What time?")
        memory.add_user_message("2pm tomorrow")
        memory.set_state("workflow_step", 2)
        memory.set_variable("time", "2pm")
        memory.save_checkpoint("step-2")
        
        # Simulate failure - serialize state
        saved_state = memory.to_dict()
        
        # Simulate recovery in new process
        recovered_memory = WorkingMemory.from_dict(saved_state)
        
        # Can continue from step-2
        assert recovered_memory.get_state("workflow_step") == 2
        assert recovered_memory.get_variable("time") == "2pm"
        
        # Or rollback to step-1
        recovered_memory.restore_from_checkpoint("step-1")
        assert recovered_memory.get_state("workflow_step") == 1
        assert recovered_memory.get_variable("time") is None


# =============================================================================
# TEST CASES - MEMORY SERIALIZATION (JSON/TOML)
# =============================================================================

class TestMemorySerialization:
    """Tests for memory JSON/TOML serialization."""
    
    def test_working_memory_to_json(self):
        """Test serializing working memory to JSON."""
        from core.memory import WorkingMemory
        
        memory = WorkingMemory(session_id="json-test")
        memory.add_system_message("You are a salon assistant.")
        memory.add_user_message("I want to book a haircut")
        memory.add_assistant_message("Great! When would you like to come in?")
        memory.set_variable("service_name", "haircut")
        memory.set_variable("current_node", "booking")
        memory.save_checkpoint("booking-start")
        
        # Serialize to JSON
        json_str = memory.to_json()
        
        assert json_str is not None
        assert "json-test" in json_str
        assert "haircut" in json_str
        assert "booking" in json_str
        
        # Verify it's valid JSON
        import json
        data = json.loads(json_str)
        assert data["session_id"] == "json-test"
        assert data["variables"]["service_name"] == "haircut"
    
    def test_working_memory_from_json(self):
        """Test deserializing working memory from JSON."""
        from core.memory import WorkingMemory
        
        # Create and serialize
        original = WorkingMemory(session_id="json-restore-test")
        original.add_user_message("Hello!")
        original.add_assistant_message("Welcome!")
        original.set_variable("intent", "greeting")
        original.save_checkpoint("initial")
        
        json_str = original.to_json()
        
        # Deserialize
        restored = WorkingMemory.from_json(json_str)
        
        assert restored.session_id == "json-restore-test"
        assert len(restored.get_conversation_history()) == 2
        assert restored.get_variable("intent") == "greeting"
        assert len(restored.list_checkpoints()) == 1
    
    def test_working_memory_to_toml(self):
        """Test serializing working memory to TOML."""
        from core.memory import WorkingMemory
        
        try:
            memory = WorkingMemory(session_id="toml-test")
            memory.add_user_message("Book appointment")
            memory.set_variable("service", "haircut")
            memory.set_variable("date", "tomorrow")
            
            # Serialize to TOML
            toml_str = memory.to_toml()
            
            assert toml_str is not None
            assert "toml-test" in toml_str
            assert "haircut" in toml_str
            assert "tomorrow" in toml_str
            
        except ImportError as e:
            pytest.skip(f"TOML support not available: {e}")
    
    def test_working_memory_from_toml(self):
        """Test deserializing working memory from TOML."""
        from core.memory import WorkingMemory
        
        try:
            # Create and serialize
            original = WorkingMemory(session_id="toml-restore-test")
            original.add_user_message("Cancel my appointment")
            original.set_variable("intent", "cancellation")
            
            toml_str = original.to_toml()
            
            # Deserialize
            restored = WorkingMemory.from_toml(toml_str)
            
            assert restored.session_id == "toml-restore-test"
            assert len(restored.get_conversation_history()) == 1
            assert restored.get_variable("intent") == "cancellation"
            
        except ImportError as e:
            pytest.skip(f"TOML support not available: {e}")
    
    def test_conversation_history_to_json(self):
        """Test serializing conversation history to JSON."""
        from core.memory import ConversationHistory
        
        history = ConversationHistory()
        history.add_message("system", "You are helpful.")
        history.add_message("user", "Hello!")
        history.add_message("assistant", "Hi there!")
        
        json_str = history.to_json()
        
        assert json_str is not None
        import json
        data = json.loads(json_str)
        assert len(data["messages"]) == 3
    
    def test_conversation_history_from_json(self):
        """Test deserializing conversation history from JSON."""
        from core.memory import ConversationHistory
        
        original = ConversationHistory()
        original.add_message("user", "Test message")
        original.add_message("assistant", "Test response")
        
        json_str = original.to_json()
        restored = ConversationHistory.from_json(json_str)
        
        assert restored.get_message_count() == 2
        assert restored.get_last_message()["content"] == "Test response"
    
    def test_state_tracker_to_json(self):
        """Test serializing state tracker to JSON."""
        from core.memory import InMemoryStateTracker
        
        tracker = InMemoryStateTracker(session_id="tracker-json-test")
        tracker.set_state("current_node", "greeting")
        tracker.set_state("step", 1)
        tracker.save_checkpoint("cp-1", {"status": "completed"})
        
        json_str = tracker.to_json()
        
        assert json_str is not None
        import json
        data = json.loads(json_str)
        assert data["session_id"] == "tracker-json-test"
        assert data["state"]["current_node"] == "greeting"
    
    def test_state_tracker_from_json(self):
        """Test deserializing state tracker from JSON."""
        from core.memory import InMemoryStateTracker
        
        original = InMemoryStateTracker(session_id="tracker-restore")
        original.set_state("key", "value")
        original.save_checkpoint("cp-1", {"data": "test"})
        
        json_str = original.to_json()
        restored = InMemoryStateTracker.from_json(json_str)
        
        assert restored.session_id == "tracker-restore"
        assert restored.get_state("key") == "value"
        assert len(restored.list_checkpoints()) == 1


# =============================================================================
# TEST CASES - MEMORY FILE SAVE/LOAD
# =============================================================================

class TestMemoryFilePersistence:
    """Tests for saving/loading memory to/from files."""
    
    def test_save_and_load_json_file(self, tmp_path):
        """Test saving and loading memory to JSON file."""
        from core.memory import WorkingMemory
        
        memory = WorkingMemory(session_id="file-json-test")
        memory.add_user_message("Book a haircut")
        memory.set_variable("service", "haircut")
        memory.save_checkpoint("initial")
        
        # Save to JSON file
        json_file = tmp_path / "memory.json"
        memory.save(json_file)
        
        assert json_file.exists()
        
        # Load from JSON file
        loaded = WorkingMemory.load(json_file)
        
        assert loaded.session_id == "file-json-test"
        assert loaded.get_variable("service") == "haircut"
        assert len(loaded.list_checkpoints()) == 1
    
    def test_save_and_load_toml_file(self, tmp_path):
        """Test saving and loading memory to TOML file."""
        from core.memory import WorkingMemory
        
        try:
            memory = WorkingMemory(session_id="file-toml-test")
            memory.add_user_message("Cancel appointment")
            memory.set_variable("intent", "cancellation")
            
            # Save to TOML file
            toml_file = tmp_path / "memory.toml"
            memory.save(toml_file)
            
            assert toml_file.exists()
            
            # Load from TOML file
            loaded = WorkingMemory.load(toml_file)
            
            assert loaded.session_id == "file-toml-test"
            assert loaded.get_variable("intent") == "cancellation"
            
        except ImportError as e:
            pytest.skip(f"TOML support not available: {e}")
    
    def test_auto_detect_format_from_extension(self, tmp_path):
        """Test that format is auto-detected from file extension."""
        from core.memory import WorkingMemory
        
        memory = WorkingMemory(session_id="auto-detect-test")
        memory.set_variable("key", "value")
        
        # Save as JSON (detected from .json extension)
        json_file = tmp_path / "auto.json"
        memory.save(json_file)
        
        # Verify it's valid JSON
        import json
        with open(json_file) as f:
            data = json.load(f)
        assert data["session_id"] == "auto-detect-test"


# =============================================================================
# TEST CASES - MEMORY FACTORY WITH CUSTOM IMPLEMENTATIONS
# =============================================================================

class TestMemoryFactoryCustomImplementations:
    """Tests for memory factory with custom implementations."""
    
    def test_register_custom_working_memory(self):
        """Test registering and using custom working memory implementation."""
        from core.memory import (
            MemoryFactory,
            BaseWorkingMemory,
            DefaultConversationHistory,
            DefaultStateTracker,
        )
        from core.memory.state.models import MemoryState
        
        class SalonWorkingMemory(BaseWorkingMemory):
            """Custom working memory for salon workflows."""
            
            def __init__(self, salon_id: str = None, **kwargs):
                super().__init__(**kwargs)
                self._salon_id = salon_id or "default-salon"
                self._conversation = DefaultConversationHistory(self._max_messages)
                self._state_tracker = DefaultStateTracker(
                    self._session_id, self._max_checkpoints
                )
                self._state_tracker.set_messages_reference(self._conversation._messages)
                self._state_tracker.set_variables_reference(self._variables)
            
            @property
            def salon_id(self) -> str:
                return self._salon_id
            
            @property
            def conversation(self):
                return self._conversation
            
            @property
            def state_tracker(self):
                return self._state_tracker
            
            def add_message(self, role, content, metadata=None):
                return self._conversation.add_message(role, content, metadata)
            
            def get_conversation_history(self, max_messages=None):
                return self._conversation.to_llm_messages(max_messages)
            
            def save_checkpoint(self, checkpoint_id, metadata=None):
                state = {"salon_id": self._salon_id}
                return self._state_tracker.save_checkpoint(checkpoint_id, state, metadata)
            
            def restore_from_checkpoint(self, checkpoint_id):
                cp = self._state_tracker.get_checkpoint(checkpoint_id)
                if not cp:
                    return False
                self._conversation.set_raw_messages(cp.messages)
                self._variables.clear()
                self._variables.update(cp.variables)
                return True
            
            def clear(self):
                self._conversation.clear_messages()
                self._variables.clear()
                self._state_tracker.clear_state()
                self._state_tracker.clear_checkpoints()
            
            def to_dict(self):
                return {
                    "session_id": self._session_id,
                    "salon_id": self._salon_id,
                    "conversation": self._conversation.to_dict(),
                    "variables": self._variables.copy(),
                    "state_tracker": self._state_tracker.to_dict(),
                }
            
            @classmethod
            def from_dict(cls, data):
                memory = cls(
                    session_id=data["session_id"],
                    salon_id=data.get("salon_id"),
                )
                if "conversation" in data:
                    memory._conversation = DefaultConversationHistory.from_dict(data["conversation"])
                memory._variables = data.get("variables", {}).copy()
                if "state_tracker" in data:
                    memory._state_tracker = DefaultStateTracker.from_dict(data["state_tracker"])
                memory._state_tracker.set_messages_reference(memory._conversation._messages)
                memory._state_tracker.set_variables_reference(memory._variables)
                return memory
            
            def create_memory_state(self):
                return MemoryState(
                    session_id=self._session_id,
                    messages=self._conversation.get_raw_messages(),
                    state=self._state_tracker.get_full_state(),
                    variables=self._variables.copy(),
                )
        
        # Register custom implementation
        MemoryFactory.register_working_memory("salon", SalonWorkingMemory)
        
        # Create using factory
        memory = MemoryFactory.create_working_memory(
            session_id="salon-session",
            implementation="salon",
            salon_id="glamour-salon",
        )
        
        assert isinstance(memory, SalonWorkingMemory)
        assert memory.salon_id == "glamour-salon"
        
        # Use the memory
        memory.add_user_message("Book a haircut")
        memory.set_variable("service", "haircut")
        
        assert len(memory.get_conversation_history()) == 1
        assert memory.get_variable("service") == "haircut"
    
    def test_list_registered_implementations(self):
        """Test listing registered implementations."""
        from core.memory import MemoryFactory
        
        implementations = MemoryFactory.list_working_memory_implementations()
        
        assert "default" in implementations
        assert isinstance(implementations, list)
    
    def test_create_from_config_with_implementation(self):
        """Test creating memory from config with implementation."""
        from core.memory import MemoryFactory, WorkingMemory
        
        memory = MemoryFactory.create_from_config({
            "type": "working",
            "implementation": "default",
            "session_id": "config-test",
            "max_messages": 100,
        })
        
        assert isinstance(memory, WorkingMemory)
        assert memory.session_id == "config-test"
    
    def test_invalid_implementation_raises_error(self):
        """Test that invalid implementation raises ValueError."""
        from core.memory import MemoryFactory
        
        with pytest.raises(ValueError) as exc_info:
            MemoryFactory.create_working_memory(
                implementation="nonexistent"
            )
        
        assert "nonexistent" in str(exc_info.value)


# =============================================================================
# TEST CASES - MEMORY BASE CLASSES
# =============================================================================

class TestMemoryBaseClasses:
    """Tests for memory base classes."""
    
    def test_base_conversation_history_abstract(self):
        """Test that BaseConversationHistory is abstract."""
        from core.memory.conversation_history import BaseConversationHistory
        
        # Cannot instantiate directly
        with pytest.raises(TypeError):
            BaseConversationHistory()
    
    def test_base_state_tracker_abstract(self):
        """Test that BaseStateTracker is abstract."""
        from core.memory.state_tracker import BaseStateTracker
        
        # Cannot instantiate directly
        with pytest.raises(TypeError):
            BaseStateTracker(session_id="test")
    
    def test_base_working_memory_abstract(self):
        """Test that BaseWorkingMemory is abstract."""
        from core.memory.working_memory import BaseWorkingMemory
        
        # Cannot instantiate directly
        with pytest.raises(TypeError):
            BaseWorkingMemory()
    
    def test_default_conversation_history_implements_interface(self):
        """Test DefaultConversationHistory implements IConversationMemory protocol."""
        from core.memory import ConversationHistory
        
        history = ConversationHistory()
        
        # Check it has all required methods
        assert hasattr(history, 'add_message')
        assert hasattr(history, 'get_messages')
        assert hasattr(history, 'get_last_message')
        assert hasattr(history, 'get_message_count')
        assert hasattr(history, 'clear_messages')
        assert hasattr(history, 'to_llm_messages')
        
        # Check serialization methods from mixin
        assert hasattr(history, 'to_json')
        assert hasattr(history, 'to_toml')
        assert hasattr(history, 'from_json')
        assert hasattr(history, 'from_toml')
        assert hasattr(history, 'save')
        assert hasattr(history, 'load')
    
    def test_default_state_tracker_implements_interface(self):
        """Test DefaultStateTracker implements IStateTracker protocol."""
        from core.memory import InMemoryStateTracker
        
        tracker = InMemoryStateTracker(session_id="test")
        
        # Check it has all required methods
        assert hasattr(tracker, 'save_checkpoint')
        assert hasattr(tracker, 'get_checkpoint')
        assert hasattr(tracker, 'get_latest_checkpoint')
        assert hasattr(tracker, 'list_checkpoints')
        assert hasattr(tracker, 'delete_checkpoint')
        assert hasattr(tracker, 'clear_checkpoints')
        assert hasattr(tracker, 'get_state')
        assert hasattr(tracker, 'set_state')
        assert hasattr(tracker, 'get_full_state')
        
        # Check serialization methods from mixin
        assert hasattr(tracker, 'to_json')
        assert hasattr(tracker, 'to_toml')
    
    def test_default_working_memory_implements_interface(self):
        """Test DefaultWorkingMemory implements IWorkingMemory protocol."""
        from core.memory import WorkingMemory
        
        memory = WorkingMemory()
        
        # Check it has all required properties
        assert hasattr(memory, 'session_id')
        assert hasattr(memory, 'conversation')
        assert hasattr(memory, 'state_tracker')
        
        # Check it has all required methods
        assert hasattr(memory, 'add_message')
        assert hasattr(memory, 'get_conversation_history')
        assert hasattr(memory, 'set_variable')
        assert hasattr(memory, 'get_variable')
        assert hasattr(memory, 'save_checkpoint')
        assert hasattr(memory, 'restore_from_checkpoint')
        
        # Check serialization methods from mixin
        assert hasattr(memory, 'to_json')
        assert hasattr(memory, 'to_toml')
        assert hasattr(memory, 'save')
        assert hasattr(memory, 'load')


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("\n" + "="*80)
    print("Running Salon Workflow Tests with Production Logging")
    print("="*80)
    pytest.main([__file__, "-v", "--tb=short", "-x", "-s"])
