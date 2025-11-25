"""
Token usage calculators. Includes normal env-aware functions and dev defaults.
"""

from ...config import is_dev
from ...constants import EXC_CALCULATION_NOT_IMPLEMENTED, TOKENS_IN, TOKENS_OUT


def calculate_tokens_in_dev() -> int:
    return 0


def calculate_tokens_out_dev() -> int:
    return 0


def calculate_tokens_in() -> int:
    if is_dev():
        return calculate_tokens_in_dev()
    raise NotImplementedError(EXC_CALCULATION_NOT_IMPLEMENTED.format(name=TOKENS_IN))


def calculate_tokens_out() -> int:
    if is_dev():
        return calculate_tokens_out_dev()
    raise NotImplementedError(EXC_CALCULATION_NOT_IMPLEMENTED.format(name=TOKENS_OUT))

