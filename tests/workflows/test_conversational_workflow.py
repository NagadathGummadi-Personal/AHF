"""
Conversational AI Workflow Test.

This test demonstrates how to build a conversational AI workflow similar to 
ElevenLabs' agent configuration but with more customization options.

Features tested:
1. Multiple agent nodes (Greeter, Booking, FAQ, Support)
2. Decision nodes for intent-based routing
3. Conditional edges
4. Custom node types and edge types
5. Workflow context and variable passing
6. TTS/ASR-like configuration options
7. Node/Edge factories with custom registration
8. Full workflow execution with streaming
"""

import pytest
import asyncio
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

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
    TransformSpec,
    WorkflowContext,
    RetryConfig,
    # Implementations
    Workflow,
    BaseNode,
    BaseEdge,
    AgentNode,
    StartNode,
    EndNode,
    DecisionNode,
    TransformNode,
    # Factories
    NodeFactory,
    EdgeFactory,
    # Interfaces
    INode,
    IEdge,
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
logger = LoggerAdaptor.get_logger("tests.workflows.conversational")


# ============================================================================
# CONFIGURATION - Similar to ElevenLabs Agent Config
# ============================================================================

class ConversationConfig:
    """Configuration similar to ElevenLabs conversation_config."""
    
    def __init__(
        self,
        # ASR (Automatic Speech Recognition) Config
        asr_provider: str = "azure",
        asr_language: str = "en-US",
        asr_quality: str = "high",
        # TTS (Text-to-Speech) Config  
        tts_provider: str = "elevenlabs",
        tts_voice_id: str = "default_voice",
        tts_model: str = "eleven_turbo_v2",
        tts_stability: float = 0.5,
        tts_similarity: float = 0.75,
        # Turn Config
        turn_timeout_seconds: float = 30.0,
        silence_end_threshold_ms: int = 1000,
        max_duration_seconds: float = 600.0,
        # Agent Config
        agent_prompt: str = "",
        first_message: Optional[str] = None,
        language: str = "en",
        # LLM Config
        llm_provider: str = "azure",
        llm_model: str = "gpt-4",
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ):
        self.asr = {
            "provider": asr_provider,
            "language": asr_language,
            "quality": asr_quality,
        }
        self.tts = {
            "provider": tts_provider,
            "voice_id": tts_voice_id,
            "model": tts_model,
            "stability": tts_stability,
            "similarity": tts_similarity,
        }
        self.turn = {
            "timeout_seconds": turn_timeout_seconds,
            "silence_end_threshold_ms": silence_end_threshold_ms,
            "max_duration_seconds": max_duration_seconds,
        }
        self.agent = {
            "prompt": agent_prompt,
            "first_message": first_message,
            "language": language,
        }
        self.llm = {
            "provider": llm_provider,
            "model": llm_model,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "asr": self.asr,
            "tts": self.tts,
            "turn": self.turn,
            "agent": self.agent,
            "llm": self.llm,
        }


# ============================================================================
# CUSTOM NODE TYPES
# ============================================================================

class GreeterNode(BaseNode):
    """
    Custom node for greeting users and collecting initial intent.
    
    Similar to an ElevenLabs agent's first interaction.
    """
    
    def __init__(self, spec: NodeSpec, conversation_config: Optional[ConversationConfig] = None):
        super().__init__(spec)
        logger.debug(f"[GREETER:INIT] Initializing GreeterNode: {spec.name}")
        self._conversation_config = conversation_config or ConversationConfig()
        self._first_message = self._config.get(
            "first_message", 
            self._conversation_config.agent["first_message"]
        ) or "Hello! How can I help you today?"
        self._greeting_variations = self._config.get("greeting_variations", [
            "Hello! Welcome to our service. How may I assist you?",
            "Hi there! I'm here to help. What can I do for you today?",
            "Good day! How can I help you?",
        ])
        logger.debug(f"[GREETER:INIT] First message configured: '{self._first_message[:50]}...'")
    
    async def execute(self, input_data: Any, context: IWorkflowContext) -> Any:
        """Execute the greeter node."""
        logger.info("+" + "-" * 68 + "+")
        logger.info(f"| [GREETER] Executing node: {self._name}".ljust(69) + "|")
        logger.info("+" + "-" * 68 + "+")
        
        # Step 1: Check conversation state
        logger.info("[GREETER:STEP 1] Checking conversation state...")
        is_new = context.get("is_new_conversation", True)
        user_name = context.get("user_name", "there")
        logger.info(f"[GREETER:STEP 1]   is_new_conversation: {is_new}")
        logger.info(f"[GREETER:STEP 1]   user_name: {user_name}")
        
        # Step 2: Generate greeting
        logger.info("[GREETER:STEP 2] Generating greeting...")
        if is_new:
            # First interaction - use first message
            greeting = self._first_message
            context.set("is_new_conversation", False)
            context.set("conversation_started_at", datetime.now().isoformat())
            logger.info(f"[GREETER:STEP 2]   New conversation - using first message")
        else:
            # Returning user - personalized greeting
            greeting = f"Welcome back, {user_name}! How can I help you today?"
            logger.info(f"[GREETER:STEP 2]   Returning user - personalized greeting")
        logger.info(f"[GREETER:STEP 2]   Greeting: '{greeting}'")
        
        # Step 3: Store conversation config
        logger.info("[GREETER:STEP 3] Storing conversation config in context...")
        context.set("conversation_config", self._conversation_config.to_dict())
        logger.info(f"[GREETER:STEP 3]   Config keys: {list(self._conversation_config.to_dict().keys())}")
        
        # Step 4: Build result
        logger.info("[GREETER:STEP 4] Building result object...")
        user_input = input_data.get("user_input", "") if isinstance(input_data, dict) else str(input_data)
        result = {
            "greeting": greeting,
            "user_input": user_input,
            "timestamp": datetime.now().isoformat(),
            "node_id": self._id,
        }
        logger.info(f"[GREETER:STEP 4]   User input: '{user_input[:50]}...' (len={len(user_input)})")
        
        logger.info(f"[GREETER:DONE] Node execution complete")
        return result


class IntentClassifierNode(BaseNode):
    """
    Custom node for classifying user intent.
    
    Determines which specialized agent should handle the request.
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
            "faq": ["question", "what is", "how do", "tell me", "explain", "info"],
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
        
        # Step 1: Extract user input
        logger.info("[INTENT:STEP 1] Extracting user input...")
        user_input = ""
        if isinstance(input_data, dict):
            user_input = input_data.get("user_input", "")
            logger.info(f"[INTENT:STEP 1]   Input type: dict")
        elif isinstance(input_data, str):
            user_input = input_data
            logger.info(f"[INTENT:STEP 1]   Input type: str")
        logger.info(f"[INTENT:STEP 1]   User input: '{user_input[:60]}...'")
        
        user_input_lower = user_input.lower()
        
        # Step 2: Keyword-based classification
        logger.info("[INTENT:STEP 2] Running keyword-based classification...")
        detected_intent = "unknown"
        confidence = 0.0
        matched_keyword = None
        
        for intent, keywords in self._intent_keywords.items():
            for keyword in keywords:
                if keyword in user_input_lower:
                    detected_intent = intent
                    confidence = 0.8  # Simplified confidence
                    matched_keyword = keyword
                    logger.info(f"[INTENT:STEP 2]   MATCH! keyword='{keyword}' -> intent='{intent}'")
                    break
            if detected_intent != "unknown":
                break
        
        # Step 3: Handle unknown intent
        logger.info("[INTENT:STEP 3] Checking for fallback...")
        if detected_intent == "unknown" and len(user_input) > 5:
            detected_intent = "faq"
            confidence = 0.5
            logger.info(f"[INTENT:STEP 3]   Unknown with input -> defaulting to 'faq'")
        elif detected_intent == "unknown":
            logger.info(f"[INTENT:STEP 3]   No fallback needed, input too short")
        else:
            logger.info(f"[INTENT:STEP 3]   No fallback needed, intent found")
        
        # Step 4: Store in context
        logger.info("[INTENT:STEP 4] Storing results in context...")
        context.set("detected_intent", detected_intent)
        context.set("intent_confidence", confidence)
        logger.info(f"[INTENT:STEP 4]   Set detected_intent='{detected_intent}'")
        logger.info(f"[INTENT:STEP 4]   Set intent_confidence={confidence}")
        
        # Step 5: Build result
        logger.info("[INTENT:STEP 5] Building result...")
        result = {
            "intent": detected_intent,
            "confidence": confidence,
            "user_input": user_input,
            "available_intents": self.INTENTS,
        }
        
        logger.info("+" + "-" * 68 + "+")
        logger.info(f"| [INTENT:RESULT] Intent: '{detected_intent}' (conf: {confidence:.2f})".ljust(69) + "|")
        logger.info("+" + "-" * 68 + "+")
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
        
        # Step 1: Extract user input
        logger.info("[BOOKING:STEP 1] Extracting user input...")
        user_input = input_data.get("user_input", "") if isinstance(input_data, dict) else str(input_data)
        logger.info(f"[BOOKING:STEP 1]   User input: '{user_input[:60]}...'")
        
        # Step 2: Get available slots
        logger.info("[BOOKING:STEP 2] Retrieving available slots...")
        slots_to_offer = self._available_slots[:3]
        logger.info(f"[BOOKING:STEP 2]   Slots to offer: {slots_to_offer}")
        
        # Step 3: Generate response
        logger.info("[BOOKING:STEP 3] Generating booking response...")
        response = f"I'd be happy to help you book an appointment. Here are our available slots: {', '.join(slots_to_offer)}. Which would you prefer?"
        logger.info(f"[BOOKING:STEP 3]   Response length: {len(response)} chars")
        
        # Step 4: Build result
        logger.info("[BOOKING:STEP 4] Building result...")
        result = {
            "response": response,
            "available_slots": self._available_slots,
            "action": "booking_offered",
            "user_input": user_input,
        }
        
        logger.info(f"[BOOKING:DONE] Offered {len(self._available_slots)} slots, action='booking_offered'")
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
        logger.debug(f"[FAQ:INIT] Knowledge base has {len(self._knowledge_base)} topics: {list(self._knowledge_base.keys())}")
    
    async def execute(self, input_data: Any, context: IWorkflowContext) -> Any:
        """Answer FAQ question."""
        logger.info("+" + "-" * 68 + "+")
        logger.info(f"| [FAQ] Executing node: {self._name}".ljust(69) + "|")
        logger.info("+" + "-" * 68 + "+")
        
        # Step 1: Extract user input
        logger.info("[FAQ:STEP 1] Extracting user input...")
        user_input = input_data.get("user_input", "") if isinstance(input_data, dict) else str(input_data)
        user_input_lower = user_input.lower()
        logger.info(f"[FAQ:STEP 1]   User input: '{user_input[:60]}...'")
        
        # Step 2: Search knowledge base
        logger.info("[FAQ:STEP 2] Searching knowledge base...")
        response = "I'm not sure about that. Let me transfer you to someone who can help better."
        matched_topic = None
        
        for topic, answer in self._knowledge_base.items():
            logger.debug(f"[FAQ:STEP 2]   Checking topic: '{topic}'...")
            if topic in user_input_lower:
                response = answer
                matched_topic = topic
                logger.info(f"[FAQ:STEP 2]   MATCH! topic='{topic}'")
                break
        
        if not matched_topic:
            logger.info(f"[FAQ:STEP 2]   No match found in knowledge base")
        
        # Step 3: Determine action
        logger.info("[FAQ:STEP 3] Determining action...")
        action = "faq_answered" if matched_topic else "faq_not_found"
        logger.info(f"[FAQ:STEP 3]   Action: '{action}'")
        
        # Step 4: Build result
        logger.info("[FAQ:STEP 4] Building result...")
        result = {
            "response": response,
            "matched_topic": matched_topic,
            "action": action,
            "user_input": user_input,
        }
        
        logger.info(f"[FAQ:DONE] Response: '{response[:50]}...'")
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
        
        # Step 1: Extract user input
        logger.info("[SUPPORT:STEP 1] Extracting user input...")
        user_input = input_data.get("user_input", "") if isinstance(input_data, dict) else str(input_data)
        user_input_lower = user_input.lower()
        logger.info(f"[SUPPORT:STEP 1]   User input: '{user_input[:60]}...'")
        
        # Step 2: Check for escalation keywords
        logger.info("[SUPPORT:STEP 2] Checking for escalation keywords...")
        matched_keywords = [kw for kw in self._escalation_keywords if kw in user_input_lower]
        needs_escalation = len(matched_keywords) > 0
        logger.info(f"[SUPPORT:STEP 2]   Matched keywords: {matched_keywords}")
        logger.info(f"[SUPPORT:STEP 2]   Needs escalation: {needs_escalation}")
        
        # Step 3: Generate response based on escalation
        logger.info("[SUPPORT:STEP 3] Generating response...")
        if needs_escalation:
            response = "I understand this is urgent. Let me connect you with a senior support specialist right away."
            action = "escalated"
            logger.info(f"[SUPPORT:STEP 3]   ESCALATION PATH - connecting to specialist")
        else:
            response = "I'm here to help! Could you please describe the issue you're experiencing in more detail?"
            action = "support_started"
            logger.info(f"[SUPPORT:STEP 3]   NORMAL PATH - requesting more details")
        
        # Step 4: Create support ticket
        logger.info("[SUPPORT:STEP 4] Creating support ticket...")
        ticket_id = f"TKT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        context.set("support_ticket_id", ticket_id)
        logger.info(f"[SUPPORT:STEP 4]   Ticket ID: {ticket_id}")
        logger.info(f"[SUPPORT:STEP 4]   Stored in context: support_ticket_id")
        
        # Step 5: Build result
        logger.info("[SUPPORT:STEP 5] Building result...")
        result = {
            "response": response,
            "action": action,
            "ticket_id": ticket_id,
            "needs_escalation": needs_escalation,
            "user_input": user_input,
        }
        
        logger.info(f"[SUPPORT:DONE] Ticket: {ticket_id}, Action: '{action}'")
        return result


class ResponseFormatterNode(BaseNode):
    """
    Node for formatting the final response with TTS-ready output.
    """
    
    def __init__(self, spec: NodeSpec):
        super().__init__(spec)
        logger.debug(f"[FORMATTER:INIT] Initializing ResponseFormatterNode: {spec.name}")
        self._add_closing = self._config.get("add_closing", True)
        self._closing_message = self._config.get("closing_message", "Is there anything else I can help you with?")
        logger.debug(f"[FORMATTER:INIT] add_closing={self._add_closing}, closing='{self._closing_message[:30]}...'")
    
    async def execute(self, input_data: Any, context: IWorkflowContext) -> Any:
        """Format the response for output."""
        logger.info("+" + "-" * 68 + "+")
        logger.info(f"| [FORMATTER] Executing node: {self._name}".ljust(69) + "|")
        logger.info("+" + "-" * 68 + "+")
        
        # Step 1: Extract response from input
        logger.info("[FORMATTER:STEP 1] Extracting response from input...")
        response = ""
        if isinstance(input_data, dict):
            response = input_data.get("response", str(input_data))
            logger.info(f"[FORMATTER:STEP 1]   Input type: dict, extracted 'response' key")
        else:
            response = str(input_data)
            logger.info(f"[FORMATTER:STEP 1]   Input type: {type(input_data)}, converted to str")
        logger.info(f"[FORMATTER:STEP 1]   Response: '{response[:60]}...'")
        
        # Step 2: Get TTS config
        logger.info("[FORMATTER:STEP 2] Getting TTS configuration...")
        conv_config = context.get("conversation_config", {})
        tts_config = conv_config.get("tts", {})
        logger.info(f"[FORMATTER:STEP 2]   TTS provider: {tts_config.get('provider', 'N/A')}")
        logger.info(f"[FORMATTER:STEP 2]   TTS voice: {tts_config.get('voice_id', 'N/A')}")
        
        # Step 3: Format response (add closing if needed)
        logger.info("[FORMATTER:STEP 3] Formatting response...")
        detected_intent = context.get("detected_intent")
        logger.info(f"[FORMATTER:STEP 3]   Detected intent: '{detected_intent}'")
        logger.info(f"[FORMATTER:STEP 3]   Add closing: {self._add_closing}")
        
        formatted_response = response
        if self._add_closing and detected_intent not in ["goodbye", "transfer"]:
            formatted_response = f"{response} {self._closing_message}"
            logger.info(f"[FORMATTER:STEP 3]   Added closing message")
        else:
            logger.info(f"[FORMATTER:STEP 3]   Skipped closing (intent='{detected_intent}')")
        
        # Step 4: Generate SSML
        logger.info("[FORMATTER:STEP 4] Generating SSML...")
        ssml = f"<speak>{formatted_response}</speak>"
        logger.info(f"[FORMATTER:STEP 4]   SSML length: {len(ssml)} chars")
        
        # Step 5: Build result
        logger.info("[FORMATTER:STEP 5] Building result...")
        result = {
            "text": formatted_response,
            "tts_config": tts_config,
            "ssml": ssml,
            "intent": detected_intent,
            "conversation_id": context.execution_id,
        }
        
        logger.info(f"[FORMATTER:DONE] Formatted response ({len(formatted_response)} chars)")
        return result


# ============================================================================
# CUSTOM OBSERVERS
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
        logger.info(f"[WORKFLOW_OBS]     Input: {str(input_data)[:80]}...")
        logger.info("=" * 70)
    
    async def on_workflow_complete(
        self, workflow: Any, output: Any, context: IWorkflowContext, duration_ms: float
    ) -> None:
        event = {
            "event": "workflow_complete",
            "workflow_name": workflow.name,
            "timestamp": datetime.now().isoformat(),
            "duration_ms": duration_ms,
            "output_preview": str(output)[:100] if output else None,
        }
        self.events.append(event)
        logger.info("=" * 70)
        logger.info(f"[WORKFLOW_OBS] <<< WORKFLOW COMPLETE: {workflow.name}")
        logger.info(f"[WORKFLOW_OBS]     Duration: {duration_ms:.2f}ms")
        logger.info(f"[WORKFLOW_OBS]     Execution path: {' -> '.join(context.execution_path)}")
        logger.info(f"[WORKFLOW_OBS]     Output type: {type(output).__name__}")
        logger.info("=" * 70)
    
    async def on_workflow_error(
        self, workflow: Any, error: Exception, context: IWorkflowContext
    ) -> None:
        event = {
            "event": "workflow_error",
            "workflow_name": workflow.name,
            "timestamp": datetime.now().isoformat(),
            "error": str(error),
        }
        self.events.append(event)
        logger.error(f"[OBSERVER] Workflow error: {error}")
    
    async def on_workflow_pause(
        self, workflow: Any, context: IWorkflowContext
    ) -> None:
        event = {
            "event": "workflow_pause",
            "workflow_name": workflow.name,
            "timestamp": datetime.now().isoformat(),
        }
        self.events.append(event)
        logger.info(f"[OBSERVER] Workflow paused: {workflow.name}")
    
    async def on_workflow_resume(
        self, workflow: Any, context: IWorkflowContext
    ) -> None:
        event = {
            "event": "workflow_resume",
            "workflow_name": workflow.name,
            "timestamp": datetime.now().isoformat(),
        }
        self.events.append(event)
        logger.info(f"[OBSERVER] Workflow resumed: {workflow.name}")
    
    async def on_workflow_cancel(
        self, workflow: Any, context: IWorkflowContext
    ) -> None:
        event = {
            "event": "workflow_cancel",
            "workflow_name": workflow.name,
            "timestamp": datetime.now().isoformat(),
        }
        self.events.append(event)
        logger.info(f"[OBSERVER] Workflow cancelled: {workflow.name}")


class NodeTrackingObserver(INodeObserver):
    """Observer that tracks node executions."""
    
    def __init__(self):
        self.node_executions: List[Dict[str, Any]] = []
        logger.debug("[NODE_OBS:INIT] NodeTrackingObserver initialized")
    
    async def on_node_start(
        self, node: INode, input_data: Any, context: IWorkflowContext
    ) -> None:
        logger.info(f"[NODE_OBS] >>> NODE START: {node.name} (id={node.id}, type={node.node_type.value})")
        input_preview = str(input_data)[:80] if input_data else "None"
        logger.info(f"[NODE_OBS]     Input preview: {input_preview}...")
    
    async def on_node_complete(
        self, node: INode, output: Any, context: IWorkflowContext, duration_ms: float
    ) -> None:
        record = {
            "node_id": node.id,
            "node_name": node.name,
            "node_type": node.node_type.value,
            "duration_ms": duration_ms,
            "timestamp": datetime.now().isoformat(),
        }
        self.node_executions.append(record)
        output_preview = str(output)[:80] if output else "None"
        logger.info(f"[NODE_OBS] <<< NODE COMPLETE: {node.name} ({duration_ms:.2f}ms)")
        logger.info(f"[NODE_OBS]     Output preview: {output_preview}...")
    
    async def on_node_error(
        self, node: INode, error: Exception, context: IWorkflowContext
    ) -> None:
        record = {
            "node_id": node.id,
            "node_name": node.name,
            "node_type": node.node_type.value,
            "error": str(error),
            "timestamp": datetime.now().isoformat(),
        }
        self.node_executions.append(record)
        logger.error(f"[NODE_OBS] !!! NODE ERROR: {node.name}")
        logger.error(f"[NODE_OBS]     Error: {error}")
    
    async def on_node_skip(
        self, node: INode, reason: str, context: IWorkflowContext
    ) -> None:
        record = {
            "node_id": node.id,
            "node_name": node.name,
            "node_type": node.node_type.value,
            "skipped": True,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
        }
        self.node_executions.append(record)
        logger.info(f"[NODE_OBS] --- NODE SKIPPED: {node.name}")
        logger.info(f"[NODE_OBS]     Reason: {reason}")


# ============================================================================
# REGISTER CUSTOM NODE TYPES
# ============================================================================

def register_custom_nodes():
    """Register all custom node types with the factory."""
    logger.info("+" + "=" * 68 + "+")
    logger.info("| REGISTERING CUSTOM NODE TYPES".ljust(69) + "|")
    logger.info("+" + "=" * 68 + "+")
    
    factory = NodeFactory()
    logger.info("[FACTORY] NodeFactory instance created")
    
    # Register Greeter Node using register_custom for string type IDs
    logger.info("[FACTORY] Registering: greeter (Greeter Agent)")
    factory.register_custom(
        type_id="greeter",
        node_class=GreeterNode,
        display_name="Greeter Agent",
        description="Greets users and initiates conversation",
        factory_func=lambda spec, **kwargs: GreeterNode(spec, **kwargs),
    )
    
    # Register Intent Classifier
    logger.info("[FACTORY] Registering: intent_classifier (Intent Classifier)")
    factory.register_custom(
        type_id="intent_classifier",
        node_class=IntentClassifierNode,
        display_name="Intent Classifier",
        description="Classifies user intent for routing",
        factory_func=lambda spec, **kwargs: IntentClassifierNode(spec, **kwargs),
    )
    
    # Register Booking Agent
    logger.info("[FACTORY] Registering: booking_agent (Booking Agent)")
    factory.register_custom(
        type_id="booking_agent",
        node_class=BookingAgentNode,
        display_name="Booking Agent",
        description="Handles appointment bookings",
        factory_func=lambda spec, **kwargs: BookingAgentNode(spec, **kwargs),
    )
    
    # Register FAQ Agent
    logger.info("[FACTORY] Registering: faq_agent (FAQ Agent)")
    factory.register_custom(
        type_id="faq_agent",
        node_class=FAQAgentNode,
        display_name="FAQ Agent",
        description="Answers frequently asked questions",
        factory_func=lambda spec, **kwargs: FAQAgentNode(spec, **kwargs),
    )
    
    # Register Support Agent
    logger.info("[FACTORY] Registering: support_agent (Support Agent)")
    factory.register_custom(
        type_id="support_agent",
        node_class=SupportAgentNode,
        display_name="Support Agent",
        description="Handles support requests",
        factory_func=lambda spec, **kwargs: SupportAgentNode(spec, **kwargs),
    )
    
    # Register Response Formatter
    logger.info("[FACTORY] Registering: response_formatter (Response Formatter)")
    factory.register_custom(
        type_id="response_formatter",
        node_class=ResponseFormatterNode,
        display_name="Response Formatter",
        description="Formats responses for TTS output",
        factory_func=lambda spec, **kwargs: ResponseFormatterNode(spec, **kwargs),
    )
    
    logger.info("[FACTORY] All 6 custom node types registered successfully")
    logger.info("+" + "=" * 68 + "+")
    
    return factory


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def custom_node_factory():
    """Create and register custom node factory."""
    return register_custom_nodes()


@pytest.fixture
def conversation_config():
    """Create test conversation configuration."""
    return ConversationConfig(
        asr_provider="azure",
        asr_language="en-US",
        tts_provider="elevenlabs",
        tts_voice_id="rachel",
        agent_prompt="You are a helpful customer service assistant.",
        first_message="Hello! Welcome to Acme Corp. How can I help you today?",
        llm_provider="azure",
        llm_model="gpt-4.1-mini",
    )


@pytest.fixture
def workflow_observer():
    """Create workflow observer for testing."""
    return ConversationObserver()


@pytest.fixture
def node_observer():
    """Create node observer for testing."""
    return NodeTrackingObserver()


# ============================================================================
# TESTS
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
                "conditions": [
                    {"field": "value", "operator": "greater_than", "value": 10}
                ]
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


@pytest.mark.asyncio
class TestCustomNodes:
    """Test custom node implementations."""
    
    async def test_greeter_node(self, conversation_config):
        """Test the greeter node execution."""
        logger.info("+" + "=" * 68 + "+")
        logger.info("| TEST: greeter_node".ljust(69) + "|")
        logger.info("+" + "=" * 68 + "+")
        
        spec = NodeSpec(
            id="greeter_test",
            name="Test Greeter",
            node_type=NodeType.AGENT,
            config={
                "first_message": "Welcome to our service!",
            }
        )
        
        node = GreeterNode(spec, conversation_config)
        
        context = WorkflowContext(
            workflow_id="test_workflow",
        )
        
        result = await node.execute({"user_input": "Hello"}, context)
        
        assert "greeting" in result
        assert result["greeting"] == "Welcome to our service!"
        assert context.get("is_new_conversation") == False
        logger.info(f"[OK] Greeter result: {result['greeting']}")
    
    async def test_intent_classifier_node(self):
        """Test the intent classifier node."""
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
            logger.info(f"[TEST] Input: '{user_input[:30]}...' -> Intent: {result['intent']}")
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
            config={
                "available_slots": ["Monday 10AM", "Tuesday 2PM"],
            }
        )
        
        node = BookingAgentNode(spec)
        context = WorkflowContext(workflow_id="test")
        
        result = await node.execute({"user_input": "I want to book"}, context)
        
        assert "response" in result
        assert "available_slots" in result
        assert result["action"] == "booking_offered"
        logger.info(f"[OK] Booking response: {result['response'][:50]}...")


@pytest.mark.asyncio
class TestWorkflowExecution:
    """Test complete workflow execution."""
    
    async def test_conversational_workflow_booking_intent(
        self, custom_node_factory, workflow_observer, node_observer
    ):
        """Test full conversational workflow with booking intent."""
        logger.info("+" + "=" * 68 + "+")
        logger.info("| TEST: conversational_workflow_booking_intent".ljust(69) + "|")
        logger.info("+" + "=" * 68 + "+")
        
        # Build the conversational workflow
        workflow = (
            WorkflowBuilder()
            .with_name("Customer Service Workflow")
            .with_description("Handles customer inquiries with intent-based routing")
            .with_max_iterations(50)
            # Start
            .add_node("start", NodeType.START)
            # Greeter
            .add_node("greeter", NodeType.AGENT, name="Greeter", config={
                "first_message": "Hello! How can I help you today?"
            })
            # Intent Classification
            .add_node("intent", NodeType.DECISION, name="Intent Classifier")
            # Specialized Agents
            .add_node("booking", NodeType.AGENT, name="Booking Agent")
            .add_node("faq", NodeType.AGENT, name="FAQ Agent")
            .add_node("support", NodeType.AGENT, name="Support Agent")
            # Response Formatter
            .add_node("formatter", NodeType.TRANSFORM, name="Response Formatter")
            # End
            .add_node("end", NodeType.END)
            # Edges
            .add_edge("start", "greeter")
            .add_edge("greeter", "intent")
            # Intent routing - using conditional edges
            .add_conditional_edge("intent", "booking", field="$ctx.detected_intent", operator="equals", value="booking", priority=10)
            .add_conditional_edge("intent", "faq", field="$ctx.detected_intent", operator="equals", value="faq", priority=10)
            .add_conditional_edge("intent", "support", field="$ctx.detected_intent", operator="equals", value="support", priority=10)
            # Default fallback to FAQ - use unique ID to avoid conflict with conditional edge
            .add_fallback_edge("intent", "faq", id="edge_intent_faq_fallback")
            # All paths to formatter
            .add_edge("booking", "formatter")
            .add_edge("faq", "formatter")
            .add_edge("support", "formatter")
            .add_edge("formatter", "end")
            .build()
        )
        
        logger.info(f"[BUILD] Created workflow: {workflow.name}")
        logger.info(f"        Nodes: {len(workflow.nodes)}")
        logger.info(f"        Edges: {len(workflow.edges)}")
        
        # Replace with custom nodes
        # Create custom node instances
        greeter_spec = NodeSpec(id="greeter", name="Greeter", node_type=NodeType.AGENT)
        greeter_node = GreeterNode(greeter_spec, ConversationConfig(
            first_message="Hello! How can I help you today?"
        ))
        
        intent_spec = NodeSpec(id="intent", name="Intent Classifier", node_type=NodeType.DECISION)
        intent_node = IntentClassifierNode(intent_spec)
        
        booking_spec = NodeSpec(id="booking", name="Booking Agent", node_type=NodeType.AGENT)
        booking_node = BookingAgentNode(booking_spec)
        
        faq_spec = NodeSpec(id="faq", name="FAQ Agent", node_type=NodeType.AGENT)
        faq_node = FAQAgentNode(faq_spec)
        
        support_spec = NodeSpec(id="support", name="Support Agent", node_type=NodeType.AGENT)
        support_node = SupportAgentNode(support_spec)
        
        formatter_spec = NodeSpec(id="formatter", name="Response Formatter", node_type=NodeType.TRANSFORM)
        formatter_node = ResponseFormatterNode(formatter_spec)
        
        # Inject custom nodes into workflow
        workflow._nodes["greeter"] = greeter_node
        workflow._nodes["intent"] = intent_node
        workflow._nodes["booking"] = booking_node
        workflow._nodes["faq"] = faq_node
        workflow._nodes["support"] = support_node
        workflow._nodes["formatter"] = formatter_node
        
        # Create engine with observers
        engine = WorkflowEngine(
            workflow_observers=[workflow_observer],
            node_observers=[node_observer],
        )
        
        # Execute with booking intent
        input_data = {"user_input": "I want to book an appointment for next week"}
        
        logger.info("-" * 70)
        logger.info("[EXECUTE] Starting workflow execution...")
        logger.info(f"[INPUT] {input_data}")
        logger.info("-" * 70)
        
        output, final_context = await engine.execute(workflow, input_data)
        
        # Verify results
        logger.info("-" * 70)
        logger.info("[RESULTS]")
        logger.info(f"  Output type: {type(output)}")
        if isinstance(output, dict):
            logger.info(f"  Response: {output.get('text', str(output))[:100]}...")
        logger.info(f"  Detected Intent: {final_context.get('detected_intent')}")
        logger.info(f"  Execution Path: {final_context.execution_path}")
        logger.info(f"  Observer Events: {len(workflow_observer.events)}")
        logger.info(f"  Node Executions: {len(node_observer.node_executions)}")
        
        # Assertions
        assert output is not None
        assert final_context.get("detected_intent") == "booking"
        assert "greeter" in final_context.execution_path
        assert "intent" in final_context.execution_path
        assert "booking" in final_context.execution_path
        
        logger.info("+" + "=" * 68 + "+")
        logger.info("| TEST PASSED: conversational_workflow_booking_intent".ljust(69) + "|")
        logger.info("+" + "=" * 68 + "+")
    
    async def test_conversational_workflow_support_intent(
        self, custom_node_factory, workflow_observer, node_observer
    ):
        """Test workflow with support intent."""
        logger.info("+" + "=" * 68 + "+")
        logger.info("| TEST: conversational_workflow_support_intent".ljust(69) + "|")
        logger.info("+" + "=" * 68 + "+")
        
        # Build workflow (simplified)
        workflow = (
            WorkflowBuilder()
            .with_name("Support Workflow Test")
            .add_node("start", NodeType.START)
            .add_node("intent", NodeType.DECISION)
            .add_node("support", NodeType.AGENT)
            .add_node("end", NodeType.END)
            .add_edge("start", "intent")
            .add_conditional_edge("intent", "support", field="$ctx.detected_intent", operator="equals", value="support")
            .add_fallback_edge("intent", "end")
            .add_edge("support", "end")
            .build()
        )
        
        # Inject custom intent node
        intent_spec = NodeSpec(id="intent", name="Intent", node_type=NodeType.DECISION)
        workflow._nodes["intent"] = IntentClassifierNode(intent_spec)
        
        support_spec = NodeSpec(id="support", name="Support", node_type=NodeType.AGENT)
        workflow._nodes["support"] = SupportAgentNode(support_spec)
        
        engine = WorkflowEngine(
            workflow_observers=[workflow_observer],
            node_observers=[node_observer],
        )
        
        # Execute with support intent
        input_data = {"user_input": "I have a problem with my account, it's not working"}
        output, context = await engine.execute(workflow, input_data)
        
        assert context.get("detected_intent") == "support"
        assert "support" in context.execution_path
        assert context.get("support_ticket_id") is not None
        
        logger.info(f"[OK] Support ticket created: {context.get('support_ticket_id')}")
        logger.info("+" + "=" * 68 + "+")


@pytest.mark.asyncio  
class TestNodeFactory:
    """Test node factory registration and creation."""
    
    async def test_register_and_create_custom_node(self, custom_node_factory):
        """Test registering and creating custom nodes."""
        logger.info("+" + "=" * 68 + "+")
        logger.info("| TEST: register_and_create_custom_node".ljust(69) + "|")
        logger.info("+" + "=" * 68 + "+")
        
        # List registered types
        registered = custom_node_factory.list_registered_types()
        types = [r.display_name for r in registered]
        logger.info(f"[INFO] Registered types: {len(registered)}")
        
        # Check custom types are registered
        assert custom_node_factory.is_registered("greeter")
        assert custom_node_factory.is_registered("intent_classifier")
        assert custom_node_factory.is_registered("booking_agent")
        logger.info("[OK] Custom types are registered: greeter, intent_classifier, booking_agent")
        
        # Create a greeter node via factory using the registration's factory_func
        registration = custom_node_factory.get_registration("greeter")
        assert registration is not None
        
        spec = NodeSpec(
            id="factory_greeter",
            name="Factory Greeter",
            node_type=NodeType.CUSTOM,  # Custom nodes use CUSTOM type
        )
        
        # Use the factory function directly from registration
        node = registration.factory_func(spec)
        assert node is not None
        assert isinstance(node, GreeterNode)
        
        logger.info(f"[OK] Created node via factory: {node.name}")
    
    async def test_custom_node_validation(self, custom_node_factory):
        """Test custom node validation."""
        logger.info("+" + "=" * 68 + "+")
        logger.info("| TEST: custom_node_validation".ljust(69) + "|")
        logger.info("+" + "=" * 68 + "+")
        
        spec = NodeSpec(
            id="validation_test",
            name="Validation Test Node",
            node_type=NodeType.AGENT,
        )
        
        node = GreeterNode(spec)
        context = WorkflowContext(workflow_id="test")
        
        # Validate should pass for greeter
        errors = await node.validate(context)
        assert len(errors) == 0
        
        logger.info("[OK] Node validation passed")


@pytest.mark.asyncio
class TestWorkflowStreaming:
    """Test workflow streaming execution."""
    
    async def test_streaming_execution(self, workflow_observer, node_observer):
        """Test streaming workflow execution."""
        logger.info("+" + "=" * 68 + "+")
        logger.info("| TEST: streaming_execution".ljust(69) + "|")
        logger.info("+" + "=" * 68 + "+")
        
        # Build simple workflow
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
        
        # Execute with streaming
        stream_results = []
        async for node_id, output, context in engine.execute_streaming(
            workflow, {"data": "test"}
        ):
            stream_results.append({
                "node_id": node_id,
                "has_output": output is not None,
            })
            logger.info(f"[STREAM] Node completed: {node_id}")
        
        assert len(stream_results) >= 2  # At least start and end
        logger.info(f"[OK] Streaming completed with {len(stream_results)} results")


@pytest.mark.asyncio
class TestEdgeConditions:
    """Test edge conditions and routing."""
    
    async def test_conditional_edge_evaluation(self):
        """Test that conditional edges evaluate correctly."""
        logger.info("+" + "=" * 68 + "+")
        logger.info("| TEST: conditional_edge_evaluation".ljust(69) + "|")
        logger.info("+" + "=" * 68 + "+")
        
        # Create edge spec with string equality condition
        # Note: Fields in context use $ctx. prefix for variables stored via context.set()
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
        
        from core.workflows.edges import ConditionalEdge
        edge = ConditionalEdge(spec)
        
        # Test with intent = "booking"
        context_match = WorkflowContext(workflow_id="test")
        context_match.set("intent", "booking")
        assert edge.can_traverse(context_match) == True
        logger.info("[OK] Edge traversable when $ctx.intent='booking'")
        
        # Test with intent != "booking"
        context_no_match = WorkflowContext(workflow_id="test")
        context_no_match.set("intent", "support")
        assert edge.can_traverse(context_no_match) == False
        logger.info("[OK] Edge not traversable when $ctx.intent='support'")


@pytest.mark.asyncio
class TestFullConversationalAgent:
    """
    Full integration test simulating an ElevenLabs-style conversational agent.
    """
    
    async def test_multi_turn_conversation(self, workflow_observer, node_observer):
        """Test a multi-turn conversation through the workflow."""
        logger.info("+" + "=" * 68 + "+")
        logger.info("| TEST: multi_turn_conversation".ljust(69) + "|")
        logger.info("+" + "=" * 68 + "+")
        
        # Build comprehensive workflow
        workflow = (
            WorkflowBuilder()
            .with_name("Multi-Turn Conversational Agent")
            .with_description("Full conversational AI with multiple turns")
            .with_metadata(
                author="AHF Team",
                version="1.0.0",
                category="conversational_ai",
            )
            .add_node("start", NodeType.START)
            .add_node("greeter", NodeType.AGENT, name="Greeting Agent")
            .add_node("intent", NodeType.DECISION, name="Intent Router")
            .add_node("booking", NodeType.AGENT, name="Booking Handler")
            .add_node("faq", NodeType.AGENT, name="FAQ Handler")
            .add_node("support", NodeType.AGENT, name="Support Handler")
            .add_node("goodbye", NodeType.AGENT, name="Goodbye Handler")
            .add_node("formatter", NodeType.TRANSFORM, name="Output Formatter")
            .add_node("end", NodeType.END)
            # Connections
            .add_edge("start", "greeter")
            .add_edge("greeter", "intent")
            .add_conditional_edge("intent", "booking", "$ctx.detected_intent", "equals", "booking", priority=10)
            .add_conditional_edge("intent", "faq", "$ctx.detected_intent", "equals", "faq", priority=10)
            .add_conditional_edge("intent", "support", "$ctx.detected_intent", "equals", "support", priority=10)
            .add_conditional_edge("intent", "goodbye", "$ctx.detected_intent", "equals", "goodbye", priority=10)
            .add_fallback_edge("intent", "faq", id="edge_intent_faq_fallback")
            .add_edge("booking", "formatter")
            .add_edge("faq", "formatter")
            .add_edge("support", "formatter")
            .add_edge("goodbye", "end")
            .add_edge("formatter", "end")
            .build()
        )
        
        # Inject custom nodes
        workflow._nodes["greeter"] = GreeterNode(
            NodeSpec(id="greeter", name="Greeter", node_type=NodeType.AGENT),
            ConversationConfig(first_message="Welcome! How can I assist you?")
        )
        workflow._nodes["intent"] = IntentClassifierNode(
            NodeSpec(id="intent", name="Intent", node_type=NodeType.DECISION)
        )
        workflow._nodes["booking"] = BookingAgentNode(
            NodeSpec(id="booking", name="Booking", node_type=NodeType.AGENT)
        )
        workflow._nodes["faq"] = FAQAgentNode(
            NodeSpec(id="faq", name="FAQ", node_type=NodeType.AGENT)
        )
        workflow._nodes["support"] = SupportAgentNode(
            NodeSpec(id="support", name="Support", node_type=NodeType.AGENT)
        )
        workflow._nodes["goodbye"] = ResponseFormatterNode(
            NodeSpec(id="goodbye", name="Goodbye", node_type=NodeType.AGENT, config={
                "add_closing": False,
            })
        )
        workflow._nodes["formatter"] = ResponseFormatterNode(
            NodeSpec(id="formatter", name="Formatter", node_type=NodeType.TRANSFORM)
        )
        
        engine = WorkflowEngine(
            workflow_observers=[workflow_observer],
            node_observers=[node_observer],
        )
        
        # Simulate multiple conversation turns
        conversation_turns = [
            {"user_input": "Hello, I need some help"},
            {"user_input": "What are your business hours?"},
            {"user_input": "I want to schedule an appointment"},
            {"user_input": "I have a problem with my account"},
        ]
        
        logger.info("-" * 70)
        logger.info("[CONVERSATION] Starting multi-turn conversation")
        logger.info("-" * 70)
        
        for i, turn_input in enumerate(conversation_turns):
            logger.info(f"\n[TURN {i+1}] User: {turn_input['user_input']}")
            
            output, context = await engine.execute(workflow, turn_input)
            
            detected_intent = context.get("detected_intent")
            logger.info(f"[TURN {i+1}] Intent: {detected_intent}")
            logger.info(f"[TURN {i+1}] Path: {' -> '.join(context.execution_path)}")
            
            if isinstance(output, dict) and "text" in output:
                logger.info(f"[TURN {i+1}] Response: {output['text'][:80]}...")
        
        # Final stats
        logger.info("-" * 70)
        logger.info("[STATS] Conversation Summary")
        logger.info(f"        Total turns: {len(conversation_turns)}")
        logger.info(f"        Observer events: {len(workflow_observer.events)}")
        logger.info(f"        Node executions: {len(node_observer.node_executions)}")
        
        logger.info("+" + "=" * 68 + "+")
        logger.info("| TEST PASSED: multi_turn_conversation".ljust(69) + "|")
        logger.info("+" + "=" * 68 + "+")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

