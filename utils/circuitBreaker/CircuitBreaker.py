import pybreaker
from enum import Enum
import time

class CircuitBreakerState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half-open"

class CircuitBreaker:
    """
    Circuit Breaker implementation using pybreaker library.
    
    This class provides a wrapper around the pybreaker library while maintaining
    our existing interface for backward compatibility.
    """
    
    def __init__(self, max_failures=5, reset_timeout=30):
        """
        Initialize the Circuit Breaker.
        
        Args:
            max_failures (int): Maximum number of failures before opening the circuit
            reset_timeout (int): Time in seconds before attempting to close the circuit
        """
        self.max_failures = max_failures
        self.reset_timeout = reset_timeout
        
        # Create the underlying pybreaker instance
        self._pybreaker = pybreaker.CircuitBreaker(
            fail_max=max_failures,
            reset_timeout=reset_timeout
        )
        
        # Initialize counters and state tracking
        self.failure_count = 0
        self.last_failure_time = 0
        
        # Add a listener to track our state
        self._pybreaker.add_listener(self._StateListener(self))
    
    class _StateListener(pybreaker.CircuitBreakerListener):
        """Internal listener to track state changes and update our counters."""
        
        def __init__(self, circuit_breaker):
            self.circuit_breaker = circuit_breaker
        
        def failure(self, cb, exc):
            """Called when a function invocation raises a system error."""
            self.circuit_breaker.failure_count = cb.fail_counter
            self.circuit_breaker.last_failure_time = time.time()
        
        def success(self, cb):
            """Called when a function invocation succeeds."""
            self.circuit_breaker.failure_count = cb.fail_counter
        
        def state_change(self, cb, old_state, new_state):
            """Called when the circuit breaker state changes."""
            # Update our internal state tracking if needed
            pass
    
    @property
    def state(self):
        """Get the current state as our State enum."""
        pybreaker_state = self._pybreaker.current_state
        if pybreaker_state == "closed":
            return CircuitBreakerState.CLOSED
        elif pybreaker_state == "open":
            return CircuitBreakerState.OPEN
        elif pybreaker_state == "half-open":
            return CircuitBreakerState.HALF_OPEN
        else:
            return CircuitBreakerState.CLOSED  # Default fallback
    
    @state.setter
    def state(self, new_state):
        """Set the state manually."""
        if new_state == CircuitBreakerState.CLOSED:
            self._pybreaker.close()
        elif new_state == CircuitBreakerState.OPEN:
            self._pybreaker.open()
        elif new_state == CircuitBreakerState.HALF_OPEN:
            self._pybreaker.half_open()
    
    def is_open(self):
        """Check if the circuit breaker is open."""
        return self._pybreaker.current_state == CircuitBreakerState.OPEN
    
    def is_closed(self):
        """Check if the circuit breaker is closed."""
        return self._pybreaker.current_state == CircuitBreakerState.CLOSED
    
    def is_half_open(self):
        """Check if the circuit breaker is half-open."""
        return self._pybreaker.current_state == CircuitBreakerState.HALF_OPEN
    
    def record_failure(self):
        """
        Record a failure manually.
        
        Note: When using pybreaker, failures are typically recorded automatically
        when exceptions are raised during protected function calls.
        """
        self.failure_count = self._pybreaker.fail_counter + 1
        self.last_failure_time = time.time()
        
        # Manually increment the pybreaker counter by calling a failing function
        try:
            @self._pybreaker
            def _manual_failure():
                raise Exception("Manual failure recording")
            _manual_failure()
        except Exception:
            pass  # Expected to fail
    
    def record_success(self):
        """
        Record a success manually.
        
        Note: When using pybreaker, successes are typically recorded automatically
        when protected function calls complete without exceptions.
        """
        # Manually record success by calling a successful function
        @self._pybreaker
        def _manual_success():
            return "success"
        
        try:
            _manual_success()
            self.failure_count = self._pybreaker.fail_counter
        except Exception:
            pass
    
    def call(self, func, *args, **kwargs):
        """
        Call a function through the circuit breaker.
        
        Args:
            func: The function to call
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            The result of the function call
            
        Raises:
            Exception: If the function fails or circuit breaker is open
        """
        try:
            result = self._pybreaker.call(func, *args, **kwargs)
            self.failure_count = self._pybreaker.fail_counter
            return result
        except pybreaker.CircuitBreakerError as e:
            # Convert pybreaker errors to maintain interface compatibility
            raise Exception(f"Circuit breaker is open: {str(e)}")
        except Exception:
            self.failure_count = self._pybreaker.fail_counter
            self.last_failure_time = time.time()
            raise
    
    def __call__(self, func):
        """
        Use circuit breaker as a decorator.
        
        Args:
            func: The function to decorate
            
        Returns:
            Decorated function that's protected by the circuit breaker
        """
        @self._pybreaker
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        # Update our counters after each call
        def protected_wrapper(*args, **kwargs):
            try:
                result = wrapper(*args, **kwargs)
                self.failure_count = self._pybreaker.fail_counter
                return result
            except pybreaker.CircuitBreakerError as e:
                raise Exception(f"Circuit breaker is open: {str(e)}")
            except Exception:
                self.failure_count = self._pybreaker.fail_counter
                self.last_failure_time = time.time()
                raise
        
        return protected_wrapper
    
    def add_listener(self, listener):
        """
        Add a listener to the circuit breaker.
        
        Args:
            listener: A pybreaker.CircuitBreakerListener instance
        """
        self._pybreaker.add_listener(listener)
    
    def remove_listener(self, listener):
        """
        Remove a listener from the circuit breaker.
        
        Args:
            listener: The listener to remove
        """
        self._pybreaker.remove_listener(listener)
    
    def open(self):
        """Manually open the circuit breaker."""
        self._pybreaker.open()
    
    def close(self):
        """Manually close the circuit breaker."""
        self._pybreaker.close()
    
    def half_open(self):
        """Manually set the circuit breaker to half-open state."""
        self._pybreaker.half_open()
    
    @property
    def excluded_exceptions(self):
        """Get the list of excluded exceptions."""
        return self._pybreaker.excluded_exceptions
    
    def add_excluded_exception(self, exception_type):
        """
        Add an exception type to be excluded from failure counting.
        
        Args:
            exception_type: Exception class to exclude
        """
        self._pybreaker.add_excluded_exception(exception_type)
    
    def remove_excluded_exception(self, exception_type):
        """
        Remove an exception type from the excluded list.
        
        Args:
            exception_type: Exception class to remove from exclusions
        """
        self._pybreaker.remove_excluded_exception(exception_type)
    
    def __str__(self):
        """String representation of the circuit breaker."""
        return f"CircuitBreaker(state={self.state}, failures={self.failure_count}/{self.max_failures})"
    
    def __repr__(self):
        """Detailed string representation of the circuit breaker."""
        return (f"CircuitBreaker(max_failures={self.max_failures}, "
                f"reset_timeout={self.reset_timeout}, "
                f"state={self.state}, "
                f"failure_count={self.failure_count})")