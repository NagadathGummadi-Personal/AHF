"""
Generic usage calculators for attempts, retries, and state flags. Includes
normal env-aware functions and dev defaults.
"""

from ...config import is_dev
from ...constants import (
    EXC_CALCULATION_NOT_IMPLEMENTED,
    ATTEMPTS,
    RETRIES,
    CACHED_HIT,
    IDEMPOTENCY_REUSED,
    CIRCUIT_OPENED,
)


def calculate_attempts_dev() -> int:
    return 1


def calculate_retries_dev() -> int:
    return 0


def check_cached_hit_dev() -> bool:
    return False


def check_idempotency_reused_dev() -> bool:
    return False


def check_circuit_opened_dev() -> bool:
    return False


def calculate_attempts() -> int:
    if is_dev():
        return calculate_attempts_dev()
    raise NotImplementedError(EXC_CALCULATION_NOT_IMPLEMENTED.format(name=ATTEMPTS))


def calculate_retries() -> int:
    if is_dev():
        return calculate_retries_dev()
    raise NotImplementedError(EXC_CALCULATION_NOT_IMPLEMENTED.format(name=RETRIES))


def check_cached_hit() -> bool:
    if is_dev():
        return check_cached_hit_dev()
    raise NotImplementedError(EXC_CALCULATION_NOT_IMPLEMENTED.format(name=CACHED_HIT))


def check_idempotency_reused() -> bool:
    if is_dev():
        return check_idempotency_reused_dev()
    raise NotImplementedError(EXC_CALCULATION_NOT_IMPLEMENTED.format(name=IDEMPOTENCY_REUSED))


def check_circuit_opened() -> bool:
    if is_dev():
        return check_circuit_opened_dev()
    raise NotImplementedError(EXC_CALCULATION_NOT_IMPLEMENTED.format(name=CIRCUIT_OPENED))

