"""Aggregate metrics over a completed (or in-progress) game.

This module serves two phases:

- **Phase 1 (calibration):** ``peak_orders`` and ``bullwhip_ratio`` provide the
  max-based amplification metric used by ``tests/test_bullwhip_emerges.py``
  (GATE 2). These compute ``max(factory_orders) / max(retailer_orders)`` and
  must keep their existing signatures — load-bearing for the canonical bullwhip
  bounds [2.0, 4.0] at seed=42.

- **Phase 3 (debrief):** ``variance_bullwhip_ratio``, ``per_echelon_amplification``,
  and ``cost_breakdown`` (returning ``CostRow`` instances) power the post-game
  debrief view (DEB-03, DEB-04). These compute population-variance ratios via
  ``statistics.pvariance`` and decompose per-station cumulative cost into
  holding vs backorder components. The cost decomposition mirrors
  ``beergame/engine/costs.py::weekly_cost`` exactly so totals reconcile with
  ``station.cost_history[-1]`` to floating-point tolerance.

All functions are pure derivations from ``GameState`` — no NumPy, no pandas,
no Streamlit, no mutation of input state.
"""
from dataclasses import dataclass
from statistics import pvariance, StatisticsError

from beergame.config.costs import BACKORDER_COST, HOLDING_COST
from beergame.engine.state import GameState, Role


def peak_orders(state: GameState, role: Role) -> int:
    """Max order placed by ``role`` over the game so far."""
    h = state.stations[role.value].orders_placed_history
    return max(h) if h else 0


def bullwhip_ratio(state: GameState) -> float:
    """max(factory orders) / max(retailer orders) — the canonical bullwhip metric."""
    retailer_peak = peak_orders(state, Role.RETAILER)
    factory_peak = peak_orders(state, Role.FACTORY)
    if retailer_peak == 0:
        raise ValueError("retailer never ordered — cannot compute ratio")
    return factory_peak / retailer_peak


@dataclass(frozen=True, slots=True)
class CostRow:
    """One station's cumulative cost decomposed into holding + backorder.

    Invariant: ``total == holding + backorder`` AND ``total`` equals
    ``state.stations[role.value].cost_history[-1]`` to floating-point tolerance.
    Enforced by ``tests/test_metrics_debrief.py::test_cost_breakdown_reconciles_*``.
    """
    role: Role
    holding: float
    backorder: float
    total: float


def variance_bullwhip_ratio(state: GameState) -> float:
    """DEB-03 headline metric: ``pvariance(factory_orders) / pvariance(customer_demand)``.

    Returns 0.0 in three defensive cases (never raises):
    - ``customer_demand_history`` is empty or length-1 (``StatisticsError``)
    - ``orders_placed_history`` at Factory is empty or length-1 (``StatisticsError``)
    - ``pvariance(customer_demand_history) == 0`` (flat-demand scenario — canonical
      step demand has nonzero variance, but a future flat-demand scenario shouldn't crash)

    Uses ``statistics.pvariance`` (POPULATION variance, ddof=0) — we have the
    complete 36-week series, not a sample.
    """
    factory = state.stations[Role.FACTORY.value]
    try:
        denom = pvariance(state.customer_demand_history)
        numer = pvariance(factory.orders_placed_history)
    except StatisticsError:
        return 0.0
    if denom == 0:
        return 0.0
    return numer / denom


def per_echelon_amplification(state: GameState) -> dict[Role, float]:
    """DEB-03 per-station ratios: ``pvariance(role_orders) / pvariance(customer_demand)``.

    Returns a dict keyed by every ``Role`` member (length-4 always). On the
    same defensive cases as ``variance_bullwhip_ratio``, the affected entry is
    ``0.0`` (never raises).

    The canonical bullwhip signature: Retailer's ratio is near 1 (Retailer sees
    customer demand directly), and ratios grow monotonically upstream so that
    Factory's ratio is the largest.
    """
    try:
        denom = pvariance(state.customer_demand_history)
    except StatisticsError:
        return {r: 0.0 for r in Role}
    if denom == 0:
        return {r: 0.0 for r in Role}

    out: dict[Role, float] = {}
    for role in Role:
        s = state.stations[role.value]
        try:
            numer = pvariance(s.orders_placed_history)
        except StatisticsError:
            out[role] = 0.0
            continue
        out[role] = numer / denom
    return out


def cost_breakdown(state: GameState) -> tuple[CostRow, ...]:
    """DEB-04: per-station cumulative cost decomposed into holding + backorder.

    For each ``role in Role`` (RETAILER, WHOLESALER, DISTRIBUTOR, FACTORY):

    - ``holding = HOLDING_COST * sum(max(0, x) for x in inventory_history)``
    - ``backorder = BACKORDER_COST * sum(backlog_history)``
    - ``total = holding + backorder``

    This formula MIRRORS ``engine/costs.py::weekly_cost`` EXACTLY
    (``HOLDING_COST * max(0, station.inventory) + BACKORDER_COST * station.backlog``,
    called per-tick from ``record_state``). Summing the same formula over the
    history tuples must therefore reproduce ``cost_history[-1]`` to floating-point
    tolerance — this is the load-bearing reconciliation invariant tested by
    ``test_cost_breakdown_reconciles_with_engine_cost_history``.

    ``max(0, x)`` is symbolic — Phase 1 invariants keep ``inventory`` non-negative
    in practice — but kept here to match the engine formula 1:1.

    Returns a tuple of 4 ``CostRow`` instances in ``Role`` iteration order.
    """
    rows: list[CostRow] = []
    for role in Role:
        s = state.stations[role.value]
        holding = HOLDING_COST * sum(max(0, x) for x in s.inventory_history)
        backorder = BACKORDER_COST * sum(s.backlog_history)
        total = holding + backorder
        rows.append(CostRow(role=role, holding=holding, backorder=backorder, total=total))
    return tuple(rows)
