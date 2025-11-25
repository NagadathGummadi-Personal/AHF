from typing import List, Optional

from pydantic import BaseModel, Field
from ..defaults import (
    RETRY_DEFAULT_MAX_ATTEMPTS,
    RETRY_DEFAULT_BASE_DELAY_S,
    RETRY_DEFAULT_MAX_DELAY_S,
    RETRY_DEFAULT_JITTER_S,
    CB_DEFAULT_ENABLED,
    CB_DEFAULT_FAILURE_THRESHOLD,
    CB_DEFAULT_RECOVERY_TIMEOUT_S,
    CB_DEFAULT_HALF_OPEN_MAX_CALLS,
    CB_DEFAULT_ERROR_CODES_TO_TRIP,
    IDEMPOTENCY_DEFAULT_ENABLED,
    IDEMPOTENCY_DEFAULT_TTL_S,
    IDEMPOTENCY_DEFAULT_PERSIST_RESULT,
    IDEMPOTENCY_DEFAULT_BYPASS_ON_MISSING_KEY,
)

class RetryConfig(BaseModel):
    """Configuration for retry behavior"""
    max_attempts: int = RETRY_DEFAULT_MAX_ATTEMPTS
    base_delay_s: float = RETRY_DEFAULT_BASE_DELAY_S
    max_delay_s: float = RETRY_DEFAULT_MAX_DELAY_S
    jitter_s: float = RETRY_DEFAULT_JITTER_S


class CircuitBreakerConfig(BaseModel):
    """Configuration for circuit breaker pattern"""
    enabled: bool = CB_DEFAULT_ENABLED
    failure_threshold: int = CB_DEFAULT_FAILURE_THRESHOLD  # consecutive failures to open
    recovery_timeout_s: int = CB_DEFAULT_RECOVERY_TIMEOUT_S  # OPEN -> HALF_OPEN after timeout
    half_open_max_calls: int = CB_DEFAULT_HALF_OPEN_MAX_CALLS  # allowed test calls in HALF_OPEN
    error_codes_to_trip: List[str] = Field(default_factory=lambda: CB_DEFAULT_ERROR_CODES_TO_TRIP)


class IdempotencyConfig(BaseModel):
    """Configuration for idempotency behavior"""
    enabled: bool = IDEMPOTENCY_DEFAULT_ENABLED
    key_fields: Optional[List[str]] = None  # if None, use all args
    ttl_s: Optional[int] = IDEMPOTENCY_DEFAULT_TTL_S
    persist_result: bool = IDEMPOTENCY_DEFAULT_PERSIST_RESULT  # store result for reuse
    bypass_on_missing_key: bool = IDEMPOTENCY_DEFAULT_BYPASS_ON_MISSING_KEY  # if key_fields missing, bypass idempotency
