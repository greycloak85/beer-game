"""Customer-demand functions consumed by the Retailer in step 2 (fill_orders).

A demand function has signature ``(week: int, total_weeks: int) -> int`` and is
required to be deterministic and pure — no global RNG state. ``week`` is the
1-indexed week being filled (``state.week + 1`` from the engine's perspective).
"""
from beergame.config.scenarios import (
    CLASSIC_POST_STEP_DEMAND,
    CLASSIC_PRE_STEP_DEMAND,
    CLASSIC_STEP_BREAK_WEEK,
    TOTAL_WEEKS,
)


def demand_for_week(week: int, total_weeks: int = TOTAL_WEEKS) -> int:
    """Classic step demand: 4 cases/wk weeks 1-4, 8 cases/wk weeks 5-36."""
    if week < 1 or week > total_weeks:
        raise ValueError(f"week {week} out of range [1, {total_weeks}]")
    return (
        CLASSIC_PRE_STEP_DEMAND
        if week <= CLASSIC_STEP_BREAK_WEEK
        else CLASSIC_POST_STEP_DEMAND
    )


def constant_demand(week: int, total_weeks: int = TOTAL_WEEKS, value: int = 4) -> int:
    """Used by GATE 1 equilibrium test — demand stays constant the whole game."""
    if week < 1 or week > total_weeks:
        raise ValueError(f"week {week} out of range [1, {total_weeks}]")
    return value
