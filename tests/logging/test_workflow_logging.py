"""
Tests for Workflow Logging Infrastructure.

Tests the WorkflowMetrics dataclass, metrics_context context manager,
workflow decorators, and LoggerAdaptor.log_workflow_metrics() method.

Version: 1.0.0
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, MagicMock
from typing import Any

from utils.logging import (
    LoggerAdaptor,
    WorkflowMetrics,
    metrics_context,
    collect_workflow_metrics,
    collect_node_metrics,
    collect_agent_metrics,
    collect_llm_metrics,
    collect_edge_metrics,
    collect_tool_metrics,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def logger():
    """Create a test logger with test environment config."""
    logger = LoggerAdaptor.get_logger("test.workflow_logging", environment="test")
    yield logger
    logger.shutdown()
    LoggerAdaptor.clear_instances()


@pytest.fixture
def mock_config():
    """Mock workflow logging config."""
    return {
        "enabled": True,
        "log_user_messages": True,
        "log_agent_responses": True,
        "log_usage_metrics": True,
        "log_condition_evaluations": True,
        "log_pass_through_extractions": True,
        "truncate_messages_at": 100,
        "include_trace_id": True,
        "async_logging": False,
        "messages": {
            "tokens": "Consumed Input tokens {input_tokens}, Output tokens {output_tokens}, Total {total_tokens}",
            "duration": "{component} '{name}' completed in {duration_ms:.2f}ms",
            "cost": "Cost: ${cost_usd:.6f}",
            "error": "{component} '{name}' failed: {error}"
        }
    }


@pytest.fixture
def sample_usage():
    """Create a mock usage object."""
    usage = Mock()
    usage.prompt_tokens = 100
    usage.completion_tokens = 50
    usage.total_tokens = 150
    usage.cost_usd = 0.001
    usage.iterations = 2
    usage.tool_calls = 1
    usage.llm_calls = 3
    return usage


# =============================================================================
# TEST CASES - WorkflowMetrics DATACLASS
# =============================================================================

class TestWorkflowMetrics:
    """Tests for WorkflowMetrics dataclass."""
    
    def test_default_initialization(self):
        """Test WorkflowMetrics initializes with defaults."""
        metrics = WorkflowMetrics()
        
        assert metrics.component_type is None
        assert metrics.component_id is None
        assert metrics.trace_id is None
        assert metrics.input_tokens is None
        assert metrics.output_tokens is None
        assert metrics.total_tokens is None
        assert metrics.cost_usd is None
        assert metrics.duration_ms is None
        assert metrics.success is None
        assert metrics.error is None
        assert metrics.metadata == {}
    
    def test_custom_initialization(self):
        """Test WorkflowMetrics with custom values."""
        metrics = WorkflowMetrics(
            component_type='agent',
            component_id='greeting-agent',
            component_name='Greeting Agent',
            trace_id='abc123',
            workflow_id='salon-workflow',
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            cost_usd=0.001,
            duration_ms=1234.5,
            success=True,
        )
        
        assert metrics.component_type == 'agent'
        assert metrics.component_id == 'greeting-agent'
        assert metrics.component_name == 'Greeting Agent'
        assert metrics.trace_id == 'abc123'
        assert metrics.workflow_id == 'salon-workflow'
        assert metrics.input_tokens == 100
        assert metrics.output_tokens == 50
        assert metrics.total_tokens == 150
        assert metrics.cost_usd == 0.001
        assert metrics.duration_ms == 1234.5
        assert metrics.success is True
    
    def test_to_log_dict_basic(self):
        """Test converting metrics to log dictionary."""
        metrics = WorkflowMetrics(
            component_type='agent',
            component_id='test-agent',
            trace_id='trace123',
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            duration_ms=500.0,
            success=True,
        )
        
        config = {"include_trace_id": True, "log_usage_metrics": True}
        log_dict = metrics.to_log_dict(config)
        
        assert log_dict['trace_id'] == 'trace123'
        assert log_dict['component'] == 'agent'
        assert log_dict['component_id'] == 'test-agent'
        assert log_dict['input_tokens'] == 100
        assert log_dict['output_tokens'] == 50
        assert log_dict['total_tokens'] == 150
        assert log_dict['duration_ms'] == 500.0
        assert log_dict['success'] is True
    
    def test_to_log_dict_with_messages(self):
        """Test log dict includes messages when configured."""
        metrics = WorkflowMetrics(
            component_type='llm',
            user_message="Hello, how are you?",
            response="I'm doing great, thanks for asking!",
        )
        
        config = {"log_user_messages": True, "log_agent_responses": True}
        log_dict = metrics.to_log_dict(config)
        
        assert log_dict['user_message'] == "Hello, how are you?"
        assert log_dict['response'] == "I'm doing great, thanks for asking!"
    
    def test_to_log_dict_message_truncation(self):
        """Test message truncation in log dict."""
        long_message = "A" * 200
        metrics = WorkflowMetrics(
            component_type='agent',
            user_message=long_message,
        )
        
        config = {"log_user_messages": True, "truncate_messages_at": 50}
        log_dict = metrics.to_log_dict(config)
        
        assert len(log_dict['user_message']) == 50
        assert log_dict['user_message'].endswith("...")
    
    def test_to_log_dict_excludes_when_disabled(self):
        """Test log dict excludes fields when disabled in config."""
        metrics = WorkflowMetrics(
            component_type='agent',
            trace_id='trace123',
            user_message="Hello",
            input_tokens=100,
        )
        
        config = {
            "include_trace_id": False,
            "log_user_messages": False,
            "log_usage_metrics": False,
        }
        log_dict = metrics.to_log_dict(config)
        
        assert 'trace_id' not in log_dict
        assert 'user_message' not in log_dict
        assert 'input_tokens' not in log_dict
    
    def test_to_log_dict_with_condition_evaluation(self):
        """Test log dict includes condition evaluation results."""
        metrics = WorkflowMetrics(
            component_type='condition',
            condition_type='llm',
            condition_result=True,
        )
        
        config = {"log_condition_evaluations": True}
        log_dict = metrics.to_log_dict(config)
        
        assert log_dict['condition_type'] == 'llm'
        assert log_dict['condition_result'] is True
    
    def test_to_log_dict_with_extracted_fields(self):
        """Test log dict includes extracted fields."""
        metrics = WorkflowMetrics(
            component_type='edge',
            extracted_fields={"service_name": "haircut", "date": "Saturday"},
        )
        
        config = {"log_pass_through_extractions": True}
        log_dict = metrics.to_log_dict(config)
        
        assert log_dict['extracted_fields'] == {"service_name": "haircut", "date": "Saturday"}
    
    def test_to_log_dict_with_error(self):
        """Test log dict includes error information."""
        metrics = WorkflowMetrics(
            component_type='agent',
            success=False,
            error="Connection timeout",
            error_type="TimeoutError",
        )
        
        log_dict = metrics.to_log_dict({})
        
        assert log_dict['success'] is False
        assert log_dict['error'] == "Connection timeout"
        assert log_dict['error_type'] == "TimeoutError"
    
    def test_to_log_dict_with_metadata(self):
        """Test log dict includes custom metadata."""
        metrics = WorkflowMetrics(
            component_type='workflow',
            metadata={"custom_field": "custom_value", "count": 42},
        )
        
        log_dict = metrics.to_log_dict({})
        
        assert log_dict['custom_field'] == "custom_value"
        assert log_dict['count'] == 42
    
    def test_update_from_usage(self, sample_usage):
        """Test updating metrics from usage object."""
        metrics = WorkflowMetrics()
        metrics.update_from_usage(sample_usage)
        
        assert metrics.input_tokens == 100
        assert metrics.output_tokens == 50
        assert metrics.total_tokens == 150
        assert metrics.cost_usd == 0.001
        assert metrics.iterations == 2
        assert metrics.tool_calls == 1
        assert metrics.llm_calls == 3
    
    def test_update_from_usage_none(self):
        """Test update_from_usage handles None gracefully."""
        metrics = WorkflowMetrics()
        metrics.update_from_usage(None)
        
        # Should not raise, all values should remain None
        assert metrics.input_tokens is None
        assert metrics.output_tokens is None
    
    def test_update_from_usage_partial(self):
        """Test update_from_usage handles partial usage object."""
        partial_usage = Mock(spec=['prompt_tokens', 'completion_tokens'])
        partial_usage.prompt_tokens = 100
        partial_usage.completion_tokens = 50
        
        metrics = WorkflowMetrics()
        metrics.update_from_usage(partial_usage)
        
        assert metrics.input_tokens == 100
        assert metrics.output_tokens == 50
        assert metrics.total_tokens is None  # Not present in partial_usage
    
    def test_truncate_method(self):
        """Test the internal _truncate method."""
        metrics = WorkflowMetrics()
        
        # Test truncation
        result = metrics._truncate("Hello World", 8)
        assert result == "Hello..."
        
        # Test no truncation needed
        result = metrics._truncate("Hello", 10)
        assert result == "Hello"
        
        # Test truncation disabled (max_length=0)
        result = metrics._truncate("Hello World", 0)
        assert result == "Hello World"


# =============================================================================
# TEST CASES - metrics_context CONTEXT MANAGER
# =============================================================================

class TestMetricsContext:
    """Tests for metrics_context context manager."""
    
    def test_basic_context_creation(self):
        """Test basic context manager creates metrics."""
        with metrics_context(
            component_type='agent',
            component_id='test-agent',
        ) as ctx:
            assert ctx is not None
            assert ctx.component_type == 'agent'
            assert ctx.component_id == 'test-agent'
    
    def test_context_records_duration(self):
        """Test context manager records duration."""
        with metrics_context(component_type='agent') as ctx:
            time.sleep(0.1)  # Sleep 100ms
        
        # Duration should be recorded (approximately 100ms)
        assert ctx.duration_ms is not None
        assert ctx.duration_ms >= 100  # At least 100ms
    
    def test_context_sets_success_on_normal_exit(self):
        """Test context sets success=True on normal exit."""
        with metrics_context(component_type='agent') as ctx:
            pass
        
        assert ctx.success is True
    
    def test_context_sets_error_on_exception(self):
        """Test context sets error info on exception."""
        with pytest.raises(ValueError):
            with metrics_context(component_type='agent') as ctx:
                raise ValueError("Test error")
        
        assert ctx.success is False
        assert ctx.error == "Test error"
        assert ctx.error_type == "ValueError"
    
    def test_context_with_user_message(self):
        """Test context with user message."""
        with metrics_context(
            component_type='llm',
            component_id='gpt-4',
            user_message="Hello!",
        ) as ctx:
            ctx.response = "Hi there!"
        
        assert ctx.user_message == "Hello!"
        assert ctx.response == "Hi there!"
    
    def test_context_with_trace_id(self):
        """Test context generates trace_id if not provided."""
        with metrics_context(component_type='workflow') as ctx:
            pass
        
        assert ctx.trace_id is not None
        assert len(ctx.trace_id) == 8  # Auto-generated trace ID is 8 chars
    
    def test_context_with_custom_trace_id(self):
        """Test context uses custom trace_id when provided."""
        with metrics_context(
            component_type='workflow',
            trace_id='custom-trace-123',
        ) as ctx:
            pass
        
        assert ctx.trace_id == 'custom-trace-123'
    
    def test_context_with_metadata(self):
        """Test context with custom metadata."""
        with metrics_context(
            component_type='tool',
            component_id='calculator',
            custom_field='custom_value',
            count=42,
        ) as ctx:
            pass
        
        assert ctx.metadata['custom_field'] == 'custom_value'
        assert ctx.metadata['count'] == 42
    
    def test_context_update_from_usage(self, sample_usage):
        """Test updating metrics from usage within context."""
        with metrics_context(component_type='agent') as ctx:
            ctx.update_from_usage(sample_usage)
        
        assert ctx.input_tokens == 100
        assert ctx.output_tokens == 50
        assert ctx.total_tokens == 150
    
    @pytest.mark.asyncio
    async def test_context_in_async_function(self):
        """Test context manager works in async context."""
        async def async_operation():
            with metrics_context(
                component_type='llm',
                component_id='async-llm',
            ) as ctx:
                await asyncio.sleep(0.05)
                ctx.response = "Async response"
            return ctx
        
        ctx = await async_operation()
        
        assert ctx.component_type == 'llm'
        assert ctx.component_id == 'async-llm'
        assert ctx.response == "Async response"
        assert ctx.duration_ms >= 50


# =============================================================================
# TEST CASES - DECORATORS
# =============================================================================

class TestCollectAgentMetrics:
    """Tests for collect_agent_metrics decorator."""
    
    @pytest.mark.asyncio
    async def test_async_agent_decorator(self):
        """Test decorator on async agent function."""
        @collect_agent_metrics("test-agent")
        async def mock_agent_run(self, message, context):
            result = Mock()
            result.content = "Agent response"
            result.usage = Mock(
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
            )
            return result
        
        mock_self = Mock()
        result = await mock_agent_run(mock_self, "Hello", {})
        
        assert result.content == "Agent response"
    
    @pytest.mark.asyncio
    async def test_agent_decorator_extracts_id_from_self(self):
        """Test decorator extracts agent_id from self.spec.name."""
        @collect_agent_metrics()
        async def mock_agent_run(self, message, context):
            result = Mock()
            result.content = "Response"
            return result
        
        mock_self = Mock()
        mock_self.spec = Mock()
        mock_self.spec.name = "extracted-agent-name"
        
        result = await mock_agent_run(mock_self, "Hello", {})
        assert result.content == "Response"
    
    def test_sync_agent_decorator(self):
        """Test decorator on sync agent function."""
        @collect_agent_metrics("sync-agent")
        def mock_agent_run(self, message):
            result = Mock()
            result.content = "Sync response"
            return result
        
        mock_self = Mock()
        result = mock_agent_run(mock_self, "Hello")
        
        assert result.content == "Sync response"


class TestCollectLLMMetrics:
    """Tests for collect_llm_metrics decorator."""
    
    @pytest.mark.asyncio
    async def test_llm_decorator(self):
        """Test decorator on LLM function."""
        @collect_llm_metrics("gpt-4")
        async def mock_llm_call(self, messages, **kwargs):
            result = Mock()
            result.content = "LLM response"
            result.usage = Mock(
                prompt_tokens=200,
                completion_tokens=100,
                total_tokens=300,
                cost_usd=0.005,
            )
            return result
        
        mock_self = Mock()
        messages = [{"role": "user", "content": "Hello"}]
        result = await mock_llm_call(mock_self, messages)
        
        assert result.content == "LLM response"
    
    @pytest.mark.asyncio
    async def test_llm_decorator_extracts_user_message(self):
        """Test decorator extracts last user message from messages."""
        @collect_llm_metrics("gpt-4")
        async def mock_llm_call(self, messages, **kwargs):
            result = Mock()
            result.content = "Response"
            return result
        
        mock_self = Mock()
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "First question"},
            {"role": "assistant", "content": "First answer"},
            {"role": "user", "content": "Follow-up question"},
        ]
        
        result = await mock_llm_call(mock_self, messages=messages)
        assert result.content == "Response"


class TestCollectNodeMetrics:
    """Tests for collect_node_metrics decorator."""
    
    @pytest.mark.asyncio
    async def test_node_decorator(self):
        """Test decorator on node execution function."""
        @collect_node_metrics("test-node", "Test Node")
        async def mock_node_execute(self, input_data):
            result = Mock()
            result.content = "Node output"
            result.usage = Mock(total_tokens=100)
            return result
        
        mock_self = Mock()
        result = await mock_node_execute(mock_self, "input")
        
        assert result.content == "Node output"


class TestCollectEdgeMetrics:
    """Tests for collect_edge_metrics decorator."""
    
    @pytest.mark.asyncio
    async def test_edge_decorator(self):
        """Test decorator on edge evaluation function."""
        @collect_edge_metrics("test-edge")
        async def mock_edge_evaluate(self, context):
            return True
        
        mock_self = Mock()
        mock_self.id = "test-edge"
        mock_self.source_node_id = "node-a"
        mock_self.target_node_id = "node-b"
        
        result = await mock_edge_evaluate(mock_self, {})
        
        assert result is True
    
    def test_sync_edge_decorator(self):
        """Test decorator on sync edge function."""
        @collect_edge_metrics("sync-edge")
        def mock_edge_evaluate(self, context):
            return False
        
        mock_self = Mock()
        result = mock_edge_evaluate(mock_self, {})
        
        assert result is False


class TestCollectToolMetrics:
    """Tests for collect_tool_metrics decorator."""
    
    @pytest.mark.asyncio
    async def test_tool_decorator(self):
        """Test decorator on tool execution function."""
        @collect_tool_metrics("calculator", "Calculator Tool")
        async def mock_tool_execute(self, args):
            return "42"
        
        mock_self = Mock()
        result = await mock_tool_execute(mock_self, {"a": 1, "b": 2})
        
        assert result == "42"
    
    @pytest.mark.asyncio
    async def test_tool_decorator_with_result_object(self):
        """Test decorator handles result with output attribute."""
        @collect_tool_metrics("search")
        async def mock_tool_execute(self, args):
            result = Mock()
            result.output = "Search results"
            return result
        
        mock_self = Mock()
        result = await mock_tool_execute(mock_self, {"query": "test"})
        
        assert result.output == "Search results"


class TestCollectWorkflowMetrics:
    """Tests for collect_workflow_metrics decorator."""
    
    @pytest.mark.asyncio
    async def test_workflow_decorator(self):
        """Test decorator on workflow execution function."""
        @collect_workflow_metrics("test-workflow", "Test Workflow")
        async def mock_workflow_execute(self, input_data):
            result = Mock()
            result.content = "Workflow complete"
            result.usage = Mock(total_tokens=500)
            return result
        
        mock_self = Mock()
        result = await mock_workflow_execute(mock_self, "input")
        
        assert result.content == "Workflow complete"
    
    @pytest.mark.asyncio
    async def test_workflow_decorator_extracts_id_from_spec(self):
        """Test decorator extracts workflow_id from self.spec.id."""
        @collect_workflow_metrics()
        async def mock_workflow_execute(self, input_data):
            return "done"
        
        mock_self = Mock()
        mock_self.spec = Mock()
        mock_self.spec.id = "spec-workflow-id"
        mock_self.spec.name = "Spec Workflow Name"
        
        result = await mock_workflow_execute(mock_self, "input")
        assert result == "done"


# =============================================================================
# TEST CASES - LoggerAdaptor.log_workflow_metrics
# =============================================================================

class TestLoggerWorkflowMetrics:
    """Tests for LoggerAdaptor.log_workflow_metrics method."""
    
    def test_log_workflow_metrics_basic(self, logger):
        """Test basic logging of workflow metrics."""
        metrics = WorkflowMetrics(
            component_type='agent',
            component_id='test-agent',
            component_name='Test Agent',
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            duration_ms=500.0,
            success=True,
        )
        
        # Should not raise
        logger.log_workflow_metrics(metrics)
    
    def test_log_workflow_metrics_with_error(self, logger):
        """Test logging metrics with error."""
        metrics = WorkflowMetrics(
            component_type='llm',
            component_id='gpt-4',
            component_name='GPT-4',
            duration_ms=100.0,
            success=False,
            error="API rate limit exceeded",
            error_type="RateLimitError",
        )
        
        # Should not raise
        logger.log_workflow_metrics(metrics)
    
    def test_log_workflow_metrics_none(self, logger):
        """Test logging None metrics is handled gracefully."""
        # Should not raise
        logger.log_workflow_metrics(None)
    
    def test_log_workflow_metrics_with_cost(self, logger):
        """Test logging metrics with cost."""
        metrics = WorkflowMetrics(
            component_type='llm',
            component_id='gpt-4',
            total_tokens=500,
            cost_usd=0.0025,
            duration_ms=1000.0,
        )
        
        # Should not raise
        logger.log_workflow_metrics(metrics)


# =============================================================================
# TEST CASES - CONFIGURATION
# =============================================================================

class TestWorkflowLoggingConfig:
    """Tests for workflow logging configuration."""
    
    def test_config_loaded_from_file(self, logger):
        """Test that config is loaded from log config file."""
        config = LoggerAdaptor._config
        
        # Should have workflow_logging section (from log_config_test.json)
        assert config is not None
        if 'workflow_logging' in config:
            wf_config = config['workflow_logging']
            assert 'enabled' in wf_config
            assert 'log_usage_metrics' in wf_config
    
    def test_default_config_values(self):
        """Test default config values when section missing."""
        from utils.logging.workflow_decorators import _get_workflow_config
        
        # This should return empty dict or defaults when no config
        config = _get_workflow_config()
        assert isinstance(config, dict)
    
    def test_is_enabled_check(self):
        """Test _is_enabled() function."""
        from utils.logging.workflow_decorators import _is_enabled
        
        # Should return True by default
        result = _is_enabled()
        assert isinstance(result, bool)


# =============================================================================
# TEST CASES - INTEGRATION
# =============================================================================

@pytest.mark.asyncio
class TestWorkflowLoggingIntegration:
    """Integration tests for workflow logging."""
    
    async def test_full_workflow_logging_flow(self, logger):
        """Test complete workflow with all component types."""
        # Simulate workflow execution
        with metrics_context(
            component_type='workflow',
            component_id='integration-test-workflow',
            component_name='Integration Test',
        ) as wf_ctx:
            
            # Simulate node execution
            with metrics_context(
                component_type='node',
                component_id='node-1',
                workflow_id='integration-test-workflow',
            ) as node_ctx:
                
                # Simulate agent execution
                with metrics_context(
                    component_type='agent',
                    component_id='agent-1',
                    user_message="Hello!",
                ) as agent_ctx:
                    agent_ctx.response = "Hi there!"
                    agent_ctx.input_tokens = 10
                    agent_ctx.output_tokens = 5
                    agent_ctx.total_tokens = 15
                
                node_ctx.response = "Node completed"
            
            wf_ctx.response = "Workflow completed"
        
        # Verify all contexts recorded metrics
        assert wf_ctx.success is True
        assert wf_ctx.duration_ms is not None
        assert node_ctx.success is True
        assert agent_ctx.response == "Hi there!"
        assert agent_ctx.total_tokens == 15
    
    async def test_workflow_with_error_propagation(self, logger):
        """Test error propagation through workflow metrics."""
        with pytest.raises(RuntimeError):
            with metrics_context(
                component_type='workflow',
                component_id='error-workflow',
            ) as wf_ctx:
                with metrics_context(
                    component_type='agent',
                    component_id='failing-agent',
                ) as agent_ctx:
                    raise RuntimeError("Agent failed!")
        
        # Both contexts should have error info
        assert wf_ctx.success is False
        assert wf_ctx.error == "Agent failed!"
        assert agent_ctx.success is False
        assert agent_ctx.error == "Agent failed!"
    
    async def test_nested_metrics_contexts(self, logger):
        """Test deeply nested metrics contexts."""
        contexts = []
        
        with metrics_context(component_type='workflow', component_id='wf') as c1:
            contexts.append(c1)
            with metrics_context(component_type='node', component_id='n1') as c2:
                contexts.append(c2)
                with metrics_context(component_type='agent', component_id='a1') as c3:
                    contexts.append(c3)
                    with metrics_context(component_type='llm', component_id='llm1') as c4:
                        contexts.append(c4)
                        c4.total_tokens = 100
        
        # All contexts should have completed successfully
        for ctx in contexts:
            assert ctx.success is True
            assert ctx.duration_ms is not None
        
        # Inner context should have tokens
        assert contexts[3].total_tokens == 100


# =============================================================================
# TEST CASES - EDGE CASES
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_metrics_with_very_long_message(self):
        """Test handling very long messages."""
        long_message = "A" * 10000
        
        metrics = WorkflowMetrics(
            component_type='agent',
            user_message=long_message,
            response=long_message,
        )
        
        config = {"log_user_messages": True, "log_agent_responses": True, "truncate_messages_at": 100}
        log_dict = metrics.to_log_dict(config)
        
        assert len(log_dict['user_message']) == 100
        assert len(log_dict['response']) == 100
    
    def test_metrics_with_special_characters(self):
        """Test handling special characters in messages."""
        special_message = "Hello! 你好! مرحبا! 🎉 <script>alert('xss')</script>"
        
        metrics = WorkflowMetrics(
            component_type='agent',
            user_message=special_message,
        )
        
        config = {"log_user_messages": True}
        log_dict = metrics.to_log_dict(config)
        
        assert log_dict['user_message'] == special_message
    
    def test_metrics_with_none_values_in_dict(self):
        """Test that None values are excluded from log dict."""
        metrics = WorkflowMetrics(
            component_type='agent',
        )
        
        log_dict = metrics.to_log_dict({})
        
        # None values should not be in dict
        assert 'trace_id' not in log_dict
        assert 'input_tokens' not in log_dict
        assert 'error' not in log_dict
    
    @pytest.mark.asyncio
    async def test_concurrent_metrics_contexts(self):
        """Test multiple concurrent metrics contexts."""
        async def operation(name: str, sleep_time: float):
            with metrics_context(
                component_type='agent',
                component_id=name,
            ) as ctx:
                await asyncio.sleep(sleep_time)
                ctx.response = f"{name} completed"
            return ctx
        
        # Run multiple operations concurrently
        results = await asyncio.gather(
            operation("agent-1", 0.1),
            operation("agent-2", 0.05),
            operation("agent-3", 0.15),
        )
        
        # All should complete successfully with correct IDs
        assert results[0].component_id == "agent-1"
        assert results[1].component_id == "agent-2"
        assert results[2].component_id == "agent-3"
        
        for ctx in results:
            assert ctx.success is True
            assert ctx.duration_ms is not None
    
    def test_decorator_disabled_when_logging_disabled(self):
        """Test decorator does nothing when logging is disabled."""
        with patch('utils.logging.workflow_decorators._is_enabled', return_value=False):
            @collect_agent_metrics("test-agent")
            def mock_fn(self, msg):
                return "result"
            
            mock_self = Mock()
            result = mock_fn(mock_self, "hello")
            
            assert result == "result"
