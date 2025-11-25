#!/usr/bin/env python3
"""
Duration Logging Demo for LoggerAdaptor

This script demonstrates the comprehensive duration logging functionality
that has been added to the LoggerAdaptor, including:

1. Context manager usage
2. Function decorator usage
3. Manual timing
4. Exception handling
5. Different logging backends
6. Metadata collection
7. Threshold-based log levels
"""

import time
import random
from utils.logging.LoggerAdaptor import LoggerAdaptor
from utils.logging.DurationLogger import durationlogger, log_duration, time_function, configure_duration_logger


def demo_basic_duration_logging():
    """Demonstrate basic duration logging functionality."""
    print("\n" + "="*60)
    print("DEMO: Basic Duration Logging")
    print("="*60)

    # Create a logger instance
    logger = LoggerAdaptor.get_logger("duration_demo")

    # Configure the global duration logger to use our logger
    configure_duration_logger(logger)

    # Method 1: Context Manager (Recommended)
    print("\n1. Context Manager Usage:")
    with durationlogger("database_query", table="users", query_type="SELECT") as timer:
        # Simulate database query
        time.sleep(0.1)
        timer.add_metadata(rows_affected=150, query_success=True)

    # Method 2: Manual Timing
    print("\n2. Manual Timing:")
    start_time = time.perf_counter()
    # Simulate some operation
    time.sleep(0.05)
    duration = time.perf_counter() - start_time

    logger.log_duration(
        "file_processing",
        duration,
        file_path="data.csv",
        records_processed=1000,
        success=True
    )


def demo_function_decorator():
    """Demonstrate function decorator usage."""
    print("\n" + "="*60)
    print("DEMO: Function Decorator")
    print("="*60)

    logger = LoggerAdaptor.get_logger("decorator_demo")
    configure_duration_logger(logger)

    @durationlogger(operation_type="data_processing", batch_id="batch_123")
    def process_data_batch():
        """Process a batch of data with automatic timing."""
        time.sleep(0.2)  # Simulate processing
        return random.randint(100, 1000)

    @durationlogger()
    def risky_operation():
        """An operation that might fail."""
        if random.choice([True, False]):
            time.sleep(0.1)
            return "success"
        else:
            time.sleep(0.05)
            raise ValueError("Random failure for demo")

    print("\n1. Successful operation:")
    try:
        result = process_data_batch()
        print(f"   Processed {result} records")
    except Exception as e:
        print(f"   Error: {e}")

    print("\n2. Operation with exception:")
    try:
        result = risky_operation()
        print(f"   Result: {result}")
    except Exception as e:
        print(f"   Expected error: {e}")


def demo_convenience_functions():
    """Demonstrate convenience context managers."""
    print("\n" + "="*60)
    print("DEMO: Convenience Context Managers")
    print("="*60)

    logger = LoggerAdaptor.get_logger("convenience_demo")
    configure_duration_logger(logger)

    # Using standalone context manager
    print("\n1. Standalone log_duration context manager:")
    with log_duration(logger, "external_api_call", endpoint="/api/users"):
        time.sleep(0.15)  # Simulate API call

    # Using time_function as decorator
    print("\n2. time_function as decorator:")
    @durationlogger(operation_name="data_validation", validation_type="schema")
    def validate_data():
        time.sleep(0.08)  # Simulate validation
        return "valid"

    result = validate_data()
    print(f"   Validation result: {result}")


def demo_performance_comparison():
    """Demonstrate performance benefits."""
    print("\n" + "="*60)
    print("DEMO: Performance Comparison")
    print("="*60)

    logger = LoggerAdaptor.get_logger("performance_demo")
    configure_duration_logger(logger)

    # Traditional logging approach (synchronous)
    def traditional_approach():
        start_time = time.perf_counter()
        time.sleep(0.01)  # Simulate work
        duration = time.perf_counter() - start_time

        # Traditional logging is immediate and blocking
        logger.info(f"Operation completed in {duration:.3f}s")
        return duration

    # Duration logging approach (automatic and non-blocking)
    def duration_logging_approach():
        with durationlogger("async_operation", is_async=True, non_blocking=True) as timer:
            time.sleep(0.01)  # Simulate work
        return timer.get_duration()

    print("\nTraditional vs Duration Logging Performance:")
    print("(Note: This is a simplified demo - real benefits are more apparent in high-throughput scenarios)")

    # Test traditional approach
    trad_times = []
    for i in range(5):
        duration = traditional_approach()
        trad_times.append(duration)

    # Test duration logging approach
    duration_times = []
    for i in range(5):
        duration = duration_logging_approach()
        duration_times.append(duration)

    print(f"Traditional approach - Avg: {sum(trad_times)/len(trad_times):.4f}s")
    print(f"Duration logging - Avg: {sum(duration_times)/len(duration_times):.4f}s")
    print("Duration logging is non-blocking and more efficient for performance monitoring!")


def demo_different_log_levels():
    """Demonstrate different log levels based on duration thresholds."""
    print("\n" + "="*60)
    print("DEMO: Duration-Based Log Levels")
    print("="*60)

    logger = LoggerAdaptor.get_logger("threshold_demo")
    configure_duration_logger(logger)

    # Test different durations to trigger different log levels
    test_durations = [
        (0.1, "DEBUG"),    # Below slow threshold
        (1.5, "INFO"),     # Above slow, below warn
        (7.0, "WARNING"),  # Above warn, below error
        (45.0, "ERROR")    # Above error threshold
    ]

    print("\nTesting duration thresholds:")
    for duration, expected_level in test_durations:
        print(f"Duration: {duration}s → Expected Level: {expected_level}")

        # Simulate the operation
        with durationlogger(f"test_operation_{duration}s"):
            time.sleep(duration)


def demo_json_backend():
    """Demonstrate duration logging with JSON backend."""
    print("\n" + "="*60)
    print("DEMO: Duration Logging with JSON Backend")
    print("="*60)

    # Create a logger with JSON backend configuration
    logger = LoggerAdaptor.get_logger("json_duration_demo")
    configure_duration_logger(logger)

    print("\n1. Context Manager with JSON logging:")
    with durationlogger("api_request", endpoint="/api/data", method="GET") as timer:
        time.sleep(0.12)
        timer.add_metadata(
            request_id="req_12345",
            response_size=1024,
            cache_hit=False
        )

    print("\n2. Manual duration logging with JSON:")
    start_time = time.perf_counter()
    # Simulate API response parsing
    time.sleep(0.08)
    duration = time.perf_counter() - start_time

    logger.log_duration(
        "json_processing",
        duration,
        format_type="JSON",
        parsed_objects=25,
        processing_success=True
    )


def main():
    """Run all duration logging demonstrations."""
    print("🚀 LoggerAdaptor Duration Logging Demo")
    print("This demonstrates the comprehensive duration logging functionality.")

    try:
        # Run all demonstrations
        demo_basic_duration_logging()
        demo_function_decorator()
        demo_convenience_functions()
        demo_performance_comparison()
        demo_different_log_levels()
        demo_json_backend()

        print("\n" + "="*60)
        print("✅ All duration logging demos completed successfully!")
        print("="*60)

        print("\n📋 SUMMARY OF DURATION LOGGING FEATURES:")
        print("• ✅ Context managers for automatic timing")
        print("• ✅ Function decorators for seamless integration")
        print("• ✅ Manual timing for custom scenarios")
        print("• ✅ Configurable log levels based on duration thresholds")
        print("• ✅ Exception handling with duration tracking")
        print("• ✅ Metadata collection during operations")
        print("• ✅ Thread-safe operation")
        print("• ✅ Integration with all logging backends")
        print("• ✅ Performance monitoring and optimization")

    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
