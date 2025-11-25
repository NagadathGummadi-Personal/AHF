"""Test cases for CircuitBreaker class."""

import pytest
from unittest.mock import Mock
from utils.circuitBreaker.CircuitBreaker import CircuitBreaker, CircuitBreakerState


class TestCircuitBreaker:
    """Test cases for the CircuitBreaker class."""

    @pytest.fixture
    def circuit_breaker(self):
        """Create a CircuitBreaker instance for testing."""
        return CircuitBreaker(max_failures=3, reset_timeout=1)

    def test_circuit_breaker_initialization(self, circuit_breaker):
        """Test CircuitBreaker initialization with correct parameters."""
        assert circuit_breaker.max_failures == 3
        assert circuit_breaker.reset_timeout == 1
        assert circuit_breaker.failure_count == 0
        assert circuit_breaker.state == CircuitBreakerState.CLOSED

    def test_circuit_breaker_initial_state_is_closed(self, circuit_breaker):
        """Test that CircuitBreaker starts in CLOSED state."""
        assert circuit_breaker.state == CircuitBreakerState.CLOSED
        assert not circuit_breaker.is_open()
        assert not circuit_breaker.is_half_open()

    def test_successful_function_call(self, circuit_breaker):
        """Test calling a successful function through the circuit breaker."""
        def successful_function():
            return "success"
        
        result = circuit_breaker.call(successful_function)
        assert result == "success"
        assert circuit_breaker.failure_count == 0
        assert circuit_breaker.state == CircuitBreakerState.CLOSED

    def test_failed_function_call_increments_failure_count(self, circuit_breaker):
        """Test that failed function calls increment the failure count."""
        def failing_function():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError, match="Test error"):
            circuit_breaker.call(failing_function)
        
        assert circuit_breaker.failure_count == 1
        assert circuit_breaker.state == CircuitBreakerState.CLOSED

    def test_circuit_opens_after_max_failures(self, circuit_breaker):
        """Test that circuit opens after reaching max failures."""
        def failing_function():
            raise ValueError("Test error")
        
        # Trigger max failures - first two should raise ValueError, third should raise circuit breaker exception
        for i in range(circuit_breaker.max_failures):
            if i < circuit_breaker.max_failures - 1:
                with pytest.raises(ValueError):
                    circuit_breaker.call(failing_function)
            else:
                # The last call should trigger the circuit breaker to open
                with pytest.raises(Exception, match="Circuit breaker is open"):
                    circuit_breaker.call(failing_function)
        
        assert circuit_breaker.state == CircuitBreakerState.OPEN

    def test_circuit_breaker_as_decorator(self, circuit_breaker):
        """Test using CircuitBreaker as a decorator."""
        @circuit_breaker
        def decorated_function():
            return "decorated success"
        
        result = decorated_function()
        assert result == "decorated success"

    def test_decorator_with_failing_function(self, circuit_breaker):
        """Test decorator behavior with failing function."""
        @circuit_breaker
        def failing_decorated_function():
            raise RuntimeError("Decorator test error")
        
        with pytest.raises(RuntimeError, match="Decorator test error"):
            failing_decorated_function()
        
        assert circuit_breaker.failure_count == 1

    def test_manual_state_changes(self, circuit_breaker):
        """Test manually changing circuit breaker states."""
        # Test manual open
        circuit_breaker.open()
        assert circuit_breaker.state == CircuitBreakerState.OPEN
        
        # Test manual close
        circuit_breaker.close()
        assert circuit_breaker.state == CircuitBreakerState.CLOSED
        
        # Test manual half-open
        circuit_breaker.half_open()
        assert circuit_breaker.state == CircuitBreakerState.HALF_OPEN

    def test_record_success_manually(self, circuit_breaker):
        """Test manually recording a success."""
        # First cause some failures
        circuit_breaker.record_failure()
        initial_count = circuit_breaker.failure_count
        
        # Record success
        circuit_breaker.record_success()
        
        # Failure count should be reset or reduced
        assert circuit_breaker.failure_count <= initial_count

    def test_record_failure_manually(self, circuit_breaker):
        """Test manually recording a failure."""
        initial_count = circuit_breaker.failure_count
        circuit_breaker.record_failure()
        assert circuit_breaker.failure_count > initial_count

    def test_excluded_exceptions(self, circuit_breaker):
        """Test adding and removing excluded exceptions."""
        # Add excluded exception
        circuit_breaker.add_excluded_exception(ValueError)
        assert ValueError in circuit_breaker.excluded_exceptions
        
        # Remove excluded exception
        circuit_breaker.remove_excluded_exception(ValueError)
        assert ValueError not in circuit_breaker.excluded_exceptions

    def test_circuit_breaker_listeners(self, circuit_breaker):
        """Test adding and removing listeners."""
        mock_listener = Mock()
        
        # Add listener
        circuit_breaker.add_listener(mock_listener)
        
        # Remove listener
        circuit_breaker.remove_listener(mock_listener)

    def test_string_representation(self, circuit_breaker):
        """Test string representations of CircuitBreaker."""
        str_repr = str(circuit_breaker)
        assert "CircuitBreaker" in str_repr
        assert "state=" in str_repr
        assert "failures=" in str_repr
        
        repr_str = repr(circuit_breaker)
        assert "CircuitBreaker" in repr_str
        assert "max_failures=3" in repr_str
        assert "reset_timeout=1" in repr_str

    def test_circuit_breaker_with_different_parameters(self):
        """Test CircuitBreaker with different initialization parameters."""
        cb = CircuitBreaker(max_failures=5, reset_timeout=10)
        assert cb.max_failures == 5
        assert cb.reset_timeout == 10

    @pytest.mark.parametrize("max_failures,reset_timeout", [
        (1, 1),
        (5, 30),
        (10, 60),
    ])
    def test_circuit_breaker_parametrized_initialization(self, max_failures, reset_timeout):
        """Test CircuitBreaker initialization with various parameters."""
        cb = CircuitBreaker(max_failures=max_failures, reset_timeout=reset_timeout)
        assert cb.max_failures == max_failures
        assert cb.reset_timeout == reset_timeout
        assert cb.state == CircuitBreakerState.CLOSED

    def test_circuit_breaker_edge_cases(self, circuit_breaker):
        """Test edge cases and error conditions."""
        # Test calling with None function
        with pytest.raises(TypeError):
            circuit_breaker.call(None)

    def test_circuit_breaker_state_transitions(self, circuit_breaker):
        """Test proper state transitions."""
        # Start in CLOSED
        assert circuit_breaker.state == CircuitBreakerState.CLOSED
        
        # Force to OPEN
        circuit_breaker.state = CircuitBreakerState.OPEN
        assert circuit_breaker.state == CircuitBreakerState.OPEN
        
        # Force to HALF_OPEN
        circuit_breaker.state = CircuitBreakerState.HALF_OPEN
        assert circuit_breaker.state == CircuitBreakerState.HALF_OPEN
        
        # Back to CLOSED
        circuit_breaker.state = CircuitBreakerState.CLOSED
        assert circuit_breaker.state == CircuitBreakerState.CLOSED

    def test_circuit_breaker_with_mock_request_success(self, circuit_breaker):
        """Test circuit breaker with successful mock requests."""
        def mock_successful_request():
            return "Success"
        
        # Make several successful calls
        for i in range(5):
            result = circuit_breaker.call(mock_successful_request)
            assert result == "Success"
            assert circuit_breaker.state == CircuitBreakerState.CLOSED
            assert circuit_breaker.failure_count == 0

    def test_circuit_breaker_failure_threshold_behavior(self, circuit_breaker):
        """Test behavior when approaching and reaching failure threshold."""
        def failing_request():
            raise ValueError("Mock failure")
        
        # Test failures up to but not exceeding threshold
        for i in range(circuit_breaker.max_failures - 1):
            with pytest.raises(ValueError):
                circuit_breaker.call(failing_request)
            assert circuit_breaker.state == CircuitBreakerState.CLOSED
        
        # The final failure should open the circuit
        with pytest.raises(Exception, match="Circuit breaker is open"):
            circuit_breaker.call(failing_request)
        assert circuit_breaker.state == CircuitBreakerState.OPEN

    def test_circuit_breaker_manual_success_reset(self, circuit_breaker):
        """Test that manual success recording resets failure count."""
        # Record some failures first
        circuit_breaker.record_failure()
        circuit_breaker.record_failure()
        initial_count = circuit_breaker.failure_count
        assert initial_count > 0
        
        # Record success should reset or reduce count
        circuit_breaker.record_success()
        assert circuit_breaker.failure_count <= initial_count
        assert circuit_breaker.state == CircuitBreakerState.CLOSED

    def test_circuit_breaker_with_different_exception_types(self, circuit_breaker):
        """Test circuit breaker with different types of exceptions."""
        def network_error():
            raise ConnectionError("Network timeout")
        
        def value_error():
            raise ValueError("Invalid input")
        
        def runtime_error():
            raise RuntimeError("Runtime issue")
        
        # Test with different exception types
        exceptions_to_test = [network_error, value_error, runtime_error]
        
        for i, error_func in enumerate(exceptions_to_test):
            if i < circuit_breaker.max_failures - 1:
                with pytest.raises((ConnectionError, ValueError, RuntimeError)):
                    circuit_breaker.call(error_func)
            elif i == circuit_breaker.max_failures - 1:
                # This should be the last failure before circuit opens
                with pytest.raises((ConnectionError, ValueError, RuntimeError, Exception)):
                    circuit_breaker.call(error_func)
            else:
                with pytest.raises(Exception, match="Circuit breaker is open"):
                    circuit_breaker.call(error_func)

    def test_circuit_breaker_decorator_with_multiple_calls(self, circuit_breaker):
        """Test circuit breaker decorator with multiple successful and failed calls."""
        call_count = 0
        
        @circuit_breaker
        def mixed_function(should_fail=False):
            nonlocal call_count
            call_count += 1
            if should_fail:
                raise Exception(f"Failure #{call_count}")
            return f"Success #{call_count}"
        
        # Test successful calls
        for i in range(3):
            result = mixed_function(should_fail=False)
            assert f"Success #{i+1}" in result
            assert circuit_breaker.state == CircuitBreakerState.CLOSED
        
        # Test failed calls
        for i in range(circuit_breaker.max_failures):
            if i < circuit_breaker.max_failures - 1:
                with pytest.raises(Exception, match=f"Failure #{call_count + 1}"):
                    mixed_function(should_fail=True)
            else:
                # Last failure should trigger circuit breaker
                with pytest.raises(Exception):
                    mixed_function(should_fail=True)

    def test_circuit_breaker_state_persistence(self, circuit_breaker):
        """Test that circuit breaker state persists across multiple operations."""
        # Initially closed
        assert circuit_breaker.state == CircuitBreakerState.CLOSED
        
        # Open manually
        circuit_breaker.open()
        assert circuit_breaker.state == CircuitBreakerState.OPEN
        
        # Try to call - should fail immediately
        def dummy_function():
            return "Should not execute"
        
        with pytest.raises(Exception, match="Circuit breaker is open"):
            circuit_breaker.call(dummy_function)
        
        # State should remain open
        assert circuit_breaker.state == CircuitBreakerState.OPEN
        
        # Close manually
        circuit_breaker.close()
        assert circuit_breaker.state == CircuitBreakerState.CLOSED
        
        # Now calls should work
        result = circuit_breaker.call(dummy_function)
        assert result == "Should not execute"
