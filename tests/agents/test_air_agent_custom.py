"""
Custom AIR Agent Test.

This test demonstrates how to:
1. Create a completely custom agent type
2. Register it with AgentFactory
3. Use it via AgentBuilder with as_custom_type()
4. Handle task switching with scratchpad

The AIR Agent (Adaptive Intelligent Reasoning) will:
- Build a speaker step by step
- Switch to building a laptop mid-way
- Use scratchpad to track all steps and the switch
"""

import pytest
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from core.llms import LLMFactory
from core.agents import (
    AgentBuilder,
    AgentFactory,
    BaseAgent,
    AgentSpec,
    AgentContext,
    AgentState,
    AgentInputType,
    AgentOutputType,
    StructuredScratchpad,
    create_context,
)
from core.agents.exceptions import AgentBuildError
from core.agents.interfaces import IAgentScratchpad
from utils.logging.LoggerAdaptor import LoggerAdaptor

# Setup logger
logger = LoggerAdaptor.get_logger("tests.agents.air_agent_custom")


# ============================================================================
# AZURE CONFIGURATION
# ============================================================================

AZURE_CONFIG = {
    "endpoint": "https://zeenie-sweden.openai.azure.com/",
    "deployment_name": "gpt-4.1-mini",
    "api_version": "2024-02-15-preview",
    "api_key": "ss",
    "timeout": 60,
}


# ============================================================================
# CUSTOM AIR AGENT IMPLEMENTATION
# ============================================================================

@dataclass
class TaskContext:
    """Represents a task being tracked by the AIR Agent."""
    task_id: str
    task_name: str
    description: str
    steps: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "active"  # active, paused, completed, switched
    created_at: datetime = field(default_factory=datetime.now)
    switched_at: Optional[datetime] = None
    switch_reason: Optional[str] = None


class AIRAgent(BaseAgent):
    """
    AIR (Adaptive Intelligent Reasoning) Agent.
    
    A custom agent that:
    - REQUIRES a scratchpad (creates one if not provided)
    - Breaks down complex tasks into steps
    - Supports task switching with context preservation
    - Tracks all steps and switches in scratchpad
    """
    
    # Class-level configuration
    AGENT_TYPE_ID = "air_agent"
    DISPLAY_NAME = "AIR Agent"
    DESCRIPTION = "Adaptive Intelligent Reasoning Agent with task switching support"
    
    def __init__(
        self,
        spec: AgentSpec,
        llm: Any,
        backup_llm: Optional[Any] = None,
        tools: Optional[List[Any]] = None,
        memory: Optional[Any] = None,
        scratchpad: Optional[IAgentScratchpad] = None,
        checklist: Optional[Any] = None,
        planner: Optional[Any] = None,
        observers: Optional[List[Any]] = None,
        input_processor: Optional[Any] = None,
        output_processor: Optional[Any] = None,
        prompt_registry: Optional[Any] = None,
    ):
        # AIR Agent REQUIRES a scratchpad - create StructuredScratchpad if not provided
        if scratchpad is None:
            logger.info("[AIR] Creating default StructuredScratchpad")
            scratchpad = StructuredScratchpad()
        
        super().__init__(
            spec=spec,
            llm=llm,
            backup_llm=backup_llm,
            tools=tools,
            memory=memory,
            scratchpad=scratchpad,
            checklist=checklist,
            planner=planner,
            observers=observers,
            input_processor=input_processor,
            output_processor=output_processor,
            prompt_registry=prompt_registry,
        )
        
        # Task tracking
        self._tasks: Dict[str, TaskContext] = {}
        self._current_task_id: Optional[str] = None
        self._task_counter: int = 0
    
    def _create_task(self, name: str, description: str) -> TaskContext:
        """Create a new task context."""
        self._task_counter += 1
        task_id = f"task_{self._task_counter}"
        task = TaskContext(
            task_id=task_id,
            task_name=name,
            description=description
        )
        self._tasks[task_id] = task
        logger.info(f"[+] Created task: {task_id} - '{name}'")
        return task
    
    def _record_switch(self, from_task: TaskContext, to_task: TaskContext, reason: str) -> None:
        """Record a task switch in the scratchpad."""
        from_task.status = "paused"
        from_task.switched_at = datetime.now()
        from_task.switch_reason = reason
        
        switch_entry = f"""
===============================================================
TASK SWITCH
---------------------------------------------------------------
From: {from_task.task_name}
To: {to_task.task_name}
Reason: {reason}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Steps completed in previous task: {len(from_task.steps)}
===============================================================
"""
        self.scratchpad.append(switch_entry)
        self._current_task_id = to_task.task_id
        logger.info(f"[SWITCH] '{from_task.task_name}' -> '{to_task.task_name}'")
        logger.info(f"[REASON] {reason}")
    
    def _add_step(self, task: TaskContext, step_num: int, title: str, details: str) -> None:
        """Add a step to task and scratchpad."""
        task.steps.append({
            "step": step_num,
            "title": title,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
        
        step_entry = f"""
+-- {task.task_name} - Step {step_num} -------------------------------
| {title}
| 
| {details[:200]}{'...' if len(details) > 200 else ''}
+----------------------------------------------------------------------
"""
        self.scratchpad.append(step_entry)
        logger.info(f"[STEP {step_num}] {task.task_name}: {title[:60]}{'...' if len(title) > 60 else ''}")
    
    async def _execute_iteration(
        self,
        input_data: Any,
        ctx: AgentContext,
        iteration: int,
        system_prompt: Optional[str]
    ) -> tuple[Any, bool]:
        """
        Execute a single iteration of the AIR Agent.
        
        Since AIR Agent handles its own multi-step logic internally,
        this method does all the work in a single iteration.
        
        Returns:
            Tuple of (result_content, should_continue=False)
        """
        # Initialize on first iteration
        if iteration == 1:
            logger.info("+" + "=" * 68 + "+")
            logger.info("|" + " AIR AGENT - Starting Execution ".center(68) + "|")
            logger.info("+" + "=" * 68 + "+")
            logger.info(f"[INPUT] {str(input_data)[:100]}...")
            self.scratchpad.clear()
            self._tasks.clear()
            self._current_task_id = None
            self._task_counter = 0
            
            # Add header to scratchpad
            header = f"""
+==============================================================+
|                    AIR AGENT SESSION                         |
|                    {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}                        |
+==============================================================+

Input: {str(input_data)[:300]}

"""
            self.scratchpad.append(header)
        
        # Step 1: Analyze input
        analysis_prompt = f"""Analyze this request and identify:
1. The primary task
2. Any secondary tasks or switches mentioned
3. Key components needed

Request: {input_data}

Be brief (2-3 sentences)."""
        
        logger.info("[STEP 1] Analyzing input request...")
        messages = [{"role": "user", "content": analysis_prompt}]
        response = await self._call_llm(messages, ctx)
        analysis = response.content if hasattr(response, 'content') else str(response)
        self.scratchpad.append(f"[ANALYSIS]\n{analysis}\n")
        logger.info(f"[OK] Analysis: {analysis[:80]}...")
        
        # Step 2: Create and execute primary task (Building Speaker)
        logger.info("-" * 70)
        logger.info("[STEP 2] PRIMARY TASK: Building a Speaker")
        logger.info("-" * 70)
        primary_task = self._create_task("Building a Speaker", str(input_data))
        self._current_task_id = primary_task.task_id
        
        self.scratchpad.append(f"\n[TARGET] STARTING: {primary_task.task_name}\n")
        
        # Generate steps for building a speaker
        speaker_prompt = """List exactly 5 steps to build a basic speaker system.
Format: numbered list (1. Step, 2. Step, etc.)
Be practical and specific."""
        
        logger.info("[BUILD] Generating speaker build steps via LLM...")
        messages = [{"role": "user", "content": speaker_prompt}]
        response = await self._call_llm(messages, ctx)
        speaker_steps = response.content if hasattr(response, 'content') else str(response)
        logger.debug(f"[RAW] Steps: {speaker_steps[:150]}...")
        
        # Parse and execute each step (3 steps before switch)
        step_lines = [line.strip() for line in speaker_steps.split('\n') if line.strip() and line.strip()[0].isdigit()]
        logger.info(f"[PARSE] Parsed {len(step_lines)} steps, executing first 3 before switch...")
        for i, line in enumerate(step_lines[:3], 1):
            step_title = line.lstrip('0123456789.-) ').strip()
            
            detail_prompt = f"Briefly explain how to: {step_title}"
            messages = [{"role": "user", "content": detail_prompt}]
            response = await self._call_llm(messages, ctx)
            step_detail = response.content if hasattr(response, 'content') else str(response)
            
            self._add_step(primary_task, i, step_title, step_detail)
        
        # Step 3: TASK SWITCH - Now switch to building a laptop
        logger.info("-" * 70)
        logger.info("[STEP 3] TASK SWITCH: Speaker -> Laptop")
        logger.info("-" * 70)
        switch_prompt = """The user wants to switch tasks. 
We need to pause building the speaker and start building a laptop.
Acknowledge the switch briefly."""
        
        messages = [{"role": "user", "content": switch_prompt}]
        response = await self._call_llm(messages, ctx)
        switch_response = response.content if hasattr(response, 'content') else str(response)
        logger.info(f"[LLM] Switch acknowledged: {switch_response[:80]}...")
        
        # Create secondary task and record switch
        logger.info("[TARGET] Creating SECONDARY TASK: Building a Laptop")
        secondary_task = self._create_task("Building a Laptop", "Switched from speaker to laptop")
        self._record_switch(primary_task, secondary_task, "User requested task switch to build a laptop")
        
        # Generate steps for building a laptop
        logger.info("-" * 70)
        logger.info("[STEP 3b] SECONDARY TASK: Building a Laptop")
        logger.info("-" * 70)
        laptop_prompt = """List exactly 5 steps to build/assemble a laptop.
Format: numbered list (1. Step, 2. Step, etc.)
Be practical and specific."""
        
        logger.info("[BUILD] Generating laptop build steps via LLM...")
        messages = [{"role": "user", "content": laptop_prompt}]
        response = await self._call_llm(messages, ctx)
        laptop_steps = response.content if hasattr(response, 'content') else str(response)
        logger.debug(f"[RAW] Steps: {laptop_steps[:150]}...")
        
        # Parse and execute laptop steps
        laptop_lines = [line.strip() for line in laptop_steps.split('\n') if line.strip() and line.strip()[0].isdigit()]
        logger.info(f"[PARSE] Parsed {len(laptop_lines)} steps, executing all...")
        for i, line in enumerate(laptop_lines[:5], 1):
            step_title = line.lstrip('0123456789.-) ').strip()
            
            detail_prompt = f"Briefly explain how to: {step_title}"
            messages = [{"role": "user", "content": detail_prompt}]
            response = await self._call_llm(messages, ctx)
            step_detail = response.content if hasattr(response, 'content') else str(response)
            
            self._add_step(secondary_task, i, step_title, step_detail)
        
        secondary_task.status = "completed"
        logger.info(f"[OK] Laptop task COMPLETED with {len(secondary_task.steps)} steps")
        
        # Step 4: Generate final summary
        logger.info("-" * 70)
        logger.info("[STEP 4] Generating FINAL SUMMARY")
        logger.info("-" * 70)
        summary_prompt = f"""Summarize the work completed:
1. Started building a speaker ({len(primary_task.steps)} steps completed)
2. Switched to building a laptop ({len(secondary_task.steps)} steps completed)

Provide a brief summary of what was accomplished and the task switch."""
        
        messages = [{"role": "user", "content": summary_prompt}]
        response = await self._call_llm(messages, ctx)
        summary = response.content if hasattr(response, 'content') else str(response)
        
        # Add summary to scratchpad
        self.scratchpad.append(f"""
+==============================================================+
|                       FINAL SUMMARY                          |
+==============================================================+

{summary}

Tasks:
- {primary_task.task_name}: {len(primary_task.steps)} steps, status: {primary_task.status}
- {secondary_task.task_name}: {len(secondary_task.steps)} steps, status: {secondary_task.status}

Session completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
""")
        
        # Store task info in context for result metadata
        ctx.metadata["air_tasks"] = {
            task_id: {
                "name": task.task_name,
                "status": task.status,
                "steps_count": len(task.steps),
                "switched_at": task.switched_at.isoformat() if task.switched_at else None,
                "switch_reason": task.switch_reason
            }
            for task_id, task in self._tasks.items()
        }
        ctx.metadata["air_scratchpad"] = self.scratchpad.read()
        
        logger.info("+" + "=" * 68 + "+")
        logger.info("|" + " AIR AGENT - Execution Complete ".center(68) + "|")
        logger.info("+" + "=" * 68 + "+")
        logger.info(f"| Speaker: {len(primary_task.steps)} steps ({primary_task.status})")
        logger.info(f"| Laptop:  {len(secondary_task.steps)} steps ({secondary_task.status})")
        logger.info("+" + "=" * 68 + "+")
        
        # Return result and False to stop (all work done in one iteration)
        return summary, False
    
    def get_scratchpad_content(self) -> str:
        """Get the current scratchpad content."""
        return self.scratchpad.read()
    
    def get_tasks(self) -> Dict[str, TaskContext]:
        """Get all tracked tasks."""
        return self._tasks.copy()


# ============================================================================
# CUSTOM VALIDATOR FOR AIR AGENT
# ============================================================================

def validate_air_agent_config(config: Dict[str, Any]) -> bool:
    """
    Custom validator for AIR Agent configuration.
    
    Ensures:
    - LLM is provided
    - Scratchpad is available (or will be created)
    """
    logger.debug(f"Validating AIR Agent config: {list(config.keys())}")
    if 'llm' not in config or config['llm'] is None:
        logger.warning("AIR Agent config validation failed: LLM not provided")
        return False
    logger.debug("AIR Agent config validation passed")
    return True


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
async def azure_llm():
    """Create Azure LLM instance."""
    llm = LLMFactory.create_llm(
        "azure-gpt-4.1-mini",
        connector_config=AZURE_CONFIG
    )
    yield llm
    if hasattr(llm.connector, 'close'):
        await llm.connector.close()


@pytest.fixture
def agent_context():
    """Create test agent context."""
    return create_context(
        user_id="test-user-air",
        session_id="test-session-air-001",
        metadata={"test": "air_agent_custom"}
    )


@pytest.fixture(autouse=True)
def register_air_agent():
    """Register the AIR Agent type before tests."""
    logger.info("+" + "-" * 68 + "+")
    logger.info("|" + " FIXTURE: Registering AIR Agent ".center(68) + "|")
    logger.info("+" + "-" * 68 + "+")
    # Register the custom AIR Agent
    AgentFactory.register(
        type_id=AIRAgent.AGENT_TYPE_ID,
        agent_class=AIRAgent,
        display_name=AIRAgent.DISPLAY_NAME,
        description=AIRAgent.DESCRIPTION,
        default_config={
            "max_iterations": 10,
        },
        required_components=[],  # Scratchpad is auto-created
        validator=validate_air_agent_config,
        metadata={
            "version": "1.0.0",
            "author": "AHF Team",
            "supports_task_switching": True,
        },
        override=True,  # Allow re-registration in tests
    )
    logger.info("[OK] AIR Agent registered: type_id='air_agent', display='AIR Agent'")
    
    yield
    
    # Cleanup: unregister after tests
    logger.info("[CLEANUP] Unregistering AIR Agent type...")
    AgentFactory.unregister(AIRAgent.AGENT_TYPE_ID)
    logger.info("[OK] AIR Agent unregistered")


# ============================================================================
# TESTS
# ============================================================================

@pytest.mark.asyncio
class TestAgentFactoryRegistration:
    """Test AgentFactory registration functionality."""
    
    async def test_air_agent_is_registered(self):
        """Test that AIR Agent is properly registered."""
        logger.info("+-- TEST: air_agent_is_registered " + "-" * 36 + "+")
        logger.info("| Verifying AIR Agent registration in factory")
        logger.info("+" + "-" * 68 + "+")
        
        assert AgentFactory.is_registered("air_agent")
        logger.info("[OK] AgentFactory.is_registered('air_agent') = True")
        
        registration = AgentFactory.get_registration("air_agent")
        assert registration is not None
        assert registration.display_name == "AIR Agent"
        assert registration.agent_class == AIRAgent
        logger.info(f"[OK] Registration verified: {registration.display_name} -> {registration.agent_class.__name__}")
    
    async def test_list_types_includes_air_agent(self):
        """Test that list_types includes the custom AIR Agent."""
        logger.info("+-- TEST: list_types_includes_air_agent " + "-" * 30 + "+")
        logger.info("| Verifying all agent types are listed")
        logger.info("+" + "-" * 68 + "+")
        
        types = AgentFactory.list_types()
        logger.info(f"[INFO] Available types: {types}")
        
        # Built-in types
        assert "react" in types
        assert "simple" in types
        assert "goal_based" in types
        assert "hierarchical" in types
        logger.info("[OK] All built-in types present: react, simple, goal_based, hierarchical")
        
        # Custom type
        assert "air_agent" in types
        logger.info("[OK] Custom type 'air_agent' also present")
    
    async def test_get_type_info(self):
        """Test getting detailed type info."""
        logger.info("+-- TEST: get_type_info " + "-" * 46 + "+")
        logger.info("| Retrieving detailed info for 'air_agent' type")
        logger.info("+" + "-" * 68 + "+")
        
        info = AgentFactory.get_type_info("air_agent")
        logger.info(f"[INFO] Type info keys: {list(info.keys())}")
        logger.info(f"       type_id: {info['type_id']}")
        logger.info(f"       display_name: {info['display_name']}")
        logger.info(f"       metadata: {info.get('metadata', {})}")
        
        assert info["type_id"] == "air_agent"
        assert info["display_name"] == "AIR Agent"
        assert info["metadata"]["supports_task_switching"] is True
        logger.info("[OK] Type info verified: supports_task_switching=True")
    
    async def test_cannot_register_duplicate_without_override(self):
        """Test that duplicate registration fails without override flag."""
        logger.info("+-- TEST: cannot_register_duplicate_without_override " + "-" * 18 + "+")
        logger.info("| Attempting duplicate registration (should fail)")
        logger.info("+" + "-" * 68 + "+")
        
        logger.info("[WARN] Attempting to register 'air_agent' again with override=False...")
        with pytest.raises(AgentBuildError):
            AgentFactory.register(
                type_id="air_agent",
                agent_class=AIRAgent,
                override=False,  # Should fail
            )
        logger.info("[OK] Correctly raised AgentBuildError for duplicate registration")


@pytest.mark.asyncio
class TestAIRAgentCreation:
    """Test AIR Agent creation via factory and builder."""
    
    async def test_create_via_factory(self, azure_llm, agent_context):
        """Test creating AIR Agent directly via factory."""
        logger.info("+-- TEST: create_via_factory " + "-" * 41 + "+")
        logger.info("| Creating AIR Agent using AgentFactory.create()")
        logger.info("+" + "-" * 68 + "+")
        from core.agents.spec import create_agent_spec
        
        spec = create_agent_spec(
            name="factory_air_agent",
            description="AIR Agent created via factory"
        )
        logger.info(f"[INFO] Created spec: name='{spec.name}'")
        
        agent = AgentFactory.create(
            "air_agent",
            spec=spec,
            llm=azure_llm,
        )
        logger.info("[BUILD] AgentFactory.create('air_agent', ...) called")
        
        assert agent is not None
        assert isinstance(agent, AIRAgent)
        logger.info(f"[OK] Created AIR Agent via factory: {agent.spec.name}")
    
    async def test_create_via_builder_custom_type(self, azure_llm, agent_context):
        """Test creating AIR Agent via builder with as_custom_type()."""
        logger.info("+-- TEST: create_via_builder_custom_type " + "-" * 29 + "+")
        logger.info("| Creating AIR Agent using AgentBuilder.as_custom_type()")
        logger.info("+" + "-" * 68 + "+")
        
        logger.info("[BUILD] Building agent chain:")
        logger.info("        .with_name('builder_air_agent')")
        logger.info("        .with_description(...)")
        logger.info("        .with_llm(azure_llm)")
        logger.info("        .with_input_types([TEXT])")
        logger.info("        .with_output_types([TEXT])")
        logger.info("        .as_custom_type('air_agent')")
        logger.info("        .build()")
        
        agent = (AgentBuilder()
            .with_name("builder_air_agent")
            .with_description("AIR Agent created via builder")
            .with_llm(azure_llm)
            .with_input_types([AgentInputType.TEXT])
            .with_output_types([AgentOutputType.TEXT])
            .as_custom_type("air_agent")
            .build())
        
        assert agent is not None
        assert isinstance(agent, AIRAgent)
        logger.info(f"[OK] Created AIR Agent via builder: {agent.spec.name}")
    
    async def test_air_agent_auto_creates_scratchpad(self, azure_llm):
        """Test that AIR Agent auto-creates scratchpad if not provided."""
        logger.info("+-- TEST: air_agent_auto_creates_scratchpad " + "-" * 26 + "+")
        logger.info("| Verifying AIR Agent auto-creates scratchpad if None")
        logger.info("+" + "-" * 68 + "+")
        from core.agents.spec import create_agent_spec
        
        spec = create_agent_spec(name="auto_scratchpad_test")
        logger.info("[INFO] Created spec with scratchpad=None")
        
        agent = AgentFactory.create(
            "air_agent",
            spec=spec,
            llm=azure_llm,
            scratchpad=None,  # Not provided
        )
        logger.info("[BUILD] Agent created with scratchpad=None")
        
        # Should have auto-created a scratchpad
        assert agent.scratchpad is not None
        assert isinstance(agent.scratchpad, StructuredScratchpad)
        logger.info(f"[OK] Scratchpad auto-created: {type(agent.scratchpad).__name__}")


@pytest.mark.asyncio
class TestAIRAgentExecution:
    """Test AIR Agent execution with task switching."""
    
    async def test_air_agent_speaker_to_laptop_switch(self, azure_llm, agent_context):
        """
        Main test: AIR Agent builds a speaker, then switches to building a laptop.
        
        This demonstrates:
        1. Custom agent registration
        2. Task execution with step tracking
        3. Task switching with scratchpad logging
        """
        logger.info("+" + "=" * 68 + "+")
        logger.info("|" + " MAIN TEST: Speaker -> Laptop Task Switching ".center(68) + "|")
        logger.info("|" + "-" * 68 + "|")
        logger.info("|" + " This test demonstrates:".ljust(68) + "|")
        logger.info("|" + "   1. Custom agent registration".ljust(68) + "|")
        logger.info("|" + "   2. Task execution with step tracking".ljust(68) + "|")
        logger.info("|" + "   3. Task switching with scratchpad logging".ljust(68) + "|")
        logger.info("+" + "=" * 68 + "+")
        
        # Create AIR Agent via builder
        logger.info("[BUILD] Creating AIR Agent with builder...")
        agent = (AgentBuilder()
            .with_name("speaker_laptop_builder")
            .with_description("Builds a speaker then switches to laptop")
            .with_llm(azure_llm)
            .with_scratchpad(StructuredScratchpad())
            .with_max_iterations(15)
            .as_custom_type("air_agent")
            .build())
        logger.info(f"[OK] Agent created: {agent.spec.name}")
        
        # Run the agent
        logger.info("[RUN] Running agent with input: 'Build a speaker step by step, then switch to building a laptop instead'")
        result = await agent.run(
            "Build a speaker step by step, then switch to building a laptop instead",
            agent_context
        )
        logger.info("[OK] Agent run complete")
        
        # Log results
        logger.info("-" * 70)
        logger.info("[RESULTS]")
        logger.info(f"       State: {result.state}")
        logger.info(f"       Content preview: {str(result.content)[:100]}...")
        logger.info(f"       Usage: {result.usage}")
        
        # Get scratchpad content from agent directly
        scratchpad_content = agent.get_scratchpad_content()
        logger.info("-" * 70)
        logger.info("[SCRATCHPAD CONTENT]")
        logger.info("-" * 70)
        for line in scratchpad_content.split('\n')[:30]:  # First 30 lines
            logger.info(f"  {line}")
        if scratchpad_content.count('\n') > 30:
            logger.info(f"  ... ({scratchpad_content.count(chr(10)) - 30} more lines)")
        
        # Get task info from agent
        tasks = agent.get_tasks()
        logger.info("-" * 70)
        logger.info(f"[TASKS] {len(tasks)} tasks tracked:")
        for task_id, task in tasks.items():
            logger.info(f"  [{task_id}] {task.task_name}: {len(task.steps)} steps, status={task.status}")
        
        # Assertions
        logger.info("-" * 70)
        logger.info("[ASSERTIONS]")
        
        assert result.is_success()
        logger.info("[OK] result.is_success() = True")
        
        assert result.state == AgentState.COMPLETED
        logger.info("[OK] result.state == AgentState.COMPLETED")
        
        # Check scratchpad contains key elements
        assert "TASK SWITCH" in scratchpad_content
        logger.info("[OK] 'TASK SWITCH' found in scratchpad")
        
        assert "Building a Speaker" in scratchpad_content or "speaker" in scratchpad_content.lower()
        logger.info("[OK] 'speaker' reference found in scratchpad")
        
        assert "Building a Laptop" in scratchpad_content or "laptop" in scratchpad_content.lower()
        logger.info("[OK] 'laptop' reference found in scratchpad")
        
        # Check tasks were tracked
        assert len(tasks) == 2  # Speaker and Laptop tasks
        logger.info(f"[OK] {len(tasks)} tasks tracked (expected: 2)")
        
        # Verify task statuses
        task_list = [{"name": t.task_name, "status": t.status} for t in tasks.values()]
        assert any(t["status"] == "paused" for t in task_list)  # Speaker was paused
        logger.info("[OK] At least one task has status='paused' (Speaker)")
        
        assert any(t["status"] == "completed" for t in task_list)  # Laptop was completed
        logger.info("[OK] At least one task has status='completed' (Laptop)")
        
        logger.info("+" + "=" * 68 + "+")
        logger.info("|" + " TEST PASSED: Speaker -> Laptop Task Switching ".center(68) + "|")
        logger.info("+" + "=" * 68 + "+")
    
    async def test_air_agent_scratchpad_tracking(self, azure_llm, agent_context):
        """Test that scratchpad properly tracks all steps."""
        logger.info("+-- TEST: air_agent_scratchpad_tracking " + "-" * 30 + "+")
        logger.info("| Verifying scratchpad tracks all steps properly")
        logger.info("+" + "-" * 68 + "+")
        
        scratchpad = StructuredScratchpad()
        
        agent = (AgentBuilder()
            .with_name("scratchpad_test_agent")
            .with_llm(azure_llm)
            .with_scratchpad(scratchpad)
            .as_custom_type("air_agent")
            .build())
        logger.info("[OK] Agent created with StructuredScratchpad")
        
        logger.info("[RUN] Running agent...")
        await agent.run(
            "Build a speaker then switch to building a laptop",
            agent_context
        )
        logger.info("[OK] Agent run complete")
        
        # Get scratchpad content directly from agent
        content = agent.get_scratchpad_content()
        
        logger.info("[STATS] Scratchpad stats:")
        logger.info(f"        - Length: {len(content)} characters")
        logger.info(f"        - Lines: {content.count(chr(10))} lines")
        
        # Should contain session header
        assert "AIR AGENT SESSION" in content
        logger.info("[OK] Contains 'AIR AGENT SESSION' header")
        
        # Should contain steps
        assert "Step" in content
        logger.info("[OK] Contains 'Step' markers")
        
        # Should contain summary
        assert "FINAL SUMMARY" in content
        logger.info("[OK] Contains 'FINAL SUMMARY' section")


@pytest.mark.asyncio
class TestAgentFactoryFeatures:
    """Test additional AgentFactory features."""
    
    async def test_clear_custom_types(self):
        """Test clearing custom types."""
        logger.info("+-- TEST: clear_custom_types " + "-" * 41 + "+")
        logger.info("| Testing AgentFactory.clear_custom_types() functionality")
        logger.info("+" + "-" * 68 + "+")
        
        # Register a temporary type
        logger.info("[+] Registering temporary 'temp_agent' type...")
        AgentFactory.register(
            type_id="temp_agent",
            agent_class=AIRAgent,
            override=True,
        )
        
        assert AgentFactory.is_registered("temp_agent")
        logger.info("[OK] temp_agent registered successfully")
        
        # Clear custom types
        logger.info("[CLEANUP] Calling clear_custom_types()...")
        cleared = AgentFactory.clear_custom_types()
        logger.info(f"[OK] Cleared {cleared} custom types")
        
        # temp_agent should be gone, but built-ins remain
        assert not AgentFactory.is_registered("temp_agent")
        logger.info("[OK] temp_agent is no longer registered")
        
        assert AgentFactory.is_registered("react")
        assert AgentFactory.is_registered("simple")
        logger.info("[OK] Built-in types (react, simple) still registered")
        
        # Re-register air_agent for other tests
        logger.info("[+] Re-registering air_agent for subsequent tests...")
        AgentFactory.register(
            type_id="air_agent",
            agent_class=AIRAgent,
            override=True,
        )
        logger.info("[OK] air_agent re-registered")
    
    async def test_list_registrations(self):
        """Test listing all registrations."""
        logger.info("+-- TEST: list_registrations " + "-" * 41 + "+")
        logger.info("| Testing AgentFactory.list_registrations() functionality")
        logger.info("+" + "-" * 68 + "+")
        
        registrations = AgentFactory.list_registrations()
        
        logger.info(f"[INFO] Found {len(registrations)} registrations:")
        for reg in registrations:
            logger.info(f"       [{reg.type_id}] {reg.display_name or 'N/A'}")
        
        assert len(registrations) >= 4  # At least built-in types
        logger.info(f"[OK] At least 4 registrations present (found {len(registrations)})")
        
        # Find AIR Agent registration
        air_reg = next((r for r in registrations if r.type_id == "air_agent"), None)
        assert air_reg is not None
        assert air_reg.display_name == "AIR Agent"
        logger.info(f"[OK] AIR Agent found in registrations: {air_reg.display_name}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
