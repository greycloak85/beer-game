"""Unit tests for the Phase 3 debrief metrics in ``beergame/engine/metrics.py``.

Covers DEB-03 (variance-based bullwhip ratio + per-echelon amplification) and
DEB-04 (per-station cost decomposition reconciled against the engine's own
cost ledger).
"""
from dataclasses import replace

import pytest

from beergame.config.costs import BACKORDER_COST, HOLDING_COST
from beergame.engine.metrics import (
    CostRow,
    cost_breakdown,
    per_echelon_amplification,
    variance_bullwhip_ratio,
)
from beergame.engine.state import Role


# -------------------------------------------------------------------- variance


def test_variance_bullwhip_ratio_empty_history_returns_zero(initial_game):
    """A brand-new game has empty histories; pvariance would raise — guard returns 0.0."""
    assert variance_bullwhip_ratio(initial_game) == 0.0


def test_variance_bullwhip_ratio_canonical_is_greater_than_one(canonical_done_state):
    """DEB-03 headline: at seed=42 the canonical bullwhip MUST amplify
    (variance ratio > 1.0). If this fails, either the Sterman parameters
    regressed to "optimal" (alpha=beta=1) or the engine's tick order is wrong."""
    ratio = variance_bullwhip_ratio(canonical_done_state)
    assert ratio > 1.0, (
        f"Expected variance bullwhip ratio > 1.0 at seed=42 — got {ratio:.3f}. "
        "This is the lesson: there IS amplification. If the ratio collapses to "
        "<= 1.0, suspect Sterman parameter regression or tick-order break."
    )


def test_variance_bullwhip_ratio_zero_denominator_returns_zero(initial_game):
    """Flat customer demand (no variance) must not crash — defensive guard
    returns 0.0 even though canonical scenario never hits this case."""
    flat = replace(initial_game, customer_demand_history=(4, 4, 4))
    assert variance_bullwhip_ratio(flat) == 0.0


# ------------------------------------------------------- per-echelon ratios


def test_per_echelon_amplification_has_all_four_roles(canonical_done_state):
    """Output dict MUST be keyed by every Role member (length 4) — callers
    iterate Role and look up; a missing key would KeyError in the view."""
    ratios = per_echelon_amplification(canonical_done_state)
    assert set(ratios) == set(Role)


def test_per_echelon_amplification_factory_exceeds_retailer(canonical_done_state):
    """Canonical bullwhip signature: amplification grows monotonically upstream,
    so Factory's variance ratio MUST exceed Retailer's at seed=42. (Retailer's
    ratio is roughly 1.0 since the player plays a constant 4; Factory's ratio
    is dominated by the Sterman overshoot.)"""
    ratios = per_echelon_amplification(canonical_done_state)
    assert ratios[Role.FACTORY] > ratios[Role.RETAILER], (
        f"Bullwhip inverted: Factory ratio = {ratios[Role.FACTORY]:.2f}, "
        f"Retailer ratio = {ratios[Role.RETAILER]:.2f}. Expected F > R."
    )


# ------------------------------------------------------------- cost breakdown


def test_cost_breakdown_returns_four_rows_in_role_order(canonical_done_state):
    """Tuple order is Role iteration order (R, W, D, F) — the view renders
    rows in this order; a permutation would mislabel the table."""
    rows = cost_breakdown(canonical_done_state)
    assert tuple(r.role for r in rows) == tuple(Role)
    assert all(isinstance(r, CostRow) for r in rows)


def test_cost_breakdown_total_equals_holding_plus_backorder(canonical_done_state):
    """Per-row arithmetic invariant — guards against off-by-one decomposition bugs."""
    rows = cost_breakdown(canonical_done_state)
    for r in rows:
        assert r.total == pytest.approx(r.holding + r.backorder, abs=0.01), (
            f"{r.role.name}: total={r.total}, holding+backorder={r.holding + r.backorder}"
        )


def test_cost_breakdown_reconciles_with_engine_cost_history(canonical_done_state):
    """LOAD-BEARING invariant (Pitfall 3 in 03-RESEARCH.md): the debrief table's
    per-station Total MUST equal the engine's cumulative cost ledger
    (``cost_history[-1]``) to one-cent tolerance. If this fails the player
    sees inconsistent numbers and loses trust in the whole debrief.

    The reconciliation works because ``cost_breakdown`` mirrors
    ``engine/costs.py::weekly_cost`` exactly:
        HOLDING_COST * max(0, inventory) + BACKORDER_COST * backlog
    summed over the history tuples == the per-tick sum accumulated into
    ``cost_history``.
    """
    rows = cost_breakdown(canonical_done_state)
    for r in rows:
        ledger = canonical_done_state.stations[r.role.value].cost_history[-1]
        assert r.total == pytest.approx(ledger, abs=0.01), (
            f"{r.role.name}: cost_breakdown total = {r.total:.4f} but engine "
            f"cost_history[-1] = {ledger:.4f}. The decomposition formula has "
            f"drifted from engine/costs.py::weekly_cost."
        )


def test_cost_breakdown_holding_uses_max_zero_inventory(initial_game):
    """The holding formula uses ``max(0, x)`` symbolically. Construct a fake
    StationState with negative inventory entries (impossible in practice but
    matches the formula) and verify the negatives don't contribute to holding.
    """
    # Inject a fake Retailer history with mixed positive/negative inventory.
    fake_retailer = replace(
        initial_game.stations[Role.RETAILER.value],
        inventory_history=(12, 8, -3, 5, -10, 0),
        backlog_history=(0, 0, 3, 0, 10, 0),
        cost_history=(0.0, 0.0, 0.0, 0.0, 0.0, 0.0),  # not under test here
    )
    new_stations = (
        fake_retailer,
        *initial_game.stations[1:],
    )
    fake_state = replace(initial_game, stations=new_stations)

    rows = cost_breakdown(fake_state)
    retailer_row = next(r for r in rows if r.role == Role.RETAILER)
    # Holding should sum only the non-negative inventory values: 12 + 8 + 5 + 0 = 25.
    expected_holding = HOLDING_COST * (12 + 8 + 5 + 0)
    assert retailer_row.holding == pytest.approx(expected_holding, abs=0.01), (
        f"Holding should ignore negative inventories. Expected "
        f"{expected_holding}, got {retailer_row.holding}."
    )
    # Backorder sums all backlog entries: 0 + 0 + 3 + 0 + 10 + 0 = 13.
    expected_backorder = BACKORDER_COST * 13
    assert retailer_row.backorder == pytest.approx(expected_backorder, abs=0.01)
