"""
Retry Policies for Tools Specification System.

This module provides pluggable retry strategies for handling transient failures
with configurable retry logic, backoff strategies, and exception handling.

Strategy Pattern Implementation:
=================================
All policies implement IRetryPolicy, allowing runtime selection of the
appropriate retry strategy for each tool.

Available Strategies:
=====================
- NoRetryPolicy: Fail immediately on first error
- FixedRetryPolicy: Retry with fixed delay between attempts
- ExponentialBackoffRetryPolicy: Retry with exponentially increasing delays
- CustomRetryPolicy: User-defined retry logic

Usage:
    from core.tools.executors.policies import ExponentialBackoffRetryPolicy
    
    # Configure at tool spec creation
    spec.retry_policy = ExponentialBackoffRetryPolicy(
        max_attempts=3,
        base_delay=1.0,
        max_delay=10.0
    )
    
    # Or use factory
    from core.tools.executors.policies import RetryPolicyFactory
    policy = RetryPolicyFactory.get_policy('exponential')
    spec.retry_policy = policy

Extending:
==========
Create custom policy by implementing IRetryPolicy:

    class CircuitBreakerRetry(IRetryPolicy):
        async def execute_with_retry(self, func, *args, **kwargs):
            # Your retry logic
            pass

Note:
    Retry policies should handle only retryable errors. Validation errors,
    authentication failures, etc. should fail immediately.
"""
from .retry_policy import IRetryPolicy
from .no_retry_policy import NoRetryPolicy
from .fixed_retry_policy import FixedRetryPolicy
from .exponential_backoff_retry_policy import ExponentialBackoffRetryPolicy
from .custom_retry_policy import CustomRetryPolicy
from .retry_policy_factory import RetryPolicyFactory

__all__ = [
    "IRetryPolicy",
    "NoRetryPolicy",
    "FixedRetryPolicy",
    "ExponentialBackoffRetryPolicy",
    "CustomRetryPolicy",
    "RetryPolicyFactory",
]