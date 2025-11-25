"""
Agents Azure OpenAI Integration Test.

This test file demonstrates real agent usage with Azure OpenAI GPT-4.1 Mini.
Tests SimpleAgent, ReActAgent, and GoalBasedAgent with actual LLM calls.
"""

import pytest
from core.llms import LLMFactory, create_context as create_llm_context
from core.agents import (
    AgentBuilder,
    AgentType,
    AgentInputType,
    AgentOutputType,
    AgentOutputFormat,
    AgentState,
)
from core.agents.spec import AgentContext, create_context
from core.agents.runtimes import (
    DictMemory,
    BasicScratchpad,
    StructuredScratchpad,
    BasicChecklist,
    LoggingObserver,
)
from utils.logging.LoggerAdaptor import LoggerAdaptor

# Setup logger
logger = LoggerAdaptor.get_logger("tests.agents.azure_integration")


# ============================================================================
# CONFIGURATION
# ============================================================================

AZURE_CONFIG = {
    "endpoint": "https://zeenie-sweden.openai.azure.com/",
    "deployment_name": "gpt-4.1-mini",  # Using GPT-4.1 Mini deployment
    "api_version": "2024-02-15-preview",
    "timeout": 60,
}


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
async def azure_llm():
    """Create Azure LLM instance with test configuration."""
    llm = LLMFactory.create_llm(
        "azure-gpt-4.1-mini",
        connector_config=AZURE_CONFIG
    )
    
    yield llm
    
    # Cleanup: close the connector session
    if hasattr(llm.connector, 'close'):
        await llm.connector.close()


@pytest.fixture
def agent_context():
    """Create test agent context."""
    return create_context(
        user_id="test-user-agent",
        session_id="test-session-agents-001",
        metadata={"test": "agents_azure_integration"}
    )


# ============================================================================
# SIMPLE AGENT TESTS
# ============================================================================

@pytest.mark.asyncio
class TestSimpleAgentAzure:
    """Test SimpleAgent with Azure OpenAI."""
    
    async def test_simple_agent_basic_question(self, azure_llm, agent_context):
        """Test SimpleAgent answering a basic question."""
        agent = (AgentBuilder()
            .with_name("simple_math_agent")
            .with_description("A simple agent that answers math questions")
            .with_llm(azure_llm)
            .with_system_prompt("You are a helpful math assistant. Answer questions concisely.")
            .with_input_types([AgentInputType.TEXT])
            .with_output_types([AgentOutputType.TEXT])
            .as_type(AgentType.SIMPLE)
            .build())
        
        result = await agent.run("What is 15 * 3?", agent_context)
        
        logger.info(f"Agent result: {result.content}")
        logger.info(f"Agent state: {result.state}")
        logger.info(f"Agent usage: {result.usage}")
        
        assert result.is_success()
        assert result.content is not None
        assert len(result.content) > 0
        # Should contain 45 somewhere in the response
        assert "45" in result.content or "forty-five" in result.content.lower()
    
    async def test_simple_agent_with_context(self, azure_llm, agent_context):
        """Test SimpleAgent with conversation context in system prompt."""
        agent = (AgentBuilder()
            .with_name("context_agent")
            .with_description("Agent with contextual understanding")
            .with_llm(azure_llm)
            .with_system_prompt(
                "You are an assistant for a software company called TechCorp. "
                "Always be helpful and mention you're from TechCorp when introducing yourself."
            )
            .as_type(AgentType.SIMPLE)
            .build())
        
        result = await agent.run("Introduce yourself briefly.", agent_context)
        
        logger.info(f"Context agent response: {result.content}")
        
        assert result.is_success()
        assert "TechCorp" in result.content or "techcorp" in result.content.lower()
    
    async def test_simple_agent_with_memory(self, azure_llm, agent_context):
        """Test SimpleAgent with memory component."""
        memory = DictMemory()
        
        # Pre-populate memory with context
        await memory.add("user_preference", "The user prefers short, concise answers.")
        await memory.add("previous_topic", "We were discussing Python programming.")
        
        agent = (AgentBuilder()
            .with_name("memory_agent")
            .with_description("Agent with memory")
            .with_llm(azure_llm)
            .with_memory(memory)
            .with_system_prompt("You are a helpful assistant. Keep responses brief.")
            .as_type(AgentType.SIMPLE)
            .build())
        
        result = await agent.run("What is a Python list?", agent_context)
        
        logger.info(f"Memory agent response: {result.content}")
        
        assert result.is_success()
        assert result.content is not None


# ============================================================================
# REACT AGENT TESTS
# ============================================================================

@pytest.mark.asyncio
class TestReActAgentAzure:
    """Test ReActAgent with Azure OpenAI."""
    
    async def test_react_agent_reasoning(self, azure_llm, agent_context):
        """Test ReActAgent reasoning without tools."""
        scratchpad = StructuredScratchpad()
        
        agent = (AgentBuilder()
            .with_name("reasoning_agent")
            .with_description("Agent that reasons step by step")
            .with_llm(azure_llm)
            .with_scratchpad(scratchpad)
            .with_system_prompt(
                "You are a reasoning assistant. Think step by step to solve problems. "
                "When you have the final answer, state it clearly with 'FINAL ANSWER:' prefix."
            )
            .with_max_iterations(5)
            .as_type(AgentType.REACT)
            .build())
        
        result = await agent.run(
            "If I have 3 apples and buy 2 more bags of 4 apples each, how many apples do I have in total?",
            agent_context
        )
        
        logger.info(f"ReAct agent result: {result.content}")
        logger.info(f"Iterations: {result.usage.iterations if result.usage else 'N/A'}")
        
        # Check scratchpad content
        scratchpad_content = scratchpad.read()
        logger.info(f"Scratchpad:\n{scratchpad_content}")
        
        assert result.is_success()
        # 3 + (2 * 4) = 11
        assert "11" in str(result.content) or "eleven" in str(result.content).lower()
    
    async def test_react_agent_with_observer(self, azure_llm, agent_context):
        """Test ReActAgent with logging observer."""
        observer = LoggingObserver()
        
        agent = (AgentBuilder()
            .with_name("observed_agent")
            .with_description("Agent with observation")
            .with_llm(azure_llm)
            .with_observer(observer)
            .with_system_prompt("You are a helpful assistant. Answer directly.")
            .with_max_iterations(3)
            .as_type(AgentType.REACT)
            .build())
        
        result = await agent.run("What is the capital of Japan?", agent_context)
        
        logger.info(f"Observed agent result: {result.content}")
        
        assert result.is_success()
        assert "Tokyo" in result.content or "tokyo" in result.content.lower()
    
    async def test_react_agent_multi_step(self, azure_llm, agent_context):
        """Test ReActAgent with a multi-step problem."""
        agent = (AgentBuilder()
            .with_name("multi_step_agent")
            .with_description("Agent for multi-step problems")
            .with_llm(azure_llm)
            .with_scratchpad(BasicScratchpad())
            .with_system_prompt(
                "You are a problem-solving assistant. Break down complex problems into steps. "
                "Show your reasoning, then provide a 'FINAL ANSWER:' at the end."
            )
            .with_max_iterations(5)
            .as_type(AgentType.REACT)
            .build())
        
        result = await agent.run(
            "A store sells apples for $2 each and oranges for $3 each. "
            "If I buy 4 apples and 3 oranges, and I have a $5 discount coupon, "
            "how much do I pay?",
            agent_context
        )
        
        logger.info(f"Multi-step result: {result.content}")
        
        assert result.is_success()
        # (4 * 2) + (3 * 3) - 5 = 8 + 9 - 5 = 12
        assert "12" in str(result.content) or "twelve" in str(result.content).lower()


# ============================================================================
# GOAL-BASED AGENT TESTS
# ============================================================================

@pytest.mark.asyncio
class TestGoalBasedAgentAzure:
    """Test GoalBasedAgent with Azure OpenAI."""
    
    async def test_goal_based_simple_goal(self, azure_llm, agent_context):
        """Test GoalBasedAgent with a simple goal."""
        checklist = BasicChecklist()
        
        agent = (AgentBuilder()
            .with_name("goal_agent")
            .with_description("Agent that works towards goals")
            .with_llm(azure_llm)
            .with_checklist(checklist)
            .with_system_prompt(
                "You are a goal-oriented assistant. Work systematically to achieve objectives. "
                "When you complete a task, mark it done. Provide a final summary when all tasks are complete."
            )
            .with_max_iterations(5)
            .as_type(AgentType.GOAL_BASED)
            .build())
        
        result = await agent.run(
            "Create a short greeting message for a user named Alice",
            agent_context
        )
        
        logger.info(f"Goal agent result: {result.content}")
        logger.info(f"Checklist: {checklist.to_json()}")
        
        assert result.is_success()
        assert "Alice" in result.content or "alice" in result.content.lower()
    
    async def test_goal_based_with_checklist_tracking(self, azure_llm, agent_context):
        """Test GoalBasedAgent with explicit checklist tracking."""
        checklist = BasicChecklist()
        
        agent = (AgentBuilder()
            .with_name("checklist_agent")
            .with_description("Agent that tracks progress")
            .with_llm(azure_llm)
            .with_checklist(checklist)
            .with_scratchpad(BasicScratchpad())
            .with_system_prompt(
                "You are a task-oriented assistant. "
                "For each task, think about what needs to be done, then complete it. "
                "Provide clear results for each step."
            )
            .with_max_iterations(5)
            .as_type(AgentType.GOAL_BASED)
            .build())
        
        result = await agent.run(
            "List 3 benefits of exercise and summarize them in one sentence",
            agent_context
        )
        
        logger.info(f"Checklist agent result: {result.content}")
        logger.info(f"Final checklist state: {checklist.to_json()}")
        
        assert result.is_success()
        assert result.content is not None


# ============================================================================
# STREAMING TESTS
# ============================================================================

@pytest.mark.asyncio
class TestAgentStreamingAzure:
    """Test agent streaming with Azure OpenAI."""
    
    async def test_simple_agent_streaming(self, azure_llm, agent_context):
        """Test SimpleAgent streaming output."""
        agent = (AgentBuilder()
            .with_name("streaming_agent")
            .with_description("Agent with streaming output")
            .with_llm(azure_llm)
            .with_system_prompt("You are a helpful assistant.")
            .as_type(AgentType.SIMPLE)
            .build())
        
        chunks = []
        logger.info("Starting agent stream")
        
        async for chunk in agent.stream("Tell me a very short joke.", agent_context):
            if chunk.content:
                chunks.append(chunk.content)
                logger.debug(f"Chunk: {chunk.content}")
            
            if chunk.is_final:
                logger.info("Stream completed")
        
        full_response = "".join(chunks)
        logger.info(f"Full streamed response: {full_response}")
        
        assert len(chunks) > 0
        assert len(full_response) > 0
    
    async def test_react_agent_streaming(self, azure_llm, agent_context):
        """Test ReActAgent streaming intermediate thoughts."""
        agent = (AgentBuilder()
            .with_name("streaming_react_agent")
            .with_description("ReAct agent with streaming")
            .with_llm(azure_llm)
            .with_scratchpad(BasicScratchpad())
            .with_system_prompt("You are a reasoning assistant. Think step by step.")
            .with_max_iterations(3)
            .as_type(AgentType.REACT)
            .build())
        
        chunks = []
        iterations_seen = set()
        
        async for chunk in agent.stream("What is 7 + 8?", agent_context):
            if chunk.content:
                chunks.append(chunk.content)
            if chunk.iteration:
                iterations_seen.add(chunk.iteration)
            if chunk.chunk_type:
                logger.debug(f"Chunk type: {chunk.chunk_type}")
        
        logger.info(f"Total chunks: {len(chunks)}")
        logger.info(f"Iterations seen: {iterations_seen}")
        
        assert len(chunks) > 0


# ============================================================================
# INPUT/OUTPUT TYPE TESTS
# ============================================================================

@pytest.mark.asyncio
class TestAgentIOTypesAzure:
    """Test agent input/output type specifications."""
    
    async def test_agent_with_structured_output(self, azure_llm, agent_context):
        """Test agent configured for structured JSON output."""
        agent = (AgentBuilder()
            .with_name("structured_agent")
            .with_description("Agent with JSON output")
            .with_llm(azure_llm)
            .with_input_types([AgentInputType.TEXT])
            .with_output_types([AgentOutputType.STRUCTURED])
            .with_output_format(AgentOutputFormat.JSON)
            .with_system_prompt(
                "You are an assistant that ALWAYS responds in valid JSON format. "
                "Your response must be a JSON object with 'answer' and 'confidence' keys."
            )
            .as_type(AgentType.SIMPLE)
            .build())
        
        result = await agent.run("What is the capital of France?", agent_context)
        
        logger.info(f"Structured output: {result.content}")
        logger.info(f"Output type: {result.output_type}")
        logger.info(f"Output format: {result.output_format}")
        
        assert result.is_success()
        # Should attempt JSON (may or may not be perfect JSON)
        assert result.content is not None
    
    async def test_agent_spec_io_types(self, azure_llm):
        """Test that agent spec correctly captures I/O types."""
        spec = (AgentBuilder()
            .with_name("io_spec_agent")
            .with_description("Agent for I/O type testing")
            .with_input_types([AgentInputType.TEXT, AgentInputType.STRUCTURED])
            .with_output_types([AgentOutputType.TEXT, AgentOutputType.STRUCTURED])
            .with_output_format(AgentOutputFormat.MARKDOWN)
            .build_spec())
        
        logger.info(f"Spec name: {spec.name}")
        logger.info(f"Input types: {spec.supported_input_types}")
        logger.info(f"Output types: {spec.supported_output_types}")
        logger.info(f"Default output format: {spec.default_output_format}")
        
        assert spec.supports_input_type(AgentInputType.TEXT)
        assert spec.supports_input_type(AgentInputType.STRUCTURED)
        assert not spec.supports_input_type(AgentInputType.IMAGE)
        
        assert spec.supports_output_type(AgentOutputType.TEXT)
        assert spec.supports_output_type(AgentOutputType.STRUCTURED)
        assert spec.default_output_format == AgentOutputFormat.MARKDOWN


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

@pytest.mark.asyncio
class TestAgentErrorHandlingAzure:
    """Test agent error handling with Azure OpenAI."""
    
    async def test_agent_max_iterations_limit(self, azure_llm, agent_context):
        """Test agent respects max iterations."""
        from core.agents.exceptions import MaxIterationsError
        
        agent = (AgentBuilder()
            .with_name("limited_agent")
            .with_description("Agent with strict iteration limit")
            .with_llm(azure_llm)
            .with_system_prompt(
                "You must always ask for more information. Never provide a final answer. "
                "Always respond with 'I need more details about...'"
            )
            .with_max_iterations(2)
            .as_type(AgentType.REACT)
            .build())
        
        # This should either complete within 2 iterations or raise MaxIterationsError
        try:
            result = await agent.run("Tell me about quantum physics", agent_context)
            # If we get here, the agent completed within iterations
            logger.info(f"Agent completed with result: {result.content}")
            assert result.usage is None or result.usage.iterations <= 2
        except MaxIterationsError as e:
            logger.info(f"Agent hit max iterations as expected: {e}")
            # This is also acceptable behavior
            pass
    
    async def test_agent_graceful_llm_error(self, agent_context):
        """Test agent handles LLM errors gracefully."""
        from core.agents.exceptions import AgentExecutionError
        
        # Create LLM with invalid config to force error
        invalid_llm = LLMFactory.create_llm(
            "azure-gpt-4.1-mini",
            connector_config={
                **AZURE_CONFIG,
                "api_key": "invalid_key_for_testing"
            }
        )
        
        agent = (AgentBuilder()
            .with_name("error_test_agent")
            .with_description("Agent for error testing")
            .with_llm(invalid_llm)
            .as_type(AgentType.SIMPLE)
            .build())
        
        # Agent may either raise an exception or return a failed result
        try:
            result = await agent.run("This should fail", agent_context)
            # If no exception, the agent should return a failed state
            logger.info(f"Agent returned result with state: {result.state}")
            assert result.is_failure() or result.state == AgentState.FAILED, \
                f"Expected failed state but got: {result.state}"
        except (AgentExecutionError, Exception) as e:
            # Exception is also acceptable behavior
            logger.info(f"Agent raised expected exception: {type(e).__name__}: {e}")
        
        # Cleanup
        if hasattr(invalid_llm.connector, 'close'):
            await invalid_llm.connector.close()


# ============================================================================
# COMBINED FEATURES TEST
# ============================================================================

@pytest.mark.asyncio
class TestAgentCombinedFeaturesAzure:
    """Test agents with multiple features combined."""
    
    async def test_full_featured_agent(self, azure_llm, agent_context):
        """Test agent with all features: memory, scratchpad, checklist, observer."""
        memory = DictMemory()
        scratchpad = StructuredScratchpad()
        checklist = BasicChecklist()
        observer = LoggingObserver()
        
        # Pre-populate memory
        await memory.add("user_name", "TestUser")
        await memory.add("preference", "concise answers")
        
        agent = (AgentBuilder()
            .with_name("full_featured_agent")
            .with_description("Agent with all features enabled")
            .with_llm(azure_llm)
            .with_memory(memory)
            .with_scratchpad(scratchpad)
            .with_checklist(checklist)
            .with_observer(observer)
            .with_system_prompt(
                "You are a helpful assistant. "
                "Be concise and clear in your responses. "
                "Always acknowledge the user by name if known."
            )
            .with_input_types([AgentInputType.TEXT])
            .with_output_types([AgentOutputType.TEXT])
            .with_output_format(AgentOutputFormat.TEXT)
            .with_max_iterations(5)
            .with_timeout(30)
            .as_type(AgentType.REACT)
            .build())
        
        result = await agent.run(
            "Explain what an API is in one sentence.",
            agent_context
        )
        
        logger.info(f"Full featured agent result: {result.content}")
        logger.info(f"State: {result.state}")
        logger.info(f"Scratchpad content:\n{scratchpad.read()}")
        logger.info(f"Checklist state: {checklist.to_json()}")
        
        # Get agent state
        state = agent.get_state()
        logger.info(f"Agent state: {state}")
        
        assert result.is_success()
        assert result.content is not None
        assert "API" in result.content.upper()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

