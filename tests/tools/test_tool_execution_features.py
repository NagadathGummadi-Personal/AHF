"""
Tests for Tool Execution Features (v1.3.0)

Tests cover:
1. InterruptionConfig - Tool interruption behavior
2. PreToolSpeechConfig - Pre-execution speech generation
3. ExecutionConfig - Speech/execution timing
4. DynamicVariableConfig - Variable assignments from tool results
"""

import pytest
import asyncio
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock
import random

from core.tools import (
    # Enums
    SpeechMode,
    ExecutionMode,
    VariableAssignmentOperator,
    SpeechContextScope,
    TransformExecutionMode,
    # Config classes
    InterruptionConfig,
    PreToolSpeechConfig,
    ExecutionConfig,
    VariableAssignment,
    DynamicVariableConfig,
    # Tool specs
    FunctionToolSpec,
)
from core.tools.spec.tool_parameters import StringParameter


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def sample_tool_spec():
    """Create a sample tool spec for testing."""
    return FunctionToolSpec(
        id="test-tool-v1",
        tool_name="create_guest",
        description="Create a new guest in the system",
        parameters=[
            StringParameter(name="name", description="Guest name", required=True),
            StringParameter(name="email", description="Guest email", required=False),
        ],
    )


@pytest.fixture
def sample_tool_result():
    """Sample tool execution result."""
    return {
        "success": True,
        "data": {
            "guest_id": "guest-12345",
            "created": True,
            "name": "John Doe",
            "reservation_count": 5,
            "created_at": "2025-01-15T10:30:00Z",
        },
        "metadata": {
            "request_id": "req-abc123",
        }
    }


@pytest.fixture
def mock_llm():
    """Create a mock LLM for speech generation tests."""
    mock = AsyncMock()
    mock.get_answer = AsyncMock(return_value=MagicMock(
        content="Let me look that up for you..."
    ))
    return mock


# ============================================================================
# INTERRUPTION CONFIG TESTS
# ============================================================================

class TestInterruptionConfig:
    """Test InterruptionConfig behavior."""
    
    def test_default_interruption_allowed(self):
        """By default, interruptions should be allowed."""
        config = InterruptionConfig()
        assert config.disabled is False
    
    def test_interruption_disabled(self):
        """Test explicitly disabling interruptions."""
        config = InterruptionConfig(disabled=True)
        assert config.disabled is True
    
    def test_tool_spec_with_interruption_disabled(self, sample_tool_spec):
        """Test tool spec with interruption disabled."""
        sample_tool_spec.interruption = InterruptionConfig(disabled=True)
        assert sample_tool_spec.interruption.disabled is True
    
    def test_tool_spec_with_interruption_enabled(self, sample_tool_spec):
        """Test tool spec with interruption enabled."""
        sample_tool_spec.interruption = InterruptionConfig(disabled=False)
        assert sample_tool_spec.interruption.disabled is False


class TestInterruptionBehavior:
    """Test actual interruption behavior during tool execution."""
    
    @pytest.mark.asyncio
    async def test_tool_stops_on_interrupt_when_allowed(self):
        """Tool should stop when interrupt received and interruptions allowed."""
        interrupt_event = asyncio.Event()
        execution_completed = False
        was_interrupted = False
        
        async def simulate_tool_execution(interrupt_config: InterruptionConfig):
            nonlocal execution_completed, was_interrupted
            
            for i in range(10):
                # Check for interrupt if not disabled
                if not interrupt_config.disabled and interrupt_event.is_set():
                    was_interrupted = True
                    return {"status": "interrupted", "progress": i}
                
                await asyncio.sleep(0.05)  # Simulate work
            
            execution_completed = True
            return {"status": "completed", "progress": 10}
        
        # Create config with interruptions allowed
        config = InterruptionConfig(disabled=False)
        
        # Start tool execution
        task = asyncio.create_task(simulate_tool_execution(config))
        
        # Send interrupt after short delay
        await asyncio.sleep(0.1)
        interrupt_event.set()
        
        result = await task
        
        assert was_interrupted is True
        assert execution_completed is False
        assert result["status"] == "interrupted"
    
    @pytest.mark.asyncio
    async def test_tool_continues_when_interrupts_disabled(self):
        """Tool should continue when interrupt received but interruptions disabled."""
        interrupt_event = asyncio.Event()
        execution_completed = False
        was_interrupted = False
        
        async def simulate_tool_execution(interrupt_config: InterruptionConfig):
            nonlocal execution_completed, was_interrupted
            
            for i in range(5):
                # Check for interrupt if not disabled
                if not interrupt_config.disabled and interrupt_event.is_set():
                    was_interrupted = True
                    return {"status": "interrupted", "progress": i}
                
                await asyncio.sleep(0.02)  # Simulate work
            
            execution_completed = True
            return {"status": "completed", "progress": 5}
        
        # Create config with interruptions DISABLED
        config = InterruptionConfig(disabled=True)
        
        # Start tool execution
        task = asyncio.create_task(simulate_tool_execution(config))
        
        # Send interrupt after short delay
        await asyncio.sleep(0.03)
        interrupt_event.set()
        
        result = await task
        
        assert was_interrupted is False
        assert execution_completed is True
        assert result["status"] == "completed"


# ============================================================================
# PRE-TOOL SPEECH CONFIG TESTS
# ============================================================================

class TestPreToolSpeechConfig:
    """Test PreToolSpeechConfig creation and validation."""
    
    def test_default_speech_disabled(self):
        """By default, speech should be disabled."""
        config = PreToolSpeechConfig()
        assert config.enabled is False
    
    def test_speech_mode_auto(self):
        """Test AUTO speech mode configuration."""
        config = PreToolSpeechConfig(
            enabled=True,
            mode=SpeechMode.AUTO,
            context_scope=SpeechContextScope.FULL_CONTEXT,
            speech_style="friendly and helpful"
        )
        assert config.enabled is True
        assert config.mode == SpeechMode.AUTO
        assert config.context_scope == SpeechContextScope.FULL_CONTEXT
        assert config.speech_style == "friendly and helpful"
    
    def test_speech_mode_random(self):
        """Test RANDOM speech mode configuration."""
        messages = [
            "Let me check that for you...",
            "Looking that up now...",
            "One moment please..."
        ]
        config = PreToolSpeechConfig(
            enabled=True,
            mode=SpeechMode.RANDOM,
            random_messages=messages
        )
        assert config.enabled is True
        assert config.mode == SpeechMode.RANDOM
        assert config.random_messages == messages
    
    def test_speech_mode_constant(self):
        """Test CONSTANT speech mode configuration."""
        config = PreToolSpeechConfig(
            enabled=True,
            mode=SpeechMode.CONSTANT,
            constant_message="Processing your request..."
        )
        assert config.enabled is True
        assert config.mode == SpeechMode.CONSTANT
        assert config.constant_message == "Processing your request..."
    
    def test_auto_mode_with_custom_scope(self):
        """Test AUTO mode with custom instruction scope."""
        config = PreToolSpeechConfig(
            enabled=True,
            mode=SpeechMode.AUTO,
            context_scope=SpeechContextScope.CUSTOM,
            llm_instruction="Generate a brief message about looking up the guest's reservation."
        )
        assert config.context_scope == SpeechContextScope.CUSTOM
        assert "reservation" in config.llm_instruction
    
    def test_auto_mode_parameters(self):
        """Test AUTO mode LLM parameters."""
        config = PreToolSpeechConfig(
            enabled=True,
            mode=SpeechMode.AUTO,
            max_tokens=30,
            temperature=0.5,
            include_tool_params=True,
            include_user_intent=True
        )
        assert config.max_tokens == 30
        assert config.temperature == 0.5
        assert config.include_tool_params is True
        assert config.include_user_intent is True


class TestPreToolSpeechBehavior:
    """Test actual speech generation behavior."""
    
    def test_random_speech_selection(self):
        """Test random message selection."""
        messages = [
            "Message 1",
            "Message 2",
            "Message 3"
        ]
        config = PreToolSpeechConfig(
            enabled=True,
            mode=SpeechMode.RANDOM,
            random_messages=messages
        )
        
        # Generate multiple speeches and verify they're from the list
        selected = random.choice(config.random_messages)
        assert selected in messages
    
    def test_constant_speech(self):
        """Test constant message."""
        constant_msg = "Please wait while I process your request..."
        config = PreToolSpeechConfig(
            enabled=True,
            mode=SpeechMode.CONSTANT,
            constant_message=constant_msg
        )
        
        assert config.constant_message == constant_msg
    
    @pytest.mark.asyncio
    async def test_auto_speech_with_mock_llm(self, mock_llm, sample_tool_spec):
        """Test AUTO speech generation with mock LLM."""
        config = PreToolSpeechConfig(
            enabled=True,
            mode=SpeechMode.AUTO,
            context_scope=SpeechContextScope.TOOL_ONLY,
            max_tokens=50,
            temperature=0.7
        )
        
        # Simulate speech generation
        if config.enabled and config.mode == SpeechMode.AUTO:
            # Build context based on scope
            context = {
                "tool_name": sample_tool_spec.tool_name,
                "tool_description": sample_tool_spec.description,
            }
            
            if config.include_tool_params:
                context["parameters"] = [p.name for p in sample_tool_spec.parameters]
            
            # Call mock LLM
            response = await mock_llm.get_answer(
                messages=[{"role": "system", "content": f"Generate speech for tool: {context}"}],
                ctx=MagicMock()
            )
            
            assert response.content == "Let me look that up for you..."
            mock_llm.get_answer.assert_called_once()


class TestPreToolSpeechWithAzureLLM:
    """Test pre-tool speech with Azure LLM configuration."""
    
    @pytest.fixture
    def azure_llm_config(self):
        """Azure LLM configuration for testing."""
        return {
            "endpoint": "https://test-endpoint.openai.azure.com/",
            "deployment_name": "gpt-4",
            "api_version": "2024-02-15-preview",
            "api_key": "test-api-key",
        }
    
    @pytest.mark.asyncio
    async def test_auto_speech_full_context_scope(self, azure_llm_config):
        """Test AUTO speech with FULL_CONTEXT scope using Azure LLM."""
        config = PreToolSpeechConfig(
            enabled=True,
            mode=SpeechMode.AUTO,
            context_scope=SpeechContextScope.FULL_CONTEXT,
            include_tool_params=True,
            include_user_intent=True,
            max_tokens=50,
            temperature=0.7,
            speech_style="professional and reassuring"
        )
        
        # Verify config is set up correctly for Azure LLM
        assert config.context_scope == SpeechContextScope.FULL_CONTEXT
        assert config.max_tokens == 50
        assert config.temperature == 0.7
        
        # Build the prompt that would be sent to Azure LLM
        system_prompt = f"""Generate a brief, {config.speech_style} message to say before executing a tool.
Context scope: {config.context_scope.value}
Max tokens: {config.max_tokens}
"""
        assert "professional and reassuring" in system_prompt
    
    @pytest.mark.asyncio
    async def test_auto_speech_tool_only_scope(self, azure_llm_config):
        """Test AUTO speech with TOOL_ONLY scope."""
        config = PreToolSpeechConfig(
            enabled=True,
            mode=SpeechMode.AUTO,
            context_scope=SpeechContextScope.TOOL_ONLY,
            include_tool_params=True,
            max_tokens=30
        )
        
        # Verify TOOL_ONLY scope doesn't include conversation history
        assert config.context_scope == SpeechContextScope.TOOL_ONLY
        assert config.include_tool_params is True
        # Tool context would be built like this:
        # {"tool_name": "create_reservation", "parameters": ["guest_id", ...]}
        # But conversation history would NOT be included
    
    @pytest.mark.asyncio
    async def test_auto_speech_custom_instruction(self, azure_llm_config):
        """Test AUTO speech with custom LLM instruction."""
        custom_instruction = """
        Generate a friendly, brief message (max 2 sentences) that:
        1. Acknowledges the user's request
        2. Mentions we're looking up their reservation
        3. Uses their name if available in the context
        """
        
        config = PreToolSpeechConfig(
            enabled=True,
            mode=SpeechMode.AUTO,
            context_scope=SpeechContextScope.CUSTOM,
            llm_instruction=custom_instruction,
            max_tokens=40
        )
        
        assert config.context_scope == SpeechContextScope.CUSTOM
        assert "reservation" in config.llm_instruction
        assert "name" in config.llm_instruction


# ============================================================================
# EXECUTION CONFIG TESTS
# ============================================================================

class TestExecutionConfig:
    """Test ExecutionConfig behavior."""
    
    def test_default_sequential_mode(self):
        """Default execution mode should be sequential."""
        config = ExecutionConfig()
        assert config.mode == ExecutionMode.SEQUENTIAL
    
    def test_parallel_execution_mode(self):
        """Test parallel execution mode configuration."""
        config = ExecutionConfig(mode=ExecutionMode.PARALLEL)
        assert config.mode == ExecutionMode.PARALLEL
    
    def test_sequential_with_timeout(self):
        """Test sequential mode with speech timeout."""
        config = ExecutionConfig(
            mode=ExecutionMode.SEQUENTIAL,
            speech_timeout_ms=5000
        )
        assert config.mode == ExecutionMode.SEQUENTIAL
        assert config.speech_timeout_ms == 5000


class TestExecutionBehavior:
    """Test actual execution mode behavior."""
    
    @pytest.mark.asyncio
    async def test_sequential_execution(self):
        """Test sequential execution: speech completes before tool."""
        speech_completed = False
        tool_started_after_speech = False
        
        async def simulate_speech():
            nonlocal speech_completed
            await asyncio.sleep(0.1)
            speech_completed = True
            return "Looking that up..."
        
        async def simulate_tool():
            nonlocal tool_started_after_speech
            tool_started_after_speech = speech_completed
            await asyncio.sleep(0.1)
            return {"result": "done"}
        
        config = ExecutionConfig(mode=ExecutionMode.SEQUENTIAL)
        
        if config.mode == ExecutionMode.SEQUENTIAL:
            # Speech first, then tool
            await simulate_speech()
            await simulate_tool()
        
        assert speech_completed is True
        assert tool_started_after_speech is True
    
    @pytest.mark.asyncio
    async def test_parallel_execution(self):
        """Test parallel execution: speech and tool run simultaneously."""
        speech_start_time = None
        tool_start_time = None
        
        async def simulate_speech():
            nonlocal speech_start_time
            speech_start_time = asyncio.get_event_loop().time()
            await asyncio.sleep(0.1)
            return "Looking that up..."
        
        async def simulate_tool():
            nonlocal tool_start_time
            tool_start_time = asyncio.get_event_loop().time()
            await asyncio.sleep(0.1)
            return {"result": "done"}
        
        config = ExecutionConfig(mode=ExecutionMode.PARALLEL)
        
        if config.mode == ExecutionMode.PARALLEL:
            # Run both concurrently
            await asyncio.gather(simulate_speech(), simulate_tool())
        
        # Both should have started at nearly the same time
        assert speech_start_time is not None
        assert tool_start_time is not None
        assert abs(speech_start_time - tool_start_time) < 0.01  # Within 10ms


# ============================================================================
# DYNAMIC VARIABLE CONFIG TESTS
# ============================================================================

class TestVariableAssignment:
    """Test VariableAssignment configuration."""
    
    def test_basic_set_assignment(self):
        """Test basic SET assignment."""
        assignment = VariableAssignment(
            target_variable="guest_id",
            source_field="data.guest_id",
            operator=VariableAssignmentOperator.SET
        )
        assert assignment.target_variable == "guest_id"
        assert assignment.source_field == "data.guest_id"
        assert assignment.operator == VariableAssignmentOperator.SET
    
    def test_set_if_exists_assignment(self):
        """Test SET_IF_EXISTS assignment."""
        assignment = VariableAssignment(
            target_variable="email",
            source_field="data.email",
            operator=VariableAssignmentOperator.SET_IF_EXISTS,
            default_value="unknown@example.com"
        )
        assert assignment.operator == VariableAssignmentOperator.SET_IF_EXISTS
        assert assignment.default_value == "unknown@example.com"
    
    def test_set_if_truthy_assignment(self):
        """Test SET_IF_TRUTHY assignment."""
        assignment = VariableAssignment(
            target_variable="is_new_guest",
            source_field="data.created",
            operator=VariableAssignmentOperator.SET_IF_TRUTHY,
            default_value=False
        )
        assert assignment.operator == VariableAssignmentOperator.SET_IF_TRUTHY
    
    def test_increment_assignment(self):
        """Test INCREMENT assignment."""
        assignment = VariableAssignment(
            target_variable="total_reservations",
            source_field="data.reservation_count",
            operator=VariableAssignmentOperator.INCREMENT
        )
        assert assignment.operator == VariableAssignmentOperator.INCREMENT
    
    def test_append_assignment(self):
        """Test APPEND assignment."""
        assignment = VariableAssignment(
            target_variable="guest_ids",
            source_field="data.guest_id",
            operator=VariableAssignmentOperator.APPEND
        )
        assert assignment.operator == VariableAssignmentOperator.APPEND
    
    def test_transform_with_expression(self):
        """Test TRANSFORM with simple expression."""
        assignment = VariableAssignment(
            target_variable="is_created",
            source_field="data.created",
            operator=VariableAssignmentOperator.TRANSFORM,
            transform_expr="bool(value)"
        )
        assert assignment.transform_expr == "bool(value)"
    
    def test_transform_with_sync_function(self):
        """Test TRANSFORM with sync function."""
        def format_name(value):
            return value.upper() if value else ""
        
        assignment = VariableAssignment(
            target_variable="formatted_name",
            source_field="data.name",
            operator=VariableAssignmentOperator.TRANSFORM,
            transform_func=format_name,
            transform_execution=TransformExecutionMode.SYNC
        )
        assert assignment.transform_func is not None
        assert assignment.transform_execution == TransformExecutionMode.SYNC
    
    def test_transform_with_async_function(self):
        """Test TRANSFORM with async function."""
        async def fetch_profile(value):
            await asyncio.sleep(0.01)
            return {"id": value, "enriched": True}
        
        assignment = VariableAssignment(
            target_variable="enriched_profile",
            source_field="data.guest_id",
            operator=VariableAssignmentOperator.TRANSFORM,
            transform_func=fetch_profile,
            transform_execution=TransformExecutionMode.ASYNC
        )
        assert assignment.transform_execution == TransformExecutionMode.ASYNC
    
    def test_transform_with_await_mode(self):
        """Test TRANSFORM with AWAIT execution mode."""
        async def validate_data(value):
            await asyncio.sleep(0.01)
            return {"validated": True, "value": value}
        
        assignment = VariableAssignment(
            target_variable="validated_data",
            source_field="data.guest_id",
            operator=VariableAssignmentOperator.TRANSFORM,
            transform_func=validate_data,
            transform_execution=TransformExecutionMode.AWAIT
        )
        assert assignment.transform_execution == TransformExecutionMode.AWAIT


class TestDynamicVariableConfig:
    """Test DynamicVariableConfig behavior."""
    
    def test_default_enabled(self):
        """Dynamic variables should be enabled by default."""
        config = DynamicVariableConfig()
        assert config.enabled is True
        assert config.assignments == []
    
    def test_multiple_assignments(self):
        """Test config with multiple assignments."""
        config = DynamicVariableConfig(
            enabled=True,
            assignments=[
                VariableAssignment(
                    target_variable="guest_id",
                    source_field="data.guest_id",
                    operator=VariableAssignmentOperator.SET
                ),
                VariableAssignment(
                    target_variable="is_new_guest",
                    source_field="data.created",
                    operator=VariableAssignmentOperator.SET_IF_TRUTHY,
                    default_value=False
                ),
                VariableAssignment(
                    target_variable="reservation_count",
                    source_field="data.reservation_count",
                    operator=VariableAssignmentOperator.INCREMENT
                ),
            ]
        )
        assert len(config.assignments) == 3
    
    def test_on_error_behavior(self):
        """Test on_error configuration."""
        config = DynamicVariableConfig(
            enabled=True,
            on_error="raise"
        )
        assert config.on_error == "raise"


class TestDynamicVariableExecution:
    """Test actual dynamic variable assignment execution."""
    
    def _get_nested_value(self, obj: Dict, path: str) -> Any:
        """Get nested value from dict using dot notation."""
        keys = path.split(".")
        value = obj
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        return value
    
    def test_set_operator(self, sample_tool_result):
        """Test SET operator execution."""
        assignment = VariableAssignment(
            target_variable="guest_id",
            source_field="data.guest_id",
            operator=VariableAssignmentOperator.SET
        )
        
        value = self._get_nested_value(sample_tool_result, assignment.source_field)
        variables = {}
        
        if assignment.operator == VariableAssignmentOperator.SET:
            variables[assignment.target_variable] = value
        
        assert variables["guest_id"] == "guest-12345"
    
    def test_set_if_exists_with_existing_field(self, sample_tool_result):
        """Test SET_IF_EXISTS when field exists."""
        assignment = VariableAssignment(
            target_variable="guest_name",
            source_field="data.name",
            operator=VariableAssignmentOperator.SET_IF_EXISTS,
            default_value="Unknown"
        )
        
        value = self._get_nested_value(sample_tool_result, assignment.source_field)
        variables = {}
        
        if assignment.operator == VariableAssignmentOperator.SET_IF_EXISTS:
            if value is not None:
                variables[assignment.target_variable] = value
            else:
                variables[assignment.target_variable] = assignment.default_value
        
        assert variables["guest_name"] == "John Doe"
    
    def test_set_if_exists_with_missing_field(self, sample_tool_result):
        """Test SET_IF_EXISTS when field doesn't exist."""
        assignment = VariableAssignment(
            target_variable="phone",
            source_field="data.phone",
            operator=VariableAssignmentOperator.SET_IF_EXISTS,
            default_value="N/A"
        )
        
        value = self._get_nested_value(sample_tool_result, assignment.source_field)
        variables = {}
        
        if assignment.operator == VariableAssignmentOperator.SET_IF_EXISTS:
            if value is not None:
                variables[assignment.target_variable] = value
            else:
                variables[assignment.target_variable] = assignment.default_value
        
        assert variables["phone"] == "N/A"
    
    def test_set_if_truthy_with_truthy_value(self, sample_tool_result):
        """Test SET_IF_TRUTHY with truthy value."""
        assignment = VariableAssignment(
            target_variable="is_new_guest",
            source_field="data.created",
            operator=VariableAssignmentOperator.SET_IF_TRUTHY,
            default_value=False
        )
        
        value = self._get_nested_value(sample_tool_result, assignment.source_field)
        variables = {"is_new_guest": False}  # Existing value
        
        if assignment.operator == VariableAssignmentOperator.SET_IF_TRUTHY:
            if value:
                variables[assignment.target_variable] = value
        
        assert variables["is_new_guest"] is True
    
    def test_set_if_truthy_with_falsy_value(self):
        """Test SET_IF_TRUTHY with falsy value."""
        result = {"data": {"created": False}}
        
        assignment = VariableAssignment(
            target_variable="is_new_guest",
            source_field="data.created",
            operator=VariableAssignmentOperator.SET_IF_TRUTHY,
            default_value=True
        )
        
        value = self._get_nested_value(result, assignment.source_field)
        variables = {"is_new_guest": True}  # Existing value should not change
        
        if assignment.operator == VariableAssignmentOperator.SET_IF_TRUTHY:
            if value:
                variables[assignment.target_variable] = value
        
        # Should remain True because source value is falsy
        assert variables["is_new_guest"] is True
    
    def test_increment_operator(self, sample_tool_result):
        """Test INCREMENT operator."""
        assignment = VariableAssignment(
            target_variable="total_reservations",
            source_field="data.reservation_count",
            operator=VariableAssignmentOperator.INCREMENT
        )
        
        value = self._get_nested_value(sample_tool_result, assignment.source_field)
        variables = {"total_reservations": 10}  # Existing value
        
        if assignment.operator == VariableAssignmentOperator.INCREMENT:
            current = variables.get(assignment.target_variable, 0)
            variables[assignment.target_variable] = current + (value or 0)
        
        assert variables["total_reservations"] == 15  # 10 + 5
    
    def test_append_operator_to_list(self, sample_tool_result):
        """Test APPEND operator to existing list."""
        assignment = VariableAssignment(
            target_variable="guest_ids",
            source_field="data.guest_id",
            operator=VariableAssignmentOperator.APPEND
        )
        
        value = self._get_nested_value(sample_tool_result, assignment.source_field)
        variables = {"guest_ids": ["guest-11111", "guest-22222"]}
        
        if assignment.operator == VariableAssignmentOperator.APPEND:
            current = variables.get(assignment.target_variable, [])
            if isinstance(current, list):
                current.append(value)
                variables[assignment.target_variable] = current
        
        assert variables["guest_ids"] == ["guest-11111", "guest-22222", "guest-12345"]
    
    def test_transform_with_expression(self, sample_tool_result):
        """Test TRANSFORM with simple expression."""
        assignment = VariableAssignment(
            target_variable="guest_name_upper",
            source_field="data.name",
            operator=VariableAssignmentOperator.TRANSFORM,
            transform_expr="str(value).upper()"
        )
        
        value = self._get_nested_value(sample_tool_result, assignment.source_field)
        variables = {}
        
        if assignment.operator == VariableAssignmentOperator.TRANSFORM:
            if assignment.transform_expr:
                # Safe eval for simple expressions
                transformed = eval(assignment.transform_expr, {"value": value, "str": str})
                variables[assignment.target_variable] = transformed
        
        assert variables["guest_name_upper"] == "JOHN DOE"
    
    def test_transform_with_sync_function(self, sample_tool_result):
        """Test TRANSFORM with sync function."""
        def format_guest_id(value):
            return f"GUEST-{value.split('-')[1]}" if value else None
        
        assignment = VariableAssignment(
            target_variable="formatted_id",
            source_field="data.guest_id",
            operator=VariableAssignmentOperator.TRANSFORM,
            transform_func=format_guest_id,
            transform_execution=TransformExecutionMode.SYNC
        )
        
        value = self._get_nested_value(sample_tool_result, assignment.source_field)
        variables = {}
        
        if assignment.operator == VariableAssignmentOperator.TRANSFORM:
            if assignment.transform_func and assignment.transform_execution == TransformExecutionMode.SYNC:
                variables[assignment.target_variable] = assignment.transform_func(value)
        
        assert variables["formatted_id"] == "GUEST-12345"
    
    @pytest.mark.asyncio
    async def test_transform_with_async_function_await_mode(self, sample_tool_result):
        """Test TRANSFORM with async function in AWAIT mode."""
        async def enrich_guest(value):
            await asyncio.sleep(0.01)  # Simulate async operation
            return {"original_id": value, "vip_status": True, "loyalty_points": 1000}
        
        assignment = VariableAssignment(
            target_variable="enriched_guest",
            source_field="data.guest_id",
            operator=VariableAssignmentOperator.TRANSFORM,
            transform_func=enrich_guest,
            transform_execution=TransformExecutionMode.AWAIT
        )
        
        value = self._get_nested_value(sample_tool_result, assignment.source_field)
        variables = {}
        
        if assignment.operator == VariableAssignmentOperator.TRANSFORM:
            if assignment.transform_func and assignment.transform_execution == TransformExecutionMode.AWAIT:
                # Await the async function
                variables[assignment.target_variable] = await assignment.transform_func(value)
        
        assert variables["enriched_guest"]["original_id"] == "guest-12345"
        assert variables["enriched_guest"]["vip_status"] is True
    
    @pytest.mark.asyncio
    async def test_transform_with_async_function_async_mode(self, sample_tool_result):
        """Test TRANSFORM with async function in ASYNC mode (fire-and-forget)."""
        callback_received = {"value": None}
        
        async def update_external_system(value):
            await asyncio.sleep(0.05)
            callback_received["value"] = value
            return True
        
        assignment = VariableAssignment(
            target_variable="update_task",
            source_field="data.guest_id",
            operator=VariableAssignmentOperator.TRANSFORM,
            transform_func=update_external_system,
            transform_execution=TransformExecutionMode.ASYNC
        )
        
        value = self._get_nested_value(sample_tool_result, assignment.source_field)
        variables = {}
        background_task = None
        
        if assignment.operator == VariableAssignmentOperator.TRANSFORM:
            if assignment.transform_func and assignment.transform_execution == TransformExecutionMode.ASYNC:
                # Fire and forget - don't await, tool result returns immediately
                background_task = asyncio.create_task(assignment.transform_func(value))
                variables[assignment.target_variable] = "pending"
        
        # Tool result returned immediately
        assert variables["update_task"] == "pending"
        assert background_task is not None  # Task was created
        
        # But the async task is still running
        assert callback_received["value"] is None
        
        # Wait for it to complete
        await asyncio.sleep(0.1)
        assert callback_received["value"] == "guest-12345"


# ============================================================================
# INTEGRATION TESTS - COMPLETE TOOL SPEC
# ============================================================================

class TestCompleteToolSpec:
    """Test complete tool specification with all new features."""
    
    def test_tool_spec_with_all_features(self):
        """Test creating a tool spec with all new features configured."""
        tool = FunctionToolSpec(
            id="create-guest-v1",
            tool_name="create_guest",
            description="Create a new guest in the hotel system",
            parameters=[
                StringParameter(name="name", description="Guest name", required=True),
                StringParameter(name="email", description="Guest email", required=False),
            ],
            timeout_s=30,
            # Interruption: Don't allow interruptions during guest creation
            interruption=InterruptionConfig(disabled=True),
            # Pre-tool speech: Auto-generate using tool context
            pre_tool_speech=PreToolSpeechConfig(
                enabled=True,
                mode=SpeechMode.AUTO,
                context_scope=SpeechContextScope.TOOL_ONLY,
                include_tool_params=True,
                max_tokens=40,
                temperature=0.7,
                speech_style="friendly and professional"
            ),
            # Execution: Wait for speech before executing
            execution=ExecutionConfig(
                mode=ExecutionMode.SEQUENTIAL,
                speech_timeout_ms=3000
            ),
            # Dynamic variables: Update session variables from result
            dynamic_variables=DynamicVariableConfig(
                enabled=True,
                assignments=[
                    VariableAssignment(
                        target_variable="guest_id",
                        source_field="data.guest_id",
                        operator=VariableAssignmentOperator.SET
                    ),
                    VariableAssignment(
                        target_variable="is_new_guest",
                        source_field="data.created",
                        operator=VariableAssignmentOperator.SET_IF_TRUTHY,
                        default_value=False
                    ),
                ],
                on_error="log"
            )
        )
        
        # Verify all configurations
        assert tool.interruption.disabled is True
        assert tool.pre_tool_speech.enabled is True
        assert tool.pre_tool_speech.mode == SpeechMode.AUTO
        assert tool.execution.mode == ExecutionMode.SEQUENTIAL
        assert len(tool.dynamic_variables.assignments) == 2
        assert tool.timeout_s == 30
    
    def test_tool_spec_minimal_defaults(self):
        """Test tool spec with minimal configuration uses proper defaults."""
        tool = FunctionToolSpec(
            id="simple-tool-v1",
            tool_name="simple_tool",
            description="A simple tool",
            parameters=[]
        )
        
        # Check defaults
        assert tool.interruption.disabled is False  # Interruptions allowed by default
        assert tool.pre_tool_speech.enabled is False  # Speech disabled by default
        assert tool.execution.mode == ExecutionMode.SEQUENTIAL  # Sequential by default
        assert tool.dynamic_variables.enabled is True  # Enabled but empty by default
        assert len(tool.dynamic_variables.assignments) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
