"""
Cost calculators. Includes normal env-aware function and dev default.
"""

from ...config import is_dev
from ...constants import EXC_CALCULATION_NOT_IMPLEMENTED, COST_USD


def calculate_cost_usd_dev() -> float:
    return 0.0


def calculate_cost_usd() -> float:
    if is_dev():
        return calculate_cost_usd_dev()
    raise NotImplementedError(EXC_CALCULATION_NOT_IMPLEMENTED.format(name=COST_USD))

